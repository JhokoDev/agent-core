import { useEffect, useMemo, useRef } from 'react';
import { AudioLines, Search, Clipboard, ArrowDownToLine, Mic, Headphones, RefreshCw, Activity } from 'lucide-react';
import type { TranscriptEntry, Notify } from '../contracts';
import { transcriptText, downloadTranscript, formatMessageTime } from './format';

export function BrandMark() {
  return <span className="brand-mark" aria-hidden="true"><AudioLines size={19} strokeWidth={2.1} /></span>;
}

export function StatusDot({ tone = 'neutral' }: { tone?: 'neutral' | 'blue' | 'green' | 'red' }) {
  return <span className={`status-dot status-dot--${tone}`} aria-hidden="true" />;
}

export function TranscriptList({ entries, query, emptyText, live = false }: {
  entries: TranscriptEntry[];
  query: string;
  emptyText: string;
  live?: boolean;
}) {
  const endRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const followingRef = useRef(true);
  const filtered = useMemo(() => entries.filter((entry) =>
    entry.text.toLocaleLowerCase('pt-BR').includes(query.toLocaleLowerCase('pt-BR')),
  ), [entries, query]);

  useEffect(() => {
    if (live && !query && followingRef.current) endRef.current?.scrollIntoView({ behavior: 'auto', block: 'nearest' });
  }, [entries, query, live]);

  if (!entries.length) {
    return <div className="empty-transcript"><AudioLines size={24} /><p>{emptyText}</p></div>;
  }
  if (!filtered.length) {
    return <div className="empty-transcript"><Search size={23} /><p>Nenhuma fala corresponde à busca.</p></div>;
  }
  return (
    <div className="transcript-list" ref={listRef} onScroll={() => { const el = listRef.current; if (el) followingRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80; }}>
      {filtered.map((entry) => (
        <div className={`transcript-item transcript-item--${entry.speaker} ${entry.final ? '' : 'transcript-item--partial'}`} key={entry.id}>
          <div className="transcript-avatar" aria-hidden="true">{entry.speaker === 'agent' ? 'H' : 'V'}</div>
          <div className="transcript-content">
            <div className="transcript-meta">
              <strong>{entry.speaker === 'agent' ? 'Harvey' : 'Você'}</strong>
              <time>{formatMessageTime(entry.timestamp)}</time>
              {!entry.final && <span>transcrevendo</span>}
              {entry.interrupted && <span>interrompido</span>}
            </div>
            <p>{entry.text}</p>
          </div>
        </div>
      ))}
      <div ref={endRef} />
      {live && <button className="text-button" onClick={() => { followingRef.current = true; endRef.current?.scrollIntoView({ behavior: 'auto', block: 'nearest' }); }}>Ir para o fim</button>}
    </div>
  );
}

export function TranscriptToolbar({ entries, query, onQuery, room, onNotice }: {
  entries: TranscriptEntry[];
  query: string;
  onQuery: (value: string) => void;
  room: string;
  onNotice: Notify;
}) {
  const hasFinal = entries.some((entry) => entry.final);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(transcriptText(entries));
      onNotice('Transcrição copiada.');
    } catch {
      onNotice('Não foi possível copiar a transcrição.', 'error');
    }
  };
  return (
    <div className="transcript-toolbar">
      <label className="search-field">
        <Search size={16} aria-hidden="true" />
        <input value={query} onChange={(event) => onQuery(event.target.value)} placeholder="Buscar na conversa" aria-label="Buscar na conversa" />
      </label>
      <button className="icon-button" onClick={copy} disabled={!hasFinal} title="Copiar transcrição" aria-label="Copiar transcrição"><Clipboard size={17} /></button>
      <button className="icon-button" onClick={() => downloadTranscript(entries, room)} disabled={!hasFinal} title="Baixar transcrição" aria-label="Baixar transcrição"><ArrowDownToLine size={17} /></button>
    </div>
  );
}

export function DeviceFields({ devices, inputId, outputId, onInput, onOutput, onRefresh, onTest, busy }: {
  devices: MediaDeviceInfo[];
  inputId: string;
  outputId: string;
  onInput: (value: string) => void;
  onOutput: (value: string) => void;
  onRefresh: () => void;
  onTest?: () => void;
  busy?: boolean;
}) {
  const inputs = devices.filter((device) => device.kind === 'audioinput');
  const outputs = devices.filter((device) => device.kind === 'audiooutput');
  return (
    <div className="device-fields">
      <label className="field-label">
        <span><Mic size={16} /> Microfone</span>
        <select value={inputId} onChange={(event) => onInput(event.target.value)}>
          <option value="">Padrão do sistema</option>
          {inputs.map((device, index) => <option value={device.deviceId} key={device.deviceId}>{device.label || `Microfone ${index + 1}`}</option>)}
        </select>
      </label>
      <label className="field-label">
        <span><Headphones size={16} /> Saída de áudio</span>
        <select value={outputId} onChange={(event) => onOutput(event.target.value)} disabled={!outputs.length}>
          <option value="">Padrão do sistema</option>
          {outputs.map((device, index) => <option value={device.deviceId} key={device.deviceId}>{device.label || `Saída ${index + 1}`}</option>)}
        </select>
      </label>
      <div className="device-actions">
        <button className="text-button" onClick={onRefresh}><RefreshCw size={15} /> Atualizar dispositivos</button>
        {onTest && <button className="text-button" onClick={onTest} disabled={busy}><Activity size={15} /> {busy ? 'Testando...' : 'Testar microfone'}</button>}
      </div>
    </div>
  );
}

