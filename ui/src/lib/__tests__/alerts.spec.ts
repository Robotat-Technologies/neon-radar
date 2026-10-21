import { describe, expect, it } from 'vitest'

import { readExample } from '@/__tests__/fixtures'
import type { Alert } from '@/api/types'
import { alertDataLabel, SYNTHETIC_ACTIVITY_TEXT } from '@/lib/alerts'

describe('alertDataLabel', () => {
  it('labels an alert among synthetic entities only as synthetic', () => {
    const example = readExample<Alert>('c4/circular_flow.json')
    expect(alertDataLabel(example.data_flags)).toEqual({ kind: 'synthetic' })
  })

  it('says a pattern next to a real entity lies in synthetic background activity', () => {
    expect(alertDataLabel({ involves_real_entities: true, synthetic_activity: true })).toEqual({
      kind: 'synthetic_activity',
      text: SYNTHETIC_ACTIVITY_TEXT,
    })
  })

  it('adds nothing when real entities and real relationships are involved', () => {
    expect(alertDataLabel({ involves_real_entities: true, synthetic_activity: false })).toEqual({
      kind: 'none',
    })
  })
})
