import { NativeModules, Platform } from 'react-native';
import Constants from 'expo-constants';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  DashboardStatus,
  Tarefa,
  TransacaoFinanceira,
  Meta,
  Habito,
  ChatMessage,
  SaldoCaixasResponse,
  CategoriaCaixa
} from '../types';

export function getBundlerHost(): string {
  try {
    // 1. Obtém o IP do host diretamente de onde o app baixou o bundle JavaScript do Metro
    const scriptURL: string | undefined = NativeModules.SourceCode?.scriptURL;
    if (scriptURL) {
      const match = scriptURL.match(/^https?:\/\/([^:/]+)/);
      if (match && match[1] && match[1] !== 'localhost' && match[1] !== '127.0.0.1') {
        return match[1];
      }
    }
  } catch {}

  try {
    // 2. Extrai do hostUri informado pelo Expo Go
    const hostUri =
      Constants.expoConfig?.hostUri ||
      (Constants as any).manifest?.debuggerHost ||
      (Constants as any).manifest2?.extra?.expoClient?.hostUri;

    if (hostUri) {
      const host = hostUri.split(':')[0];
      if (host && host !== 'localhost' && host !== '127.0.0.1') {
        return host;
      }
    }
  } catch {}

  // 3. Fallback para o IP da interface de rede do seu PC
  return '10.113.90.51';
}

function computeDefaultBaseUrl(): string {
  const host = getBundlerHost();
  return `http://${host}:8000`;
}

let API_BASE_URL = computeDefaultBaseUrl();
let API_TOKEN = 'minhasenha_super_segura_de_32_caracteres_minimo_aqui';

// Carrega preferências salvas no dispositivo e limpa entradas antigas com 127.0.0.1
AsyncStorage.getItem('@agent_core_server_url').then((savedUrl) => {
  if (savedUrl) {
    const clean = savedUrl.trim().replace(/\/$/, '');
    if (clean.includes('127.0.0.1') || clean.includes('localhost')) {
      // Descarta localhost inválido no Android físico
      AsyncStorage.removeItem('@agent_core_server_url');
      API_BASE_URL = computeDefaultBaseUrl();
    } else {
      API_BASE_URL = clean;
    }
  }
});

AsyncStorage.getItem('@agent_core_token').then((savedToken) => {
  if (savedToken) API_TOKEN = savedToken;
});

export async function setApiConfig(baseUrl: string, token?: string) {
  let clean = baseUrl.trim().replace(/\/$/, '');
  if (clean.includes('127.0.0.1') || clean.includes('localhost')) {
    clean = computeDefaultBaseUrl();
  }
  API_BASE_URL = clean;
  await AsyncStorage.setItem('@agent_core_server_url', API_BASE_URL);
  if (token) {
    API_TOKEN = token;
    await AsyncStorage.setItem('@agent_core_token', token);
  }
}

export function getApiBaseUrl(): string {
  if (!API_BASE_URL || API_BASE_URL.includes('127.0.0.1') || API_BASE_URL.includes('localhost')) {
    API_BASE_URL = computeDefaultBaseUrl();
  }
  return API_BASE_URL;
}

function getHeaders(contentType: string = 'application/json'): HeadersInit {
  return {
    'Content-Type': contentType,
    'Authorization': `Bearer ${API_TOKEN}`
  };
}

