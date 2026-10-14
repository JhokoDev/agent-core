/** Contrato HTTP único. Respostas e erros existentes permanecem preservados. */
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
}

export const api: HarveyApi = {
  status: () => fetch('/api/status'),
  preferences: () => fetch('/api/preferences'),
  exportData: () => fetch('/api/export'),
  sessions: (params={}) => fetch(`/api/sessions?${new URLSearchParams(Object.entries(params).filter(([,v])=>v!==undefined).map(([k,v])=>[k,String(v)]))}`),
  renameSession: (room,title) => fetch(`/api/session/${encodeURIComponent(room)}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({title})}),
  deleteSession: room => fetch(`/api/session/${encodeURIComponent(room)}`,{method:'DELETE'}),
  history: (room) => fetch(`/api/session/${encodeURIComponent(room)}/history`),
  metrics: (room) => fetch(`/api/session/${encodeURIComponent(room)}/metrics`),
  token: () => fetch('/api/token'),
  notes: (query, signal, offset=0) => fetch(`/api/notes?query=${encodeURIComponent(query)}&offset=${offset}`, { signal }),
  addNote: (text) => fetch('/api/notes', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) }),
  updateNote: (id,text) => fetch(`/api/notes/${id}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})}),
  deleteNote: (id) => fetch(`/api/notes/${id}`, { method: 'DELETE' }),
  profile: () => fetch('/api/profile'),
  saveProfile: (profile,version) => jsonRequest('/api/profile','PUT',{profile,version}),
  capabilities: () => fetch('/api/capabilities'),
  installSkill: id => jsonRequest(`/api/skills/${encodeURIComponent(id)}/install`,'POST',{}),
  configureSkill: (id,config) => jsonRequest(`/api/skills/${encodeURIComponent(id)}/config`,'PUT',{config}),
  enableSkill: (id,enabled) => jsonRequest(`/api/skills/${encodeURIComponent(id)}/enabled`,'PUT',{enabled}),
  skillOptions: (id,query) => fetch(`/api/skills/${encodeURIComponent(id)}/options?query=${encodeURIComponent(query)}`),
  authorize: (capability,scope,allowed) => jsonRequest('/api/authorizations','PUT',{capability,scope,allowed}),
  executeCapability: (name,arguments_) => jsonRequest(`/api/capabilities/${encodeURIComponent(name)}/execute`,'POST',{arguments:arguments_}),
  capabilityRuns: room => fetch('/api/capability-runs'+(room?'?limit=100&session_id='+encodeURIComponent(room):'')),
  browserStatus: () => fetch('/api/browser/status'),
  browserPairCode: () => jsonRequest('/api/browser/pair-code','POST',{}),
  browserRevoke: () => fetch('/api/browser/pair',{method:'DELETE'}),
};

function jsonRequest(path:string,method:string,body:unknown) {
  return fetch(path,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
}
