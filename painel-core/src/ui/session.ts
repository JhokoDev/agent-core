import type { SessionSummary } from '../contracts';
export { formatSessionDate } from './format';

export function sessionStatus(session: SessionSummary | undefined) {
  if (!session) return 'Carregando';
  if (['worker_lost', 'failed', 'job_shutdown'].includes(session.end_reason || '')) return 'Interrompida';
  return session.ended_at ? 'Encerrada' : 'Em andamento';
}

