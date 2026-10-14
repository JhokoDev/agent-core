import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Activity, Terminal, FolderOpen, BarChart2, Settings, Power, RefreshCw } from 'lucide-react';

// Importação dos subcomponentes que criámos
import Playground from './Playground';
import Analytics from './Analytics';
import Monitoramento from './Monitoramento';
import Sistema from './Sistema';
import Configuracoes from './Configuracoes';

// --- CSS RESPONSIVO INJETADO ---
const estilosGlobais = `
  * { box-sizing: border-box; }
  body { margin: 0; padding: 0; background: #0f172a; color: #f8fafc; font-family: system-ui, sans-serif; }
  
  .app-layout { display: flex; height: 100vh; width: 100vw; overflow: hidden; }
  .sidebar { width: 250px; background: #020617; padding: 1rem; display: flex; flex-direction: column; transition: all 0.3s; z-index: 50; }
  .sidebar h2 { color: #38bdf8; letter-spacing: 2px; font-size: 1.2rem; margin-bottom: 1rem; text-align: center; }
  .nav-menu { display: flex; flex-direction: column; gap: 0.5rem; }
  .nav-link { display: flex; align-items: center; gap: 1rem; padding: 0.75rem 1rem; text-decoration: none; color: #94a3b8; border-radius: 8px; transition: all 0.2s; }
  .nav-link:hover { color: #fff; background: #1e293b; }
  .nav-link.active { color: #fff; background: #1e293b; font-weight: bold; }
  
  .content-area { flex: 1; overflow-y: auto; background: #0f172a; position: relative; }
  .painel-container { padding: 2rem; }
  .card-controles { background: #1e293b; padding: 2rem; border-radius: 12px; max-width: 500px; width: 100%; }
  .btn-group { display: flex; gap: 1rem; }
  .btn-acao { flex: 1; padding: 1rem; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; display: flex; justify-content: center; align-items: center; gap: 0.5rem; transition: opacity 0.2s; }

  /* MODO MOBILE (Smartphones) */
  @media (max-width: 768px) {
    .app-layout { flex-direction: column-reverse; } 
    .sidebar { width: 100%; height: 75px; padding: 0.5rem; flex-direction: row; justify-content: center; box-shadow: 0 -4px 10px rgba(0,0,0,0.5); }
    .sidebar h2 { display: none; } 
    .nav-menu { flex-direction: row; width: 100%; justify-content: space-around; gap: 0; }
    .nav-link { flex-direction: column; gap: 0.25rem; padding: 0.5rem; justify-content: center; }
    .nav-link span { font-size: 0.65rem; }
    
    .painel-container { padding: 1rem; }
    .card-controles { padding: 1.5rem; }
    .btn-group { flex-direction: column; gap: 0.75rem; }
    .status-title { font-size: 1.2rem !important; }
  }
`;

// --- COMPONENTE: VISÃO GERAL (DASHBOARD) ---
function VisaoGeral() {
  const [isOnline, setIsOnline] = useState(false);
  const [loading, setLoading] = useState(false);
  const [isChecking, setIsChecking] = useState(false);

  const checarStatus = async () => {
    setIsChecking(true);
    try {
      const res = await fetch(`/api/system/status`);
      const data = await res.json();
      setIsOnline(data.online);
    } catch (e) {
      setIsOnline(false);
    }
    setIsChecking(false);
  };

  useEffect(() => { checarStatus(); }, []);

  const controlarAgente = async (acao) => {
    setLoading(true);
    try {
      await fetch(`/api/system/${acao}`, { method: 'POST' });
      setTimeout(checarStatus, 1500);
    } catch (e) {
      alert("Erro ao comunicar com o Lançador através do Proxy.");
    }
    setLoading(false);
  };

  return (
    <div className="painel-container">
      <h1 style={{ fontSize: '2rem', margin: '0 0 2rem 0' }}>Visão Geral</h1>
      <div className="card-controles">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '2rem' }}>
          <div style={{ 
            width: '20px', height: '20px', borderRadius: '50%', flexShrink: 0,
            background: isOnline ? '#22c55e' : '#ef4444',
            boxShadow: isOnline ? '0 0 15px #22c55e' : '0 0 15px #ef4444'
          }} />
          <h2 className="status-title" style={{ margin: 0 }}>
            Motor: {isOnline ? 'ONLINE' : 'OFFLINE'}
          </h2>
          <button 
            onClick={checarStatus} disabled={isChecking} title="Atualizar Status"
            style={{ 
              marginLeft: 'auto', background: '#334155', color: '#f8fafc', border: 'none', 
              padding: '0.5rem', borderRadius: '8px', cursor: 'pointer', opacity: isChecking ? 0.5 : 1 
            }}>
            <RefreshCw size={20} />
          </button>
        </div>

        <div className="btn-group">
          <button className="btn-acao" disabled={loading || isOnline} onClick={() => controlarAgente('start')}
            style={{ background: '#22c55e', opacity: (loading || isOnline) ? 0.5 : 1 }}>
            <Power size={20} /> INICIAR MOTOR
          </button>
          <button className="btn-acao" disabled={loading || !isOnline} onClick={() => controlarAgente('stop')}
            style={{ background: '#ef4444', opacity: (loading || !isOnline) ? 0.5 : 1 }}>
            <Power size={20} /> PARAR MOTOR
          </button>
        </div>
      </div>
    </div>
  );
}

const Sandbox = () => <div className="painel-container"><h1>Sandbox (Projetos)</h1><p>Em breve...</p></div>;

// --- COMPONENTE: BARRA LATERAL ---
function Sidebar() {
  const location = useLocation();
  const menus = [
    { nome: 'Visão Geral', rota: '/', icon: <Activity size={22} /> },
    { nome: 'Playground', rota: '/playground', icon: <Terminal size={22} /> },
    { nome: 'Sandbox', rota: '/sandbox', icon: <FolderOpen size={22} /> },
    { nome: 'Analytics', rota: '/analytics', icon: <BarChart2 size={22} /> },
    { nome: 'Monitor', rota: '/monitoramento', icon: <Activity size={22} /> },
    { nome: 'Configurações', rota: '/configuracoes', icon: <Settings size={22} /> },
    { nome: 'Sistema', rota: '/sistema', icon: <Settings size={22} /> },
  ];

  return (
    <div className="sidebar">
      <h2>AGENT CORE</h2>
      <nav className="nav-menu">
        {menus.map(menu => (
          <Link key={menu.rota} to={menu.rota} className={`nav-link ${location.pathname === menu.rota ? 'active' : ''}`}>
            {menu.icon} <span>{menu.nome}</span>
          </Link>
        ))}
      </nav>
    </div>
  );
}

// --- APLICAÇÃO PRINCIPAL ---
export default function App() {
  return (
    <BrowserRouter>
      <style>{estilosGlobais}</style>
      <div className="app-layout">
        <Sidebar />
        <div className="content-area">
          <Routes>
            <Route path="/" element={<VisaoGeral />} />
            <Route path="/playground" element={<Playground />} />
            <Route path="/sandbox" element={<Sandbox />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/monitoramento" element={<Monitoramento />} />
            <Route path="/sistema" element={<Sistema />} />
            <Route path="/configuracoes" element={<Configuracoes />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}