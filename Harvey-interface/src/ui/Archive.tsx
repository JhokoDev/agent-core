import { useCallback, useEffect, useRef, useState } from 'react';
import { History, RefreshCw } from 'lucide-react';
import type { Notify, SessionMetrics, SessionSummary, TranscriptEntry } from '../contracts';
import type { HarveyApi } from '../services/api';
import { TranscriptList, TranscriptToolbar } from './shared';
import { formatSessionDate, formatClock } from './format';
import { sessionStatus } from './session';
import Pagination from './Pagination';
import {IntegrationResults} from './WebBrowserPanel';

export default function Archive({api,selectedRoom,entries,metrics,loading,error,query,onQuery,onSelect,onNotice,onChanged,onDeleted}: {
  api:HarveyApi;selectedRoom:string|null;entries:TranscriptEntry[];metrics:SessionMetrics|null;
  loading:boolean;error:boolean;query:string;onQuery:(s:string)=>void;onSelect:(s:string)=>void;
  onNotice:Notify;onChanged:()=>void;onDeleted:()=>void;
}) {
  const [sessions,setSessions]=useState<SessionSummary[]>([]);
  const [total,setTotal]=useState(0),[offset,setOffset]=useState(0);
  const [search,setSearch]=useState(''),[state,setState]=useState('all');
  const [after,setAfter]=useState(''),[before,setBefore]=useState('');
  const [failed,setFailed]=useState(false),[fetching,setFetching]=useState(true);
  const [editing,setEditing]=useState(false),[title,setTitle]=useState('');
  const [confirm,setConfirm]=useState(false),[busy,setBusy]=useState(false);
  const request=useRef(0);
  const load=useCallback(async()=>{
    const id=++request.current;setFetching(true);setFailed(false);
    try {
      const response=await api.sessions({query:search,state,offset,after:after?new Date(`${after}T00:00:00`).getTime()/1000:undefined,before:before?new Date(`${before}T23:59:59.999`).getTime()/1000:undefined});
      if(!response.ok)throw new Error();const data=await response.json();if(id!==request.current)return;
      if(offset>0&&offset>=data.total){setOffset(Math.max(0,Math.floor((data.total-1)/20)*20));return;}
      setSessions(data.sessions);setTotal(data.total);
    } catch {if(id===request.current)setFailed(true);} finally {if(id===request.current)setFetching(false);}
  },[api,search,state,offset,after,before]);
  useEffect(()=>{const timer=window.setTimeout(()=>void load(),180);return()=>{clearTimeout(timer);request.current++;};},[load]);
  useEffect(()=>{setEditing(false);setConfirm(false);},[selectedRoom]);
  const selected=sessions.find(s=>s.room===selectedRoom);
  const rename=async()=>{
    if(!selectedRoom||busy)return;setBusy(true);
    try{const r=await api.renameSession(selectedRoom,title);if(!r.ok)throw new Error();setEditing(false);await load();onChanged();onNotice('Título atualizado.');}
    catch{onNotice('Não foi possível atualizar o título.','error');}finally{setBusy(false);}
  };
  const remove=async()=>{
    if(!selectedRoom||busy)return;setBusy(true);
    try{const r=await api.deleteSession(selectedRoom);if(r.status===409){onNotice('Encerre a conversa antes de removê-la.','error');return;}if(!r.ok)throw new Error();setConfirm(false);onDeleted();await load();onNotice('Conversa removida.');}
    catch{onNotice('Não foi possível remover a conversa.','error');}finally{setBusy(false);}
  };
  return <section className="archive-page">
    <div className="section-heading"><div><h1>Histórico</h1><p>Consulte e organize suas conversas salvas.</p></div></div>
    <div className="archive-filters">
      <label>Buscar conversas<input aria-label="Buscar conversas" maxLength={100} placeholder="Título ou conteúdo" value={search} onChange={e=>{setSearch(e.target.value);setOffset(0);}}/></label>
      <label>Estado<select value={state} onChange={e=>{setState(e.target.value);setOffset(0);}}><option value="all">Todas</option><option value="closed">Encerradas</option><option value="active">Em andamento</option></select></label>
      <label>De<input type="date" value={after} onChange={e=>{setAfter(e.target.value);setOffset(0);}}/></label>
      <label>Até<input type="date" value={before} onChange={e=>{setBefore(e.target.value);setOffset(0);}}/></label>
    </div>
    {failed && <div className="error-banner" role="alert">Não foi possível carregar as conversas ou o intervalo é inválido. <button className="text-button" onClick={()=>void load()}>Tentar novamente</button></div>}
    <div className="archive-layout"><div className="archive-list">
      <div className="panel-heading"><h2>Conversas</h2><span className="count-badge">{total}</span></div>
      <div className="archive-scroll" aria-busy={fetching}>
        {fetching && <p className="archive-empty" role="status">Carregando conversas…</p>}
        {sessions.map(s=><button key={s.room} className={`archive-row ${s.room===selectedRoom?'archive-row--active':''}`} onClick={()=>onSelect(s.room)}><History size={18}/><div><strong>{s.title||formatSessionDate(s.started_at)}</strong><span>{formatSessionDate(s.started_at)} · {s.message_count} {s.message_count===1?'mensagem':'mensagens'}</span></div></button>)}
        {!fetching&&!failed&&!sessions.length&&<p className="archive-empty">Nenhuma conversa corresponde aos filtros.</p>}
      </div><Pagination offset={offset} total={total} busy={fetching} onPage={setOffset}/>
    </div><div className="archive-detail">
      {selectedRoom ? <>
        <div className="panel-heading archive-detail-head"><div><h2>{selected?.title||metrics?.title||((selected?.started_at||metrics?.started_at)?formatSessionDate((selected?.started_at||metrics?.started_at)!):'Conversa selecionada')}</h2></div><span className="session-state">{selected?sessionStatus(selected):metrics?.status==='active'?'Em andamento':'Salva'}</span></div>
        <div className="archive-actions"><button className="text-button" disabled={busy||loading||error} onClick={()=>{setTitle(selected?.title||metrics?.title||'');setEditing(!editing);setConfirm(false);}}>Renomear conversa</button><button className="text-button danger-text" disabled={busy||loading||error||metrics?.status==='active'} onClick={()=>{setConfirm(!confirm);setEditing(false);}}>Remover conversa</button></div>
        {editing&&<form className="archive-edit" onSubmit={e=>{e.preventDefault();void rename();}}><label>Título<input aria-label="Título da conversa" autoFocus maxLength={120} value={title} onChange={e=>setTitle(e.target.value)}/></label><button className="secondary-button" disabled={busy}>Salvar título</button><button type="button" className="text-button" onClick={()=>setEditing(false)}>Cancelar</button></form>}
        {confirm&&<div className="note-confirm"><span>Remover esta conversa e sua transcrição? Esta ação não pode ser desfeita na interface.</span><button disabled={busy} onClick={()=>void remove()}>Confirmar remoção</button><button onClick={()=>setConfirm(false)}>Cancelar</button></div>}
        <div className="archive-metrics"><span>{metrics?formatClock(metrics.duration_seconds):'—'}</span><span>{metrics?.user_turns??0} {(metrics?.user_turns??0)===1?'fala':'falas'}</span><span>{metrics?.agent_turns??0} {(metrics?.agent_turns??0)===1?'resposta':'respostas'}</span></div>
        <TranscriptToolbar entries={loading||error?[]:entries} query={query} onQuery={onQuery} room={selectedRoom} onNotice={onNotice}/>
        <IntegrationResults key={selectedRoom} api={api} room={selectedRoom}/>
        {error?<div className="error-banner" role="alert">Não foi possível carregar esta conversa.<button className="text-button" onClick={()=>onSelect(selectedRoom)}>Tentar novamente</button></div>:loading?<div className="empty-transcript"><RefreshCw className="spin" size={22}/><p>Carregando conversa…</p></div>:<TranscriptList entries={entries} query={query} emptyText="Esta sessão não tem transcrição disponível."/>}
      </>:<div className="archive-placeholder"><History size={32}/><h3>Selecione uma conversa</h3><p>Consulte a transcrição e as informações da sessão.</p></div>}
    </div></div>
  </section>;
}
