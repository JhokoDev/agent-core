import {
  DashboardStatus,
  Tarefa,
  TransacaoFinanceira,
  Meta,
  Habito,
  ChatMessage
} from '../types';

// Configuração Base do Agent Core
// Em desenvolvimento via Tailscale ou emulador:
// 'http://10.0.2.2:8000' (Emulador Android) ou 'http://127.0.0.1:8000' ou IP Tailscale
let API_BASE_URL = 'http://127.0.0.1:8000';
let API_TOKEN = 'minhasenha_super_segura_de_32_caracteres_minimo_aqui';

export function setApiConfig(baseUrl: string, token?: string) {
  API_BASE_URL = baseUrl.replace(/\/$/, '');
  if (token) API_TOKEN = token;
}

export function getApiBaseUrl(): string {
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
    const res = await fetch(`${API_BASE_URL}/api/life/status`, {
      headers: getHeaders()
    });
    if (!res.ok) throw new Error(`Erro ao obter dashboard: HTTP ${res.status}`);
    return await res.json();
  },

  // 2. Tarefas
  async listarTarefas(params?: { status?: string; criticidade?: string; data?: string }): Promise<Tarefa[]> {
    const url = new URL(`${API_BASE_URL}/api/life/tarefas`);
    if (params?.status) url.searchParams.set('status', params.status);
    if (params?.criticidade) url.searchParams.set('criticidade', params.criticidade);
    if (params?.data) url.searchParams.set('data', params.data);

    const res = await fetch(url.toString(), { headers: getHeaders() });
    if (!res.ok) throw new Error(`Erro ao listar tarefas: HTTP ${res.status}`);
    return await res.json();
  },

  async criarTarefa(tarefa: Partial<Tarefa>): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/life/tarefas`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(tarefa)
    });
    if (!res.ok) throw new Error(`Erro ao criar tarefa: HTTP ${res.status}`);
    return await res.json();
  },

  async adiarTarefa(tarefaId: number, motivo: string, minutos: number = 15): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/life/tarefas/${tarefaId}/adiar`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ motivo, minutos_adiamento: minutos })
    });
    if (!res.ok) throw new Error(`Erro ao adiar tarefa: HTTP ${res.status}`);
    return await res.json();
  },

  async concluirTarefa(tarefaId: number, evidencia: string = ''): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/life/tarefas/${tarefaId}/concluir`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ evidencia })
    });
    if (!res.ok) throw new Error(`Erro ao concluir tarefa: HTTP ${res.status}`);
    return await res.json();
  },

  async prepararPC(tarefaId?: number): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/life/acoes-ntfy`, {
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
  async listarFinancas(limite: number = 30): Promise<TransacaoFinanceira[]> {
    const res = await fetch(`${API_BASE_URL}/api/life/financas?limite=${limite}`, {
      headers: getHeaders()
    });
    if (!res.ok) throw new Error(`Erro ao obter finanças: HTTP ${res.status}`);
    return await res.json();
  },

  async registrarGasto(valor: number, descricao: string, categoria: string = 'geral'): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/life/financas/transacao`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({
        tipo: 'despesa',
        valor,
        descricao,
        categoria,
        origem: 'mobile_app'
      })
    });
    if (!res.ok) throw new Error(`Erro ao registrar gasto: HTTP ${res.status}`);
    return await res.json();
  },

  async calcularPedagio(valor: number, item: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/life/financas/pedagio?valor=${valor}&item=${encodeURIComponent(item)}`, {
      method: 'POST',
      headers: getHeaders()
    });
    if (!res.ok) throw new Error(`Erro ao calcular pedágio: HTTP ${res.status}`);
    return await res.json();
  },

  // 4. Metas & Hábitos
  async listarMetas(): Promise<Meta[]> {
    const res = await fetch(`${API_BASE_URL}/api/life/metas`, {
      headers: getHeaders()
    });
    if (!res.ok) throw new Error(`Erro ao listar metas: HTTP ${res.status}`);
    return await res.json();
  },

  async listarHabitos(): Promise<Habito[]> {
    const res = await fetch(`${API_BASE_URL}/api/life/habitos`, {
      headers: getHeaders()
    });
    if (!res.ok) throw new Error(`Erro ao listar hábitos: HTTP ${res.status}`);
    return await res.json();
  },

  async checkinHabito(habitoId: number): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/life/habitos/${habitoId}/checkin`, {
      method: 'POST',
      headers: getHeaders()
    });
    if (!res.ok) throw new Error(`Erro ao registrar check-in: HTTP ${res.status}`);
    return await res.json();
  },

  // 5. Transcrição de Áudio
  async transcreverAudio(audioUri: string, fileName: string = 'audio.m4a'): Promise<string> {
    const formData = new FormData();
    formData.append('arquivo', {
      uri: audioUri,
      name: fileName,
      type: 'audio/m4a'
    } as any);

    const res = await fetch(`${API_BASE_URL}/transcrever`, {
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

  // 6. Envio de Mensagem para o Chat
  async enviarMensagem(
    texto: string,
    chatId?: string,
    onChunk?: (chunk: string) => void
  ): Promise<string> {
    const res = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({
        texto,
        chat_id: chatId
      })
    });

    if (!res.ok) throw new Error(`Erro no chat: HTTP ${res.status}`);

    const reader = res.body?.getReader();
    if (!reader) {
      const text = await res.text();
      return text;
    }

    const decoder = new TextDecoder('utf-8');
    let fullResponse = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      fullResponse += chunk;
      if (onChunk) onChunk(chunk);
    }

    return fullResponse;
  }
};
