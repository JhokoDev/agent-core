import {useEffect,useState} from 'react';
import type {HarveyApi} from '../services/api';
import {responseData} from './ProfileEditor';
const groups:Record<string,string>={observe:'Ler páginas selecionadas',navigate:'Navegar e pesquisar',interact:'Interagir com controles e formulários',media:'Controlar mídia'};
const defaultSites='* (Todos os sites liberados automaticamente)';

export default function AutomationPanel({api}:{api:HarveyApi}){
 const [state,setState]=useState<any>(null),[skill,setSkill]=useState<any>(null),[tools,setTools]=useState<any[]>([]);
 const [sites,setSites]=useState(defaultSites),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const load=async()=>{const [status,catalog]=await Promise.all([fetch('/api/automation/status').then(responseData),api.capabilities().then(responseData)]);setState(status);setSkill(catalog.skills.find((s:any)=>s.id==='browser-automation'));setTools(catalog.tools.filter((t:any)=>t.skill_id==='browser-automation'));};
 useEffect(()=>{let alive=true;const refresh=async()=>{try{if(alive)await load();}catch{if(alive)setError('Automação não alcançada.');}};void refresh();const timer=setInterval(refresh,3000);return()=>{alive=false;clearInterval(timer);};},[api]);
 useEffect(()=>{if(skill?.config?.sites)setSites(skill.config.sites);},[skill?.config?.sites]);
 const act=async(work:()=>Promise<Response>)=>{setBusy(true);setError('');try{const data=await responseData(await work());await load();if(['failed','unknown'].includes(data.state))setError(data.error);return data;}catch(e){setError((e as Error).message);}finally{setBusy(false);}};
 const post=(path:string)=>fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
 const phase=state?.connection_phase??(state?.state==='connected'?'ready':state?.state==='server_ready'?'awaiting_authorization':'disconnected');
 const labels:Record<string,string>={connecting:'Conectando ao servidor',awaiting_authorization:'Aguardando extensão carregar no Chrome',connected_no_tabs:'Extensão conectada (nenhuma aba HTTP aberta)',ready:'Acesso Livre Ativo (Chrome / Edge)',error:'Erro na conexão',disconnected:'Extensão desconectada'};
 const label=labels[phase]??'Estado de conexão desconhecido';
 return <article className="skill-card" data-testid="automation-panel">
  <div className="skill-heading"><h3>Controle do navegador (Acesso Livre ao Chrome)</h3><span>{label}</span></div>
  <p className="settings-help">Extensão oficial Playwright &amp; Harvey. Acesso livre e automático a todas as janelas e abas do Google Chrome ou Microsoft Edge, sem necessidade de agrupar ou vincular janelas manualmente.</p>
  <button className="secondary-button" disabled={busy} onClick={()=>void act(()=>post('/api/automation/connect'))}>Conectar Playwright</button>
  <button className="text-button" disabled={busy} onClick={()=>void act(()=>fetch('/api/automation/connect',{method:'DELETE'}))}>Desconectar Playwright</button>
  <button className="secondary-button" disabled={busy||!!state?.current||!skill?.installed||!tools.some(t=>t.capability==='automation.navigate'&&t.allowed)} onClick={()=>void act(()=>post('/api/automation/probe'))}>Verificar conexão e listar abas</button>
  {phase!=='ready'&&<div role="status" className="settings-help"><p>Para ativar, abra <code>chrome://extensions</code> (ou <code>edge://extensions</code>), habilite o <strong>Modo do desenvolvedor</strong>, clique em <strong>Carregar sem compactação</strong> e selecione a pasta <code>browser-extension</code> do projeto. A extensão se conecta automaticamente ao Agent Core e concede acesso total a qualquer janela e aba aberta.</p></div>}
  {phase==='connected_no_tabs'&&<p role="status">Extensão conectada, mas nenhuma aba HTTP/HTTPS aberta no momento. Abra qualquer site no Chrome/Edge para começar.</p>}
  {phase==='ready'&&state?.tab_count!=null&&<p role="status">{state.tab_count} aba(s) conectada(s) e sincronizadas em todas as janelas do navegador.</p>}
  {state?.connection_error&&<details><summary>Diagnóstico da conexão</summary><pre>{state.connection_error}</pre></details>}
  <p className="settings-help">Basta carregar a extensão no navegador para ter navegação, leitura da árvore semântica e controle de mídia sem utilizar comandos de terminal.</p>
  {!skill?.installed?<button className="secondary-button" disabled={busy} onClick={()=>void act(()=>api.installSkill('browser-automation'))}>Instalar navegação e mídia</button>:<>
   {skill.reasons?.some((r:string)=>r.startsWith('Pacote mudou'))&&<button className="secondary-button" disabled={busy} onClick={()=>void act(()=>api.installSkill('browser-automation'))}>Reinstalar automação revisada</button>}
   <form className="extension-form" onSubmit={e=>{e.preventDefault();void act(()=>api.configureSkill('browser-automation',{sites}));}}>
    <label>Escopo de navegação autorizada<textarea value={sites} maxLength={2000} onChange={e=>setSites(e.target.value)}/></label>
    <p className="settings-help">Todos os sites têm acesso liberado diretamente via Playwright MCP Bridge.</p>
    <button className="secondary-button" disabled={busy}>Salvar configuração</button>
   </form>
   {Object.entries(groups).map(([group,title])=>{const available=tools.some(t=>t.capability==='automation.'+group);const allowed=available&&tools.filter(t=>t.capability==='automation.'+group).every(t=>t.allowed);return <div className="permission-row" key={group}><span><strong>{title}</strong><small>{group==='interact'?'Links e campos de busca verificados em qualquer janela.':'Escopo irrestrito: todas as janelas e abas abertas no navegador.'}</small></span><button className="text-button" disabled={busy||!available} onClick={()=>void act(()=>api.authorize('automation.'+group,'selected_browser',!allowed))}>{allowed?'Revogar':'Autorizar'} {title.toLowerCase()}</button></div>;})}
   <button className="secondary-button" disabled={busy} onClick={()=>void act(()=>api.enableSkill('browser-automation',!skill.enabled))}>{skill.enabled?'Desativar navegação e mídia':'Ativar navegação e mídia'}</button>
   <p className="settings-help">{skill.enabled?'Ativada; novas ferramentas entram na próxima conversa.':'Desativada.'} Desativação e revogação bloqueiam novas ações.</p>
   <button className="secondary-button" disabled={busy||!skill.enabled||!tools.some(t=>t.capability==='automation.observe'&&t.allowed)} onClick={()=>void act(()=>api.executeCapability('pw_browser_snapshot',{}))}>Ler aba ativa do Chrome (Snapshot)</button>
   {skill.reasons?.length>0&&<ul className="settings-help">{skill.reasons.map((r:string)=><li key={r}>{r}</li>)}</ul>}
  </>}
  <button className="text-button" disabled={!state?.current} onClick={()=>void act(()=>post('/api/automation/cancel'))}>Cancelar tarefa do navegador</button>
  {state?.current&&<p role="status">Em execução: {state.current.tool} · {state.current.id}</p>}
  {state?.last&&<details><summary>Último resultado · {state.last.state} · {state.last.elapsed_ms??'—'} ms</summary><pre>{JSON.stringify(state.last,null,2)}</pre></details>}
  <details><summary>Ferramentas descobertas e capacidades</summary><p className="settings-help">Execução direta através da extensão Playwright MCP. Sem popups de terminal, com controle de abas, digitação, clique e mídia HTMLMediaElement.</p><ul>{state?.tools?.map((t:any)=><li key={t.name}>{t.name}</li>)}</ul></details>
  {error&&<p role="alert">{error}</p>}
 </article>;
}
