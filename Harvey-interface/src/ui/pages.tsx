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
        <div className="section-heading"><div><p className="eyebrow">SEU ESPAÇO DE VOZ</p><h1>Conversa</h1></div></div>
        <div className="home-hero">
          <div className="hero-copy"><span className="hero-kicker"><StatusDot tone={ready ? 'green' : 'red'} /> {loading ? 'Verificando serviços' : ready ? 'Credenciais configuradas' : 'Configuração necessária'}</span><h2>Converse com o Harvey</h2><p>Inicie uma chamada de voz. As transcrições e notas ficam salvas neste computador; o áudio é processado na nuvem.</p></div>
          
          <div className="hero-bottom"><button className="primary-button" onClick={onStart} disabled={!ready || loading || connecting}>{connecting ? <RefreshCw className="spin" size={18} /> : <Play size={18} fill="currentColor" />}{connecting ? 'Iniciando conversa' : 'Iniciar conversa'}<ArrowRight size={17} /></button><span>Microfone necessário · Sem vídeo</span></div>
        </div>
        {!ready && !loading && <div className="notice-card"><AlertCircle size={19} /><div><strong>{status?.api_available ? 'Credenciais pendentes' : 'API não alcançada'}</strong><p>{status?.missing_credentials?.length ? `Verifique: ${status.missing_credentials.join(', ')} no arquivo .env.` : 'Não foi possível alcançar o servidor local.'}</p></div><button className="text-button" onClick={onRetry}><RefreshCw size={15} /> Verificar</button></div>}
        <div className="home-section-heading"><div><p className="eyebrow">RECENTES</p><h2>Conversas recentes</h2></div><span>{sessions.length ? `${total} salvas` : 'Ainda sem conversas'}</span></div>
        <div className="recent-grid">
          {sessions.slice(0, 3).map((session) => <button className="recent-card" key={session.room} onClick={() => onOpenSession(session.room)}><div className="recent-icon"><History size={20} /></div><div><strong>{session.title || `Conversa de ${formatSessionDate(session.started_at)}`}</strong><span>{session.message_count} {session.message_count === 1 ? 'mensagem' : 'mensagens'} · {session.ended_at ? 'Encerrada' : 'Sem encerramento'}</span></div><ChevronRight size={18} /></button>)}
          {!sessions.length && <div className="recent-empty">Suas conversas aparecerão aqui depois da primeira sessão.</div>}
        </div>
      </div>
      <aside className="home-aside"><div className="aside-tip"><span>ATALHO RÁPIDO</span><p>Durante uma conversa, pressione <kbd>M</kbd> para ligar ou desligar o microfone.</p></div></aside>
    </section>
  );
}

