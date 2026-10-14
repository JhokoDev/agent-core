import { useCallback, useEffect, useRef, useState } from 'react';
import { Check, Plus, Search, StickyNote, Trash2, X, Pencil, Clipboard, ArrowDownToLine } from 'lucide-react';

import type { Note, Notify } from './contracts';
import type { HarveyApi } from './services/api';
import Pagination from './ui/Pagination';

export default function NotesPage({ api, onNotice }: { api: HarveyApi; onNotice: Notify }) {
  const [notes, setNotes] = useState<Note[]>([]);
  const [query, setQuery] = useState('');
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [editingId,setEditingId]=useState<number|null>(null);
  const [editText,setEditText]=useState('');
  const [offset,setOffset]=useState(0),[total,setTotal]=useState(0);
  const request=useRef(0);

  const refresh = useCallback(async (search: string, signal?: AbortSignal) => {
    const id=++request.current;
    try {
      const response = await api.notes(search, signal, offset);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (!signal?.aborted && id===request.current) {
        if(offset>0&&offset>=data.total){setOffset(Math.max(0,Math.floor((data.total-1)/20)*20));return;}
        setNotes(data.notes || []); setTotal(data.total); setFailed(false);
      }
    } catch (error) {
      if (!signal?.aborted && id===request.current) setFailed(true);
    } finally {
      if (!signal?.aborted && id===request.current) setLoading(false);
    }
  }, [api, offset]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    const timer = window.setTimeout(() => void refresh(query, controller.signal), 180);
    const poll = window.setInterval(() => void refresh(query, controller.signal), 5000);
    return () => { window.clearTimeout(timer); window.clearInterval(poll); controller.abort(); };
  }, [query, refresh]);

  const addNote = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!draft.trim() || busy) return;
    setBusy(true);
    try {
      const response = await api.addNote(draft.trim());
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setDraft('');
      onNotice('Nota salva.');
      await refresh(query);
    } catch {
      onNotice('Não foi possível salvar a nota.', 'error');
    } finally { setBusy(false); }
  };

  const saveEdit=async(id:number)=>{
    if(busy||!editText.trim())return;setBusy(true);
    try{const r=await api.updateNote(id,editText.trim());if(!r.ok)throw new Error();setEditingId(null);await refresh(query);onNotice('Nota atualizada.');}
    catch{onNotice('Não foi possível atualizar a nota.','error');}finally{setBusy(false);}
  };
  const copyNote=async(note:Note)=>{
    try{await navigator.clipboard.writeText(note.text);onNotice('Nota copiada.');}catch{onNotice('Não foi possível copiar a nota.','error');}
  };
  const exportNote=(note:Note)=>{
    const url=URL.createObjectURL(new Blob([note.text+'\n'],{type:'text/plain;charset=utf-8'}));const link=document.createElement('a');link.href=url;link.download=`harvey-nota-${note.id}.txt`;link.click();window.setTimeout(()=>URL.revokeObjectURL(url),1000);
  };

  const removeNote = async (id: number) => {
    setBusy(true);
    try {
      const response = await api.deleteNote(id);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setDeletingId(null);
      onNotice('Nota removida.');
      await refresh(query);
    } catch {
      onNotice('Não foi possível remover a nota.', 'error');
    } finally { setBusy(false); }
  };

  return (
    <section className="notes-page">
      <div className="section-heading">
        <div><p className="eyebrow">MEMÓRIA LOCAL</p><h1>Notas</h1><p>O que você pedir ao Harvey para guardar aparece aqui.</p></div>
      </div>
      <div className="notes-layout">
        <form className="note-composer" onSubmit={(event) => void addNote(event)}>
          <div className="settings-icon"><StickyNote size={23} /></div>
          <h2>Nova nota</h2>
          <p>Guarde algo agora ou diga ao Harvey “anote...” durante uma conversa.</p>
          <label htmlFor="note-text">Conteúdo</label>
          <textarea id="note-text" value={draft} onChange={(event) => setDraft(event.target.value)} maxLength={1000} rows={5} placeholder="Escreva sua nota aqui..." />
          <div className="note-compose-footer"><span>{draft.length}/1000</span><button className="primary-button" disabled={!draft.trim() || busy}><Plus size={16} /> Salvar nota</button></div>
        </form>
        <div className="notes-list-panel">
          <div className="panel-heading"><div><p className="eyebrow">SALVAS NESTE COMPUTADOR</p><h2>Suas notas</h2></div><span className="count-badge">{total}</span></div>
          <label className="search-field notes-search"><Search size={16} /><input value={query} onChange={(event) => {setQuery(event.target.value);setOffset(0);}} maxLength={100} placeholder="Buscar nas notas" aria-label="Buscar nas notas" /></label>
          <div className="notes-list">
            {loading && <p className="notes-empty">Carregando notas...</p>}
            {failed && <div className="error-banner" role="alert">Não foi possível carregar as notas. <button className="text-button" onClick={() => void refresh(query)}>Tentar novamente</button></div>}
            {!loading && !failed && !notes.length && <div className="notes-empty"><StickyNote size={25} /><p>{query ? 'Nenhuma nota corresponde à busca.' : 'Sua primeira nota aparecerá aqui.'}</p></div>}
            {notes.map((note) => (
              <article className="note-card" key={note.id}>
                <div className="note-card-head"><time>{new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(note.created_at * 1000))}</time><div className="note-actions">
                  <button className="icon-button" onClick={()=>{setEditingId(note.id);setEditText(note.text);setDeletingId(null);}} aria-label="Editar nota" title="Editar nota"><Pencil size={16}/></button>
                  <button className="icon-button" onClick={()=>void copyNote(note)} aria-label="Copiar nota" title="Copiar nota"><Clipboard size={16}/></button>
                  <button className="icon-button" onClick={()=>exportNote(note)} aria-label="Exportar nota" title="Exportar nota"><ArrowDownToLine size={16}/></button>
                  <button className="icon-button" onClick={() => {setDeletingId(note.id);setEditingId(null);}} aria-label="Remover nota" title="Remover nota"><Trash2 size={16} /></button></div></div>
                <p>{note.text}</p>
                {editingId===note.id&&<form className="note-edit" onSubmit={e=>{e.preventDefault();void saveEdit(note.id);}}><label>Editar conteúdo<textarea aria-label="Editar conteúdo da nota" value={editText} maxLength={1000} rows={4} onChange={e=>setEditText(e.target.value)}/></label><button className="secondary-button" disabled={busy||!editText.trim()}>Salvar alterações</button><button type="button" className="text-button" onClick={()=>setEditingId(null)}>Cancelar</button></form>}
                {deletingId === note.id && <div className="note-confirm"><span>Remover esta nota?</span><button onClick={() => void removeNote(note.id)} disabled={busy}><Check size={15} /> Remover</button><button onClick={() => setDeletingId(null)}><X size={15} /> Cancelar</button></div>}
              </article>
            ))}
          </div>
          <Pagination offset={offset} total={total} busy={loading} onPage={setOffset}/>
        </div>
      </div>
    </section>
  );
}
