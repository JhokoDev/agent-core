import {useEffect,useState} from 'react';
import type {HarveyApi} from '../services/api';
import {desktopRequest} from '../services/desktop';
import {taskLabels,permissionLabels} from './taskState';
import {responseData} from './ProfileEditor';

export default function DesktopPanel({api}:{api:HarveyApi}){
 const [state,setState]=useState<any>(null),[skill,setSkill]=useState<any>(null),[monitors,setMonitors]=useState<any[]>([]);
 const [monitor,setMonitor]=useState(1),[fps,setFps]=useState(2),[backend,setBackend]=useState('auto'),[region,setRegion]=useState('');
 const [error,setError]=useState(''),[busy,setBusy]=useState(false),[question,setQuestion]=useState('Explique o conteúdo desta tela.');
 const [connectionError,setConnectionError]=useState('');
 const [feedback,setFeedback]=useState('');
 const [review,setReview]=useState(true);
 const load=async()=>{const [s,c]=await Promise.all([desktopRequest('status'),api.capabilities().then(responseData)]);setState(s);setSkill(c.skills.find((x:any)=>x.id==='desktop-control'));};
 useEffect(()=>{let alive=true;const update=async()=>{try{if(alive){await load();setConnectionError('');}}catch{if(alive){setState((previous:any)=>({...previous,state:'disconnected',observing:false}));setConnectionError('Não consegui acessar o computador. Verifique se o Harvey está rodando; a conexão será tentada novamente.');}}};void update();void desktopRequest('monitors').then(setMonitors).catch(()=>{});const timer=setInterval(update,2000);return()=>{alive=false;clearInterval(timer);};},[api]);
 useEffect(()=>{if(state?.capture){setMonitor(state.capture.monitor);setFps(state.capture.fps);setBackend(state.capture.backend);setRegion(state.capture.region?.join(',')||'');}},[JSON.stringify(state?.capture)]);
 useEffect(()=>{setReview(state?.review_unknown_controls!==false);},[state?.review_unknown_controls]);
 const act=async(work:()=>Promise<any>)=>{setBusy(true);setError('');setFeedback('');try{const result=await work();await load();if(['failed','unknown','denied'].includes(result?.state))setError(result.reason);else setFeedback(result?.reason||'Alteração aplicada.');return result;}catch(e){setError((e as Error).message);}finally{setBusy(false);}};
 const granted=(group:string)=>state?.grants?.some((g:any)=>g.capability==='desktop.'+group&&g.scope==='local_device'&&g.allowed===1);
 return <article className="skill-card" data-testid="desktop-panel">
  <div className="skill-heading"><h3>Tela e aplicativos</h3><span role="status">{taskLabels[state?.state]||'Conectando…'}</span></div>
  <p className="settings-help">Compartilhe a tela e permita ações nos aplicativos escolhidos. Imagens não são gravadas; análise visual envia a captura ao modelo.</p>
  {!skill?.installed?<button className="secondary-button" disabled={busy} onClick={()=>void act(()=>api.installSkill('desktop-control').then(responseData))}>Instalar controle do computador</button>:<>
   {skill.reasons?.some((r:string)=>r.startsWith('Pacote mudou'))&&<button className="text-button" onClick={()=>void act(async()=>{const enabled=skill.enabled;await responseData(await api.installSkill('desktop-control'));if(enabled)await responseData(await api.enableSkill('desktop-control',true));})}>Reinstalar controle revisado</button>}
   {Object.entries(state?.groups||{}).map(([group,title])=><div className="permission-row" key={group}><span>{permissionLabels[group]||String(title)}</span><button className="text-button" disabled={busy} onClick={()=>void act(()=>desktopRequest('grant',{group,allowed:!granted(group)}))}>{granted(group)?'Revogar':'Autorizar'} {group==='observe'?'observação':group==='control'?'controle':'análise visual'}</button></div>)}
   <button className="secondary-button" disabled={busy} onClick={()=>void act(()=>api.enableSkill('desktop-control',!skill.enabled).then(responseData))}>{skill.enabled?'Desativar controle do computador':'Ativar controle do computador'}</button>
   <p className="settings-help">Novas ferramentas entram na próxima conversa. Revogação bloqueia ações e para a tarefa atual.</p>
   <form className="extension-form" onSubmit={e=>{e.preventDefault();void act(()=>desktopRequest('config',{monitor,fps,backend,region:region.trim()?region.split(',').map(Number):null,review_unknown_controls:review}));}}>
    <label>Monitor compartilhado<select value={monitor} onChange={e=>setMonitor(Number(e.target.value))}>{monitors.map(m=><option key={m.index} value={m.index}>{m.index} · {m.width}×{m.height} · posição {m.left},{m.top}</option>)}</select></label>
    <details><summary>Ajustes avançados de captura e revisão</summary><label>Capturas por segundo<input type="number" min={1} max={15} value={fps} onChange={e=>setFps(Number(e.target.value))}/></label>
    <label>Captura<select value={backend} onChange={e=>setBackend(e.target.value)}><option value="auto">DXcam com alternativa MSS</option><option value="dxcam">DXcam</option><option value="mss">MSS</option></select></label>
    <label>Região opcional: esquerda, topo, direita, base<input value={region} onChange={e=>setRegion(e.target.value)} placeholder="Vazio: monitor inteiro"/></label>
    <label><input type="checkbox" checked={review} onChange={e=>setReview(e.target.checked)}/> Revisar botões desconhecidos antes de clicar</label>
    <p className="settings-help">Desmarcar amplia cliques nos aplicativos autorizados. Rótulos de envio, exclusão, pagamento e publicação continuam exigindo revisão. A classificação por rótulo não garante reconhecer todos os efeitos externos.</p>
    </details><button className="secondary-button" disabled={busy||state?.observing}>Salvar captura</button>
   </form>
   <button className="secondary-button" disabled={busy||!skill.enabled||!granted('observe')} onClick={()=>void act(()=>desktopRequest('control',{operation:'begin',objective:'Observação manual'}))}>Compartilhar tela</button>
   <label className="extension-form">Pergunta sobre a tela<input value={question} onChange={e=>setQuestion(e.target.value)} maxLength={1000}/></label>
   <button className="secondary-button" disabled={busy||!granted('vision')||!skill.enabled||!state?.visual?.vision} onClick={()=>void act(()=>desktopRequest('execute',{name:'desktop_observe',arguments:{vision:true,question}}))}>Analisar tela agora</button>
   <details><summary>Detalhes do modelo visual</summary><p className="settings-help">Visão: {state?.visual?.vision?state.visual.model:'adaptador ou credencial indisponível'} · formatos: {state?.visual?.formats?.join(', ')||'não declarados'}.</p></details>
   <button className="text-button" disabled={busy} onClick={()=>void act(()=>desktopRequest('control',{operation:'resume'}))}>Retomar tarefa</button>
  </>}
  <button className="secondary-button" onClick={()=>void desktopRequest('control',{operation:'stop'}).then(load).catch(e=>setError(e.message))}>Parar computador</button>
  <p className="settings-help">Emergência local: Ctrl+Alt+Pause. Parar não desfaz ações concluídas. Captura e chamadas ao modelo têm frequências distintas.</p>
  {state?.pending?.map((p:any)=><div className="execution-result" key={p.id}><h4>{p.kind==='application'?'Autorizar aplicativo':'Revisar ação'} · {p.display_name||p.process.replace('.exe','')}</h4><p>{p.action} {p.target?.name}</p>{p.arguments&&<details><summary>Detalhes da ação solicitada</summary><pre>{JSON.stringify(p.arguments,null,2)}</pre></details>}<p className="settings-help">{p.kind==='application'?'Permite interação rotineira neste aplicativo. Ações visuais desconhecidas ou relevantes continuam exigindo revisão. Após autorizar, a tarefa será retomada com uma nova observação.':'Vale uma vez, durante 60 segundos; alteração do alvo invalida a aprovação.'}</p><button className="secondary-button" disabled={busy} onClick={()=>void act(()=>desktopRequest('approve/'+p.id,{}))}>Autorizar {p.kind==='application'?'aplicativo':'ação local'}</button><button className="text-button" disabled={busy} onClick={()=>void act(()=>desktopRequest('deny/'+p.id,{}))}>Negar acesso</button><button className="text-button" onClick={()=>void act(()=>desktopRequest('control',{operation:'stop'}))}>Cancelar pedido</button></div>)}
  <h4>Aplicativos autorizados</h4>{state?.grants?.filter((g:any)=>g.scope.startsWith('app:')&&g.allowed===1).map((g:any)=><div className="permission-row" key={g.scope}><span>{g.display_name||g.scope.slice(4)}</span><button className="text-button" onClick={()=>void act(()=>desktopRequest('grant',{group:'control',scope:g.scope,allowed:false}))}>Revogar {g.display_name||g.scope.slice(4)}</button></div>)}
  {state?.task?.last_observation?.visual&&<div className="execution-result"><p>{state.task.last_observation.visual.description}</p><small>Modelo visual: {state.task.last_observation.visual.visual_model} · {state.task.last_observation.visual.model_ms} ms</small></div>}
  <details><summary>Detalhes técnicos da tarefa</summary>{state?.frame&&<p className="settings-help">{state.frame.backend} · {state.frame.width}×{state.frame.height} · captura {state.frame.capture_ms} ms · mudança {state.frame.change_score}</p>}
  <div><pre>{JSON.stringify(state?.task,null,2)}</pre></div></details>
  {state?.task?.reason&&<p role="status">{state.task.reason}</p>}{feedback&&<p role="status">{feedback}</p>}
  {connectionError&&<p role="alert">{connectionError}</p>}
  {error&&<p role="alert">{error}</p>}
 </article>;
}
