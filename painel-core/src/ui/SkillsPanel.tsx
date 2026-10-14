import { useEffect, useState } from 'react';
import type { HarveyApi } from '../services/api';
import type { Notify } from '../contracts';
import { responseData } from './ProfileEditor';

interface Schema {type:string; enum?:string[]; default?:string; properties?:Record<string,Schema>; maxLength?:number}
interface Permission {capability:string;scope:string;allowed:boolean}
interface Tool {name:string;display_name?:string;description:string;capability:string;scope:string;status:string;allowed:boolean;skill_id?:string;managed_by_transport?:boolean;parameters?:Schema}
interface Skill {id:string;name:string;description:string;status:string;installed:boolean;enabled:boolean;reasons:string[];config:Record<string,unknown>;config_schema:Schema;permissions:Permission[];version:string;execution_label?:string}
interface Catalog {skills:Skill[];tools:Tool[];activation:string}
interface Location {id:number;name:string;country:string;region:string;latitude:number;longitude:number;timezone:string}
const labels:Record<string,string>={available:'Disponível',disabled:'Desativada',blocked:'Dependência ou autorização pendente',not_installed:'Não instalada',next_session:'Próxima conversa'};
const locationLabel=(l:Location)=>`${l.name}, ${l.region}, ${l.country} · ${l.timezone} · ${l.latitude}, ${l.longitude}`;

interface Execution {
  success?:boolean; error?:string; run_id?:number;
  result?: {location?:Location; source?:{name:string;url:string}; queried_at_local?:string;
    period?:{date:string;timezone:string}; forecast?:{minimum_celsius:number;maximum_celsius:number;rain_probability_percent:number};
    current_estimate?:{temperature_celsius:number;time:string}; subject?:string; criteria?:string[]};
}

function ExecutionResult({value}:{value:unknown}) {
  const execution=value as Execution, data=execution.result;
  return <div className="execution-result" role="status">
    <h4>{execution.success?'Resultado confirmado':'Execução não concluída'}</h4>
    {execution.error&&<p>{execution.error}</p>}
    {data?.forecast&&data.location&&data.period&&<>
      <p><strong>{data.location.name}, {data.location.region}, {data.location.country}</strong></p>
      <p>Previsão para {data.period.date} · {data.period.timezone}</p>
      <p>Mínima {data.forecast.minimum_celsius} °C · máxima {data.forecast.maximum_celsius} °C · probabilidade de chuva {data.forecast.rain_probability_percent}%</p>
      {data.current_estimate&&<p>Estimativa atual: {data.current_estimate.temperature_celsius} °C, referente a {data.current_estimate.time}.</p>}
      <p className="settings-help">Fonte: <a href={data.source?.url} target="_blank" rel="noreferrer">{data.source?.name}</a>. Consulta: {data.queried_at_local}. Valores consultados; sem interpretação do agente.</p>
    </>}
    {data?.criteria&&<><p><strong>{data.subject}</strong></p><ul>{data.criteria.map(item=><li key={item}>{item}</li>)}</ul><p className="settings-help">Checklist gerado. Nenhuma memória salva automaticamente.</p></>}
    <details><summary>Dados e comprovante da execução {execution.run_id||''}</summary><pre>{JSON.stringify(value,null,2)}</pre></details>
  </div>;
}

