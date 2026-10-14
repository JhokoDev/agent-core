import { useState, useEffect, useRef } from 'react';
import { Activity, Cpu, HardDrive, Terminal, RefreshCw, Copy, Check, Trash2 } from 'lucide-react';
import type { HarveyApi } from '../services/api';

export default function MonitorPanel({ api }: { api: HarveyApi }) {
  const [dados, setDados] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const terminalRef = useRef<HTMLPreElement>(null);

  const fetchDados = async () => {
    try {
      const res = await api.getMonitor();
      if (res.ok) {
        setDados(await res.json());
      }
    } catch {
      // offline fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchDados();
    const intervalo = setInterval(fetchDados, 2500);
    return () => clearInterval(intervalo);
  }, []);

  useEffect(() => {
    if (autoScroll && terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [dados?.logs, autoScroll]);

  const copiarLogs = async () => {
    if (!dados?.logs) return;
    try {
      await navigator.clipboard.writeText(dados.logs);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  };

  const limparLogs = async () => {
    if (window.confirm('Tem certeza de que deseja esvaziar os logs do servidor?')) {
      try {
        await api.clearLogs();
        await fetchDados();
      } catch {
        // erro
      }
    }
  };

  return (
    <section className="settings-page">
      <div className="section-heading">
        <div>
          <p className="eyebrow">TELEMETRIA LOCAL</p>
          <h1>Monitoramento de Hardware</h1>
          <p>Métricas de consumo em tempo real da máquina e do motor Ollama.</p>
        </div>
        <button className="secondary-button" onClick={fetchDados} title="Atualizar agora">
          <RefreshCw size={15} /> Atualizar
        </button>
      </div>

      {loading && !dados ? (
        <p className="settings-help">A recolher telemetria da máquina...</p>
      ) : !dados ? (
        <div className="notice-card">
          <Activity size={18} />
          <div>
            <strong>Lançador Offline</strong>
            <p>Não foi possível conectar ao endpoint de monitoramento (porta 8001).</p>
          </div>
        </div>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px', marginBottom: '28px' }}>
            {/* CPU */}
            <div className="skill-card" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#a8a8a8', fontSize: '12px' }}>
                <Cpu size={18} color="#4589ff" /> USO DE CPU
              </div>
              <div style={{ fontSize: '32px', fontWeight: 600, color: '#fff', margin: '12px 0 6px' }}>
                {dados.cpu}%
              </div>
              <span className="settings-help">Processador do sistema</span>
            </div>

            {/* RAM TOTAL */}
            <div className="skill-card" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#a8a8a8', fontSize: '12px' }}>
                <HardDrive size={18} color="#8a3ffc" /> MEMÓRIA RAM TOTAL
              </div>
              <div style={{ fontSize: '32px', fontWeight: 600, color: '#fff', margin: '12px 0 6px' }}>
                {dados.ram_percent}%
              </div>
              <span className="settings-help">{dados.ram_used_gb} GB / {dados.ram_total_gb} GB alocados</span>
            </div>

            {/* RAM OLLAMA */}
            <div className="skill-card" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#a8a8a8', fontSize: '12px' }}>
                <Activity size={18} color="#42be65" /> RAM MOTOR OLLAMA
              </div>
              <div style={{ fontSize: '32px', fontWeight: 600, color: '#fff', margin: '12px 0 6px' }}>
                {dados.ollama_ram_mb} <span style={{ fontSize: '16px', fontWeight: 400 }}>MB</span>
              </div>
              <span className="settings-help">Processos isolados de IA</span>
            </div>
          </div>

          <div className="skill-card" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', flexWrap: 'wrap', gap: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Terminal size={18} color="#4589ff" />
                <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600 }}>Logs do Servidor (server_log.txt)</h3>
                <span
                  style={{
                    fontSize: '11px',
                    padding: '2px 8px',
                    borderRadius: '12px',
                    background: dados.engine_online ? 'rgba(36, 161, 72, 0.2)' : 'rgba(250, 77, 86, 0.2)',
                    color: dados.engine_online ? '#42be65' : '#fa4d56',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  <span
                    style={{
                      width: '6px',
                      height: '6px',
                      borderRadius: '50%',
                      background: dados.engine_online ? '#42be65' : '#fa4d56'
                    }}
                  />
                  {dados.engine_online ? 'Motor Online (8000)' : 'Motor Offline'}
                </span>
                {dados.log_size && (
                  <span style={{ fontSize: '11px', color: '#8d8d8d' }}>
                    Tamanho: {dados.log_size}
                  </span>
                )}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#a8a8a8', cursor: 'pointer', marginRight: '4px' }}>
                  <input
                    type="checkbox"
                    checked={autoScroll}
                    onChange={(e) => setAutoScroll(e.target.checked)}
                    style={{ accentColor: '#4589ff' }}
                  />
                  Auto-scroll
                </label>
                <button
                  className="secondary-button"
                  style={{ padding: '4px 10px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '5px' }}
                  onClick={copiarLogs}
                  title="Copiar logs para a área de transferência"
                >
                  {copied ? <Check size={14} color="#42be65" /> : <Copy size={14} />}
                  {copied ? 'Copiado!' : 'Copiar'}
                </button>
                <button
                  className="secondary-button"
                  style={{ padding: '4px 10px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '5px', color: '#fa4d56' }}
                  onClick={limparLogs}
                  title="Esvaziar logs do servidor"
                >
                  <Trash2 size={14} /> Limpar
                </button>
              </div>
            </div>

            <pre
              ref={terminalRef}
              style={{
                background: '#121212',
                border: '1px solid #2d2d2d',
                borderRadius: '8px',
                padding: '16px',
                fontFamily: "'IBM Plex Mono', Consolas, 'Courier New', monospace",
                fontSize: '12px',
                lineHeight: '1.6',
                color: '#78a9ff',
                height: '420px',
                overflowY: 'auto',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
                margin: 0
              }}
            >
              {dados.logs || 'Sem logs disponíveis no momento.'}
            </pre>
          </div>
        </>
      )}
    </section>
  );
}
