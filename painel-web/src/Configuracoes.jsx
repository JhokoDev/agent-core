import React, { useState, useEffect } from 'react';
import { Settings, Brain, Cpu, MessageSquare, Save, AlertCircle } from 'lucide-react';

const estilosConfig = `
  .cfg-container { padding: 2rem; color: #f8fafc; max-width: 1200px; margin: 0 auto; }
  .cfg-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 1.5rem; }
  .cfg-card { background: #1e293b; border-radius: 12px; padding: 1.5rem; border: 1px solid #334155; }
  .cfg-header { display: flex; align-items: center; gap: 0.75rem; border-bottom: 1px solid #334155; padding-bottom: 1rem; margin-bottom: 1.5rem; color: #38bdf8; font-weight: bold; font-size: 1.1rem; }
  
  .form-group { margin-bottom: 1.25rem; }
  .form-label { display: block; color: #94a3b8; font-size: 0.9rem; margin-bottom: 0.5rem; }
  .form-input, .form-select, .form-textarea { width: 100%; background: #0f172a; border: 1px solid #334155; border-radius: 8px; color: #f8fafc; padding: 0.75rem; font-family: inherit; transition: border-color 0.2s; }
  .form-input:focus, .form-select:focus, .form-textarea:focus { outline: none; border-color: #38bdf8; }
  .form-textarea { resize: vertical; min-height: 100px; }
  
  .checkbox-group { display: flex; align-items: center; gap: 0.75rem; cursor: pointer; }
  .checkbox-input { width: 1.2rem; height: 1.2rem; cursor: pointer; accent-color: #38bdf8; }
  
  .btn-salvar { background: #10b981; color: #020617; border: none; padding: 1rem 2rem; border-radius: 8px; font-weight: bold; cursor: pointer; display: flex; align-items: center; gap: 0.5rem; margin-top: 2rem; transition: transform 0.1s; }
  .btn-salvar:active { transform: scale(0.98); }
  .btn-salvar:disabled { opacity: 0.5; cursor: not-allowed; }
  
  .toast { position: fixed; bottom: 2rem; right: 2rem; background: #10b981; color: #020617; padding: 1rem 2rem; border-radius: 8px; font-weight: bold; box-shadow: 0 4px 12px rgba(0,0,0,0.3); animation: slideUp 0.3s ease-out; }
  @keyframes slideUp { from { transform: translateY(100%); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
`;

