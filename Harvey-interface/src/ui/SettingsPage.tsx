import { useEffect, useState } from 'react';
import type { Notify, ServerStatus } from '../contracts';
import type { HarveyApi } from '../services/api';
import type { audioDevices } from '../voice/devices';
import AudioDiagnostics from '../voice/AudioDiagnostics';
import { DeviceFields, StatusDot } from './shared';
import ProfileEditor from './ProfileEditor';
import SkillsPanel from './SkillsPanel';
import WebBrowserPanel from './WebBrowserPanel';
import AutomationPanel from './AutomationPanel';
import DesktopPanel from './DesktopPanel';

type Category = 'general' | 'audio' | 'computer' | 'integrations' | 'privacy' | 'data' | 'system';
const categories: {id: Category; label:string}[] = [
  {id:'general',label:'Geral'}, {id:'audio',label:'Áudio e voz'},
  {id:'computer',label:'Computador e navegador'}, {id:'integrations',label:'Integrações e habilidades'},
  {id:'data',label:'Memória e histórico'}, {id:'privacy',label:'Privacidade e permissões'}, {id:'system',label:'Avançado'},
];
interface Preferences {voice:string|null; identity:string; storage:string; tools:{name:string;description:string}[]}
const currentCategory=():Category => {
  const raw=location.hash.split('/')[1]; const value=({skills:'integrations',personalization:'general'} as Record<string,string>)[raw]||raw;
  return categories.some(c=>c.id===value) ? value as Category : 'general';
};

