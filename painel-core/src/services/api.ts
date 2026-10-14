/** Contrato HTTP do Agent Core adaptado da Interface do Harvey. */
export interface HarveyApi {
  status(): Promise<Response>;
  preferences(): Promise<Response>;
  exportData(): Promise<Response>;
  sessions(params?: {query?:string; state?:string; offset?:number; after?:number; before?:number}): Promise<Response>;
  renameSession(room:string,title:string): Promise<Response>;
  deleteSession(room:string): Promise<Response>;
  history(room: string): Promise<Response>;
  metrics(room: string): Promise<Response>;
  token(): Promise<Response>;
  notes(query: string, signal?: AbortSignal, offset?:number): Promise<Response>;
  addNote(text: string): Promise<Response>;
  updateNote(id:number,text:string): Promise<Response>;
  deleteNote(id: number): Promise<Response>;
  profile(): Promise<Response>;
  saveProfile(profile: unknown, version: number): Promise<Response>;
  capabilities(): Promise<Response>;
  installSkill(id:string): Promise<Response>;
  configureSkill(id:string, config:unknown): Promise<Response>;
  enableSkill(id:string, enabled:boolean): Promise<Response>;
  skillOptions(id:string, query:string): Promise<Response>;
  authorize(capability:string, scope:string, allowed:boolean): Promise<Response>;
  executeCapability(name:string, arguments_:unknown): Promise<Response>;
  capabilityRuns(room?:string): Promise<Response>;
  browserStatus(): Promise<Response>;
  browserPairCode(): Promise<Response>;
  browserRevoke(): Promise<Response>;

  // Métodos adicionais do Agent Core:
  getMonitor(): Promise<Response>;
  getAdvancedSystem(): Promise<Response>;
  clearLogs(): Promise<Response>;
  getAnalytics(): Promise<Response>;
  getSystemModels(): Promise<Response>;
  startEngine(): Promise<Response>;
  stopEngine(): Promise<Response>;
  getConfig(): Promise<Response>;
  saveConfig(config: unknown): Promise<Response>;

  // Automação & PC:
  getPCCommands(): Promise<Response>;
  savePCCommand(chave: string, comando: string, acao?: string): Promise<Response>;
  executePCCommand(chave?: string, comando?: string): Promise<Response>;

  // Skills & Especialistas:
  getSkillsList(): Promise<Response>;
  saveSkill(skill: unknown): Promise<Response>;
  deleteSkill(id: string): Promise<Response>;

  // Memória RAG:
  getMemoryStats(): Promise<Response>;
  uploadMemoryFile(formData: FormData): Promise<Response>;
  deleteMemoryFile(nome: string): Promise<Response>;
  clearMemory(): Promise<Response>;
}

