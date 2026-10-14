import { AlertCircle, ArrowRight, ChevronRight, History, Play, RefreshCw } from 'lucide-react';
import type { ServerStatus, SessionSummary } from '../contracts';
import { StatusDot } from './shared';
import { formatSessionDate } from './session';

export function Home({ status, loading, connecting, sessions, total, onStart, onOpenSession, onRetry }: {
  status: ServerStatus | null;
  loading: boolean;
  connecting: boolean;
  sessions: SessionSummary[];
  total: number;
  onStart: () => void;
  onOpenSession: (room: string) => void;
  onRetry: () => void;
}) {
  const ready = Boolean(status?.ok);
  return (
    <section className="home-layout">
      <div className="home-main">
        <div className="section-heading">
          <div>
            <p className="eyebrow">AMPLIFICADOR DE PRODUTIVIDADE</p>
            <h1>Chat de Voz com IA</h1>
          </div>
        </div>
        <div className="home-hero">
          <div className="hero-copy">
            <span className="hero-kicker">
              <StatusDot tone={ready ? 'green' : 'red'} />{' '}
              {loading ? 'Verificando serviços' : ready ? `Motor Online (${status?.model || 'Ollama'})` : 'Motor Offline (Clique em Iniciar Motor)'}
            </span>
            <h2>Agent Core Voice</h2>
            <p>
              Sala de áudio interativa com transcrição Whisper, síntese de fala (TTS) e ferramentas autônomas locais.
              Converse naturalmente por voz ou texto com privacidade total como no Harvey.
            </p>
          </div>
          
          <div className="hero-bottom">
            <button className="primary-button" onClick={onStart} disabled={loading || connecting}>
              {connecting ? <RefreshCw className="spin" size={18} /> : <Play size={18} fill="currentColor" />}
              {connecting ? 'Iniciando sala...' : 'Iniciar Chat de Voz'}
              <ArrowRight size={17} />
            </button>
            <span>Áudio em tempo real · Transcrição Whisper · Síntese de voz</span>
          </div>
        </div>

        {!ready && !loading && (
          <div className="notice-card">
            <AlertCircle size={19} />
            <div>
              <strong>Motor de IA Offline</strong>
              <p>O serviço da porta 8000 não está respondendo. Inicie o motor pelo botão na barra lateral ou ligue o servidor.</p>
            </div>
            <button className="text-button" onClick={onRetry}>
              <RefreshCw size={15} /> Verificar
            </button>
          </div>
        )}

        <div className="home-section-heading">
          <div>
            <p className="eyebrow">RECENTES</p>
            <h2>Conversas recentes</h2>
          </div>
          <span>{sessions.length ? `${total} salvas` : 'Ainda sem conversas'}</span>
        </div>
        <div className="recent-grid">
          {sessions.slice(0, 4).map((session) => (
            <button className="recent-card" key={session.room} onClick={() => onOpenSession(session.room)}>
              <div className="recent-icon">
                <History size={20} />
              </div>
              <div>
                <strong>{session.title || `Conversa de ${formatSessionDate(session.started_at)}`}</strong>
                <span>ID: {session.room.slice(0, 18)}...</span>
              </div>
              <ChevronRight size={18} />
            </button>
          ))}
          {!sessions.length && (
            <div className="recent-empty">Suas conversas aparecerão aqui depois da primeira sessão.</div>
          )}
        </div>
      </div>
      <aside className="home-aside">
        <div className="aside-tip">
          <span>ATALHO RÁPIDO</span>
          <p>Durante a conversa, pressione a tecla <kbd>M</kbd> para acionar o microfone Whisper.</p>
        </div>
        <div className="aside-tip" style={{ marginTop: '16px' }}>
          <span>DISPOSITIVOS LOCAIS</span>
          <p>Controle de tela, aplicativos Windows e automações web podem ser autorizados em Configurações.</p>
        </div>
      </aside>
    </section>
  );
}
