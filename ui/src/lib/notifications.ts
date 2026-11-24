// Interface feedback (toasts) through one small facade over vue-sonner, which owns the queue,
// the timing and the dismissal. Callers pass plain text: never raw errors, payloads or traces.
import { toast } from 'vue-sonner'

export type UiSeverity = 'success' | 'error' | 'warning' | 'info'

export interface UiNotification {
  severity: UiSeverity
  message: string
  description?: string
  /** A new notification with the same key replaces (dismisses) the one shown under it. */
  dedupeKey?: string
}

/** Success and info close after five seconds; warnings and errors stay until dismissed. */
export const DEFAULT_DURATION_MS: Record<UiSeverity, number> = {
  success: 5000,
  info: 5000,
  warning: Number.POSITIVE_INFINITY,
  error: Number.POSITIVE_INFINITY,
}

let counter = 0
// Fresh ids: vue-sonner keeps a reused id's old timer, so a key dismisses its previous toast.
const activeByKey = new Map<string, string>()

/** Shows a notification and returns its id. */
export function notify(notification: UiNotification): string {
  const id = `nr-${++counter}`
  const previous = notification.dedupeKey && activeByKey.get(notification.dedupeKey)
  if (previous) toast.dismiss(previous)
  if (notification.dedupeKey) activeByKey.set(notification.dedupeKey, id)
  toast[notification.severity](notification.message, {
    id,
    description: notification.description,
    duration: DEFAULT_DURATION_MS[notification.severity],
  })
  return id
}

export function dismissNotification(id: string): void {
  toast.dismiss(id)
}
