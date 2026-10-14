import { useCallback, useEffect, useRef, useState } from 'react';
import { LiveKitRoom, RoomAudioRenderer, useLocalParticipant, useRoomContext, useVoiceAssistant } from '@livekit/components-react';
import { RoomEvent, type Participant, type TranscriptionSegment } from 'livekit-client';
import { AudioLines, Clock3, Mic, MicOff, PhoneOff, SlidersHorizontal, X, ShieldCheck } from 'lucide-react';
import type { ConversationProps, Speaker, TranscriptEntry, SessionMetrics, Notify } from '../contracts';
import { StatusDot, DeviceFields, TranscriptToolbar, TranscriptList } from '../ui/shared';
import { formatClock } from '../ui/format';
import {IntegrationResults} from '../ui/WebBrowserPanel';

function ActiveConversation({ recordEvent, api, roomName, connected, visible, devices, inputId, outputId, onInput, onOutput, onRefreshDevices, onEnd, onReturn, onNotice }: {
  api: ConversationProps['api'];
  recordEvent: ConversationProps['recordEvent'];
  roomName: string;
  connected: boolean;
  visible: boolean;
  devices: MediaDeviceInfo[];
  inputId: string;
  outputId: string;
  onInput: (value: string) => void;
  onOutput: (value: string) => void;
  onRefreshDevices: () => void;
  onEnd: () => void;
  onReturn: () => void;
  onNotice: Notify;
}) {
  const room = useRoomContext();
  const { localParticipant, isMicrophoneEnabled } = useLocalParticipant();
  const assistant = useVoiceAssistant();
  const [entries, setEntries] = useState<TranscriptEntry[]>([]);
  const [query, setQuery] = useState('');
  const [deviceOpen, setDeviceOpen] = useState(false);
  const [micLevel, setMicLevel] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [metrics, setMetrics] = useState<SessionMetrics | null>(null);
  const startedAt = useRef(Date.now());
  const appliedInputId = useRef('');
  const appliedOutputId = useRef('');

  useEffect(() => {
    const onTranscription = (segments: TranscriptionSegment[], participant?: Participant) => {
      const speaker: Speaker = participant?.identity === localParticipant.identity ? 'user' : 'agent';
      setEntries((previous) => {
        const next = [...previous];
        for (const segment of segments) {
          if (!segment.text?.trim()) continue;
          const id = `${speaker}-${segment.id}`;
          const index = next.findIndex((entry) => entry.id === id);
          if (index === -1) {
            next.push({ id, speaker, text: segment.text, timestamp: Date.now(), final: segment.final });
          } else {
            next[index] = { ...next[index], text: segment.text, final: segment.final };
          }
        }
        return next;
      });
    };
    room.on(RoomEvent.TranscriptionReceived, onTranscription);
    return () => { room.off(RoomEvent.TranscriptionReceived, onTranscription); };
  }, [room, localParticipant.identity]);

  useEffect(() => {
    const tick = window.setInterval(() => {
      setElapsed((Date.now() - startedAt.current) / 1000);
      setMicLevel(localParticipant.audioLevel || 0);
    }, 150);
    return () => window.clearInterval(tick);
  }, [localParticipant]);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const response = await api.metrics(roomName);
        if (!response.ok) return;
        const data = await response.json();
        if (alive) setMetrics(data.metrics);
      } catch { /* Os contadores são opcionais durante reconexões. */ }
    };
    void load();
    const timer = window.setInterval(load, 4000);
    return () => { alive = false; window.clearInterval(timer); };
  }, [api, roomName]);

  useEffect(() => {
    if (!connected) return;
    if (inputId !== appliedInputId.current) {
      void room.switchActiveDevice('audioinput', inputId || 'default').then(() => {
        appliedInputId.current = inputId;
      }).catch(() => onNotice('Não foi possível selecionar o microfone salvo.', 'error'));
    }
    if (outputId !== appliedOutputId.current) {
      void room.switchActiveDevice('audiooutput', outputId || 'default').then(() => {
        appliedOutputId.current = outputId;
      }).catch(() => onNotice('Este navegador não permitiu trocar a saída de áudio.', 'error'));
    }
  }, [connected, inputId, outputId, room, onNotice]);

  const toggleMic = useCallback(async () => {
    try {
      await localParticipant.setMicrophoneEnabled(!isMicrophoneEnabled);
    } catch (error) {
      recordEvent('microphone_toggle_failed', String(error), roomName);
      onNotice('Não foi possível alterar o microfone.', 'error');
    }
  }, [isMicrophoneEnabled, localParticipant, onNotice, roomName, recordEvent]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (!visible || event.altKey || event.ctrlKey || event.metaKey || event.repeat) return;
      const target = event.target as HTMLElement | null;
      if (target?.closest('input, select, textarea, button, [contenteditable="true"]')) return;
      if (event.key.toLowerCase() === 'm') {
        event.preventDefault();
        void toggleMic();
      }
      if (event.key === 'Escape') setDeviceOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [toggleMic, visible]);

  const agentReady = Boolean(assistant.agent);
  const state = assistant.state;
  const stageTitle = !connected ? 'Conectando à sala' : !agentReady ? 'Aguardando Harvey' :
    state === 'speaking' ? 'Harvey está falando' :
    !isMicrophoneEnabled ? 'Microfone desativado' :
    state === 'thinking' ? 'Preparando resposta' : 'Harvey está ouvindo';
  const stageHint = !connected ? 'Estabelecendo a conexão de áudio segura.' : !agentReady ?
    'O agente deve entrar na sala em alguns segundos.' : !isMicrophoneEnabled ?
    'Ative o microfone para continuar a conversa.' :
    'Fale naturalmente. Você pode interromper o Harvey enquanto ele responde.';
  const stageTone = state === 'speaking' ? 'speaking' : connected && agentReady ? 'listening' : 'waiting';

  const changeInput = async (value: string) => {
    try {
      if (connected) await room.switchActiveDevice('audioinput', value || 'default');
      appliedInputId.current = value;
      onInput(value);
      onNotice('Microfone atualizado.');
    } catch { onNotice('Não foi possível trocar o microfone.', 'error'); }
  };
  const changeOutput = async (value: string) => {
    try {
      if (connected) await room.switchActiveDevice('audiooutput', value || 'default');
      appliedOutputId.current = value;
      onOutput(value);
      onNotice('Saída de áudio atualizada.');
    } catch { onNotice('Não foi possível trocar a saída de áudio.', 'error'); }
  };

  return (
    <section className={`conversation-layout ${visible ? '' : 'conversation-layout--background'}`} aria-label="Conversa em andamento">
      <div className="voice-column">
        <div className="section-heading">
          <div><p className="eyebrow">SALA ATIVA</p><h1>Conversa ao vivo</h1></div>
          <div className="session-timer"><Clock3 size={15} /> {formatClock(elapsed)}</div>
        </div>
        <div className="voice-stage">
          <div className="stage-topline"><span><StatusDot tone={connected && agentReady ? 'green' : 'blue'} /> {connected && agentReady ? 'Áudio em tempo real' : 'Estabelecendo conexão'}</span><span>HARVEY LIVE</span></div>
          <div className={`voice-symbol voice-symbol--${stageTone}`} aria-hidden="true">
            <span className="voice-ring voice-ring--outer" /><span className="voice-ring voice-ring--inner" />
            <AudioLines size={43} strokeWidth={1.6} />
          </div>
          <div className="stage-copy" aria-live="polite"><h2>{stageTitle}</h2><p>{stageHint}</p></div>
          <div className="level-meter" aria-label="Nível do microfone">
            {[0.4, 0.75, 1, 0.7, 0.45, 0.9, 0.55, 0.35].map((factor, index) =>
              <span key={index} style={{ height: `${Math.max(5, 5 + micLevel * factor * 66)}px` }} />,
            )}
          </div>
          <div className="stage-controls">
            {!visible && <button className="text-button" onClick={onReturn}>Voltar à chamada</button>}
            <button className={`control-circle ${isMicrophoneEnabled ? '' : 'control-circle--muted'}`} onClick={() => void toggleMic()} title="Alternar microfone (M)" aria-label={isMicrophoneEnabled ? 'Desativar microfone' : 'Ativar microfone'}>
              {isMicrophoneEnabled ? <Mic size={21} /> : <MicOff size={21} />}
            </button>
            <button className="control-end" onClick={onEnd}><PhoneOff size={18} /> Encerrar conversa</button>
            <button className={`control-circle ${deviceOpen ? 'control-circle--active' : ''}`} onClick={() => setDeviceOpen((open) => !open)} title="Dispositivos de áudio" aria-label="Configurar dispositivos de áudio"><SlidersHorizontal size={19} /></button>
          </div>
          <p className="shortcut-note">Pressione <kbd>M</kbd> para alternar o microfone</p>
        </div>
        {deviceOpen && <div className="inline-device-panel"><div className="panel-title-row"><h3>Dispositivos de áudio</h3><button className="icon-button" onClick={() => setDeviceOpen(false)} aria-label="Fechar dispositivos"><X size={17} /></button></div><DeviceFields devices={devices} inputId={inputId} outputId={outputId} onInput={(value) => void changeInput(value)} onOutput={(value) => void changeOutput(value)} onRefresh={onRefreshDevices} /></div>}
        <div className="call-stats">
          <div><span>Conexão</span><strong>{connected ? 'Conectado' : 'Conectando'}</strong></div>
          <div><span>Suas falas</span><strong>{metrics?.user_turns ?? entries.filter((entry) => entry.speaker === 'user' && entry.final).length}</strong></div>
          <div><span>Respostas</span><strong>{metrics?.agent_turns ?? entries.filter((entry) => entry.speaker === 'agent' && entry.final).length}</strong></div>
          <div><span>Interrupções</span><strong>{metrics?.interruptions ?? 0}</strong></div>
        </div>
      </div>
      <div className="transcript-panel">
        <div className="panel-heading"><div><p className="eyebrow">EM TEMPO REAL</p><h2>Transcrição</h2></div><span className="count-badge">{entries.filter((entry) => entry.final).length}</span></div>
        <TranscriptToolbar entries={entries} query={query} onQuery={setQuery} room={roomName} onNotice={onNotice} />
        <TranscriptList live entries={entries} query={query} emptyText="As falas aparecerão aqui quando a conversa começar." />
        <IntegrationResults api={api} room={roomName}/><div className="transcript-foot"><ShieldCheck size={15} /> Salvo localmente no Harvey</div>
      </div>
    </section>
  );
}

export default function LiveKitConversation(props: ConversationProps) {
  return <LiveKitRoom serverUrl={props.serverUrl} token={props.token} connect={true}
    audio={{ deviceId: props.inputId ? { ideal: props.inputId } : undefined, echoCancellation: true, noiseSuppression: true, autoGainControl: true }}
    video={false} onConnected={props.onConnected} onDisconnected={props.onDisconnected} onError={props.onError}
    onMediaDeviceFailure={(failure, kind) => props.onMediaDeviceFailure(String(failure || 'unknown'), String(kind || 'unknown'))}>
    <RoomAudioRenderer />
    <ActiveConversation {...props} />
  </LiveKitRoom>;
}
