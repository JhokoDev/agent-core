import React, { useState, useEffect } from 'react';
import { Settings, Folder, HardDrive, Network, Smartphone, Key, Trash2, Database, ShieldCheck, AlertCircle } from 'lucide-react';

const estilosSistema = `
  .sys-container { padding: 2rem; color: #f8fafc; }
  .grid-sistema { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1.5rem; }
  .sys-card { background: #1e293b; border-radius: 12px; padding: 1.5rem; border: 1px solid #334155; box-shadow: 0 4px 6px rgba(0,0,0,0.2); }
  .sys-card-header { display: flex; align-items: center; gap: 0.75rem; border-bottom: 1px solid #334155; padding-bottom: 1rem; margin-bottom: 1rem; color: #cbd5e1; font-weight: bold; font-size: 1.1rem; }
  
  .info-row { display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 0; border-bottom: 1px solid rgba(255,255,255,0.05); }
  .info-row:last-child { border-bottom: none; }
  .info-label { color: #94a3b8; font-size: 0.9rem; display: flex; align-items: center; gap: 0.5rem; }
  .info-value { font-family: Consolas, monospace; color: #a5d6ff; background: #0f172a; padding: 0.25rem 0.5rem; border-radius: 6px; font-size: 0.85rem; }
  
  .btn-danger { width: 100%; background: #7f1d1d; color: #f8fafc; border: 1px solid #991b1b; padding: 0.75rem; border-radius: 8px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 0.5rem; transition: background 0.2s; margin-top: 1rem; }
  .btn-danger:hover { background: #991b1b; }
  
  @media (max-width: 768px) {
    .sys-container { padding: 1rem; height: calc(100vh - 75px); overflow-y: auto; }
    .info-row { flex-direction: column; align-items: flex-start; gap: 0.5rem; }
    .info-value { word-break: break-all; width: 100%; }
  }
`;

export default function Sistema() {
  const [dados, setDados] = useState(null);

  const carregarDados = async () => {
    try {
      const res = await fetch('/api/system/advanced');
      if (res.ok) setDados(await res.json());
    } catch (e) {
      console.error("Erro ao carregar sistema", e);
    }
  };

  useEffect(() => { carregarDados(); }, []);

  const limparLogs = async () => {
    if (window.confirm('Tem a certeza que deseja esvaziar os logs do servidor?')) {
      await fetch('/api/system/clear-logs', { method: 'POST' });
      carregarDados();
    }
  };

  return (
    <>
      <style>{estilosSistema}</style>
      <div className="sys-container">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '2rem' }}>
          <Settings size={28} color="#38bdf8" />
          <h1 style={{ margin: 0 }}>Gestão de Sistema</h1>
        </div>

        {!dados ? <p style={{ color: '#8b949e' }}>A varrer infraestrutura...</p> : (
          <div className="grid-sistema">
            
            {/* CARD: REDE E SERVIDOR */}
            <div className="sys-card">
              <div className="sys-card-header">
                <Network size={20} color="#38bdf8"/> Rede e Portas
              </div>
              <div className="info-row">
                <div className="info-label"><Smartphone size={16}/> Acesso Telemóvel</div>
                <div className="info-value" style={{ color: '#10b981' }}>http://{dados.network.ip_local}:5173</div>
              </div>
              <div className="info-row">
                <div className="info-label">Porta Motor IA (Ollama/Proxy)</div>
                <div className="info-value">{dados.network.porta_motor}</div>
              </div>
              <div className="info-row">
                <div className="info-label">Porta Backend (Lançador)</div>
                <div className="info-value">{dados.network.porta_api}</div>
              </div>
            </div>

            {/* CARD: ARMAZENAMENTO */}
            <div className="sys-card">
              <div className="sys-card-header">
                <Database size={20} color="#8b5cf6"/> Armazenamento Local
              </div>
              {dados.storage.map((dir, idx) => (
                <div className="info-row" key={idx}>
                  <div className="info-label"><Folder size={16}/> {dir.nome}</div>
                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', width: '100%' }}>
                    <div className="info-value" style={{ flex: 1, color: '#64748b', fontSize: '0.75rem' }}>{dir.caminho}</div>
                    <div className="info-value" style={{ background: '#1e293b', border: '1px solid #38bdf8', color: '#38bdf8' }}>{dir.tamanho}</div>
                  </div>
                </div>
              ))}
            </div>

            {/* CARD: SEGURANÇA E MANUTENÇÃO */}
            <div className="sys-card">
              <div className="sys-card-header">
                <ShieldCheck size={20} color="#f59e0b"/> Configuração e Manutenção
              </div>
              <div className="info-row">
                <div className="info-label"><Key size={16}/> Variáveis Globais (.env)</div>
                <div className="info-value" style={{ color: dados.config.env_exists ? '#10b981' : '#ef4444' }}>
                  {dados.config.env_exists ? 'Configurado' : 'Ausente'}
                </div>
              </div>
              <div className="info-row">
                <div className="info-label"><AlertCircle size={16}/> Peso do Ficheiro de Logs</div>
                <div className="info-value">{dados.config.log_size}</div>
              </div>
              <button className="btn-danger" onClick={limparLogs}>
                <Trash2 size={18} /> Esvaziar Cache de Logs
              </button>
            </div>

          </div>
        )}
      </div>
    </>
  );
}