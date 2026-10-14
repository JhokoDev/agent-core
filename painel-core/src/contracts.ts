export type View = 'conversation' | 'history' | 'notes' | 'settings' | 'monitor' | 'analytics';
export type ConnectionPhase = 'idle' | 'connecting' | 'connected';
export type Speaker = 'user' | 'agent';
export type NoticeKind = 'success' | 'error' | 'info';
export type Notify = (message: string, kind?: NoticeKind) => void;

export interface ServerStatus {
  ok: boolean;
  livekit_configured: boolean;
  provider_configured: boolean;
  provider_name: string;
  model: string;
  missing_credentials: string[];
  api_available?: boolean;
  checked_at?: number;
  agent_observation?: { state: string; last_seen_at: number | null };
}

export interface SessionSummary {
  room: string;
  started_at: number;
  ended_at: number | null;
  end_reason: string | null;
  model: string;
  message_count: number;
  title?: string;
}

export interface SessionMetrics {
  title?: string;
  started_at?: number;
  duration_seconds: number;
  user_turns: number;
  agent_turns: number;
  interruptions: number;
  status: 'active' | 'closed';
  end_reason: string | null;
}

export interface TranscriptEntry {
  id: string;
  speaker: Speaker;
  text: string;
  timestamp: number;
  final: boolean;
  interrupted?: boolean;
  reasoning?: string;
  model?: string;
  route?: string;
  isThinking?: boolean;
}

export type ClientEvent =
  | 'status_loaded' | 'status_failed' | 'microphone_granted' | 'microphone_failed'
  | 'token_issued' | 'token_failed' | 'room_connected' | 'room_disconnected'
  | 'room_error' | 'microphone_toggle_failed' | 'browser_error';

export interface Note { id: number; text: string; created_at: number; }

// O transporte de conversa pode ser substituído sem mudar as páginas.
export interface ConversationProps {
  recordEvent: (event: ClientEvent, message?: string, room?: string) => void;
  api: import('./services/api').HarveyApi;
  serverUrl: string;
  token: string;
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
  onConnected: () => void;
  onDisconnected: () => void;
  onError: (error: Error) => void;
  onMediaDeviceFailure: (failure: string, kind: string) => void;
}
