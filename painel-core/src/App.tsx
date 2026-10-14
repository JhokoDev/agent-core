import { useCallback, useEffect, useRef, useState } from 'react';
import {
  AlertCircle,
  AudioLines,
  ArrowRight,
  Check,
  ChevronRight,
  History,
  Play,
  Settings2,
  StickyNote,
  X,
  Activity,
  BarChart2,
  Power
} from 'lucide-react';
import type { View, ConnectionPhase, ServerStatus, SessionSummary, SessionMetrics, TranscriptEntry, Speaker, NoticeKind } from './contracts';
import NotesPage from './NotesPage';
import SettingsPage from './ui/SettingsPage';
import Archive from './ui/Archive';
import MonitorPanel from './ui/MonitorPanel';
import AnalyticsPanel from './ui/AnalyticsPanel';
import { frontendModules, type FrontendModules } from './composition';
import { Home } from './ui/pages';
import { BrandMark, StatusDot } from './ui/shared';
import { formatSessionDate } from './ui/format';

export default function App({ modules = frontendModules }: { modules?: FrontendModules }) {
  const { api, audioDevices, Conversation, recordEvent } = modules;
  const [route, setRoute] = useState(location.hash);
  const [view, setViewState] = useState<View>(() => {
    const page = location.hash.slice(1).split('/')[0];
    return ['conversation', 'history', 'notes', 'settings', 'monitor', 'analytics'].includes(page) ? page as View : 'conversation';
  });

  const setView = useCallback((next: View) => {
    location.hash = next;
    setViewState(next);
  }, []);

  useEffect(() => {
    const changed = () => {
      setRoute(location.hash);
      const next = location.hash.slice(1).split('/')[0];
      setViewState(['conversation', 'history', 'notes', 'settings', 'monitor', 'analytics'].includes(next) ? next as View : 'conversation');
    };
    window.addEventListener('hashchange', changed);
    return () => window.removeEventListener('hashchange', changed);
  }, []);

  const [status, setStatus] = useState<ServerStatus | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [engineLoading, setEngineLoading] = useState(false);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [sessionsTotal, setSessionsTotal] = useState(0);
  const [selectedRoom, setSelectedRoom] = useState<string | null>(null);
  const [archiveEntries, setArchiveEntries] = useState<TranscriptEntry[]>([]);
  const [archiveMetrics, setArchiveMetrics] = useState<SessionMetrics | null>(null);
  const [archiveLoading, setArchiveLoading] = useState(false);
  const [archiveError, setArchiveError] = useState(false);
  const [sessionsError, setSessionsError] = useState(false);
  const [archiveQuery, setArchiveQuery] = useState('');
  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [livekitUrl, setLivekitUrl] = useState<string | null>(null);
  const [roomName, setRoomName] = useState<string | null>(null);
  const [phase, setPhase] = useState<ConnectionPhase>('idle');
  const [connecting, setConnecting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ message: string; kind: NoticeKind } | null>(null);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [inputId, setInputId] = useState(() => audioDevices.savedInput());
  const [outputId, setOutputId] = useState(() => audioDevices.savedOutput());
  const noticeTimer = useRef<number | null>(null);
  const archiveRequestId = useRef(0);
  const endingRef = useRef(false);
  const currentRoomRef = useRef<string | null>(null);

  const showNotice = useCallback((message: string, kind: NoticeKind = 'success') => {
    setNotice({ message, kind });
    if (noticeTimer.current) window.clearTimeout(noticeTimer.current);
    noticeTimer.current = window.setTimeout(() => setNotice(null), 3500);
  }, []);

  const refreshStatus = useCallback(async () => {
    setLoadingStatus(true);
    try {
      const response = await api.status();
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data: ServerStatus = await response.json();
      setStatus(data);
      recordEvent('status_loaded', data.ok ? 'configured' : 'missing_credentials');
    } catch (error) {
      setStatus({
        ok: false,
        api_available: false,
        livekit_configured: false,
        provider_configured: false,
        provider_name: 'Agent Core',
        model: 'Offline',
        missing_credentials: []
      });
      recordEvent('status_failed', String(error));
    } finally {
      setLoadingStatus(false);
    }
  }, [api, recordEvent]);

  const toggleMotor = async () => {
    setEngineLoading(true);
    try {
      if (status?.ok) {
        await api.stopEngine();
        showNotice('Comando de parada enviado ao motor.', 'info');
      } else {
        await api.startEngine();
        showNotice('Motor acionado em segundo plano.', 'success');
      }
      setTimeout(() => {
        void refreshStatus();
      }, 2000);
    } catch {
      showNotice('Erro ao comunicar com o lançador de sistema.', 'error');
    } finally {
      setEngineLoading(false);
    }
  };

  const refreshSessions = useCallback(async () => {
    try {
      const response = await api.sessions();
      if (!response.ok) throw new Error('sessions_unavailable');
      const data = await response.json();
      setSessions(data.sessions || []);
      setSessionsTotal(data.total ?? data.sessions?.length ?? 0);
      setSessionsError(false);
    } catch {
      setSessionsError(true);
    }
  }, [api]);

  const refreshDevices = useCallback(async () => {
    try {
      if (navigator.mediaDevices) setDevices(await audioDevices.enumerate());
    } catch {}
  }, [audioDevices]);

  const openSession = useCallback(async (room: string) => {
    const requestId = ++archiveRequestId.current;
    currentRoomRef.current = room;
    setSelectedRoom(room);
    setViewState('history');
    if (location.hash !== `#history/${encodeURIComponent(room)}` && location.hash !== `history/${encodeURIComponent(room)}`) {
      location.hash = `history/${encodeURIComponent(room)}`;
    }
    setArchiveQuery('');
    setArchiveLoading(true);
    setArchiveError(false);
    setArchiveEntries([]);
    setArchiveMetrics(null);
    try {
      const [historyResponse, metricsResponse] = await Promise.all([
        api.history(room),
        api.metrics(room),
      ]);
      if (!historyResponse.ok) throw new Error('history_unavailable');
      const history = await historyResponse.json();
      const metrics = metricsResponse.ok ? await metricsResponse.json() : { metrics: null };
      if (requestId !== archiveRequestId.current) return;
      setArchiveEntries((history.history || []).map((item: { speaker: Speaker; text: string; timestamp: number; interrupted?: boolean }, index: number) => ({
        id: `${room}-${index}`,
        speaker: item.speaker,
        text: item.text,
        timestamp: item.timestamp * 1000,
        final: true,
        interrupted: item.interrupted,
      })));
      setArchiveMetrics(metrics.metrics);
    } catch {
      if (requestId !== archiveRequestId.current) return;
      setArchiveEntries([]);
      setArchiveMetrics(null);
      setArchiveError(true);
      showNotice('Não foi possível carregar esta conversa.', 'error');
    } finally {
      if (requestId === archiveRequestId.current) setArchiveLoading(false);
    }
  }, [api, showNotice]);

  useEffect(() => {
    let room: string | null = null;
    try {
      room = location.hash.startsWith('#history/') ? decodeURIComponent(location.hash.slice(9)) : null;
    } catch {}
    if (room && room !== currentRoomRef.current) void openSession(room);
  }, [route, openSession]);

  useEffect(() => {
    document.documentElement.dataset.transcriptSize = localStorage.getItem('harvey-transcript-size') || 'normal';
    void refreshStatus();
    void refreshSessions();
    void refreshDevices();
    const deviceChange = () => void refreshDevices();
    navigator.mediaDevices?.addEventListener?.('devicechange', deviceChange);
    const onError = (event: ErrorEvent) => recordEvent('browser_error', event.message);
    const onRejection = (event: PromiseRejectionEvent) => recordEvent('browser_error', String(event.reason));
    window.addEventListener('error', onError);
    window.addEventListener('unhandledrejection', onRejection);
    return () => {
      navigator.mediaDevices?.removeEventListener?.('devicechange', deviceChange);
      window.removeEventListener('error', onError);
      window.removeEventListener('unhandledrejection', onRejection);
      if (noticeTimer.current) window.clearTimeout(noticeTimer.current);
    };
  }, [refreshStatus, refreshSessions, refreshDevices, recordEvent]);

  const saveInput = (value: string) => { setInputId(value); audioDevices.saveInput(value); };
  const saveOutput = (value: string) => { setOutputId(value); audioDevices.saveOutput(value); };

  const startConversation = async () => {
    if (connecting || sessionToken) return;
    endingRef.current = false;
    setConnecting(true);
    setErrorMessage(null);

    try {
      const response = await api.token();
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setSessionToken(data.token);
      setLivekitUrl(data.url);
      setRoomName(data.room);
      setPhase('connected');
      setView('conversation');
      recordEvent('token_issued', '', data.room);
    } catch (error) {
      recordEvent('token_failed', String(error));
      setErrorMessage('Não foi possível iniciar a sessão local. Verifique o servidor Agent Core.');
    } finally {
      setConnecting(false);
    }
  };

  const endConversation = useCallback(() => {
    if (endingRef.current) return;
    endingRef.current = true;
    const endedRoom = roomName;
    setSessionToken(null);
    setLivekitUrl(null);
    setRoomName(null);
    setPhase('idle');
    void refreshSessions();
    if (endedRoom) {
      window.setTimeout(() => {
        void refreshSessions();
        void openSession(endedRoom);
      }, 850);
    }
  }, [roomName, refreshSessions, openSession]);

  const topStatus = phase === 'connected' ? { label: 'Em Conversa', tone: 'green' as const } :
    phase === 'connecting' ? { label: 'Conectando', tone: 'blue' as const } :
    status?.ok ? { label: 'Motor Online', tone: 'green' as const } :
    { label: loadingStatus ? 'Verificando' : 'Motor Offline', tone: loadingStatus ? 'blue' as const : 'red' as const };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <BrandMark />
          <div>
            <strong>Agent Core</strong>
            <span>IA AUTÔNOMA LOCAL</span>
          </div>
        </div>

        <button
          className="sidebar-new"
          onClick={() => { setView('conversation'); if (!sessionToken) void startConversation(); }}
          disabled={connecting || Boolean(sessionToken)}
        >
          <Play size={15} fill="currentColor" /> Novo Chat de Voz <ArrowRight size={15} />
        </button>

        <nav className="sidebar-nav" aria-label="Navegação principal">
          <button
            aria-current={view === 'conversation' ? 'page' : undefined}
            className={view === 'conversation' ? 'nav-active' : ''}
            onClick={() => {
              setView('conversation');
              if (!sessionToken && status?.ok) void startConversation();
            }}
          >
            <AudioLines size={18} /> Chat de Voz {sessionToken && <span className="nav-live" />}
          </button>
          <button
            aria-current={view === 'history' ? 'page' : undefined}
            className={view === 'history' ? 'nav-active' : ''}
            onClick={() => { if (selectedRoom) void openSession(selectedRoom); else if (sessions[0]) void openSession(sessions[0].room); else setView('history'); }}
          >
            <History size={18} /> Histórico
          </button>
          <button
            aria-current={view === 'notes' ? 'page' : undefined}
            className={view === 'notes' ? 'nav-active' : ''}
            onClick={() => setView('notes')}
          >
            <StickyNote size={18} /> Notas
          </button>
          <button
            aria-current={view === 'monitor' ? 'page' : undefined}
            className={view === 'monitor' ? 'nav-active' : ''}
            onClick={() => setView('monitor')}
          >
            <Activity size={18} /> Monitoramento
          </button>
          <button
            aria-current={view === 'analytics' ? 'page' : undefined}
            className={view === 'analytics' ? 'nav-active' : ''}
            onClick={() => setView('analytics')}
          >
            <BarChart2 size={18} /> Analytics
          </button>
          <button
            aria-current={view === 'settings' ? 'page' : undefined}
            className={view === 'settings' ? 'nav-active' : ''}
            onClick={() => setView('settings')}
          >
            <Settings2 size={18} /> Configurações
          </button>
        </nav>

        <div className="sidebar-recent">
          <div className="sidebar-label">RECENTES <span>{sessionsTotal}</span></div>
          {sessions.slice(0, 4).map((session) => (
            <button key={session.room} onClick={() => void openSession(session.room)}>
              <span className="recent-line" />
              <span>{session.title || formatSessionDate(session.started_at)}</span>
            </button>
          ))}
          {!sessions.length && <p>Nenhuma conversa ainda</p>}
        </div>

        <div className="sidebar-bottom">
          <div style={{ padding: '0 11px 16px' }}>
            <button
              onClick={toggleMotor}
              disabled={engineLoading}
              style={{
                width: '100%',
                height: '36px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                background: status?.ok ? '#fa4d56' : '#24a148',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'opacity 0.2s'
              }}
            >
              <Power size={14} />
              {engineLoading ? 'Processando...' : status?.ok ? 'PARAR MOTOR' : 'INICIAR MOTOR'}
            </button>
          </div>

          <div className="sidebar-status">
            <StatusDot tone={topStatus.tone} />
            <div>
              <strong>{topStatus.label}</strong>
              <span>{status?.model || 'Ollama Local'}</span>
            </div>
          </div>
          <div className="sidebar-footer">INFERÊNCIA LOCAL · PRIVACIDADE TOTAL</div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="topbar-path">
            <span>AGENT CORE</span>
            <ChevronRight size={14} />
            <strong>
              {view === 'conversation' ? 'Chat de Voz' :
               view === 'history' ? 'Histórico' :
               view === 'notes' ? 'Notas' :
               view === 'monitor' ? 'Monitoramento' :
               view === 'analytics' ? 'Analytics' : 'Configurações'}
            </strong>
          </div>
          <div className="topbar-right">
            <div className="topbar-status">
              <StatusDot tone={topStatus.tone} /> {topStatus.label}
            </div>
          </div>
        </header>

        <div className="page-content">
          {errorMessage && (
            <div className="error-banner" role="alert">
              <AlertCircle size={19} />
              <span>{errorMessage}</span>
              <button onClick={() => setErrorMessage(null)} aria-label="Fechar aviso"><X size={16} /></button>
            </div>
          )}

          {sessionToken && roomName && (
            <Conversation
              recordEvent={recordEvent}
              api={api}
              serverUrl={livekitUrl || 'http://127.0.0.1:8000'}
              token={sessionToken}
              roomName={roomName}
              connected={phase === 'connected'}
              visible={view === 'conversation'}
              devices={devices}
              inputId={inputId}
              outputId={outputId}
              onInput={saveInput}
              onOutput={saveOutput}
              onRefreshDevices={() => void refreshDevices()}
              onEnd={endConversation}
              onReturn={() => setView('conversation')}
              onNotice={showNotice}
              onConnected={() => { setPhase('connected'); recordEvent('room_connected', '', roomName); }}
              onDisconnected={() => { recordEvent('room_disconnected', '', roomName); endConversation(); }}
              onError={(error) => { recordEvent('room_error', error.message, roomName); setErrorMessage(`Falha na conexão: ${error.message}`); }}
              onMediaDeviceFailure={(failure, kind) => recordEvent('microphone_failed', `${kind}:${failure}`, roomName)}
            />
          )}

          {view === 'conversation' && !sessionToken && (
            <Home
              status={status}
              loading={loadingStatus}
              connecting={connecting}
              sessions={sessions}
              total={sessionsTotal}
              onStart={() => void startConversation()}
              onOpenSession={(room) => void openSession(room)}
              onRetry={() => void refreshStatus()}
            />
          )}

          {sessionsError && (view === 'history' || view === 'conversation') && (
            <div className="error-banner" role="alert">
              Não foi possível carregar o histórico.{' '}
              <button className="text-button" onClick={() => void refreshSessions()}>Tentar novamente</button>
            </div>
          )}

          {view === 'history' && (
            <Archive
              api={api}
              onChanged={() => void refreshSessions()}
              onDeleted={() => {
                archiveRequestId.current++;
                currentRoomRef.current = null;
                setSelectedRoom(null);
                setArchiveEntries([]);
                setArchiveMetrics(null);
                setArchiveError(false);
                setView('history');
                void refreshSessions();
              }}
              error={archiveError}
              selectedRoom={selectedRoom}
              entries={archiveEntries}
              metrics={archiveMetrics}
              loading={archiveLoading}
              query={archiveQuery}
              onQuery={setArchiveQuery}
              onSelect={(room) => void openSession(room)}
              onNotice={showNotice}
            />
          )}

          {view === 'notes' && <NotesPage api={api} onNotice={showNotice} />}

          {view === 'monitor' && <MonitorPanel api={api} />}

          {view === 'analytics' && <AnalyticsPanel api={api} />}

          {view === 'settings' && (
            <SettingsPage
              api={api}
              audioDevices={audioDevices}
              onNotice={showNotice}
              status={status}
              devices={devices}
              inputId={inputId}
              outputId={outputId}
              onInput={saveInput}
              onOutput={saveOutput}
              onRefresh={() => void refreshDevices()}
              onRetry={() => void refreshStatus()}
            />
          )}
        </div>

        <footer className="app-footer">
          <span>Agent Core</span>
          <span>IA Autônoma &middot; Controle Local &middot; Privacidade</span>
        </footer>
      </main>

      {notice && (
        <div className={`toast toast--${notice.kind}`} role={notice.kind === 'error' ? 'alert' : 'status'}>
          {notice.kind === 'error' ? <AlertCircle size={17} /> : notice.kind === 'info' ? <AudioLines size={17} /> : <Check size={17} />}{' '}
          {notice.message}
        </div>
      )}
    </div>
  );
}