export const api: HarveyApi = {
  status: async () => {
    try {
      const resStatus = await fetch('/api/system/status');
      const isOnline = resStatus.ok ? (await resStatus.json()).online : false;
      let modelName = 'Ollama (Local)';
      try {
        const resCfg = await fetch('/api/config');
        if (resCfg.ok) {
          const cfg = await resCfg.json();
          if (cfg.modelo_ativo) modelName = cfg.modelo_ativo;
        }
      } catch {}

      return new Response(JSON.stringify({
        ok: isOnline,
        api_available: true,
        livekit_configured: true,
        provider_configured: true,
        provider_name: 'Agent Core (Ollama)',
        model: modelName,
        missing_credentials: isOnline ? [] : ['Motor Offline'],
        checked_at: Date.now(),
      }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    } catch {
      return new Response(JSON.stringify({
        ok: false,
        api_available: false,
        livekit_configured: false,
        provider_configured: false,
        provider_name: 'Agent Core',
        model: 'Desconectado',
        missing_credentials: ['Motor Offline'],
        checked_at: Date.now(),
      }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
  },

  preferences: async () => {
    try {
      const res = await fetch('/api/config');
      if (res.ok) {
        const cfg = await res.json();
        return new Response(JSON.stringify({
          voice: 'Whisper Local / Ollama',
          identity: cfg.prompt_sistema || 'Agent Core',
          storage: 'C:\\Projetos\\agent-core-main\\data',
          tools: []
        }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
    } catch {}
    return new Response(JSON.stringify({ voice: null, identity: 'Agent Core', storage: 'data/', tools: [] }), { status: 200 });
  },

  exportData: async () => {
    const notes = JSON.parse(localStorage.getItem('agent_core_notes') || '[]');
    let chats: unknown[] = [];
    try {
      const res = await fetch('/api/chats');
      if (res.ok) chats = await res.json();
    } catch {}
    const blob = new Blob([JSON.stringify({ notes, chats, exported_at: new Date().toISOString() }, null, 2)], {
      type: 'application/json'
    });
    return new Response(blob, { status: 200 });
  },

  sessions: async () => {
    try {
      const res = await fetch('/api/chats');
      if (!res.ok) throw new Error('chats_failed');
      const raw = await res.json();
      const sessions = (raw || []).map((c: { id?: string; titulo?: string; atualizado_em?: number; message_count?: number }) => ({
        room: c.id || '',
        title: c.titulo || 'Conversa',
        started_at: c.atualizado_em ? Math.floor(c.atualizado_em * 1000) : Date.now(),
        ended_at: null,
        end_reason: null,
        model: 'Agent Core',
        message_count: typeof c.message_count === 'number' ? c.message_count : 0
      }));
      return new Response(JSON.stringify({ sessions, total: sessions.length }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    } catch {
      return new Response(JSON.stringify({ sessions: [], total: 0 }), { status: 200 });
    }
  },

  renameSession: async (room: string, title: string) => {
    try {
      const res = await fetch(`/api/chats/${encodeURIComponent(room)}/rename`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      });
      if (res.ok) return res;
    } catch {}
    return new Response(JSON.stringify({ ok: true }), { status: 200 });
  },

  deleteSession: async (room: string) => {
    try {
      const res = await fetch(`/api/chats/${encodeURIComponent(room)}`, { method: 'DELETE' });
      if (res.ok) return res;
    } catch {}
    return new Response(JSON.stringify({ ok: true }), { status: 200 });
  },

  history: async (room: string) => {
    try {
      const res = await fetch(`/api/chats/${encodeURIComponent(room)}`);
      if (!res.ok) throw new Error('not_found');
      const data = await res.json();
      const msgs = data.messages || data.mensagens || [];
      const history = msgs.map((m: { role?: string; content?: string; created_at?: string; timestamp?: string }) => {
        let ts = Date.now() / 1000;
        const rawTs = m.timestamp || m.created_at;
        if (rawTs) {
          const parsed = new Date(rawTs).getTime();
          if (!isNaN(parsed)) ts = parsed / 1000;
        }
        return {
          speaker: (m.role === 'user' ? 'user' : 'agent') as 'user' | 'agent',
          text: m.content || '',
          timestamp: ts,
          interrupted: false,
        };
      });
      return new Response(JSON.stringify({ history }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    } catch {
      return new Response(JSON.stringify({ history: [] }), { status: 404 });
    }
  },

  metrics: async (room: string) => {
    try {
      const res = await fetch(`/api/chats/${encodeURIComponent(room)}`);
      if (res.ok) {
        const data = await res.json();
        const msgs = data.messages || data.mensagens || [];
        const userTurns = msgs.filter((m: { role?: string }) => m.role === 'user').length;
        const agentTurns = msgs.filter((m: { role?: string }) => m.role !== 'user').length;
        return new Response(JSON.stringify({
          metrics: {
            title: data.titulo || 'Conversa',
            duration_seconds: 0,
            user_turns: userTurns,
            agent_turns: agentTurns,
            interruptions: 0,
            status: 'active',
            end_reason: null
          }
        }), { status: 200 });
      }
    } catch {}
    return new Response(JSON.stringify({ metrics: null }), { status: 200 });
  },

  token: async () => {
    const roomId = 'chat_' + Date.now();
    return new Response(JSON.stringify({
      token: 'local-token-' + roomId,
      url: 'http://127.0.0.1:8000',
      room: roomId
    }), { status: 200, headers: { 'Content-Type': 'application/json' } });
  },

  notes: async (query: string, _signal?: AbortSignal, offset = 0) => {
    const stored = JSON.parse(localStorage.getItem('agent_core_notes') || '[]');
    const filtered = query.trim()
      ? stored.filter((n: { text: string }) => n.text.toLowerCase().includes(query.toLowerCase()))
      : stored;
    return new Response(JSON.stringify({
      notes: filtered.slice(offset, offset + 20),
      total: filtered.length
    }), { status: 200, headers: { 'Content-Type': 'application/json' } });
  },

  addNote: async (text: string) => {
    const stored = JSON.parse(localStorage.getItem('agent_core_notes') || '[]');
    const newNote = { id: Date.now(), text, created_at: Math.floor(Date.now() / 1000) };
    stored.unshift(newNote);
    localStorage.setItem('agent_core_notes', JSON.stringify(stored));
    return new Response(JSON.stringify(newNote), { status: 201, headers: { 'Content-Type': 'application/json' } });
  },

  updateNote: async (id: number, text: string) => {
    const stored = JSON.parse(localStorage.getItem('agent_core_notes') || '[]');
    const idx = stored.findIndex((n: { id: number }) => n.id === id);
    if (idx !== -1) {
      stored[idx].text = text;
      localStorage.setItem('agent_core_notes', JSON.stringify(stored));
    }
    return new Response(JSON.stringify({ ok: true }), { status: 200, headers: { 'Content-Type': 'application/json' } });
  },

  deleteNote: async (id: number) => {
    const stored = JSON.parse(localStorage.getItem('agent_core_notes') || '[]');
    const filtered = stored.filter((n: { id: number }) => n.id !== id);
    localStorage.setItem('agent_core_notes', JSON.stringify(filtered));
    return new Response(JSON.stringify({ ok: true }), { status: 200, headers: { 'Content-Type': 'application/json' } });
  },

  profile: async () => {
    try {
      const local = localStorage.getItem('agent_core_profile');
      let base: Record<string, unknown> = {};
      if (local) {
        try { base = JSON.parse(local); } catch {}
      }
      return new Response(JSON.stringify({
        language: 'pt-BR',
        allowed_languages: ['pt-BR', 'en'],
        tone: 'natural',
        detail: 'balanced',
        interaction: '',
        guidance: '',
        version: 1,
        scope: 'global',
        ...base,
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    } catch {
      return new Response(JSON.stringify({
        language: 'pt-BR',
        allowed_languages: ['pt-BR', 'en'],
        tone: 'natural',
        detail: 'balanced',
        interaction: '',
        guidance: '',
        version: 1,
        scope: 'global',
      }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
  },

  saveProfile: async (profile: unknown, version: number) => {
    try {
      const nextVersion = (version || 1) + 1;
      const updated = { ...(profile as Record<string, unknown>), version: nextVersion };
      localStorage.setItem('agent_core_profile', JSON.stringify(updated));
      return new Response(JSON.stringify(updated), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    } catch (err: unknown) {
      return new Response(JSON.stringify({ detail: (err as Error).message || 'Erro ao salvar perfil' }), { status: 500 });
    }
  },

  capabilities: async () => {
    try {
      const res = await fetch('/agentes', {
        headers: {
          Authorization: 'Bearer minhasenha_super_segura_de_32_caracteres_minimo_aqui',
        },
      });
      let skills: any[] = [];
      let tools: any[] = [];
      if (res.ok) {
        const items = await res.json();
        skills = items.filter((i: { tipo?: string }) => i.tipo === 'skill' || i.tipo === 'padrao').map((s: { id: string; nome: string }) => ({
          id: s.id,
          name: s.nome,
          description: `${s.nome} (Skill do Agent Core)`,
          status: 'available',
          installed: true,
          enabled: true,
          reasons: [],
          config: {},
          config_schema: { type: 'object', properties: {} },
          permissions: [],
          version: '1.0.0',
          execution_label: 'Agent Core'
        }));
        tools = items.filter((i: { tipo?: string }) => i.tipo === 'tool').map((t: { id: string; nome: string }) => ({
          name: t.id,
          display_name: t.nome,
          description: t.nome,
          capability: 'tool.' + t.id,
          scope: 'local',
          status: 'available',
          allowed: true
        }));
      }

      // Adiciona skill e ferramentas oficiais do Playwright MCP Bridge
      const browserSkill = {
        id: 'browser-automation',
        name: 'Automação Web e Mídia (Playwright MCP)',
        description: 'Controle de abas, leitura de acessibilidade, clique e mídia via Playwright MCP Bridge.',
        status: 'available',
        installed: true,
        enabled: true,
        reasons: [],
        config: { sites: 'www.youtube.com,youtube.com,discord.com,github.com,google.com,chatgpt.com' },
        config_schema: { type: 'object', properties: {} },
        permissions: ['automation.observe', 'automation.navigate', 'automation.interact', 'automation.media'],
        version: '1.0.0',
        execution_label: 'Playwright MCP Bridge'
      };
      const browserTools = [
        { name: 'pw_browser_navigate', display_name: 'Navegar e Pesquisar', skill_id: 'browser-automation', capability: 'automation.navigate', allowed: true },
        { name: 'pw_browser_snapshot', display_name: 'Ler Páginas Selecionadas', skill_id: 'browser-automation', capability: 'automation.observe', allowed: true },
        { name: 'pw_browser_click', display_name: 'Interagir com Controles', skill_id: 'browser-automation', capability: 'automation.interact', allowed: true },
        { name: 'pw_browser_media_control', display_name: 'Controlar Mídia', skill_id: 'browser-automation', capability: 'automation.media', allowed: true },
      ];

      return new Response(JSON.stringify({
        skills: [browserSkill, ...skills],
        tools: [...browserTools, ...tools],
        activation: 'Gerenciado pelo Playwright MCP Bridge & Agent Core.'
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    } catch {
      return new Response(JSON.stringify({ skills: [], tools: [], activation: 'Sem conexão' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
  },

  installSkill: async () => new Response(JSON.stringify({ ok: true }), { status: 200 }),
  configureSkill: async () => new Response(JSON.stringify({ ok: true }), { status: 200 }),
  enableSkill: async () => new Response(JSON.stringify({ ok: true }), { status: 200 }),
  skillOptions: async () => new Response(JSON.stringify([]), { status: 200 }),
  authorize: async () => new Response(JSON.stringify({ ok: true }), { status: 200 }),
  executeCapability: (name: string, arguments_: unknown) =>
    fetch(`/api/capabilities/${name}/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(arguments_ || {})
    }),
  capabilityRuns: () => fetch('/api/capability-runs'),
  browserStatus: () => fetch('/api/browser/status'),
  browserPairCode: () => fetch('/api/browser/pair-code', { method: 'POST' }),
  browserRevoke: () => fetch('/api/browser/pair', { method: 'DELETE' }),


  // Métodos de Sistema e Monitoramento do Agent Core:
  getMonitor: () => fetch('/api/system/monitor'),
  getAdvancedSystem: () => fetch('/api/system/advanced'),
  clearLogs: () => fetch('/api/system/clear-logs', { method: 'POST' }),
  getAnalytics: () => fetch('/api/analytics'),
  getSystemModels: () => fetch('/api/system/models'),
  startEngine: () => fetch('/api/system/start', { method: 'POST' }),
  stopEngine: () => fetch('/api/system/stop', { method: 'POST' }),
  getConfig: () => fetch('/api/config'),
  saveConfig: (config: unknown) => jsonRequest('/api/config', 'POST', config),

  // Automação & PC:
  getPCCommands: () => fetch('/api/pc/commands'),
  savePCCommand: (chave: string, comando: string, acao = 'salvar') => jsonRequest('/api/pc/commands', 'POST', { chave, comando, acao }),
  executePCCommand: (chave?: string, comando?: string) => jsonRequest('/api/pc/execute', 'POST', { chave, comando }),

  // Skills & Especialistas:
  getSkillsList: () => fetch('/api/skills/list'),
  saveSkill: (skill: unknown) => jsonRequest('/api/skills/save', 'POST', skill),
  deleteSkill: (id: string) => fetch(`/api/skills/${encodeURIComponent(id)}`, { method: 'DELETE' }),

  // Memória RAG:
  getMemoryStats: () => fetch('/api/memory/stats'),
  uploadMemoryFile: (formData: FormData) => fetch('/api/memory/upload', { method: 'POST', body: formData }),
  deleteMemoryFile: (nome: string) => fetch(`/api/memory/files/${encodeURIComponent(nome)}`, { method: 'DELETE' }),
  clearMemory: () => fetch('/api/memory/clear', { method: 'POST' }),
};

function jsonRequest(path:string,method:string,body:unknown) {
  return fetch(path,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
}