function SkillCard({skill,tools,api,reload,onNotice}:{skill:Skill;tools:Tool[];api:HarveyApi;reload:()=>Promise<void>;onNotice:Notify}) {
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[query,setQuery]=useState('');
  const [locations,setLocations]=useState<Location[]>([]),[selected,setSelected]=useState<Location|null>(null);
  const [draft,setDraft]=useState<Record<string,unknown>>({});
  const [args,setArgs]=useState<Record<string,Record<string,string|number>>>({});
  const [result,setResult]=useState<unknown>(null);
  useEffect(()=>{const defaults=Object.fromEntries(Object.entries(skill.config_schema?.properties||{}).filter(([,v])=>v.default!==undefined).map(([k,v])=>[k,v.default]));setDraft({...defaults,...skill.config});setSelected((skill.config?.location as Location)||null);},[JSON.stringify(skill.config),JSON.stringify(skill.config_schema)]);
  const act=async(operation:()=>Promise<Response>,message?:string)=>{
    setBusy(true);setError('');
    try{const data=await responseData(await operation());await reload();if(message)onNotice(message,'success');return data;}
    catch(err){setError((err as Error).message);return null;}finally{setBusy(false);}
  };
  return <article className="skill-card">
    <div className="skill-heading"><h3>{skill.name}</h3><span>{labels[skill.status]||skill.status}</span></div>
    <p className="settings-help">{skill.description}</p>
    <details><summary>Informações da habilidade</summary><p>Versão {skill.version} · {skill.execution_label||'Serviço local'}</p></details>{!skill.installed?<button className="secondary-button" disabled={busy} onClick={()=>void act(()=>api.installSkill(skill.id),'Pacote instalado e desativado. Configure antes de ativar.')}>Instalar {skill.name}</button>:<>
      {skill.reasons?.length>0&&<ul className="settings-help">{skill.reasons.map(reason=><li key={reason}>{reason}</li>)}</ul>}
      {skill.reasons?.some(reason=>reason.startsWith('Pacote mudou'))&&<button className="secondary-button" disabled={busy} onClick={()=>void act(()=>api.installSkill(skill.id),'Pacote reinstalado e desativado. Confira configuração e acessos antes de ativar.')}>Reinstalar pacote revisado</button>}
      {skill.permissions.map(permission=><div className="permission-row" key={permission.scope}><span>{permission.capability} · {permission.scope}<small>Autoriza o serviço declarado nesta habilidade.</small></span><button className="secondary-button" disabled={busy} onClick={()=>void act(()=>api.authorize(permission.capability,permission.scope,!permission.allowed))}>{permission.allowed?'Revogar acesso':'Autorizar acesso'}</button></div>)}
      <form className="extension-form" onSubmit={e=>{e.preventDefault();void act(()=>api.configureSkill(skill.id,selected?{...draft,location:selected}:draft),'Configuração salva. Aplicação na próxima conversa.');}}>
        {Object.entries(skill.config_schema.properties||{}).map(([key,schema])=>schema.type==='object'?<div key={key}>
          <label>Cidade<input value={query} maxLength={100} onChange={e=>setQuery(e.target.value)} placeholder="Digite cidade ou município"/></label>
          <button className="text-button" type="button" disabled={busy||query.trim().length<2} onClick={async()=>{const data=await act(()=>api.skillOptions(skill.id,query));if(data){setLocations(data);if(!data.length)setError('Nenhuma localização encontrada.');}}}>Buscar cidades</button>
          {locations.length>0&&<label>Localizações encontradas<select aria-label="Localizações encontradas" value={selected?.id||''} onChange={e=>setSelected(locations.find(l=>l.id===Number(e.target.value))||null)}><option value="">Selecione a localização</option>{locations.map(l=><option key={l.id} value={l.id}>{locationLabel(l)}</option>)}</select></label>}
          {selected&&<p className="settings-help" data-testid="resolved-location">Localização selecionada: {locationLabel(selected)}</p>}
          {skill.config.location!==undefined&&<p className="settings-help">Localização salva: {locationLabel(skill.config.location as Location)}</p>}
        </div>:<label key={key}>{key==='criteria'?'Critérios separados por ponto e vírgula':key}<textarea value={String(draft[key]||'')} maxLength={schema.maxLength} onChange={e=>setDraft({...draft,[key]:e.target.value})}/></label>)}
        <button type="submit" className="secondary-button" disabled={busy}>Salvar configuração</button>
      </form>
      <button className="secondary-button" disabled={busy} onClick={()=>void act(()=>api.enableSkill(skill.id,!skill.enabled),skill.enabled?'Habilidade desativada. Novas execuções bloqueadas.':'Ativada. Disponível na próxima conversa.')}>{skill.enabled?'Desativar habilidade':'Ativar habilidade'}</button>
      {tools.map(tool=><div className="skill-test" key={tool.name}>
        <details><summary>Experimentar e autorizar esta habilidade</summary><h4>Teste manual</h4><p className="settings-help">Executa pela mesma validação e autorização usadas pelo agente.</p>
        <form className="extension-form" onSubmit={async e=>{e.preventDefault();const data=await act(()=>api.executeCapability(tool.name,args[tool.name]||{}));if(data)setResult(data);}}>
          {Object.entries(tool.parameters?.properties||{}).map(([key,schema])=><label key={key}>{key==='day'?'Período':key==='subject'?'Assunto':key}{schema.enum?<select aria-label={key==='day'?'Período':key} value={args[tool.name]?.[key]||schema.default||schema.enum[0]} onChange={e=>setArgs({...args,[tool.name]:{...args[tool.name],[key]:e.target.value}})}>{schema.enum.map(value=><option key={value} value={value}>{value==='today'?'Hoje':value==='tomorrow'?'Amanhã':value}</option>)}</select>:<input maxLength={schema.maxLength} value={args[tool.name]?.[key]||''} onChange={e=>setArgs({...args,[tool.name]:{...args[tool.name],[key]:schema.type==='integer'?Number(e.target.value):e.target.value}})}/>}</label>)}
          <button className="secondary-button" type="submit" disabled={busy||tool.status!=='available'}>Executar {skill.name}</button>
        </form>
        <button className="text-button" disabled={busy} onClick={()=>void act(()=>api.authorize(tool.capability,tool.scope,!tool.allowed))}>{tool.allowed?'Revogar execução':'Autorizar execução'}</button>
      </details></div>)}
    </>}
    {error&&<div className="error-banner" role="alert">{error}</div>}
    {result!==null&&<ExecutionResult value={result}/>}
  </article>;
}

