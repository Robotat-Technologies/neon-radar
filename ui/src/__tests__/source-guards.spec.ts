// Guards over the UI's own source: CSS logical properties only (RTL-ready), no wording that
// 7.1 forbids, and no address of another host (guardrail G3).
import { readdirSync, readFileSync } from 'node:fs'
import { join, relative } from 'node:path'
import { describe, expect, it } from 'vitest'

import { readRepoText, UI_ROOT } from './fixtures'

const GENERATED = new Set(['src/api/schema.d.ts'])

function sourceFiles(): string[] {
  const found: string[] = []
  const walk = (dir: string) => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const path = join(dir, entry.name)
      if (entry.isDirectory()) {
        if (entry.name !== '__tests__') walk(path)
      } else if (/\.(vue|ts|css)$/.test(entry.name)) {
        const rel = relative(UI_ROOT, path)
        if (!GENERATED.has(rel)) found.push(rel)
      }
    }
  }
  walk(join(UI_ROOT, 'src'))
  return [...found, 'index.html'].sort()
}

function read(rel: string): string {
  return readFileSync(join(UI_ROOT, rel), 'utf-8')
}

/** The CSS in a file: a .css file, or the <style> blocks and style attributes of a .vue file. */
function cssOf(rel: string): string {
  const text = read(rel)
  if (rel.endsWith('.css')) return text
  if (!rel.endsWith('.vue')) return ''
  const blocks = [...text.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)].map((m) => m[1])
  const attributes = [...text.matchAll(/\sstyle="([^"]*)"/g)].map((m) => m[1])
  return [...blocks, ...attributes].join('\n')
}

const PHYSICAL = [
  /(?<![-\w])(?:margin|padding|border)-(?:left|right|top|bottom)\b/,
  /(?<![-\w])(?:left|right|top|bottom)\s*:/,
  /(?<![-\w])(?:min-|max-)?(?:width|height)\s*:/,
  /\b(?:text-align|float|clear)\s*:\s*(?:left|right)\b/,
]

describe('UI source guards', () => {
  const files = sourceFiles()

  it('finds the source files', () => {
    expect(files).toContain('src/App.vue')
    expect(files).toContain('src/assets/main.css')
  })

  it('uses CSS logical properties only', () => {
    const offences = files.flatMap((rel) =>
      cssOf(rel)
        .replace(/\/\*[\s\S]*?\*\//g, '')
        .split('\n')
        .filter((line) => PHYSICAL.some((pattern) => pattern.test(line)))
        .map((line) => `${rel}: ${line.trim()}`),
    )
    expect(offences).toEqual([])
  })

  it('never uses a term from contracts/wording/forbidden-terms.txt', () => {
    const patterns = readRepoText('contracts/wording/forbidden-terms.txt')
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith('#'))
      .map((line) => new RegExp(line, 'i'))
    expect(patterns.length).toBeGreaterThan(20)

    const offences = files.flatMap((rel) =>
      read(rel)
        .split('\n')
        .filter((line) => patterns.some((pattern) => pattern.test(line)))
        .map((line) => `${rel}: ${line.trim()}`),
    )
    expect(offences).toEqual([])
  })

  it('names no other host: the browser only talks to its own origin', () => {
    const offences = files.flatMap((rel) =>
      read(rel)
        .split('\n')
        .filter(
          (line) => /\b(?:https?|wss?):\/\//i.test(line) || /\/\/[\w-]+\.[\w.-]+\//.test(line),
        )
        .map((line) => `${rel}: ${line.trim()}`),
    )
    expect(offences).toEqual([])
  })
})