export default function Configuracoes() {
  const [config, setConfig] = useState(null);
  const [modelos, setModelos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [toast, setToast] = useState(false);

  useEffect(() => {
    // Carrega a configuração global e a lista de modelos instalados simultaneamente
    Promise.all([
      fetch('/api/config').then(res => res.json()),
      fetch('/api/system/models').then(res => res.json())
    ])
    .then(([dadosConfig, dadosModelos]) => {
      setConfig(dadosConfig);
      setModelos(dadosModelos.modelos || []);
      setLoading(false);
    })
    .catch(err => console.error("Erro ao carregar os dados:", err));
  }, []);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    let val = type === 'checkbox' ? checked : value;
    if (type === 'number' || type === 'range') val = Number(value);
    setConfig(prev => ({ ...prev, [name]: val }));
  };

  const salvarConfig = async () => {
    setSalvando(true);
    try {
      await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      setToast(true);
      setTimeout(() => setToast(false), 3000);
    } catch (e) {
      alert("Erro ao guardar definições.");
    }
    setSalvando(false);
  };

  if (loading) return <div style={{ padding: '2rem', color: '#94a3b8' }}>A carregar matriz de configurações...</div>;

  return (
    <>
      <style>{estilosConfig}</style>
      <div className="cfg-container">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '2rem' }}>
          <Settings size={32} color="#38bdf8" />
          <h1 style={{ margin: 0 }}>Configurações do Agente</h1>
        </div>

        <div className="cfg-grid">
          {/* PAINEL 1: MOTOR IA */}
          <div className="cfg-card">
            <div className="cfg-header"><Brain size={20} /> Motor Lógico (LLM)</div>
            
            <div className="form-group">
              <label className="form-label">Modelo Ativo (Local)</label>
              <select name="modelo_ativo" className="form-select" value={config.modelo_ativo} onChange={handleChange}>
                {modelos.length === 0 && <option value={config.modelo_ativo}>{config.modelo_ativo}</option>}
                {modelos.map(mod => (
                  <option key={mod} value={mod}>{mod}</option>
                ))}
                {/* Mostra o modelo atual mesmo se não for detetado (por segurança) */}
                {config.modelo_ativo && !modelos.includes(config.modelo_ativo) && (
                  <option value={config.modelo_ativo}>{config.modelo_ativo} (Ficheiro Ausente)</option>
                )}
              </select>
            </div>
            
            <div className="form-group">
              <label className="form-label">URL do Servidor Ollama</label>
              <input type="text" name="url_servidor" className="form-input" value={config.url_servidor} onChange={handleChange} />
            </div>

            <div className="form-group">
              <label className="form-label">Temperatura: {config.temperatura}</label>
              <input type="range" name="temperatura" min="0" max="2" step="0.1" style={{ width: '100%' }} value={config.temperatura} onChange={handleChange} />
            </div>

            <div className="form-group">
              <label className="form-label">Janela de Contexto Máximo (Tokens)</label>
              <select name="contexto_maximo" className="form-select" value={config.contexto_maximo} onChange={handleChange}>
                <option value="2048">2048 (Rápido, pouca RAM)</option>
                <option value="4096">4096 (Padrão)</option>
                <option value="8192">8192 (Projetos de Código)</option>
                <option value="16384">16384 (Pesado, requer muita RAM)</option>
              </select>
            </div>
          </div>

          {/* PAINEL 2: COMPORTAMENTO */}
          <div className="cfg-card">
            <div className="cfg-header"><MessageSquare size={20} /> Comportamento e Memória</div>
            
            <div className="form-group">
              <label className="form-label">Prompt de Sistema (Persona)</label>
              <textarea name="prompt_sistema" className="form-textarea" value={config.prompt_sistema} onChange={handleChange}></textarea>
            </div>

            <div className="form-group">
              <label className="form-label">Retenção de Memória (History TTL)</label>
              <input type="number" name="memoria_ttl" className="form-input" min="1" max="50" value={config.memoria_ttl} onChange={handleChange} />
              <small style={{ color: '#64748b', marginTop: '4px', display: 'block' }}>Nº de mensagens mantidas no contexto antes de podar.</small>
            </div>

            <label className="checkbox-group">
              <input type="checkbox" name="streaming" className="checkbox-input" checked={config.streaming} onChange={handleChange} />
              <span className="form-label" style={{ margin: 0 }}>Ativar Streaming de Resposta (Token-by-Token)</span>
            </label>
          </div>

          {/* PAINEL 3: HARDWARE */}
          <div className="cfg-card">
            <div className="cfg-header"><Cpu size={20} /> Hardware e Inferência Local</div>
            
            <div className="form-group">
              <label className="form-label">Offload de GPU (GPU Layers): {config.gpu_layers}</label>
              <input type="range" name="gpu_layers" min="0" max="100" step="1" style={{ width: '100%' }} value={config.gpu_layers} onChange={handleChange} />
              <small style={{ color: '#64748b' }}>Camadas transferidas para a placa gráfica. (0 = Apenas CPU)</small>
            </div>

            <div className="form-group">
              <label className="form-label">Threads de CPU Alocadas</label>
              <input type="number" name="cpu_threads" className="form-input" min="1" max="32" value={config.cpu_threads} onChange={handleChange} />
            </div>
            
            <div style={{ marginTop: '1.5rem', padding: '1rem', background: '#334155', borderRadius: '8px', display: 'flex', gap: '0.75rem', color: '#cbd5e1', fontSize: '0.85rem' }}>
              <AlertCircle size={32} color="#f59e0b" style={{ flexShrink: 0 }} />
              <p style={{ margin: 0 }}>Alterar as alocações de Hardware exige que o modelo ativo seja descarregado da RAM. As mudanças aplicam-se na próxima requisição.</p>
            </div>
          </div>
        </div>

        <button className="btn-salvar" onClick={salvarConfig} disabled={salvando}>
          <Save size={20} /> {salvando ? 'A Gravar...' : 'Gravar Configurações'}
        </button>

        {toast && <div className="toast">Configurações gravadas e prontas a usar!</div>}
      </div>
    </>
  );
}