export default function SkillsPanel({api,onNotice,mode='integrations'}:{api:HarveyApi;onNotice:Notify;mode?:'integrations'|'privacy'|'tabs'}) {
  const [catalog,setCatalog]=useState<Catalog|null>(null),[error,setError]=useState(''),[runs,setRuns]=useState<unknown[]>([]);
  const load=async()=>{setCatalog(await responseData(await api.capabilities()));setRuns(await responseData(await api.capabilityRuns()));};
  useEffect(()=>{let alive=true;const timer=setInterval(()=>{void api.capabilities().then(responseData).then(data=>{if(alive)setCatalog(previous=>JSON.stringify(previous)===JSON.stringify(data)?previous:data);}).catch(()=>{});},3000);return()=>{alive=false;clearInterval(timer);};},[api]);
  useEffect(()=>{let alive=true;void Promise.all([api.capabilities().then(responseData),api.capabilityRuns().then(responseData)]).then(([data,history])=>{if(alive){setCatalog(data);setRuns(history);}}).catch(()=>{if(alive)setError('Não foi possível carregar capacidades.');});return()=>{alive=false;};},[api]);
  if(!catalog)return <div role="status">{error||'Carregando capacidades…'}{error&&<button className="text-button" onClick={()=>void load().then(()=>setError('')).catch(()=>setError('Falha ao carregar capacidades.'))}>Tentar novamente</button>}</div>;
  return <>
    <p className="settings-help">{catalog.activation} Uma operação já iniciada pode terminar.</p>
    {catalog.skills.filter(skill=>mode==='tabs'?skill.id==='browser-tabs':mode==='integrations'?!['browser-automation','desktop-control','browser-tabs'].includes(skill.id):false).map(skill=><SkillCard key={skill.id} skill={skill} tools={catalog.tools.filter(t=>t.skill_id===skill.id)} api={api} reload={load} onNotice={onNotice}/>)}
    {mode==='privacy'&&<><h3>Permissões da conversa</h3><p className="settings-help">Essas autorizações controlam as ferramentas do agente. A gestão manual de seus dados pela interface continua disponível.</p>
    {catalog.tools.filter(t=>!t.skill_id).map(tool=><div className="permission-row" key={tool.name}><span><strong>{tool.display_name||tool.description}</strong><small>{tool.description} · {labels[tool.status]}</small></span>{!tool.managed_by_transport&&<button className="text-button" onClick={async()=>{try{await responseData(await api.authorize(tool.capability,tool.scope,!tool.allowed));await load();}catch(err){onNotice((err as Error).message,'error');}}}>{tool.allowed?'Desautorizar':'Autorizar'}</button>}</div>)}
    </>}<details><summary>Detalhes técnicos e execuções recentes</summary><p className="settings-help">Resultados persistidos. Não representam consultas novas. Podem conter informações pessoais.</p><pre className="identity-preview">{JSON.stringify(runs,null,2)}</pre></details>
  </>;
}
