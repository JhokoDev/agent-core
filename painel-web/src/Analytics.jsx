import React, { useState, useEffect } from 'react';
import { BarChart2, Cpu, HardDrive, Zap } from 'lucide-react';

const estilosAnalytics = `
  .analytics-container { padding: 2rem; color: #f8fafc; }
  .cards-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
  .metric-card { background: linear-gradient(145deg, #161b22, #0d1117); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 4px solid #38bdf8; border-radius: 8px; padding: 1.5rem; box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: transform 0.2s; }
  .metric-card:hover { transform: translateY(-3px); border-left: 4px solid #10b981; }
  .metric-value { font-size: 2.5rem; font-weight: bold; margin: 0.5rem 0; color: #fff; }
  .metric-label { color: #8b949e; font-size: 0.95rem; display: flex; align-items: center; gap: 0.5rem; }
  
  .table-container { background: #1e293b; border-radius: 12px; padding: 1.5rem; overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; text-align: left; }
  th { padding: 1rem; border-bottom: 1px solid #334155; color: #94a3b8; font-weight: normal; }
  td { padding: 1rem; border-bottom: 1px solid rgba(255,255,255,0.05); }
  .bar-bg { width: 100%; background: #334155; border-radius: 4px; height: 8px; overflow: hidden; display: flex; }
  .bar-prompt { background: #3b82f6; height: 100%; }
  .bar-resp { background: #10b981; height: 100%; }
  
  @media (max-width: 768px) {
    .analytics-container { padding: 1rem; height: calc(100vh - 75px); overflow-y: auto; }
    .metric-value { font-size: 2rem; }
  }
`;

export default function Analytics() {
  const [dados, setDados] = useState({ dados: [], total_prompt: 0, total_resposta: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const carregarAnalytics = async () => {
      try {
        const res = await fetch('/api/analytics');
        if (res.ok) setDados(await res.json());
      } catch (e) {
        console.error("Erro ao carregar analytics", e);
      } finally {
        setLoading(false);
      }
    };
    carregarAnalytics();
  }, []);

  const totalGeral = dados.total_prompt + dados.total_resposta;

  return (
    <>
      <style>{estilosAnalytics}</style>
      <div className="analytics-container">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '2rem' }}>
          <BarChart2 size={28} color="#38bdf8" />
          <h1 style={{ margin: 0 }}>Analytics de Consumo</h1>
        </div>
        <p style={{ color: '#8b949e', marginBottom: '2rem' }}>Acompanhe o peso computacional e o consumo de tokens do seu Agente.</p>

        {loading ? (
          <p>A carregar métricas...</p>
        ) : (
          <>
            <div className="cards-grid">
              <div className="metric-card">
                <div className="metric-label"><HardDrive size={18} /> Tokens de Prompt (Leitura)</div>
                <div className="metric-value">{dados.total_prompt.toLocaleString('pt-PT')}</div>
              </div>
              <div className="metric-card">
                <div className="metric-label"><Cpu size={18} /> Tokens de Resposta (Geração)</div>
                <div className="metric-value">{dados.total_resposta.toLocaleString('pt-PT')}</div>
              </div>
              <div className="metric-card">
                <div className="metric-label"><Zap size={18} /> Total Processado</div>
                <div className="metric-value">{totalGeral.toLocaleString('pt-PT')}</div>
              </div>
            </div>

            <div className="table-container">
              <h2 style={{ fontSize: '1.2rem', marginBottom: '1rem' }}>Uso de Tokens por Conversa</h2>
              {dados.dados.length === 0 ? (
                <p style={{ color: '#8b949e' }}>Envie mensagens para a IA para começar a gerar as métricas de Tokens.</p>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Conversa</th>
                      <th>Prompt (Azul) / Resposta (Verde)</th>
                      <th>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dados.dados.map((item, idx) => {
                      const percPrompt = (item.Tokens_Prompt / item.Total) * 100;
                      const percResp = (item.Tokens_Resposta / item.Total) * 100;
                      
                      return (
                        <tr key={idx}>
                          <td style={{ fontWeight: 'bold' }}>{item.Chat}</td>
                          <td style={{ width: '50%' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '4px', color: '#8b949e' }}>
                              <span>{item.Tokens_Prompt.toLocaleString('pt-PT')}</span>
                              <span>{item.Tokens_Resposta.toLocaleString('pt-PT')}</span>
                            </div>
                            <div className="bar-bg">
                              <div className="bar-prompt" style={{ width: `${percPrompt}%` }}></div>
                              <div className="bar-resp" style={{ width: `${percResp}%` }}></div>
                            </div>
                          </td>
                          <td>{item.Total.toLocaleString('pt-PT')}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </>
        )}
      </div>
    </>
  );
}