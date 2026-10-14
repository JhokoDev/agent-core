import React, { useState, useEffect } from 'react';
import { Activity, Cpu, HardDrive, Terminal } from 'lucide-react';

const estilosMonitor = `
  .mon-container { padding: 2rem; color: #f8fafc; }
  .cards-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
  .metric-card { background: #1e293b; border-radius: 8px; padding: 1.5rem; border-left: 4px solid #38bdf8; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
  .metric-value { font-size: 2.5rem; font-weight: bold; margin: 0.5rem 0; color: #fff; }
  .metric-label { color: #8b949e; font-size: 0.95rem; display: flex; align-items: center; gap: 0.5rem; }
  .metric-sub { font-size: 0.85rem; color: #64748b; margin-top: 0.5rem; }
  .terminal-box { background: #020617; border: 1px solid #334155; border-radius: 8px; padding: 1rem; overflow-x: auto; font-family: Consolas, monospace; color: #a5d6ff; font-size: 0.9rem; line-height: 1.5; white-space: pre-wrap; height: 400px; overflow-y: auto; }
  
  @media (max-width: 768px) {
    .mon-container { padding: 1rem; height: calc(100vh - 75px); overflow-y: auto; }
  }
`;

export default function Monitoramento() {
  const [dados, setDados] = useState(null);

  const fetchDados = async () => {
    try {
      const res = await fetch('/api/system/monitor');
      if (res.ok) setDados(await res.json());
    } catch (e) {
      console.error('Falha ao ler monitoramento');
    }
  };

  useEffect(() => {
    fetchDados();
    const intervalo = setInterval(fetchDados, 3000); // Atualiza a cada 3 segundos
    return () => clearInterval(intervalo);
  }, []);

  return (
    <>
      <style>{estilosMonitor}</style>
      <div className="mon-container">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '2rem' }}>
          <Activity size={28} color="#38bdf8" />
          <h1 style={{ margin: 0 }}>Monitoramento e Logs</h1>
        </div>

        {!dados ? <p>A recolher telemetria da máquina...</p> : (
          <>
            <h2 style={{ fontSize: '1.2rem', marginBottom: '1rem', color: '#cbd5e1' }}>Hardware Local</h2>
            <div className="cards-grid">
              <div className="metric-card">
                <div className="metric-label"><Cpu size={18} /> Uso de CPU</div>
                <div className="metric-value">{dados.cpu}%</div>
              </div>
              <div className="metric-card" style={{ borderLeftColor: '#8b5cf6' }}>
                <div className="metric-label"><HardDrive size={18} /> Uso de RAM Total</div>
                <div className="metric-value">{dados.ram_percent}%</div>
                <div className="metric-sub">{dados.ram_used_gb} GB / {dados.ram_total_gb} GB</div>
              </div>
              <div className="metric-card" style={{ borderLeftColor: '#10b981' }}>
                <div className="metric-label"><Activity size={18} /> RAM Isolada (Ollama)</div>
                <div className="metric-value">{dados.ollama_ram_mb} <span style={{ fontSize: '1.2rem' }}>MB</span></div>
                <div className="metric-sub">Consumo do Motor LLM</div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem', marginTop: '2rem' }}>
              <Terminal size={20} color="#cbd5e1" />
              <h2 style={{ fontSize: '1.2rem', margin: 0, color: '#cbd5e1' }}>Logs do Backend (Ao Vivo)</h2>
            </div>
            <div className="terminal-box">
              {dados.logs}
            </div>
          </>
        )}
      </div>
    </>
  );
}