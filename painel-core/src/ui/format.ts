import type { TranscriptEntry } from '../contracts';

export function formatClock(seconds: number) {
  const total = Math.max(0, Math.floor(seconds));
  return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`;
}

export function formatSessionDate(timestamp: number) {
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  }).format(new Date(timestamp * 1000));
}

export function formatMessageTime(timestamp: number) {
  return new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit' }).format(new Date(timestamp));
}

export function transcriptText(entries: TranscriptEntry[]) {
  return entries.filter((entry) => entry.final).map((entry) => {
    let out = `[${formatMessageTime(entry.timestamp)}] ${entry.speaker === 'user' ? 'Você' : 'Agent Core'}${entry.interrupted ? ' (interrompido)' : ''}:`;
    if (entry.reasoning) {
      out += `\n[Linha de Raciocínio]\n${entry.reasoning.trim()}\n`;
    }
    out += `\n${entry.text}`;
    return out;
  }).join('\n\n');
}

export function downloadTranscript(entries: TranscriptEntry[], room: string) {
  const text = transcriptText(entries);
  if (!text) return;
  const blob = new Blob([`Agent Core · ${room}\n\n${text}\n`], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `agent-core-${room}.txt`;
  link.click();
  URL.revokeObjectURL(url);
}

