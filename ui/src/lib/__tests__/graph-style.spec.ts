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
        classes: ['type-paid', 'family-money', 'synthetic'],
      },
      {
        data: {
          id: 'e2',
          source: 'gbch-co-T0000001',
          target: 'syn-a',
          type: 'OWNS',
          properties: {},
        },
        classes: ['type-owns', 'family-ownership'],
      },
      {
        data: {
          id: 'gbch-co-T0000001|psa|syn-a',
          source: 'gbch-co-T0000001',
          target: 'syn-a',
          type: 'POSSIBLY_SAME_AS',
          properties: {},
        },
        classes: ['type-possibly_same_as', 'family-match'],
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

  it('gives each relationship family its own colour, line and marker', () => {
    const cy = styled()
    const paid = cy.getElementById('e1')
    const owns = cy.getElementById('e2')
    expect(paid.style('line-color')).toBe('rgb(15,118,110)')
    expect(paid.style('line-style')).toBe('solid')
    expect(owns.style('line-outline-color')).toBe('rgb(29,78,216)')
    expect(owns.style('target-arrow-fill')).toBe('hollow')
  })

  it('draws the alert path above the family style and keeps its dash', () => {
    const cy = styled()
    cy.edges().addClass('alert-path')
    expect(cy.getElementById('e1').style('width')).toBe('4.5px')
    expect(cy.getElementById('e1').style('z-index')).toBe('10')
    expect(cy.getElementById('gbch-co-T0000001|psa|syn-a').style('line-style')).toBe('dashed')
    cy.getElementById('e1').addClass('highlighted')
    expect(cy.getElementById('e1').style('width')).toBe('8px')
  })

  it('shows text only on elements the zoom rule switched on', () => {
    const cy = styled()
    const paid = cy.getElementById('e1')
    expect(paid.style('label')).toBe('')
    paid.data('properties', { amount: 10, currency: 'EUR' }).addClass('label-on')
    expect(paid.style('label')).toBe('EUR 10.00')
    paid.data('step', 2)
    cy.style().update()
    expect(paid.style('label')).toBe('Step 2: EUR 10.00')
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
