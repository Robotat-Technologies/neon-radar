import { beforeEach, describe, expect, it, vi } from 'vitest'

const toast = vi.hoisted(() => {
  const show = () => vi.fn<(message: string, data?: object) => string>()
  const dismiss = vi.fn<(id?: string) => void>()
  return { success: show(), info: show(), warning: show(), error: show(), dismiss }
})
vi.mock('vue-sonner', () => ({ toast }))

import { dismissNotification, notify, type UiSeverity } from '@/lib/notifications'

describe('notifications', () => {
  beforeEach(() => vi.clearAllMocks())

  it.each([
    ['success', 5000],
    ['info', 5000],
    ['warning', Number.POSITIVE_INFINITY],
    ['error', Number.POSITIVE_INFINITY],
  ] as [UiSeverity, number][])('shows %s for %s ms by default', (severity, duration) => {
    const id = notify({ severity, message: 'Done.', description: 'More.' })

    expect(toast[severity]).toHaveBeenCalledWith('Done.', { id, description: 'More.', duration })
  })

  it('gives every notification a fresh id; a dedupe key dismisses the earlier one', () => {
    const first = notify({ severity: 'info', message: 'One' })
    const keyed = notify({ severity: 'error', message: 'Two', dedupeKey: 'download' })
    const again = notify({ severity: 'info', message: 'Three', dedupeKey: 'download' })

    expect(new Set([first, keyed, again]).size).toBe(3)
    expect(toast.dismiss).toHaveBeenCalledExactlyOnceWith(keyed)
  })

  it('dismisses by id', () => {
    const id = notify({ severity: 'warning', message: 'Careful' })
    dismissNotification(id)

    expect(toast.dismiss).toHaveBeenCalledWith(id)
  })
})
