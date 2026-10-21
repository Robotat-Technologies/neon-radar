import cytoscape from 'cytoscape'
import { describe, expect, it } from 'vitest'

import { graphStyle } from '@/lib/graph-style'

// Cytoscape computes styles without a canvas in headless mode with styleEnabled.
function styled() {
  return cytoscape({
    headless: true,
    styleEnabled: true,
    style: graphStyle,
    elements: [
      { data: { id: 'syn-a', caption: 'a' }, classes: ['schema-bankaccount', 'synthetic'] },
      { data: { id: 'gbch-co-T0000001', caption: 'b' }, classes: ['schema-company'] },
      {
        data: {
          id: 'e1',
          source: 'syn-a',
          target: 'gbch-co-T0000001',
          type: 'PAID',
          properties: {},
        },
        classes: ['type-paid', 'synthetic'],
      },
      {
        data: {
          id: 'e2',
          source: 'gbch-co-T0000001',
          target: 'syn-a',
          type: 'OWNS',
          properties: {},
        },
        classes: ['type-owns'],
      },
    ],
  })
}

describe('graphStyle', () => {
  it('keeps the dashed outline of a synthetic node while it is in focus', () => {
    const cy = styled()
    cy.nodes().addClass('focus')
    expect(cy.getElementById('syn-a').style('border-style')).toBe('dashed')
    expect(cy.getElementById('gbch-co-T0000001').style('border-style')).toBe('solid')
    expect(cy.getElementById('syn-a').style('border-color')).toBe(
      cy.getElementById('gbch-co-T0000001').style('border-color'),
    )
  })

  it('keeps a synthetic relationship dashed while it is highlighted', () => {
    const cy = styled()
    cy.edges().addClass('highlighted')
    expect(cy.getElementById('e1').style('line-style')).toBe('dashed')
    expect(cy.getElementById('e2').style('line-style')).toBe('solid')
    expect(cy.getElementById('e1').style('width')).toBe('4px')
  })

  it('never sets a dash style in the highlight rules', () => {
    const rules = graphStyle.filter((rule) => /\.(focus|highlighted)\b/.test(rule.selector))
    expect(rules).toHaveLength(2)
    for (const rule of rules) {
      const style = 'style' in rule ? rule.style : rule.css
      expect(Object.keys(style)).not.toContain('border-style')
      expect(Object.keys(style)).not.toContain('line-style')
    }
  })
})
