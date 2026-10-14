import { useEffect, useState } from 'react';
import { Plus, Search, Trash2, Edit3, Sparkles, Check, X, RefreshCw } from 'lucide-react';
import type { HarveyApi } from '../services/api';
import type { Notify } from '../contracts';

interface SkillItem {
  id: string;
  nome: string;
  icone: string;
  tipo: string;
  modelo: string;
  temperatura: number;
  instrucoes: string;
  arquivo: string;
  tamanho: string;
}

export default function SkillsManager({ api, onNotice }: { api: HarveyApi; onNotice: Notify }) {
  const [skills, setSkills] = useState<SkillItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  // Edição / Criação
  const [editando, setEditando] = useState<SkillItem | null>(null);
  const [salvando, setSalvando] = useState(false);

  const carregar = async () => {
    setLoading(true);
    try {
      const res = await api.getSkillsList();
      if (res.ok) {
        const data = await res.json();
        setSkills(data.skills || []);
      }
    } catch {
      onNotice('Falha ao carregar lista de personas/skills.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const abrirNovaSkill = () => {
    setEditando({
      id: '',
      nome: '',
      icone: '🤖',
      tipo: 'skill',
      modelo: 'llama3.2',
      temperatura: 0.2,
      instrucoes: '# Objetivo\nAtuar como especialista...',
      arquivo: '',
      tamanho: '0 KB'
    });
  };

  const salvar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editando || !editando.id.trim() || !editando.nome.trim()) {
      onNotice('Preencha o ID e o Nome do especialista.', 'error');
      return;
    }

    setSalvando(true);
    try {
      const res = await api.saveSkill(editando);
      if (res.ok) {
        onNotice(`Persona '${editando.nome}' salva com sucesso em skills/${editando.id}.md!`);
        setEditando(null);
        void carregar();
      } else {
        onNotice('Falha ao salvar arquivo de skill.', 'error');
      }
    } catch {
      onNotice('Erro de rede ao salvar skill.', 'error');
    } finally {
      setSalvando(false);
    }
  };

  const excluir = async (id: string, nome: string) => {
    if (!window.confirm(`Tem certeza que deseja apagar a persona '${nome}' (${id}.md)?`)) return;
    try {
      const res = await api.deleteSkill(id);
      if (res.ok) {
        onNotice(`Persona '${nome}' removida.`);
        void carregar();
      } else {
        onNotice('Falha ao excluir arquivo da skill.', 'error');
      }
    } catch {
      onNotice('Erro ao remover skill.', 'error');
    }
  };

  const filtradas = skills.filter(
    (s) =>
      s.nome.toLowerCase().includes(search.toLowerCase()) ||
      s.id.toLowerCase().includes(search.toLowerCase()) ||
      s.instrucoes.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="skills-manager">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '1.25rem' }}>Especialistas & Personas (Skills)</h3>
          <p className="settings-help" style={{ margin: '4px 0 0 0' }}>
            Personas com papéis, comportamentos e regras configurados em arquivos <code>skills/*.md</code>.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button type="button" className="secondary-button" onClick={() => void carregar()} title="Recarregar">
            <RefreshCw size={15} /> Recarregar
          </button>
          <button type="button" className="primary-button" onClick={abrirNovaSkill}>
            <Plus size={16} /> Nova Persona
          </button>
        </div>
      </div>

      {editando && (
        <form onSubmit={salvar} className="extension-form" style={{ background: '#1c1c1c', padding: '1.5rem', borderRadius: '8px', marginBottom: '2rem', border: '1px solid #333' }}>
          <h4 style={{ margin: '0 0 1rem 0', color: '#10b981', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={18} /> {editando.arquivo ? `Editar Persona: ${editando.nome}` : 'Criar Nova Persona'}
          </h4>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
            <label>
              Identificador (Nome do arquivo .md)
              <input
                type="text"
                placeholder="ex: analista_financas"
                value={editando.id}
                disabled={Boolean(editando.arquivo)}
                onChange={(e) => setEditando({ ...editando, id: e.target.value.toLowerCase().replace(/\s+/g, '_') })}
                required
              />
            </label>
            <label>
              Nome de Exibição
              <input
                type="text"
                placeholder="ex: Analista de Finanças"
                value={editando.nome}
                onChange={(e) => setEditando({ ...editando, nome: e.target.value })}
                required
              />
            </label>
            <label>
              Ícone / Emoji
              <input
                type="text"
                placeholder="ex: 📈 ou 💻"
                value={editando.icone}
                onChange={(e) => setEditando({ ...editando, icone: e.target.value })}
              />
            </label>
            <label>
              Modelo Recomendado
              <input
                type="text"
                placeholder="ex: llama3.2, qwen2.5:1.5b"
                value={editando.modelo}
                onChange={(e) => setEditando({ ...editando, modelo: e.target.value })}
              />
            </label>
            <label>
              Temperatura ({editando.temperatura})
              <input
                type="range"
                min="0"
                max="1.5"
                step="0.05"
                value={editando.temperatura}
                onChange={(e) => setEditando({ ...editando, temperatura: Number(e.target.value) })}
              />
            </label>
          </div>

          <label style={{ marginTop: '14px' }}>
            Instruções e Prompt de Sistema (Markdown)
            <textarea
              rows={10}
              placeholder="Descreva o objetivo, tom e escopo de atuação do especialista..."
              value={editando.instrucoes}
              onChange={(e) => setEditando({ ...editando, instrucoes: e.target.value })}
              style={{ fontFamily: 'Consolas, monospace', fontSize: '0.85rem' }}
              required
            />
          </label>

          <div style={{ display: 'flex', gap: '8px', marginTop: '1rem' }}>
            <button type="submit" className="primary-button" disabled={salvando}>
              <Check size={16} /> {salvando ? 'Salvando...' : 'Gravar Especialista'}
            </button>
            <button type="button" className="text-button" onClick={() => setEditando(null)}>
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
            placeholder="Buscar por nome, id ou escopo do especialista..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <span style={{ fontSize: '0.85rem', color: '#888', whiteSpace: 'nowrap' }}>
          {filtradas.length} de {skills.length} especialistas
        </span>
      </div>

      {loading ? (
        <p className="settings-help">Carregando especialistas...</p>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '14px' }}>
          {filtradas.map((s) => (
            <div
              key={s.id}
              style={{
                background: '#1a1a1a',
                border: '1px solid #2d2d2d',
                borderRadius: '8px',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                gap: '12px'
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '1.3rem' }}>{s.icone || '✨'}</span>
                    <div>
                      <strong style={{ color: '#fff', fontSize: '1rem', display: 'block' }}>{s.nome}</strong>
                      <span style={{ fontSize: '0.75rem', color: '#888' }}>
                        <code>{s.arquivo}</code> ({s.tamanho})
                      </span>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => excluir(s.id, s.nome)}
                    className="text-button danger-text"
                    style={{ padding: '4px', fontSize: '0.8rem' }}
                    title="Excluir especialista"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>

                <div style={{ display: 'flex', gap: '8px', marginTop: '10px', fontSize: '0.75rem' }}>
                  <span style={{ background: '#252525', padding: '2px 6px', borderRadius: '4px', color: '#71c5ff' }}>
                    Mod: {s.modelo}
                  </span>
                  <span style={{ background: '#252525', padding: '2px 6px', borderRadius: '4px', color: '#999' }}>
                    Temp: {s.temperatura}
                  </span>
                </div>

                <p
                  style={{
                    marginTop: '10px',
                    fontSize: '0.8rem',
                    color: '#bbb',
                    lineHeight: '1.4',
                    maxHeight: '60px',
                    overflow: 'hidden',
                    display: '-webkit-box',
                    WebkitLineClamp: 3,
                    WebkitBoxOrient: 'vertical'
                  }}
                >
                  {s.instrucoes.replace(/#+/g, '').trim()}
                </p>
              </div>

              <div style={{ display: 'flex', gap: '8px', borderTop: '1px solid #262626', paddingTop: '10px' }}>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => setEditando(s)}
                  style={{ flex: 1, padding: '5px 10px', fontSize: '0.8rem', justifyContent: 'center' }}
                >
                  <Edit3 size={13} /> Editar Instruções
                </button>
              </div>
            </div>
          ))}
          {filtradas.length === 0 && (
            <p className="settings-help" style={{ gridColumn: '1 / -1' }}>
              Nenhum especialista encontrado para "{search}".
            </p>
          )}
        </div>
      )}
    </div>
  );
}
