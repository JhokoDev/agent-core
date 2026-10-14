import { useState, useEffect } from 'react';
import { Cpu, HardDrive, Zap, RefreshCw } from 'lucide-react';
import type { HarveyApi } from '../services/api';

export default function AnalyticsPanel({ api }: { api: HarveyApi }) {
  const [dados, setDados] = useState<any>({ dados: [], total_prompt: 0, total_resposta: 0 });
  const [loading, setLoading] = useState(true);

  const fetchDados = async () => {
    try {
      const res = await api.getAnalytics();
      if (res.ok) {
        setDados(await res.json());
      }
    } catch {
      // fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchDados();
  }, []);

  const totalGeral = (dados.total_prompt || 0) + (dados.total_resposta || 0);

  return (
    <section className="settings-page">
      <div className="section-heading">
        <div>
          <p className="eyebrow">MÉTRICAS NEURAIS</p>
          <h1>Analytics de Consumo</h1>
          <p>Consumo de tokens de entrada (prompt) e saída (resposta) por conversa.</p>
        </div>
        <button className="secondary-button" onClick={fetchDados} title="Atualizar agora">
          <RefreshCw size={15} /> Atualizar
        </button>
      </div>

      {loading ? (
        <p className="settings-help">A carregar métricas de consumo...</p>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px', marginBottom: '28px' }}>
            {/* Prompt Tokens */}
            <div className="skill-card" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#a8a8a8', fontSize: '12px' }}>
                <HardDrive size={18} color="#4589ff" /> TOKENS DE PROMPT (LEITURA)
              </div>
              <div style={{ fontSize: '32px', fontWeight: 600, color: '#fff', margin: '12px 0 6px' }}>
                {Number(dados.total_prompt || 0).toLocaleString('pt-BR')}
              </div>
              <span className="settings-help">Tokens enviados ao modelo</span>
            </div>

            {/* Response Tokens */}
            <div className="skill-card" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#a8a8a8', fontSize: '12px' }}>
                <Cpu size={18} color="#42be65" /> TOKENS DE RESPOSTA (GERAÇÃO)
              </div>
              <div style={{ fontSize: '32px', fontWeight: 600, color: '#fff', margin: '12px 0 6px' }}>
                {Number(dados.total_resposta || 0).toLocaleString('pt-BR')}
              </div>
              <span className="settings-help">Tokens gerados pelo modelo</span>
            </div>

            {/* Total Tokens */}
            <div className="skill-card" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#a8a8a8', fontSize: '12px' }}>
                <Zap size={18} color="#ffb300" /> TOTAL PROCESSADO
              </div>
              <div style={{ fontSize: '32px', fontWeight: 600, color: '#fff', margin: '12px 0 6px' }}>
                {totalGeral.toLocaleString('pt-BR')}
              </div>
              <span className="settings-help">Volume computacional agregado</span>
            </div>
          </div>

          <div className="skill-card" style={{ padding: '20px' }}>
            <h3 style={{ margin: '0 0 16px', fontSize: '14px', fontWeight: 600 }}>Uso de Tokens por Conversa</h3>
            {(!dados.dados || dados.dados.length === 0) ? (
              <p className="settings-help">Nenhuma conversa registrada ainda para gerar estatísticas de tokens.</p>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #393939', color: '#a8a8a8', textAlign: 'left' }}>
                      <th style={{ padding: '12px 8px', fontWeight: 500 }}>Conversa</th>
                      <th style={{ padding: '12px 8px', fontWeight: 500 }}>Prompt (Azul) / Resposta (Verde)</th>
                      <th style={{ padding: '12px 8px', fontWeight: 500 }}>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dados.dados.map((item: any, idx: number) => {
                      const percPrompt = item.Total ? (item.Tokens_Prompt / item.Total) * 100 : 50;
                      const percResp = item.Total ? (item.Tokens_Resposta / item.Total) * 100 : 50;
                      return (
                        <tr key={idx} style={{ borderBottom: '1px solid #262626' }}>
                          <td style={{ padding: '12px 8px', fontWeight: 500, color: '#f4f4f4', maxWidth: '300px' }}>
                            {item.Chat}
                          </td>
                          <td style={{ padding: '12px 8px', width: '50%' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#777', marginBottom: '4px' }}>
                              <span>{Number(item.Tokens_Prompt).toLocaleString('pt-BR')}</span>
                              <span>{Number(item.Tokens_Resposta).toLocaleString('pt-BR')}</span>
                            </div>
                            <div style={{ width: '100%', height: '6px', background: '#333', borderRadius: '3px', overflow: 'hidden', display: 'flex' }}>
                              <div style={{ width: `${percPrompt}%`, background: '#4589ff', height: '100%' }} />
                              <div style={{ width: `${percResp}%`, background: '#42be65', height: '100%' }} />
                            </div>
                          </td>
                          <td style={{ padding: '12px 8px', color: '#a8a8a8' }}>
                            {Number(item.Total).toLocaleString('pt-BR')}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </section>
  );
}
