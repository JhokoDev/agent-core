import { useEffect, useRef, useState } from 'react';
import { Database, FileText, UploadCloud, Trash2, RefreshCw, AlertTriangle, HardDrive } from 'lucide-react';
import type { HarveyApi } from '../services/api';
import type { Notify } from '../contracts';

interface UploadedFile {
  nome: string;
  tamanho: string;
  data: string;
}

interface MemoryStats {
  db_size: string;
  total_memorias: number;
  total_arquivos: number;
  arquivos: UploadedFile[];
}

export default function MemoryManager({ api, onNotice }: { api: HarveyApi; onNotice: Notify }) {
  const [stats, setStats] = useState<MemoryStats>({
    db_size: '0 B',
    total_memorias: 0,
    total_arquivos: 0,
    arquivos: []
  });
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [limpando, setLimpando] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const carregar = async () => {
    setLoading(true);
    try {
      const res = await api.getMemoryStats();
      if (res.ok) {
        setStats(await res.json());
      }
    } catch {
      onNotice('Falha ao obter estatísticas da memória.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void carregar();
  }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const file = files[0];
    const formData = new FormData();
    formData.append('file', file);

    setUploading(true);
    try {
      const res = await api.uploadMemoryFile(formData);
      if (res.ok) {
        onNotice(`Arquivo '${file.name}' salvo na base de conhecimento (uploads/)!`);
        void carregar();
      } else {
        onNotice('Falha ao enviar arquivo.', 'error');
      }
    } catch {
      onNotice('Erro de rede ao enviar arquivo.', 'error');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const excluirArquivo = async (nome: string) => {
    if (!window.confirm(`Deseja excluir '${nome}' dos documentos do agente?`)) return;
    try {
      const res = await api.deleteMemoryFile(nome);
      if (res.ok) {
        onNotice(`Arquivo '${nome}' removido.`);
        void carregar();
      }
    } catch {
      onNotice('Erro ao excluir arquivo.', 'error');
    }
  };

  const limparMemorias = async () => {
    if (!window.confirm('Tem certeza? Isso apagará as memórias de conversas gravadas em data/memory e resetará o banco SQLite.')) {
      return;
    }

    setLimpando(true);
    try {
      const res = await api.clearMemory();
      if (res.ok) {
        const d = await res.json();
        onNotice(`Memória limpa com sucesso (${d.memorias_removidas} registros apagados).`);
        void carregar();
      } else {
        onNotice('Falha ao limpar memórias.', 'error');
      }
    } catch {
      onNotice('Erro ao comunicar limpeza de memória.', 'error');
    } finally {
      setLimpando(false);
    }
  };

  return (
    <div className="memory-manager">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '1.25rem' }}>Memória de Longo Prazo & RAG</h3>
          <p className="settings-help" style={{ margin: '4px 0 0 0' }}>
            Base de conhecimento persistente do Agent Core via SQLite (<code>memory.db</code>), vetores e documentos ingeridos.
          </p>
        </div>
        <button type="button" className="secondary-button" onClick={() => void carregar()} title="Recarregar">
          <RefreshCw size={15} /> Recarregar
        </button>
      </div>

      {/* CARDS DE ESTATÍSTICA */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px', marginBottom: '2rem' }}>
        <div style={{ background: '#1c1c1c', border: '1px solid #333', borderRadius: '8px', padding: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#888', fontSize: '0.85rem' }}>
            <Database size={16} color="#38bdf8" /> Banco SQLite (memory.db)
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 'bold', color: '#f4f4f4', marginTop: '6px' }}>
            {stats.db_size}
          </div>
          <span style={{ fontSize: '0.75rem', color: '#666' }}>Tamanho em disco</span>
        </div>

        <div style={{ background: '#1c1c1c', border: '1px solid #333', borderRadius: '8px', padding: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#888', fontSize: '0.85rem' }}>
            <HardDrive size={16} color="#10b981" /> Memórias Gravadas
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 'bold', color: '#f4f4f4', marginTop: '6px' }}>
            {stats.total_memorias}
          </div>
          <span style={{ fontSize: '0.75rem', color: '#666' }}>Fragmentos em data/memory</span>
        </div>

        <div style={{ background: '#1c1c1c', border: '1px solid #333', borderRadius: '8px', padding: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#888', fontSize: '0.85rem' }}>
            <FileText size={16} color="#f59e0b" /> Documentos de Conhecimento
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 'bold', color: '#f4f4f4', marginTop: '6px' }}>
            {stats.total_arquivos}
          </div>
          <span style={{ fontSize: '0.75rem', color: '#666' }}>Arquivos na pasta uploads/</span>
        </div>
      </div>

      {/* ÁREA DE UPLOAD DE DOCUMENTOS */}
      <div style={{ background: '#1a1a1a', border: '1px solid #2d2d2d', borderRadius: '8px', padding: '1.5rem', marginBottom: '2rem' }}>
        <h4 style={{ margin: '0 0 8px 0', fontSize: '1.05rem', color: '#f4f4f4' }}>Ingestão de Documentos (RAG)</h4>
        <p className="settings-help" style={{ margin: '0 0 1rem 0' }}>
          Adicione manuais, arquivos PDF, códigos ou documentos de texto. O Agent Core consulta estes arquivos durante as respostas.
        </p>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleUpload}
            disabled={uploading}
            accept=".pdf,.txt,.md,.json,.csv,.py,.js,.html"
            style={{ display: 'none' }}
            id="file-upload-input"
          />
          <label
            htmlFor="file-upload-input"
            className="primary-button"
            style={{ cursor: uploading ? 'not-allowed' : 'pointer', display: 'inline-flex', alignItems: 'center', gap: '8px' }}
          >
            <UploadCloud size={17} /> {uploading ? 'Enviando arquivo...' : 'Selecionar Documento para Ingestão'}
          </label>
          <span style={{ fontSize: '0.8rem', color: '#777' }}>
            Suporta PDF, TXT, MD, CSV, JSON e Código
          </span>
        </div>
      </div>

      {/* LISTA DE DOCUMENTOS DISPONÍVEIS */}
      <div style={{ background: '#1a1a1a', border: '1px solid #2d2d2d', borderRadius: '8px', padding: '1.5rem', marginBottom: '2rem' }}>
        <h4 style={{ margin: '0 0 1rem 0', fontSize: '1.05rem', color: '#f4f4f4' }}>
          Documentos Salvos na Base ({stats.arquivos.length})
        </h4>

        {loading ? (
          <p className="settings-help">Carregando documentos...</p>
        ) : stats.arquivos.length === 0 ? (
          <p className="settings-help">Nenhum documento salvo ainda na pasta uploads/.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {stats.arquivos.map((arq) => (
              <div
                key={arq.nome}
                style={{
                  background: '#222',
                  padding: '10px 14px',
                  borderRadius: '6px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  gap: '12px'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', overflow: 'hidden' }}>
                  <FileText size={18} color="#38bdf8" style={{ flexShrink: 0 }} />
                  <div style={{ overflow: 'hidden' }}>
                    <strong style={{ color: '#f4f4f4', fontSize: '0.9rem', display: 'block', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                      {arq.nome}
                    </strong>
                    <span style={{ fontSize: '0.75rem', color: '#888' }}>
                      {arq.tamanho} &middot; Modificado em {arq.data}
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => excluirArquivo(arq.nome)}
                  className="text-button danger-text"
                  style={{ padding: '4px', fontSize: '0.8rem' }}
                  title="Remover documento"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* MANUTENÇÃO DA MEMÓRIA */}
      <div style={{ background: '#201616', border: '1px solid #4a2424', borderRadius: '8px', padding: '1.5rem' }}>
        <h4 style={{ margin: '0 0 8px 0', color: '#fa4d56', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertTriangle size={18} /> Zona de Limpeza de Memória
        </h4>
        <p className="settings-help" style={{ margin: '0 0 1rem 0' }}>
          Limpa todas as memórias de conversas gravadas em <code>data/memory/</code> e redefine o banco de dados.
          Os documentos originais em <code>uploads/</code> serão mantidos.
        </p>

        <button
          type="button"
          onClick={limparMemorias}
          disabled={limpando}
          className="danger-button"
        >
          <Trash2 size={16} /> {limpando ? 'Limpando...' : 'Esvaziar Fragmentos de Memória'}
        </button>
      </div>
    </div>
  );
}
