import React, { useState, useRef, useEffect } from 'react';
import { Terminal, Send, Bot, User, History, Plus, Trash2, X } from 'lucide-react';

const estilosPlayground = `
  .pg-container { display: flex; flex-direction: column; height: 100%; padding: 2rem; box-sizing: border-box; }
  .pg-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.2rem; flex-wrap: wrap; gap: 1rem; }
  .header-actions { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
  .btn-top-action { display: flex; align-items: center; gap: 0.4rem; background: #1e293b; color: #f8fafc; border: 1px solid #334155; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 0.85rem; font-weight: 600; transition: all 0.2s; }
  .btn-top-action:hover { background: #334155; }
  .btn-top-novo { background: #2563eb; border-color: #3b82f6; }
  .btn-top-novo:hover { background: #1d4ed8; }
  .select-agente { background: #0f172a; color: #a5b4fc; border: 1px solid #334155; padding: 6px 10px; border-radius: 6px; font-size: 0.85rem; font-weight: 600; outline: none; cursor: pointer; }
  
  .chat-box { flex: 1; background: #1e293b; border-radius: 12px; padding: 1.5rem; overflow-y: auto; display: flex; flex-direction: column; gap: 1.5rem; box-shadow: inset 0 4px 6px rgba(0,0,0,0.3); }
  .msg-wrapper { display: flex; gap: 1rem; }
  .msg-wrapper.user { flex-direction: row-reverse; }
  .msg-icon { width: 40px; height: 40px; border-radius: 8px; display: flex; justify-content: center; align-items: center; flex-shrink: 0; color: #fff; }
  .msg-icon.user { background: #3b82f6; }
  .msg-icon.ai { background: #10b981; }
  .msg-content { padding: 1rem 1.5rem; border-radius: 12px; color: #f8fafc; max-width: 80%; line-height: 1.5; white-space: pre-wrap; word-wrap: break-word; }
  .msg-content.user { background: #2563eb; }
  .msg-content.ai { background: #334155; font-family: Consolas, monospace; }
  .msg-badge { display: inline-block; font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; margin-bottom: 6px; font-weight: bold; }
  .msg-badge.nuvem { background: rgba(37, 99, 235, 0.2); color: #60a5fa; border: 1px solid rgba(37, 99, 235, 0.4); }
  .msg-badge.local { background: rgba(99, 102, 241, 0.2); color: #a5b4fc; border: 1px solid rgba(99, 102, 241, 0.4); }
  
  .active-chat-bar { display: flex; align-items: center; justify-content: space-between; background: #0f172a; border: 1px solid #1e293b; padding: 0.5rem 1rem; border-radius: 8px; margin-bottom: 0.75rem; font-size: 0.85rem; }
  
  .input-form { display: flex; gap: 1rem; margin-top: 1.5rem; }
  .input-box { flex: 1; padding: 1rem; background: #020617; border: 1px solid #334155; border-radius: 8px; color: #f8fafc; font-size: 1rem; outline: none; transition: border 0.2s; }
  .input-box:focus { border-color: #38bdf8; }
  .btn-enviar { background: #38bdf8; color: #020617; border: none; padding: 0 1.5rem; border-radius: 8px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: opacity 0.2s; }
  .btn-enviar:disabled { opacity: 0.5; cursor: not-allowed; }

  /* Modal de Histórico */
  .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 1rem; }
  .modal-card { background: #0f172a; border: 1px solid #334155; border-radius: 12px; width: 100%; max-width: 600px; max-height: 80vh; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5); }
  .modal-header { display: flex; align-items: center; justify-content: space-between; padding: 1.25rem 1.5rem; border-bottom: 1px solid #1e293b; }
  .modal-search { padding: 0.75rem 1.5rem; border-bottom: 1px solid #1e293b; }
  .modal-search input { width: 100%; background: #020617; border: 1px solid #334155; border-radius: 6px; padding: 0.6rem 0.8rem; color: #f8fafc; font-size: 0.9rem; outline: none; box-sizing: border-box; }
  .modal-list { flex: 1; overflow-y: auto; padding: 1rem 1.5rem; display: flex; flex-direction: column; gap: 0.75rem; }
  .chat-item { background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 0.85rem 1rem; cursor: pointer; display: flex; justify-content: space-between; align-items: center; transition: all 0.2s; }
  .chat-item:hover { border-color: #38bdf8; background: #243247; }
  .chat-item.active { border-color: #38bdf8; background: #1a365d; }
  .chat-item-title { font-weight: bold; color: #f8fafc; font-size: 0.95rem; margin-bottom: 0.25rem; }
  .chat-item-preview { color: #94a3b8; font-size: 0.8rem; line-height: 1.3; }
  .chat-item-meta { display: flex; gap: 0.5rem; align-items: center; margin-top: 0.4rem; font-size: 0.75rem; color: #64748b; }
  .chat-delete-btn { background: transparent; border: none; color: #ef4444; cursor: pointer; padding: 6px; border-radius: 4px; display: flex; align-items: center; opacity: 0.7; }
  .chat-delete-btn:hover { opacity: 1; background: rgba(239,68,68,0.1); }

  @media (max-width: 768px) {
    .pg-container { padding: 1rem; height: calc(100vh - 75px); }
    .pg-header h1 { font-size: 1.5rem; margin: 0; }
    .chat-box { padding: 1rem; gap: 1rem; }
    .msg-content { max-width: 90%; padding: 0.75rem 1rem; }
    .input-form { gap: 0.5rem; margin-top: 1rem; }
    .input-box { font-size: 16px; padding: 0.75rem; }
    .btn-enviar { padding: 0 1rem; }
  }
`;

