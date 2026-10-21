import React, { useState, useRef, useEffect } from 'react';
import { Terminal, Send, Bot, User } from 'lucide-react';

const estilosPlayground = `
  .pg-container { display: flex; flex-direction: column; height: 100%; padding: 2rem; box-sizing: border-box; }
  .pg-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem; flex-wrap: wrap; gap: 1rem; }
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
  
  .input-form { display: flex; gap: 1rem; margin-top: 1.5rem; }
  .input-box { flex: 1; padding: 1rem; background: #020617; border: 1px solid #334155; border-radius: 8px; color: #f8fafc; font-size: 1rem; outline: none; transition: border 0.2s; }
  .input-box:focus { border-color: #38bdf8; }
  .btn-enviar { background: #38bdf8; color: #020617; border: none; padding: 0 1.5rem; border-radius: 8px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: opacity 0.2s; }
  .btn-enviar:disabled { opacity: 0.5; cursor: not-allowed; }

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
  const endOfMessagesRef = useRef(null);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [mensagens]);

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
          'Authorization': 'Bearer minhasenha_super_segura_de_32_caracteres_minimo_aqui'
        },
        body: JSON.stringify({ texto: textoUsuario, skill_id: 'default', provedor })
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

  return (
    <>
      <style>{estilosPlayground}</style>
      <div className="pg-container">
        <div className="pg-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Terminal size={28} color="#38bdf8" />
            <h1 style={{ margin: 0 }}>Playground</h1>
          </div>

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

        <div className="chat-box">
          {mensagens.length === 0 && (
            <div style={{ textAlign: 'center', color: '#64748b', margin: 'auto' }}>
              Envie uma mensagem para iniciar o fluxo neural.
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
    </>
  );
}