export const agentApi = {
  // 1. Dashboard e Status
  async getDashboardStatus(): Promise<DashboardStatus> {
    const base = getApiBaseUrl();
    const res = await fetch(`${base}/api/life/status`, {
      headers: getHeaders()
    });
    if (!res.ok) throw new Error(`Erro ao obter dashboard: HTTP ${res.status}`);
    return await res.json();
  },

  // 1.1 Inbox Cognitivo Zero-Fricção (Entrada de texto livre ou voz)
  async enviarInbox(texto: string, audioBase64?: string, forcarSemTrava: boolean = false): Promise<any> {
    const base = getApiBaseUrl();
    const res = await fetch(`${base}/api/inbox`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({
        texto,
        audio_base64: audioBase64,
        forcar_sem_trava: forcarSemTrava
      })
    });
    if (!res.ok) throw new Error(`Erro no Inbox: HTTP ${res.status}`);
    return await res.json();
  },

  // 2. Tarefas
  async listarTarefas(params?: { status?: string; criticidade?: string; data?: string }): Promise<Tarefa[]> {
    const base = getApiBaseUrl();
    const url = new URL(`${base}/api/life/tarefas`);
    if (params?.status) url.searchParams.set('status', params.status);
    if (params?.criticidade) url.searchParams.set('criticidade', params.criticidade);
    if (params?.data) url.searchParams.set('data', params.data);

    const res = await fetch(url.toString(), { headers: getHeaders() });
    if (!res.ok) throw new Error(`Erro ao listar tarefas: HTTP ${res.status}`);
    return await res.json();
  },

  async criarTarefa(tarefa: Partial<Tarefa>): Promise<any> {
    const base = getApiBaseUrl();
    const res = await fetch(`${base}/api/life/tarefas`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(tarefa)
    });
    if (!res.ok) throw new Error(`Erro ao criar tarefa: HTTP ${res.status}`);
    return await res.json();
  },

  async adiarTarefa(tarefaId: number, motivo: string, minutos: number = 15): Promise<any> {
    const base = getApiBaseUrl();
    const res = await fetch(`${base}/api/life/tarefas/${tarefaId}/adiar`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ motivo, minutos_adiamento: minutos })
    });
    if (!res.ok) throw new Error(`Erro ao adiar tarefa: HTTP ${res.status}`);
    return await res.json();
  },

  async concluirTarefa(tarefaId: number, evidencia: string = ''): Promise<any> {
    const base = getApiBaseUrl();
    const res = await fetch(`${base}/api/life/tarefas/${tarefaId}/concluir`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ evidencia })
    });
    if (!res.ok) throw new Error(`Erro ao concluir tarefa: HTTP ${res.status}`);
    return await res.json();
  },

  async prepararPC(tarefaId?: number): Promise<any> {
    const base = getApiBaseUrl();
    const res = await fetch(`${base}/api/life/acoes-ntfy`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({
        acao: 'estou_a_caminho',
        tarefa_id: tarefaId
      })
    });
    if (!res.ok) throw new Error(`Erro ao acionar preparação do PC: HTTP ${res.status}`);
    return await res.json();
  },

  // 3. Finanças
  async listarFinancas(limite: number = 50): Promise<TransacaoFinanceira[]> {
    const base = getApiBaseUrl();
    const res = await fetch(`${base}/api/life/financas?limite=${limite}`, {
      headers: getHeaders()
    });
    if (!res.ok) throw new Error(`Erro ao obter finanças: HTTP ${res.status}`);
    return await res.json();
  },

  async obterSaldoCaixas(): Promise<SaldoCaixasResponse> {
    const base = getApiBaseUrl();
    const res = await fetch(`${base}/api/life/financas/caixas`, {
      headers: getHeaders()
    });
    if (!res.ok) throw new Error(`Erro ao obter saldo das caixas: HTTP ${res.status}`);
    return await res.json();
  },

  async registrarTransacao(
    tipo: 'despesa' | 'receita',
    valor: number,
    descricao: string,
    categoria: string = 'livre_lazer',
    ma: string = ''
  ): Promise<any> {
    const base = getApiBaseUrl();
    const res = await fetch(`${base}/api/life/financas/transacao`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({
        tipo,
        valor,
        descricao,
        categoria,
        origem: 'mobile_app',
        ma
      })
    });
    if (!res.ok) throw new Error(`Erro ao registrar transação: HTTP ${res.status}`);
    return await res.json();
  },

  async registrarGasto(valor: number, descricao: string, categoria: string = 'livre_lazer', ma: string = ''): Promise<any> {
    return this.registrarTransacao('despesa', valor, descricao, categoria, ma);
  },

  async registrarReceita(valor: number, descricao: string, categoria: string = 'construcao_futuro', ma: string = ''): Promise<any> {
    return this.registrarTransacao('receita', valor, descricao, categoria, ma);
  },

  async obterOrcamentoLazer(): Promise<any> {
    const base = getApiBaseUrl();
    const res = await fetch(`${base}/api/life/financas/orcamento-lazer`, {
      headers: getHeaders()
    });
    if (!res.ok) throw new Error(`Erro ao obter orçamento de lazer: HTTP ${res.status}`);
    return await res.json();
  },

  async calcularPedagio(valor: number, item: string): Promise<any> {
    const base = getApiBaseUrl();
    const res = await fetch(`${base}/api/life/financas/pedagio?valor=${valor}&item=${encodeURIComponent(item)}`, {
      method: 'POST',
      headers: getHeaders()
    });
    if (!res.ok) throw new Error(`Erro ao calcular pedágio: HTTP ${res.status}`);
    return await res.json();
  },

  // 4. Metas & Hábitos
  async listarMetas(): Promise<Meta[]> {
    const base = getApiBaseUrl();
    const res = await fetch(`${base}/api/life/metas`, {
      headers: getHeaders()
    });
    if (!res.ok) throw new Error(`Erro ao listar metas: HTTP ${res.status}`);
    return await res.json();
  },

  async listarHabitos(): Promise<Habito[]> {
    const base = getApiBaseUrl();
    const res = await fetch(`${base}/api/life/habitos`, {
      headers: getHeaders()
    });
    if (!res.ok) throw new Error(`Erro ao listar hábitos: HTTP ${res.status}`);
    return await res.json();
  },

  async checkinHabito(habitoId: number): Promise<any> {
    const base = getApiBaseUrl();
    const res = await fetch(`${base}/api/life/habitos/${habitoId}/checkin`, {
      method: 'POST',
      headers: getHeaders()
    });
    if (!res.ok) throw new Error(`Erro ao registrar check-in: HTTP ${res.status}`);
    return await res.json();
  },

  // 5. Transcrição de Áudio
  async transcreverAudio(audioUri: string, fileName: string = 'audio.m4a'): Promise<string> {
    const base = getApiBaseUrl();
    const formData = new FormData();
    formData.append('arquivo', {
      uri: audioUri,
      name: fileName,
      type: 'audio/m4a'
    } as any);

    const res = await fetch(`${base}/transcrever`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${API_TOKEN}`
      },
      body: formData
    });
    if (!res.ok) throw new Error(`Falha na transcrição: HTTP ${res.status}`);
    const data = await res.json();
    return data.texto || '';
  },

  // 6. Envio de Mensagem para o Chat (Stream SSE em partes com extração limpa de tokens)
  async enviarMensagem(
    texto: string,
    chatId?: string,
    onChunk?: (tokenText: string) => void
  ): Promise<{ content: string; chatId: string; model?: string; route?: string; reasoning?: string }> {
    return new Promise((resolve, reject) => {
      const base = getApiBaseUrl();
      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${base}/chat`);
      xhr.setRequestHeader('Content-Type', 'application/json');
      if (API_TOKEN) {
        xhr.setRequestHeader('Authorization', `Bearer ${API_TOKEN}`);
      }

      let seenIndex = 0;
      let lineBuffer = '';
      let accumulatedText = '';
      let messageContent = '';
      let responseChatId = chatId || '';
      let responseMetadata: any = {};

      const parseLines = (textChunk: string) => {
        lineBuffer += textChunk;
        const lines = lineBuffer.split('\n');
        lineBuffer = lines.pop() || ''; // guarda linha incompleta

        for (const rawLine of lines) {
          const line = rawLine.trim();
          if (!line.startsWith('data:')) continue;
          const jsonStr = line.replace(/^data:\s*/, '').trim();
          if (!jsonStr || jsonStr === '[DONE]') continue;
          try {
            const data = JSON.parse(jsonStr);
            if (data.chat_id) {
              responseChatId = data.chat_id;
            }
            if (data.type === 'chunk' && data.content) {
              accumulatedText += data.content;
              if (onChunk) onChunk(data.content);
            } else if (data.type === 'message') {
              if (data.content) {
                messageContent = data.content;
              }
              responseMetadata = {
                model: data.model,
                route: data.route,
                reasoning: data.reasoning
              };
            }
          } catch {
            // Fragmento ainda em transmissão, continua acumulando
          }
        }
      };

      xhr.onprogress = () => {
        const full = xhr.responseText || '';
        const chunk = full.slice(seenIndex);
        seenIndex = full.length;
        parseLines(chunk);
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          const full = xhr.responseText || '';
          const chunk = full.slice(seenIndex);
          seenIndex = full.length;
          parseLines(chunk);

          // Verifica se sobrou linha no lineBuffer
          if (lineBuffer.trim().startsWith('data:')) {
            try {
              const data = JSON.parse(lineBuffer.trim().replace(/^data:\s*/, ''));
              if (data.chat_id) responseChatId = data.chat_id;
              if (data.type === 'chunk' && data.content) {
                accumulatedText += data.content;
                if (onChunk) onChunk(data.content);
              } else if (data.type === 'message' && data.content) {
                messageContent = data.content;
              }
            } catch {}
          }

          const finalContent = messageContent || accumulatedText || xhr.responseText;
          resolve({
            content: finalContent,
            chatId: responseChatId,
            ...responseMetadata
          });
        } else {
          reject(new Error(`Erro no chat: HTTP ${xhr.status} - ${xhr.responseText}`));
        }
      };

      xhr.onerror = () => {
        reject(new Error('Falha de conexão com o servidor do chat'));
      };

      xhr.send(
        JSON.stringify({
          texto,
          chat_id: chatId
        })
      );
    });
  }
};