export default function Playground() {
  const [mensagens, setMensagens] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [provedor, setProvedor] = useState('nuvem');
  const [currentChatId, setCurrentChatId] = useState(null);
  const [currentChatTitle, setCurrentChatTitle] = useState('Novo Chat');
  const [selectedSkill, setSelectedSkill] = useState('default');

  // Histórico e Agentes
  const [historyModalOpen, setHistoryModalOpen] = useState(false);
  const [chatsList, setChatsList] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [historySearch, setHistorySearch] = useState('');
  const [agentesList, setAgentesList] = useState([]);

  const endOfMessagesRef = useRef(null);
  const AUTH_HEADER = { 'Authorization': 'Bearer minhasenha_super_segura_de_32_caracteres_minimo_aqui' };

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [mensagens]);

  useEffect(() => {
    carregarAgentes();
  }, []);

  const carregarAgentes = async () => {
    try {
      const res = await fetch('/agentes', { headers: AUTH_HEADER });
      if (res.ok) {
        const data = await res.json();
        setAgentesList(data);
      }
    } catch {}
  };

  const abrirHistorico = async () => {
    setLoadingHistory(true);
    setHistoryModalOpen(true);
    try {
      const res = await fetch('/chats', { headers: AUTH_HEADER });
      if (res.ok) {
        const data = await res.json();
        setChatsList(data);
      }
    } catch (e) {
      alert('Falha ao listar histórico de chats');
    } finally {
      setLoadingHistory(false);
    }
  };

  const selecionarChat = async (chatItem) => {
    try {
      setLoadingHistory(true);
      const res = await fetch(`/chats/${chatItem.id}`, { headers: AUTH_HEADER });
      if (res.ok) {
        const data = await res.json();
        const msgs = (data.messages || []).map((m) => ({
          role: m.role === 'assistant' ? 'ai' : m.role,
          content: m.content || '',
          provedor: m.provedor || 'nuvem'
        }));
        setMensagens(msgs);
        setCurrentChatId(data.id);
        setCurrentChatTitle(data.titulo || chatItem.titulo || 'Conversa Antiga');
        setHistoryModalOpen(false);
      }
    } catch (e) {
      alert('Falha ao carregar conversa anterior');
    } finally {
      setLoadingHistory(false);
    }
  };

  const iniciarNovoChat = () => {
    setCurrentChatId(null);
    setCurrentChatTitle('Novo Chat');
    setMensagens([]);
    setHistoryModalOpen(false);
  };

  const deletarChat = async (e, chatId) => {
    e.stopPropagation();
    if (!window.confirm('Deseja excluir permanentemente esta conversa?')) return;
    try {
      await fetch(`/chats/${chatId}`, { method: 'DELETE', headers: AUTH_HEADER });
      if (currentChatId === chatId) {
        iniciarNovoChat();
      }
      const res = await fetch('/chats', { headers: AUTH_HEADER });
      if (res.ok) {
        const data = await res.json();
        setChatsList(data);
      }
    } catch (err) {
      alert('Falha ao excluir conversa.');
    }
  };

  const enviarMensagem = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const textoUsuario = input;
    setInput('');
    setMensagens(prev => [...prev, { role: 'user', content: textoUsuario }]);
    setIsLoading(true);
    setMensagens(prev => [...prev, { role: 'ai', content: '', provedor }]);

    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...AUTH_HEADER
        },
        body: JSON.stringify({
          texto: textoUsuario,
          chat_id: currentChatId || undefined,
          skill_id: selectedSkill,
          provedor
        })
      });

      if (!response.ok) throw new Error('Falha na comunicação.');

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const blocos = buffer.split('\n\n');
        buffer = blocos.pop() || '';

        for (const bloco of blocos) {
          if (bloco.startsWith('data: ')) {
            const jsonStr = bloco.replace('data: ', '').trim();
            if (!jsonStr) continue;
            try {
              const dados = JSON.parse(jsonStr);
              if (dados.chat_id && !currentChatId) {
                setCurrentChatId(dados.chat_id);
                setCurrentChatTitle(textoUsuario.slice(0, 35));
              }
              if (dados.type === 'message') {
                setMensagens(prev => {
                  const historico = [...prev];
                  historico[historico.length - 1].content = dados.content;
                  historico[historico.length - 1].provedor = dados.provedor || provedor;
                  return historico;
                });
              }
            } catch (err) {}
          }
        }
      }
    } catch (erro) {
      setMensagens(prev => {
        const historico = [...prev];
        historico[historico.length - 1].content = 'Erro: Motor offline ou ligação recusada.';
        return historico;
      });
    } finally {
      setIsLoading(false);
    }
  };

  const chatsFiltrados = chatsList.filter((c) => {
    if (!historySearch.trim()) return true;
    const q = historySearch.toLowerCase();
    return (c.titulo || '').toLowerCase().includes(q) || (c.preview || '').toLowerCase().includes(q);
  });

  return (
    <>
      <style>{estilosPlayground}</style>
      <div className="pg-container">
        <div className="pg-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Terminal size={28} color="#38bdf8" />
            <h1 style={{ margin: 0 }}>Playground</h1>
          </div>

          <div className="header-actions">
            {/* Botão de Histórico */}
            <button type="button" className="btn-top-action" onClick={abrirHistorico}>
              <History size={16} />
              <span>Histórico de Chats</span>
            </button>

            {/* Botão de Novo Chat */}
            <button type="button" className="btn-top-action btn-top-novo" onClick={iniciarNovoChat}>
              <Plus size={16} />
              <span>Novo Chat</span>
            </button>

            {/* Seletor de Agente / Skill */}
            <select
              className="select-agente"
              value={selectedSkill}
              onChange={(e) => setSelectedSkill(e.target.value)}
            >
              <option value="default">🤖 Assistente Padrão</option>
              {agentesList.filter(a => a.id !== 'default').map((a) => (
                <option key={a.id} value={a.id}>
                  {a.icone || '⚡'} {a.nome}
                </option>
              ))}
            </select>

            {/* Seletor de Motor IA: Nuvem vs Local */}
            <div style={{ display: 'flex', alignItems: 'center', background: '#0f172a', padding: '4px', borderRadius: '8px', border: '1px solid #334155', gap: '4px' }}>
              <button
                type="button"
                onClick={() => setProvedor('nuvem')}
                style={{
                  background: provedor === 'nuvem' ? '#2563eb' : 'transparent',
                  color: provedor === 'nuvem' ? '#fff' : '#94a3b8',
                  border: 'none',
                  padding: '6px 14px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontWeight: 'bold',
                  fontSize: '0.85rem',
                  transition: 'all 0.2s'
                }}
              >
                ☁️ Nuvem (Gemini)
              </button>
              <button
                type="button"
                onClick={() => setProvedor('local')}
                style={{
                  background: provedor === 'local' ? '#4f46e5' : 'transparent',
                  color: provedor === 'local' ? '#fff' : '#94a3b8',
                  border: 'none',
                  padding: '6px 14px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontWeight: 'bold',
                  fontSize: '0.85rem',
                  transition: 'all 0.2s'
                }}
              >
                💻 Local (Ollama)
              </button>
            </div>
          </div>
        </div>

        {/* Barra de Conversa Ativa */}
        {currentChatId && (
          <div className="active-chat-bar">
            <div>
              <span style={{ color: '#38bdf8', fontWeight: 'bold' }}>📌 Conversa Ativa: </span>
              <span style={{ color: '#f8fafc' }}>{currentChatTitle}</span>
            </div>
            <button
              onClick={iniciarNovoChat}
              style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '0.8rem' }}
            >
              Limpar / Novo
            </button>
          </div>
        )}

        <div className="chat-box">
          {mensagens.length === 0 && (
            <div style={{ textAlign: 'center', color: '#64748b', margin: 'auto' }}>
              Envie uma mensagem para iniciar o fluxo neural ou clique em <strong>Histórico</strong> para retomar conversas anteriores.
            </div>
          )}

          {mensagens.map((msg, idx) => (
            <div key={idx} className={`msg-wrapper ${msg.role}`}>
              <div className={`msg-icon ${msg.role}`}>
                {msg.role === 'user' ? <User size={20} /> : <Bot size={20} />}
              </div>
              
              <div className={`msg-content ${msg.role}`}>
                {msg.role === 'ai' && (
                  <div className={`msg-badge ${msg.provedor === 'nuvem' ? 'nuvem' : 'local'}`}>
                    {msg.provedor === 'nuvem' ? '☁️ Nuvem (Gemini)' : '💻 Local (Ollama)'}
                  </div>
                )}
                <div>{msg.content || (msg.role === 'ai' && <span style={{ opacity: 0.5 }}>A processar...</span>)}</div>
              </div>
            </div>
          ))}
          <div ref={endOfMessagesRef} />
        </div>

        <form onSubmit={enviarMensagem} className="input-form">
          <input 
            type="text" 
            className="input-box"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Comunique com o Agente..."
            disabled={isLoading}
          />
          <button type="submit" className="btn-enviar" disabled={isLoading || !input.trim()}>
            <Send size={20} />
          </button>
        </form>
      </div>

      {/* Modal de Histórico */}
      {historyModalOpen && (
        <div className="modal-overlay" onClick={() => setHistoryModalOpen(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <History size={20} color="#38bdf8" />
                <h3 style={{ margin: 0, color: '#f8fafc' }}>Histórico de Conversas</h3>
              </div>
              <button
                onClick={() => setHistoryModalOpen(false)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            <div className="modal-search">
              <input
                type="text"
                placeholder="🔍 Buscar conversa por título ou mensagem..."
                value={historySearch}
                onChange={(e) => setHistorySearch(e.target.value)}
              />
            </div>

            <div className="modal-list">
              {loadingHistory ? (
                <div style={{ textAlign: 'center', color: '#94a3b8', padding: '2rem' }}>Carregando histórico...</div>
              ) : chatsFiltrados.length === 0 ? (
                <div style={{ textAlign: 'center', color: '#64748b', padding: '2rem' }}>Nenhuma conversa encontrada.</div>
              ) : (
                chatsFiltrados.map((c) => (
                  <div
                    key={c.id}
                    className={`chat-item ${c.id === currentChatId ? 'active' : ''}`}
                    onClick={() => selecionarChat(c)}
                  >
                    <div style={{ flex: 1, minWidth: 0, marginRight: '1rem' }}>
                      <div className="chat-item-title">{c.titulo}</div>
                      {c.preview && <div className="chat-item-preview">{c.preview}</div>}
                      <div className="chat-item-meta">
                        <span>💬 {c.mensagem_count} mensagens</span>
                        <span>•</span>
                        <span>{new Date(c.atualizado_em * 1000).toLocaleString()}</span>
                      </div>
                    </div>
                    <button
                      className="chat-delete-btn"
                      title="Excluir conversa"
                      onClick={(e) => deletarChat(e, c.id)}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
