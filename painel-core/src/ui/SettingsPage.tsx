import { useEffect, useState } from 'react';
import { Trash2, Save, Download } from 'lucide-react';
import type { Notify, ServerStatus } from '../contracts';
import type { HarveyApi } from '../services/api';
import type { audioDevices } from '../voice/devices';
import AudioDiagnostics from '../voice/AudioDiagnostics';
import { DeviceFields, StatusDot } from './shared';
import PCControlPanel from './PCControlPanel';
import SkillsManager from './SkillsManager';
import MemoryManager from './MemoryManager';
import AutomationPanel from './AutomationPanel';
import WebBrowserPanel from './WebBrowserPanel';

type Category = 'model' | 'audio' | 'pc' | 'skills' | 'memory' | 'system';
const categories: { id: Category; label: string }[] = [
  { id: 'model', label: 'Motor IA & Hardware' },
  { id: 'audio', label: 'Áudio & Voz' },
  { id: 'pc', label: 'Automação & PC' },
  { id: 'skills', label: 'Skills & Especialistas' },
  { id: 'memory', label: 'Memória RAG' },
  { id: 'system', label: 'Rede & Sistema' },
];

const currentCategory = (): Category => {
  const raw = location.hash.split('/')[1];
  const value = ({
    motor: 'model',
    computer: 'pc',
    integrations: 'skills',
    data: 'memory',
    general: 'model',
    privacy: 'pc'
  } as Record<string, string>)[raw] || raw;
  return categories.some((c) => c.id === value) ? (value as Category) : 'model';
};

