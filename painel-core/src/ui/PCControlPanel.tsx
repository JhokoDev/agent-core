import { useEffect, useState } from 'react';
import { Play, Plus, Search, Trash2, Edit2, Terminal, Check, X, RefreshCw } from 'lucide-react';
import type { HarveyApi } from '../services/api';
import type { Notify } from '../contracts';

export default function PCControlPanel({ api, onNotice }: { api: HarveyApi; onNotice: Notify }) {
  const [commands, setCommands] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [executingKey, setExecutingKey] = useState<string | null>(null);

  // Form de novo / edição
  const [showForm, setShowForm] = useState(false);
  const [chave, setChave] = useState('');
  const [comando, setComando] = useState('');
  const [salvando, setSalvando] = useState(false);

  const carregar = async () => {
    setLoading(true);
    try {
      const res = await api.getPCCommands();
      if (res.ok) {
        const data = await res.json();
        setCommands(data.comandos || {});
      }
    } catch {
      onNotice('Falha ao carregar comandos do PC.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const testarComando = async (key: string, cmdStr: string) => {
    setExecutingKey(key);
    try {
      const res = await api.executePCCommand(key, cmdStr);
      if (res.ok) {
        onNotice(`Comando '${key}' executado com sucesso no Windows!`);
      } else {
        onNotice('Falha ao acionar comando.', 'error');
      }
    } catch {
      onNotice('Erro de comunicação ao executar comando.', 'error');
    } finally {
      setExecutingKey(null);
    }
  };

  const salvarComando = async (e: React.FormEvent) => {
    e.preventDefault();
    const ch = chave.trim().toLowerCase().replace(/\s+/g, '_');
    const cmd = comando.trim();
    if (!ch || !cmd) return;

    setSalvando(true);
    try {
      const res = await api.savePCCommand(ch, cmd, 'salvar');
      if (res.ok) {
        onNotice(`Comando '${ch}' salvo em comandos_pc.json!`);
        setShowForm(false);
        setChave('');
        setComando('');
        void carregar();
      } else {
        onNotice('Erro ao salvar comando.', 'error');
      }
    } catch {
      onNotice('Erro de conexão ao salvar comando.', 'error');
    } finally {
      setSalvando(false);
    }
  };

  const removerComando = async (key: string) => {
    if (!window.confirm(`Deseja remover o comando '${key}' do Agent Core?`)) return;
    try {
      const res = await api.savePCCommand(key, '', 'remover');
      if (res.ok) {
        onNotice(`Comando '${key}' removido.`);
        void carregar();
      }
    } catch {
      onNotice('Erro ao remover comando.', 'error');
    }
  };

  const entries = Object.entries(commands).filter(([k, v]) =>
    k.toLowerCase().includes(search.toLowerCase()) || v.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="pc-control-panel">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '1.25rem' }}>Automação & Controle do Windows</h3>
          <p className="settings-help" style={{ margin: '4px 0 0 0' }}>
            Comandos autorizados em <code>comandos_pc.json</code> que o Agent Core pode disparar por voz ou texto.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            type="button"
            className="secondary-button"
            onClick={() => void carregar()}
            title="Atualizar lista"
          >
            <RefreshCw size={15} /> Recarregar
          </button>
          <button
            type="button"
            className="primary-button"
            onClick={() => {
              setChave('');
              setComando('');
              setShowForm(!showForm);
            }}
          >
            <Plus size={16} /> {showForm ? 'Fechar Formulário' : 'Novo Comando'}
          </button>
        </div>
      </div>

      {showForm && (
        <form onSubmit={salvarComando} className="extension-form" style={{ background: '#1f1f1f', padding: '1.5rem', borderRadius: '8px', marginBottom: '2rem', border: '1px solid #333' }}>
          <h4 style={{ margin: '0 0 1rem 0', color: '#38bdf8' }}>Adicionar ou Atualizar Comando do PC</h4>
          <label>
            Identificador / Chave (usado pela IA)
            <input
              type="text"
              placeholder="ex: abrir_spotify, ligar_luz, backup_dados"
              value={chave}
              onChange={(e) => setChave(e.target.value)}
              required
            />
          </label>
          <label>
            Linha de Comando do Windows (CMD / PowerShell / Executável)
            <input
              type="text"
              placeholder="ex: start spotify, shutdown /s /t 60, explorer shell:Downloads"
              value={comando}
              onChange={(e) => setComando(e.target.value)}
              required
            />
          </label>
          <div style={{ display: 'flex', gap: '8px', marginTop: '1rem' }}>
            <button type="submit" className="primary-button" disabled={salvando}>
              <Check size={16} /> {salvando ? 'Salvando...' : 'Salvar no Windows'}
            </button>
            <button type="button" className="text-button" onClick={() => setShowForm(false)}>
              <X size={16} /> Cancelar
            </button>
          </div>
        </form>
      )}

      <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div className="search-field" style={{ flex: 1 }}>
          <Search size={16} />
          <input
            type="text"
            placeholder="Filtrar comandos por nome ou instrução..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <span style={{ fontSize: '0.85rem', color: '#888', whiteSpace: 'nowrap' }}>
          {entries.length} de {Object.keys(commands).length} comandos
        </span>
      </div>

      {loading ? (
        <p className="settings-help">Carregando lista de comandos...</p>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '12px' }}>
          {entries.map(([k, cmd]) => (
            <div
              key={k}
              style={{
                background: '#1a1a1a',
                border: '1px solid #2d2d2d',
                borderRadius: '8px',
                padding: '14px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                gap: '10px'
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                  <strong style={{ color: '#f4f4f4', fontSize: '0.95rem' }}>{k}</strong>
                  <button
                    type="button"
                    onClick={() => removerComando(k)}
                    className="text-button danger-text"
                    style={{ padding: '2px 4px', fontSize: '0.8rem' }}
                    title="Excluir comando"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
                <div
                  style={{
                    marginTop: '6px',
                    background: '#111',
                    padding: '6px 8px',
                    borderRadius: '4px',
                    fontSize: '0.75rem',
                    color: '#71c5ff',
                    fontFamily: 'Consolas, monospace',
                    wordBreak: 'break-all'
                  }}
                >
                  <Terminal size={12} style={{ display: 'inline', marginRight: '4px', verticalAlign: '-1px' }} />
                  {cmd}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '6px', marginTop: '4px' }}>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => testarComando(k, cmd)}
                  disabled={executingKey === k}
                  style={{ flex: 1, padding: '4px 8px', fontSize: '0.8rem', justifyContent: 'center' }}
                  title="Executar imediatamente no computador"
                >
                  <Play size={13} fill="currentColor" /> {executingKey === k ? 'Executando...' : 'Testar no Windows'}
                </button>
                <button
                  type="button"
                  className="text-button"
                  onClick={() => {
                    setChave(k);
                    setComando(cmd);
                    setShowForm(true);
                  }}
                  style={{ padding: '4px 8px', fontSize: '0.8rem' }}
                  title="Editar comando"
                >
                  <Edit2 size={13} /> Editar
                </button>
              </div>
            </div>
          ))}
          {entries.length === 0 && (
            <p className="settings-help" style={{ gridColumn: '1 / -1' }}>
              Nenhum comando encontrado com o filtro "{search}".
            </p>
          )}
        </div>
      )}
    </div>
  );
}
