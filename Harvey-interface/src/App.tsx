import { useCallback, useEffect, useRef, useState } from 'react';
import { AlertCircle, AudioLines, ArrowRight, Check, ChevronRight, History, Play, Settings2, StickyNote, X } from 'lucide-react';
import type { View, ConnectionPhase, ServerStatus, SessionSummary, SessionMetrics, TranscriptEntry, Speaker, NoticeKind } from './contracts';
import NotesPage from './NotesPage';
import SettingsPage from './ui/SettingsPage';
import Archive from './ui/Archive';
import { frontendModules, type FrontendModules } from './composition';
import { Home } from './ui/pages';
import { BrandMark, StatusDot } from './ui/shared';
import { formatSessionDate } from './ui/format';
import DesktopStatus from './ui/DesktopStatus';

export default function App({ modules = frontendModules }: { modules?: FrontendModules }) {
  const { api, audioDevices, Conversation, recordEvent } = modules;
  const [route,setRoute]=useState(location.hash);
  const [view, setViewState] = useState<View>(() => {
    const page = location.hash.slice(1).split('/')[0];
    return ['conversation', 'history', 'notes', 'settings'].includes(page) ? page as View : 'conversation';
  });
  const setView = useCallback((next: View) => { location.hash = next; setViewState(next); }, []);
  useEffect(() => {
    const changed = () => { setRoute(location.hash); const next = location.hash.slice(1).split('/')[0]; setViewState(['conversation', 'history', 'notes', 'settings'].includes(next) ? next as View : 'conversation'); };
    window.addEventListener('hashchange', changed);
    return () => window.removeEventListener('hashchange', changed);
  }, []);
  const [status, setStatus] = useState<ServerStatus | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [sessionsTotal,setSessionsTotal]=useState(0);
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
  const [notice, setNotice] = useState<{message: string; kind: NoticeKind} | null>(null);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [inputId, setInputId] = useState(() => audioDevices.savedInput());
  const [outputId, setOutputId] = useState(() => audioDevices.savedOutput());
  const noticeTimer = useRef<number | null>(null);
  const archiveRequestId = useRef(0);
  const endingRef = useRef(false);

  const showNotice = useCallback((message: string, kind: NoticeKind = 'success') => {
    setNotice({message, kind});
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
      setStatus({ ok: false, api_available: false, livekit_configured: false, provider_configured: false, provider_name: 'Provedor de voz', model: '—', missing_credentials: [] });
      recordEvent('status_failed', String(error));
    } finally { setLoadingStatus(false); }
  }, [api, recordEvent]);

  const refreshSessions = useCallback(async () => {
    try {
      const response = await api.sessions();
      if (!response.ok) throw new Error('sessions_unavailable');
      const data = await response.json();
      setSessions(data.sessions || []);
      setSessionsTotal(data.total ?? data.sessions?.length ?? 0);
      setSessionsError(false);
    } catch { setSessionsError(true); }
  }, [api, recordEvent]);

  const refreshDevices = useCallback(async () => {
    try {
      if (navigator.mediaDevices) setDevices(await audioDevices.enumerate());
    } catch { /* Alguns navegadores só listam dispositivos após a permissão. */ }
  }, [audioDevices]);

  const openSession = useCallback(async (room: string) => {
    const requestId = ++archiveRequestId.current;
    setSelectedRoom(room);
    setViewState('history');
    location.hash = `history/${encodeURIComponent(room)}`;
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
        id: `${room}-${index}`, speaker: item.speaker, text: item.text,
        timestamp: item.timestamp * 1000, final: true, interrupted: item.interrupted,
      })));
      setArchiveMetrics(metrics.metrics);
    } catch {
      if (requestId !== archiveRequestId.current) return;
      setArchiveEntries([]);
      setArchiveMetrics(null);
      setArchiveError(true);
      showNotice('Não foi possível carregar esta conversa.', 'error');
    } finally { if (requestId === archiveRequestId.current) setArchiveLoading(false); }
  }, [api, showNotice]);

  useEffect(() => {
    let room: string | null = null;
    try { room = location.hash.startsWith('#history/') ? decodeURIComponent(location.hash.slice(9)) : null; } catch { /* URL inválida preserva a seleção. */ }
    if (room && room !== selectedRoom) void openSession(room);
  }, [route, selectedRoom, openSession]);

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
      const stream = await audioDevices.acquire(inputId);
      stream.getTracks().forEach((track) => track.stop());
      recordEvent('microphone_granted');
      await refreshDevices();
    } catch (error) {
      recordEvent('microphone_failed', String(error));
      setErrorMessage('Não foi possível acessar o microfone. Autorize o acesso no navegador e tente novamente.');
      setConnecting(false);
      return;
    }
    try {
      const response = await api.token();
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setSessionToken(data.token);
      setLivekitUrl(data.url);
      setRoomName(data.room);
      setPhase('connecting');
      setView('conversation');
      recordEvent('token_issued', '', data.room);
    } catch (error) {
      recordEvent('token_failed', String(error));
      setErrorMessage('Não foi possível iniciar a sessão. Verifique a API local e tente novamente.');
    } finally { setConnecting(false); }
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

  const topStatus = phase === 'connected' ? { label: 'Conectado', tone: 'green' as const } :
    phase === 'connecting' ? { label: 'Conectando', tone: 'blue' as const } :
    status?.ok ? { label: 'Configurado para conectar', tone: 'green' as const } :
    { label: loadingStatus ? 'Verificando' : 'Atenção necessária', tone: loadingStatus ? 'blue' as const : 'red' as const };

  return (
    <div className="app-shell">
      <DesktopStatus/>
      <aside className="sidebar">
        <div className="sidebar-brand"><BrandMark /><div><strong>Harvey</strong><span>ASSISTENTE DE VOZ</span></div></div>
        <button className="sidebar-new" onClick={() => { setView('conversation'); if (!sessionToken) void startConversation(); }} disabled={connecting || Boolean(sessionToken) || !status?.ok}><Play size={15} fill="currentColor" /> Nova conversa <ArrowRight size={15} /></button>
        <nav className="sidebar-nav" aria-label="Navegação principal">
          <button aria-current={view === 'conversation' ? 'page' : undefined} className={view === 'conversation' ? 'nav-active' : ''} onClick={() => setView('conversation')}><AudioLines size={18} /> Conversa {sessionToken && <span className="nav-live" />}</button>
          <button aria-current={view === 'history' ? 'page' : undefined} className={view === 'history' ? 'nav-active' : ''} onClick={() => { if (selectedRoom) void openSession(selectedRoom); else if (sessions[0]) void openSession(sessions[0].room); else setView('history'); }}><History size={18} /> Histórico</button>
          <button aria-current={view === 'notes' ? 'page' : undefined} className={view === 'notes' ? 'nav-active' : ''} onClick={() => setView('notes')}><StickyNote size={18} /> Notas</button>
          <button aria-current={view === 'settings' ? 'page' : undefined} className={view === 'settings' ? 'nav-active' : ''} onClick={() => setView('settings')}><Settings2 size={18} /> Configurações</button>
        </nav>
        <div className="sidebar-recent"><div className="sidebar-label">RECENTES <span>{sessionsTotal}</span></div>{sessions.slice(0, 4).map((session) => <button key={session.room} onClick={() => void openSession(session.room)}><span className="recent-line" /><span>{session.title || formatSessionDate(session.started_at)}</span></button>)}{!sessions.length && <p>Nenhuma conversa ainda</p>}</div>
        <div className="sidebar-bottom"><div className="sidebar-status"><StatusDot tone={topStatus.tone} /><div><strong>{topStatus.label}</strong><span>{status?.model || 'Harvey Live'}</span></div></div><div className="sidebar-footer">REGISTROS LOCAIS · VOZ NA NUVEM</div></div>
      </aside>

      <main className="main-area">
        <header className="topbar"><div className="topbar-path"><span>HARVEY</span><ChevronRight size={14} /><strong>{view === 'conversation' ? 'Conversa' : view === 'history' ? 'Histórico' : view === 'notes' ? 'Notas' : 'Configurações'}</strong></div><div className="topbar-right"><div className="topbar-status"><StatusDot tone={topStatus.tone} /> {topStatus.label}</div></div></header>
        <div className="page-content">
          {errorMessage && <div className="error-banner" role="alert"><AlertCircle size={19} /><span>{errorMessage}</span><button onClick={() => setErrorMessage(null)} aria-label="Fechar aviso"><X size={16} /></button></div>}
          {sessionToken && livekitUrl && roomName && <Conversation recordEvent={recordEvent} api={api} serverUrl={livekitUrl} token={sessionToken} roomName={roomName}
            connected={phase === 'connected'} visible={view === 'conversation'} devices={devices} inputId={inputId} outputId={outputId}
            onInput={saveInput} onOutput={saveOutput} onRefreshDevices={() => void refreshDevices()} onEnd={endConversation} onReturn={() => setView('conversation')} onNotice={showNotice}
            onConnected={() => { setPhase('connected'); recordEvent('room_connected', '', roomName); }}
            onDisconnected={() => { recordEvent('room_disconnected', '', roomName); endConversation(); }}
            onError={(error) => { recordEvent('room_error', error.message, roomName); setErrorMessage(`Falha na conexão de áudio: ${error.message}`); }}
            onMediaDeviceFailure={(failure, kind) => recordEvent('microphone_failed', `${kind}:${failure}`, roomName)} />}
          {view === 'conversation' && !sessionToken && <Home status={status} loading={loadingStatus} connecting={connecting} sessions={sessions} total={sessionsTotal} onStart={() => void startConversation()} onOpenSession={(room) => void openSession(room)} onRetry={() => void refreshStatus()} />}
          {sessionsError && (view === 'history' || view === 'conversation') && <div className="error-banner" role="alert">Não foi possível carregar o histórico. <button className="text-button" onClick={() => void refreshSessions()}>Tentar novamente</button></div>}
          {view === 'history' && <Archive api={api} onChanged={() => void refreshSessions()} onDeleted={() => { archiveRequestId.current++; setSelectedRoom(null); setArchiveEntries([]); setArchiveMetrics(null); setArchiveError(false); setView('history'); void refreshSessions(); }} error={archiveError} selectedRoom={selectedRoom} entries={archiveEntries} metrics={archiveMetrics} loading={archiveLoading} query={archiveQuery} onQuery={setArchiveQuery} onSelect={(room) => void openSession(room)} onNotice={showNotice} />}
          {view === 'notes' && <NotesPage api={api} onNotice={showNotice} />}
          {view === 'settings' && <SettingsPage api={api} audioDevices={audioDevices} onNotice={showNotice} status={status} devices={devices} inputId={inputId} outputId={outputId} onInput={saveInput} onOutput={saveOutput} onRefresh={() => void refreshDevices()} onRetry={() => void refreshStatus()} />}
        </div>
        <footer className="app-footer"><span>Harvey Live</span><span>Seu espaço de conversa por voz</span></footer>
      </main>
      {notice && <div className={`toast toast--${notice.kind}`} role={notice.kind === 'error' ? 'alert' : 'status'}>{notice.kind === 'error' ? <AlertCircle size={17} /> : notice.kind === 'info' ? <AudioLines size={17} /> : <Check size={17} />} {notice.message}</div>}
    </div>
  );
}