export default function SettingsPage({
  status,
  api,
  audioDevices: deviceService,
  devices,
  inputId,
  outputId,
  onInput,
  onOutput,
  onRefresh,
  onNotice,
}: {
  status: ServerStatus | null;
  api: HarveyApi;
  audioDevices: typeof audioDevices;
  devices: MediaDeviceInfo[];
  inputId: string;
  outputId: string;
  onInput: (v: string) => void;
  onOutput: (v: string) => void;
  onRefresh: () => void;
  onRetry: () => void;
  onNotice: Notify;
}) {
  const [category, setCategory] = useState<Category>(currentCategory);
  const [pcSubTab, setPcSubTab] = useState<'pc' | 'playwright' | 'tabs'>('playwright');
  const [failed, setFailed] = useState(false);
  const [size, setSize] = useState(() => localStorage.getItem('harvey-transcript-size') || 'normal');

  // Configurações do Agent Core
  const [coreConfig, setCoreConfig] = useState<any>({
    modelo_ativo: 'llama3.2:1b',
    url_servidor: 'http://127.0.0.1:11434',
    temperatura: 0.7,
    contexto_maximo: 4096,
    prompt_sistema: 'Você é um assistente de IA lógico e conciso.',
    streaming: true,
    gpu_layers: 35,
    cpu_threads: 4,
    memoria_ttl: 10,
  });
  const [modelosDisponiveis, setModelosDisponiveis] = useState<string[]>([]);
  const [salvandoConfig, setSalvandoConfig] = useState(false);
  const [advancedData, setAdvancedData] = useState<any>(null);

  const carregarConfigCore = async () => {
    try {
      const [resCfg, resMod, resAdv] = await Promise.all([
        api.getConfig(),
        api.getSystemModels(),
        api.getAdvancedSystem(),
      ]);
      if (resCfg.ok) setCoreConfig(await resCfg.json());
      if (resMod.ok) {
        const d = await resMod.json();
        setModelosDisponiveis(d.modelos || []);
      }
      if (resAdv.ok) setAdvancedData(await resAdv.json());
    } catch {}
  };

  const salvarConfiguracoesCore = async (e: React.FormEvent) => {
    e.preventDefault();
    setSalvandoConfig(true);
    try {
      const res = await api.saveConfig(coreConfig);
      if (res.ok) {
        onNotice('Configurações do Agent Core gravadas com sucesso!');
      } else {
        onNotice('Falha ao gravar configurações.', 'error');
      }
    } catch {
      onNotice('Erro de rede ao salvar configurações.', 'error');
    } finally {
      setSalvandoConfig(false);
    }
  };

  const limparLogsServidor = async () => {
    if (window.confirm('Tem a certeza de que deseja esvaziar os logs do servidor?')) {
      try {
        await api.clearLogs();
        onNotice('Logs esvaziados.');
        void carregarConfigCore();
      } catch {
        onNotice('Não foi possível esvaziar os logs.', 'error');
      }
    }
  };

  const load = async () => {
    setFailed(false);
    try {
      await carregarConfigCore();
    } catch {
      setFailed(true);
    }
  };

  useEffect(() => {
    void load();
  }, [api]);

  useEffect(() => {
    const changed = () => setCategory(currentCategory());
    window.addEventListener('hashchange', changed);
    return () => window.removeEventListener('hashchange', changed);
  }, []);

  const select = (id: Category) => {
    setCategory(id);
    location.hash = `settings/${id}`;
  };

  const field = (name: string, value: string) => (
    <div className="preference-row">
      <strong>{name}</strong>
      <span>{value}</span>
    </div>
  );

  return (
    <section className="settings-page">
      <div className="section-heading">
        <div>
          <p className="eyebrow">PREFERÊNCIAS E MOTOR</p>
          <h1>Configurações</h1>
          <p>Ajuste o Agent Core, o hardware e as ferramentas ao seu modo de trabalhar.</p>
        </div>
      </div>

      <div className="settings-layout">
        <nav className="settings-nav" aria-label="Seções de configurações">
          {categories.map((c) => (
            <button
              key={c.id}
              aria-current={category === c.id ? 'page' : undefined}
              className={category === c.id ? 'active' : ''}
              onClick={() => select(c.id)}
            >
              {c.label}
            </button>
          ))}
        </nav>

        <div className="settings-section">
          <h2>{categories.find((c) => c.id === category)?.label}</h2>
          {failed && (
            <div className="error-banner" role="alert">
              Não foi possível carregar os detalhes.{' '}
              <button className="text-button" onClick={() => void load()}>
                Tentar novamente
              </button>
            </div>
          )}

          {/* 1. MOTOR IA & HARDWARE */}
          {category === 'model' && (
            <form onSubmit={salvarConfiguracoesCore} className="extension-form">
              <h3>Parâmetros do Modelo LLM (Ollama)</h3>
              <p className="settings-help">Defina o modelo ativo, temperatura e capacidades de inferência local.</p>

              <label className="preference-row" style={{ marginBottom: '1.5rem', background: '#202020', padding: '12px', borderRadius: '6px' }}>
                <div>
                  <strong>Tamanho da Transcrição de Texto</strong>
                  <p style={{ margin: 0, fontSize: '0.8rem', color: '#888' }}>Salvo neste navegador. Aplicação imediata no chat.</p>
                </div>
                <select
                  aria-label="Tamanho da transcrição"
                  value={size}
                  onChange={(e) => {
                    const value = e.target.value;
                    setSize(value);
                    localStorage.setItem('harvey-transcript-size', value);
                    document.documentElement.dataset.transcriptSize = value;
                  }}
                >
                  <option value="normal">Normal</option>
                  <option value="large">Maior</option>
                </select>
              </label>

              <label>
                Modelo Ativo
                <select
                  value={coreConfig.modelo_ativo}
                  onChange={(e) => setCoreConfig({ ...coreConfig, modelo_ativo: e.target.value })}
                >
                  {modelosDisponiveis.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                  {coreConfig.modelo_ativo && !modelosDisponiveis.includes(coreConfig.modelo_ativo) && (
                    <option value={coreConfig.modelo_ativo}>{coreConfig.modelo_ativo} (Padrão)</option>
                  )}
                </select>
              </label>

              <label>
                URL do Servidor Ollama
                <input
                  type="text"
                  value={coreConfig.url_servidor}
                  onChange={(e) => setCoreConfig({ ...coreConfig, url_servidor: e.target.value })}
                />
              </label>

              <label>
                Temperatura ({coreConfig.temperatura})
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={coreConfig.temperatura}
                  onChange={(e) => setCoreConfig({ ...coreConfig, temperatura: Number(e.target.value) })}
                />
              </label>

              <label>
                Janela de Contexto Máximo (Tokens)
                <select
                  value={coreConfig.contexto_maximo}
                  onChange={(e) => setCoreConfig({ ...coreConfig, contexto_maximo: Number(e.target.value) })}
                >
                  <option value={2048}>2048 (Rápido, pouca RAM)</option>
                  <option value={4096}>4096 (Padrão balanceado)</option>
                  <option value={8192}>8192 (Projetos de código)</option>
                  <option value={16384}>16384 (Pesado, mais contexto)</option>
                </select>
              </label>

              <label>
                Prompt de Sistema (Persona Base)
                <textarea
                  rows={4}
                  value={coreConfig.prompt_sistema}
                  onChange={(e) => setCoreConfig({ ...coreConfig, prompt_sistema: e.target.value })}
                />
              </label>

              <h3 style={{ marginTop: '24px' }}>Alocação de Hardware e Aceleração</h3>

              <label>
                Camadas de GPU (GPU Layers: {coreConfig.gpu_layers})
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="1"
                  value={coreConfig.gpu_layers}
                  onChange={(e) => setCoreConfig({ ...coreConfig, gpu_layers: Number(e.target.value) })}
                />
                <span className="settings-help">0 = Apenas CPU. Valores maiores transferem camadas para a VRAM da GPU.</span>
              </label>

              <label>
                Threads de CPU Alocadas
                <input
                  type="number"
                  min="1"
                  max="32"
                  value={coreConfig.cpu_threads}
                  onChange={(e) => setCoreConfig({ ...coreConfig, cpu_threads: Number(e.target.value) })}
                />
              </label>

              <label>
                Retenção de Memória de Contexto (TTL em turnos)
                <input
                  type="number"
                  min="1"
                  max="50"
                  value={coreConfig.memoria_ttl}
                  onChange={(e) => setCoreConfig({ ...coreConfig, memoria_ttl: Number(e.target.value) })}
                />
              </label>

              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={coreConfig.streaming}
                  onChange={(e) => setCoreConfig({ ...coreConfig, streaming: e.target.checked })}
                />
                <span>Ativar streaming de resposta (token-by-token SSE)</span>
              </label>

              <button
                type="submit"
                className="primary-button"
                disabled={salvandoConfig}
                style={{ marginTop: '20px' }}
              >
                <Save size={16} /> {salvandoConfig ? 'A gravar...' : 'Gravar Parâmetros'}
              </button>
            </form>
          )}

          {/* 2. ÁUDIO & VOZ */}
          {category === 'audio' && (
            <>
              <h3>Dispositivos de áudio</h3>
              <p className="settings-help">
                Seleção salva neste navegador. Durante uma conversa, o dispositivo é aplicado à chamada ativa.
              </p>
              <DeviceFields
                devices={devices}
                inputId={inputId}
                outputId={outputId}
                onInput={onInput}
                onOutput={onOutput}
                onRefresh={onRefresh}
              />
              <p className="settings-help">
                O navegador pode exigir permissão para mostrar os nomes. Troca de saída depende do suporte do navegador.
              </p>
              <AudioDiagnostics
                devices={deviceService}
                inputId={inputId}
                outputId={outputId}
                onNotice={onNotice}
              />
              {field('Motor de transcrição', 'Whisper local via /transcrever')}
              {field('Atalho do microfone', 'Tecla M (fora de caixas de texto)')}
              {field('Motor LLM conversacional', coreConfig.modelo_ativo || 'Ollama')}
            </>
          )}

          {/* 3. AUTOMAÇÃO & PC */}
          {category === 'pc' && (
            <>
              <div style={{ display: 'flex', gap: '8px', marginBottom: '1.5rem', borderBottom: '1px solid #333', paddingBottom: '0.75rem' }}>
                <button
                  type="button"
                  className={pcSubTab === 'playwright' ? 'secondary-button' : 'text-button'}
                  style={pcSubTab === 'playwright' ? { background: '#2563eb', color: '#fff' } : {}}
                  onClick={() => setPcSubTab('playwright')}
                >
                  Playwright MCP Bridge
                </button>
                <button
                  type="button"
                  className={pcSubTab === 'tabs' ? 'secondary-button' : 'text-button'}
                  style={pcSubTab === 'tabs' ? { background: '#2563eb', color: '#fff' } : {}}
                  onClick={() => setPcSubTab('tabs')}
                >
                  Abas do Navegador
                </button>
                <button
                  type="button"
                  className={pcSubTab === 'pc' ? 'secondary-button' : 'text-button'}
                  style={pcSubTab === 'pc' ? { background: '#2563eb', color: '#fff' } : {}}
                  onClick={() => setPcSubTab('pc')}
                >
                  Comandos do PC
                </button>
              </div>

              {pcSubTab === 'playwright' && <AutomationPanel api={api} />}
              {pcSubTab === 'tabs' && <WebBrowserPanel api={api} mode="tabs" />}
              {pcSubTab === 'pc' && <PCControlPanel api={api} onNotice={onNotice} />}
            </>
          )}


          {/* 4. SKILLS & ESPECIALISTAS */}
          {category === 'skills' && (
            <SkillsManager api={api} onNotice={onNotice} />
          )}

          {/* 5. MEMÓRIA RAG */}
          {category === 'memory' && (
            <>
              <MemoryManager api={api} onNotice={onNotice} />

              <div style={{ marginTop: '2rem', borderTop: '1px solid #333', paddingTop: '1.5rem' }}>
                <h4>Backup & Exportação Geral</h4>
                <p className="settings-help">
                  Baixe um arquivo JSON com todas as notas e transcrições salvas localmente neste dispositivo.
                </p>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={async () => {
                    try {
                      const response = await api.exportData();
                      if (!response.ok) throw new Error();
                      const url = URL.createObjectURL(await response.blob());
                      const link = document.createElement('a');
                      link.href = url;
                      link.download = 'agent-core-dados.json';
                      link.click();
                      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
                      onNotice('Exportação concluída com sucesso!');
                    } catch {
                      onNotice('Não foi possível exportar os dados.', 'error');
                    }
                  }}
                >
                  <Download size={16} /> Exportar Notas e Conversas (.json)
                </button>
              </div>
            </>
          )}

          {/* 6. REDE & SISTEMA */}
          {category === 'system' && (
            <>
              <div className="service-list">
                <div>
                  <span>
                    <StatusDot tone={status?.ok ? 'green' : 'red'} /> Motor Agent Core
                  </span>
                  <strong>{status?.ok ? 'ONLINE' : 'OFFLINE'}</strong>
                </div>
                <div>
                  <span>Lançador de Sistema</span>
                  <strong>Porta 8001</strong>
                </div>
                <div>
                  <span>Motor FastAPI</span>
                  <strong>Porta 8000</strong>
                </div>
                <div>
                  <span>Modelo Ativo</span>
                  <strong>{coreConfig.modelo_ativo || 'Ollama'}</strong>
                </div>
              </div>

              {advancedData?.network && (
                <div style={{ marginTop: '24px' }}>
                  <h3>Rede e Acesso Local</h3>
                  {field('Acesso por Telemóvel/Tablet', `http://${advancedData.network.ip_local}:3000`)}
                  {field('Porta do Motor IA', String(advancedData.network.porta_motor))}
                  {field('Porta da API/Lançador', String(advancedData.network.porta_api))}
                </div>
              )}

              {advancedData?.storage && (
                <div style={{ marginTop: '24px' }}>
                  <h3>Diretórios do Projeto</h3>
                  {advancedData.storage.map((d: any) => (
                    <div className="preference-row" key={d.id}>
                      <strong>{d.nome}</strong>
                      <span>{d.tamanho}</span>
                    </div>
                  ))}
                </div>
              )}

              {advancedData?.config && (
                <div style={{ marginTop: '24px' }}>
                  <h3>Manutenção e Logs</h3>
                  {field('Arquivo .env', advancedData.config.env_exists ? 'Configurado' : 'Ausente')}
                  {field('Tamanho de server_log.txt', advancedData.config.log_size)}
                  <button
                    className="danger-button"
                    onClick={limparLogsServidor}
                    style={{ marginTop: '12px' }}
                  >
                    <Trash2 size={16} /> Esvaziar Cache de Logs
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </section>
  );
}