export default function SettingsPage({status,api,audioDevices:deviceService,devices,inputId,outputId,onInput,onOutput,onRefresh,onRetry,onNotice}: {
  status:ServerStatus|null; api:HarveyApi; audioDevices:typeof audioDevices; devices:MediaDeviceInfo[];
  inputId:string; outputId:string; onInput:(v:string)=>void; onOutput:(v:string)=>void;
  onRefresh:()=>void; onRetry:()=>void; onNotice:Notify;
}) {
  const [computerTab,setComputerTab]=useState<'screen'|'browser'>('screen');
  const [category,setCategory]=useState<Category>(currentCategory);
  const [preferences,setPreferences]=useState<Preferences|null>(null);
  const [failed,setFailed]=useState(false);
  const [size,setSize]=useState(()=>localStorage.getItem('harvey-transcript-size') || 'normal');
  const load=async()=>{
    setFailed(false);
    try { const response=await api.preferences(); if(!response.ok) throw new Error(); setPreferences(await response.json()); }
    catch { setFailed(true); }
  };
  useEffect(()=>{ let alive=true; void api.preferences().then(async r=>{if(!r.ok) throw new Error();const data=await r.json();if(alive)setPreferences(data);}).catch(()=>{if(alive)setFailed(true);});return()=>{alive=false;}; },[api]);
  useEffect(()=>{const changed=()=>setCategory(currentCategory());window.addEventListener('hashchange',changed);return()=>window.removeEventListener('hashchange',changed);},[]);
  const select=(id:Category)=>{setCategory(id);location.hash=`settings/${id}`;};
  const field=(name:string,value:string)=><div className="preference-row"><strong>{name}</strong><span>{value}</span></div>;
  return <section className="settings-page">
    <div className="section-heading"><div><h1>Configurações</h1><p>Ajuste o Harvey ao seu modo de trabalhar.</p></div></div>
    <div className="settings-layout">
      <nav className="settings-nav" aria-label="Seções de configurações">{categories.map(c=><button key={c.id} aria-current={category===c.id?'page':undefined} className={category===c.id?'active':''} onClick={()=>select(c.id)}>{c.label}</button>)}</nav>
      <div className="settings-section">
        <h2>{categories.find(c=>c.id===category)?.label}</h2>
        {failed && <div className="error-banner" role="alert">Não foi possível carregar os detalhes. <button className="text-button" onClick={()=>void load()}>Tentar novamente</button></div>}
        {category==='general' && <>
          <label className="preference-row"><div><strong>Tamanho da transcrição</strong><p>Salvo neste navegador. Aplicação imediata.</p></div><select aria-label="Tamanho da transcrição" value={size} onChange={e=>{const value=e.target.value;setSize(value);localStorage.setItem('harvey-transcript-size',value);document.documentElement.dataset.transcriptSize=value;}}><option value="normal">Normal</option><option value="large">Maior</option></select></label>
          {field('Atalho do microfone','M, quando o foco está fora de um campo ou botão da chamada')}
          {field('Animações','Respeitam a preferência de movimento reduzido do sistema')}
          <ProfileEditor api={api} onNotice={onNotice}/>
        </>}
        {category==='audio' && <>
          <h3>Dispositivos de áudio</h3><p className="settings-help">Seleção salva neste navegador. Durante uma chamada, o dispositivo é aplicado à chamada ativa.</p>
          <DeviceFields devices={devices} inputId={inputId} outputId={outputId} onInput={onInput} onOutput={onOutput} onRefresh={onRefresh}/>
          <p className="settings-help">O navegador pode exigir permissão para mostrar os nomes. Troca de saída depende do suporte do navegador.</p>
          <AudioDiagnostics devices={deviceService} inputId={inputId} outputId={outputId} onNotice={onNotice}/>
          {field('Voz atual',preferences?.voice || 'Não informada pelo provedor')}
          <p className="settings-help">Voz definida no servidor. Mudanças exigem reinício controlado e uma nova sessão.</p>
        </>}
        {category==='computer' && <><div className="settings-tabs" role="group" aria-label="Controle do dispositivo"><button aria-pressed={computerTab==='screen'} onClick={()=>setComputerTab('screen')}>Tela e aplicativos</button><button aria-pressed={computerTab==='browser'} onClick={()=>setComputerTab('browser')}>Navegador</button></div>{computerTab==='screen'?<DesktopPanel api={api}/>:<><AutomationPanel api={api}/><details><summary>Controle básico de abas</summary><WebBrowserPanel api={api} mode="tabs"/><SkillsPanel api={api} onNotice={onNotice} mode="tabs"/></details></>}</>}
        {category==='integrations' && <><WebBrowserPanel api={api} mode="search"/><SkillsPanel api={api} onNotice={onNotice}/></>}
        {category==='privacy' && <><p className="settings-help">Áudio é processado na nuvem. Capturas permanecem em memória; consultas visuais enviam a imagem ao modelo autorizado.</p><p>Os acessos à tela, aplicativos e sites ficam em <a href="#settings/computer">Computador e navegador</a>. Cada acesso pode ser revogado ali.</p><SkillsPanel api={api} onNotice={onNotice} mode="privacy"/></>}
        {category==='data' && <>
          <p><a href="#notes">Abrir notas</a> · <a href="#history">Abrir histórico</a></p><details><summary>Local de armazenamento</summary>{field('Arquivos locais',preferences?.storage || 'Carregando…')}</details>
          <p className="settings-help">Notas e transcrições ficam no computador que executa o servidor. Preferências de dispositivos ficam neste navegador.</p>
          {field('Processamento de voz','LiveKit Cloud e provedor de voz na nuvem')}
          <p className="settings-help">Os registros locais não tornam o processamento de áudio local. As conversas permanecem salvas até serem excluídas por você.</p>
          <button className="secondary-button" onClick={async()=>{try{const response=await api.exportData();if(!response.ok)throw new Error();const url=URL.createObjectURL(await response.blob());const link=document.createElement('a');link.href=url;link.download='harvey-dados.json';link.click();window.setTimeout(()=>URL.revokeObjectURL(url),1000);}catch{onNotice('Não foi possível exportar os dados.','error');}}}>Exportar notas e conversas</button>
          <p className="settings-help">O arquivo contém suas notas e transcrições. Exclusão individual disponível em Notas e Histórico.</p>
        </>}
        {category==='system' && <>
          <div className="service-list">
            <div><span><StatusDot tone={status?.api_available?'green':'red'}/>Servidor local</span><strong>{status?.api_available?'Disponível':'Não alcançada'}</strong></div>
            <div><span>Credenciais LiveKit</span><strong>{status?.livekit_configured?'Configuradas':'Pendentes'}</strong></div>
            <div><span>Credenciais do provedor</span><strong>{status?.provider_configured?'Configuradas':'Pendentes'}</strong></div>
            <div><span>Agente</span><strong>{status?.agent_observation?.state==='session_observed'?'Presença recente em sessão':'Sem sessão recente observada'}</strong></div>
          </div>
          {field('Provedor',status?.provider_name || '—')}{field('Modelo',status?.model || '—')}
          {field('Última verificação',status?.checked_at?new Date(status.checked_at*1000).toLocaleString('pt-BR'):'Sem verificação')}
          <p className="settings-help">Credenciais configuradas não comprovam autenticação remota. Presença em sessão não garante disponibilidade do agente ocioso.</p>
          <button className="secondary-button" onClick={onRetry}>Verificar novamente</button>
          <details><summary>Ferramentas disponíveis</summary>{preferences?.tools.map(t=><div className="preference-row" key={t.name}><strong>{t.name}</strong><span>{t.description}</span></div>)}</details>
        </>}
      </div>
    </div>
  </section>;
}
