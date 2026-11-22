// Export the complete alert detail without another API request. CSV uses one field per row
// so nodes, relationships and nested provenance remain readable in a spreadsheet.
import type { AlertDetail } from '@/api/types'

type Cell = string | number | boolean | null

function csvCell(value: Cell): string {
  let text = value === null ? 'null' : String(value)
  // Spreadsheet applications may execute cells beginning with a formula, including after
  // whitespace. Prefix untrusted strings only; negative numeric values remain numbers.
  if (typeof value === 'string' && (/^\s*[=+\-@]/.test(value) || /^[\t\r]/.test(value))) {
    text = `'${text}`
  }
  return `"${text.replace(/"/g, '""')}"`
}

export function evidenceCsv(detail: AlertDetail): string {
  const rows: Cell[][] = [['Section', 'Item', 'Field', 'Value']]

  function add(section: string, item: string, path: string, value: unknown): void {
    if (Array.isArray(value)) {
      if (value.length === 0) rows.push([section, item, path, '[]'])
      else value.forEach((entry, index) => add(section, item, `${path}[${index + 1}]`, entry))
    } else if (value !== null && typeof value === 'object') {
      const entries = Object.entries(value)
      if (entries.length === 0) rows.push([section, item, path, '{}'])
      else
        entries.forEach(([key, entry]) => add(section, item, path ? `${path}.${key}` : key, entry))
    } else {
      rows.push([section, item, path, value as Cell])
    }
  }

  add('Alert', detail.alert.alert_id, '', detail.alert)
  const { nodes, edges, ...graph } = detail.evidence
  add('Graph', 'Evidence graph', '', graph)
  if (nodes.length === 0) rows.push(['Nodes', '', '', '[]'])
  nodes.forEach((node) => add('Node', node.id, '', node))
  if (edges.length === 0) rows.push(['Relationships', '', '', '[]'])
  edges.forEach((edge) => add('Relationship', edge.id, '', edge))

  // BOM helps spreadsheet software recognize UTF-8; CRLF follows the CSV convention.
  return `﻿${rows.map((row) => row.map(csvCell).join(',')).join('\r\n')}\r\n`
}

export function downloadEvidence(detail: AlertDetail, format: 'json' | 'csv'): void {
  const content = format === 'json' ? `${JSON.stringify(detail, null, 2)}\n` : evidenceCsv(detail)
  const type = format === 'json' ? 'application/json' : 'text/csv;charset=utf-8'
  const url = URL.createObjectURL(new Blob([content], { type }))
  const link = document.createElement('a')
  // An identifier is data, not a trusted file path.
  const safeId = detail.alert.alert_id.replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 100) || 'alert'
  link.href = url
  link.download = `${safeId}-evidence.${format}`
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
