import {useEffect,useState} from 'react';
import type {HarveyApi} from '../services/api';
import {responseData} from './ProfileEditor';
const groups:Record<string,string>={observe:'Ler páginas selecionadas',navigate:'Navegar e pesquisar',interact:'Interagir com controles revisados',media:'Controlar mídia'};
const defaultSites='www.youtube.com,youtube.com,en.wikipedia.org,pt.wikipedia.org,www.todamateria.com.br,example.com';

export default function AutomationPanel({api}:{api:HarveyApi}){
 const [state,setState]=useState<any>(null),[skill,setSkill]=useState<any>(null),[tools,setTools]=useState<any[]>([]);
 const [sites,setSites]=useState(defaultSites),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const load=async()=>{const [status,catalog]=await Promise.all([fetch('/api/automation/status').then(responseData),api.capabilities().then(responseData)]);setState(status);setSkill(catalog.skills.find((s:any)=>s.id==='browser-automation'));setTools(catalog.tools.filter((t:any)=>t.skill_id==='browser-automation'));};
 useEffect(()=>{let alive=true;const refresh=async()=>{try{if(alive)await load();}catch{if(alive)setError('Automação não alcançada.');}};void refresh();const timer=setInterval(refresh,3000);return()=>{alive=false;clearInterval(timer);};},[api]);
 useEffect(()=>{if(skill?.config?.sites)setSites(skill.config.sites);},[skill?.config?.sites]);
 const act=async(work:()=>Promise<Response>)=>{setBusy(true);setError('');try{const data=await responseData(await work());await load();if(['failed','unknown'].includes(data.state))setError(data.error);return data;}catch(e){setError((e as Error).message);}finally{setBusy(false);}};
 const post=(path:string)=>fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
 const phase=state?.connection_phase??(state?.state==='connected'?'ready':state?.state==='server_ready'?'awaiting_authorization':'disconnected');
 const labels:Record<string,string>={connecting:'Conectando ao servidor',awaiting_authorization:'Aguardando autorização no Edge',connected_no_tabs:'Conectado, sem abas disponíveis',ready:'Pronto para operar',error:'Erro na conexão',disconnected:'Navegador desconectado'};
 const label=labels[phase]??'Estado de conexão desconhecido';
 return <article className="skill-card" data-testid="automation-panel">
  <div className="skill-heading"><h3>Controle do navegador</h3><span>{label}</span></div>
  <p className="settings-help">Extensão oficial Playwright. Só alcança abas no grupo Harvey. Arraste abas para o grupo para conceder alcance. Remova-as para restringir.</p>
  <button className="secondary-button" disabled={busy} onClick={()=>void act(()=>post('/api/automation/connect'))}>Conectar Playwright</button>
  <button className="text-button" disabled={busy} onClick={()=>void act(()=>fetch('/api/automation/connect',{method:'DELETE'}))}>Desconectar Playwright</button>
  <button className="secondary-button" disabled={busy||!!state?.current||!skill?.installed||!tools.some(t=>t.capability==='automation.navigate'&&t.allowed)} onClick={()=>void act(()=>post('/api/automation/probe'))}>Verificar conexão e listar abas</button>
  {phase!=='ready'&&<div role="status" className="settings-help"><p>Na tela Welcome do seu perfil do Edge, escolha uma aba HTTP/HTTPS em “Allow &amp; select”. Depois, arraste outras abas para o grupo “Playwright · Harvey”. Abas de outro cliente não aparecem nesta seleção.</p><p>Lista vazia enquanto aparece “trying to connect”: abra o console da página. Se aparecer “Receiving end does not exist”, reinicie a extensão em edge://extensions; se persistir, salve seus trabalhos e reinicie o Edge. Em seguida, desconecte, conecte e verifique novamente aqui. Páginas Welcome de tentativas expiradas não recuperam o relay.</p></div>}
  {phase==='connected_no_tabs'&&<p role="status">O relay respondeu, mas não há aba HTTP/HTTPS disponível ao Harvey. Inclua uma aba no grupo e verifique novamente.</p>}
  {phase==='ready'&&state?.tab_count!=null&&<p role="status">{state.tab_count} aba(s) HTTP/HTTPS confirmada(s) pela última listagem.</p>}
  {state?.connection_error&&<details><summary>Diagnóstico da conexão</summary><pre>{state.connection_error}</pre></details>}
  <p className="settings-help">Conectar prepara o servidor e descobre ferramentas. Depois de ativar, verifique uma aba: a extensão abre sua tela de seleção no Edge pessoal.</p>
  {!skill?.installed?<button className="secondary-button" disabled={busy} onClick={()=>void act(()=>api.installSkill('browser-automation'))}>Instalar navegação e mídia</button>:<>
   {skill.reasons?.some((r:string)=>r.startsWith('Pacote mudou'))&&<button className="secondary-button" disabled={busy} onClick={()=>void act(()=>api.installSkill('browser-automation'))}>Reinstalar automação revisada</button>}
   <form className="extension-form" onSubmit={e=>{e.preventDefault();void act(()=>api.configureSkill('browser-automation',{sites}));}}>
    <label>Sites autorizados para leitura e controle<textarea value={sites} maxLength={2000} onChange={e=>setSites(e.target.value)}/></label>
    <p className="settings-help">Hosts exatos, separados por vírgula. Esta lista preserva os acessos anteriores. Para novos sites, peça leitura, pesquisa ou controle: uma autorização reutilizável aparecerá aqui. Abrir uma URL não amplia permissões.</p>
    <button className="secondary-button" disabled={busy}>Salvar sites autorizados</button>
   </form>
   {Object.entries(groups).map(([group,title])=>{const available=tools.some(t=>t.capability==='automation.'+group);const allowed=available&&tools.filter(t=>t.capability==='automation.'+group).every(t=>t.allowed);return <div className="permission-row" key={group}><span><strong>{title}</strong><small>{group==='interact'?'Links e campos de busca verificados, incluindo busca dinâmica. Outros controles exigem revisão.':'Escopo: sites autorizados no grupo de abas do Harvey.'}</small></span><button className="text-button" disabled={busy||!available} onClick={()=>void act(()=>api.authorize('automation.'+group,'selected_browser',!allowed))}>{allowed?'Revogar':'Autorizar'} {title.toLowerCase()}</button></div>;})}
   <button className="secondary-button" disabled={busy} onClick={()=>void act(()=>api.enableSkill('browser-automation',!skill.enabled))}>{skill.enabled?'Desativar navegação e mídia':'Ativar navegação e mídia'}</button>
   <p className="settings-help">{skill.enabled?'Ativada; novas ferramentas entram na próxima conversa.':'Desativada.'} Desativação e revogação bloqueiam novas ações. Interromper a fala não cancela a tarefa.</p>
   <button className="secondary-button" disabled={busy||!skill.enabled||!tools.some(t=>t.capability==='automation.observe'&&t.allowed)} onClick={()=>void act(()=>api.executeCapability('pw_browser_snapshot',{}))}>Selecionar e verificar aba do Edge</button>
   {skill.reasons?.length>0&&<ul className="settings-help">{skill.reasons.map((r:string)=><li key={r}>{r}</li>)}</ul>}
  </>}
  <button className="text-button" disabled={!state?.current} onClick={()=>void act(()=>post('/api/automation/cancel'))}>Cancelar tarefa do navegador</button>
  {state?.current&&<p role="status">Em execução: {state.current.tool} · {state.current.id}</p>}
  {state?.pending?.map((p:any)=><div className="execution-result" key={p.id}>{p.kind==='site'?<><h4>Autorizar site · {p.host}</h4><p>{p.groups.map((g:string)=>groups[g]).join(' · ')}</p><p className="settings-help">Vale para este domínio exato, nas abas do grupo Harvey. Não autoriza senhas, pagamentos, mensagens ou formulários desconhecidos. Persiste após reinício; cada capacidade pode ser revogada abaixo. Após autorizar, o pedido será revalidado e continuará.</p><button className="secondary-button" disabled={busy} onClick={()=>void act(()=>post('/api/automation/approve/'+p.id))}>Autorizar este site</button></>:<><h4>Ação precisa de revisão</h4><p>{p.name} · {p.element.name||p.element.tag} · {p.element.url}</p><pre>{JSON.stringify(p.arguments,null,2)}</pre><p className="settings-help">Aprovação vale uma vez, por 60 segundos. Mudança de alvo invalida aprovação. Confirme somente se reconhecer o efeito.</p><button className="secondary-button" disabled={busy} onClick={()=>void act(()=>post('/api/automation/approve/'+p.id))}>Autorizar esta ação</button></>}</div>)}
  {state?.site_grants?.some((g:any)=>g.allowed===1)&&<details open><summary>Autorizações por site</summary>{state.site_grants.filter((g:any)=>g.allowed===1).map((g:any)=>{const host=g.scope.slice(5),group=g.capability.slice(11);return <div className="permission-row" key={g.scope+g.capability}><span>{host} · {groups[group]}</span><button className="text-button" disabled={busy} onClick={()=>void act(()=>fetch('/api/automation/sites/revoke',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({host,group})}))}>Revogar {groups[group]?.toLowerCase()} em {host}</button></div>;})}</details>}
  {state?.last&&<details><summary>Último resultado · {state.last.state} · {state.last.elapsed_ms??'—'} ms</summary><pre>{JSON.stringify(state.last,null,2)}</pre></details>}
  <details><summary>Ferramentas descobertas e limites</summary><p className="settings-help">Sem JavaScript do modelo, upload ou cookies. Mídia usa HTMLMediaElement; DRM, anúncios e players externos podem impedir controle. Estado do player não prova áudio físico.</p><ul>{state?.tools?.map((t:any)=><li key={t.name}>{t.name}</li>)}</ul></details>
  {error&&<p role="alert">{error}</p>}
 </article>;
}
