/** Montagem central: selecione implementações compatíveis antes de iniciar a aplicação. */
import type { ComponentType } from 'react';
import type { ConversationProps, ClientEvent } from './contracts';
import { api, type HarveyApi } from './services/api';
import { audioDevices } from './voice/devices';
import { recordClientEvent } from './services/clientEvents';
import LocalConversation from './voice/LocalConversation';

export interface FrontendModules {
  api: HarveyApi;
  recordEvent: (event: ClientEvent, message?: string, room?: string) => void;
  audioDevices: typeof audioDevices;
  Conversation: ComponentType<ConversationProps>;
}

export const frontendModules: FrontendModules = { api, recordEvent: recordClientEvent, audioDevices, Conversation: LocalConversation };
