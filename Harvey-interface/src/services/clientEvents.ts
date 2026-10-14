import type { ClientEvent } from '../contracts';

export function recordClientEvent(event: ClientEvent, message = '', room?: string) {
  void fetch('/api/client-events', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ event, message: message.slice(0, 500), room }),
    keepalive: true,
  }).catch(() => {});
}

