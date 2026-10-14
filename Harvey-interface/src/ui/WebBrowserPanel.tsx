import {useEffect,useState} from 'react';
import type {HarveyApi} from '../services/api';
import {responseData} from './ProfileEditor';
export function IntegrationResults({room,api}:{room?:string;api:HarveyApi}) {
 const [runs,setRuns]=useState<any[]>([]);
 useEffect(()=>{let alive=true;const load=async()=>{try{const data=await responseData(await api.capabilityRuns(room));if(alive)setRuns(data.filter((r:any)=>(!room||r.session_id===room)&&['web-search','browser-tabs','browser-automation'].includes(r.skill)));}catch{}};void load();const timer=setInterval(load,2000);return()=>{alive=false;clearInterval(timer);};},[room,api]);
 if(!runs.length)return null;
 return <div className="integration-results">{runs.map(run=>{const result=run.result.result;return <article className="skill-card" key={run.id}>
 <strong>{result?.results?'Pesquisa web':result?.tabs?'Abas do navegador':'Ação no navegador'} · {({completed:'Concluída',failed:'Falhou',unknown:'Resultado desconhecido',confirmation_required:'Confirmação necessária'} as Record<string,string>)[result?.state]||'Falhou'}</strong>{result?.error&&<p>{result.error}</p>}
 {result?.results&&<><p>Fonte: {result.source} · consulta {new Date(result.queried_at).toLocaleString('pt-BR')}</p>{!result.results.length&&<p>Nenhum resultado encontrado.</p>}{result.results.map((item:any)=><div className="search-source" key={item.url}><a href={item.url} target="_blank" rel="noreferrer">{item.title||item.url}</a><p>{item.snippet.length>300?item.snippet.slice(0,300)+"…":item.snippet}</p>{item.snippet.length>300&&<details><summary>Trecho completo da busca</summary><p>{item.snippet}</p></details>}<small>{item.published_at?'Data indicada pelo índice: '+item.published_at:'Data não fornecida'}</small></div>)}<p className="settings-help">{result.limitation}</p></>}
 {result?.tabs&&<ul>{result.tabs.map((tab:any)=><li key={tab.tab_id}>#{tab.tab_id} · {tab.title} · {tab.url}</li>)}</ul>}
 {result?.tab_id!==undefined&&<p>Aba #{result.tab_id} {result.closed?'fechada':result.activated?'ativada':result.opened?'aberta':''}</p>}
 <details><summary>Comprovante #{run.id}</summary><pre>{JSON.stringify(run.result,null,2)}</pre></details></article>;})}</div>;
}
export default function WebBrowserPanel({api,mode='search'}:{api:HarveyApi;mode?:'search'|'tabs'}){
 const [status,setStatus]=useState<any>(null),[code,setCode]=useState(''),[error,setError]=useState('');
 const load=async()=>{try{setStatus(await responseData(await api.browserStatus()));setError('');}catch{setStatus((previous:any)=>previous?{...previous,device:{...previous.device,connected:false}}:null);setError('Falha ao consultar integrações.');}};
 useEffect(()=>{void load();const timer=setInterval(load,3000);return()=>clearInterval(timer);},[]);
 useEffect(()=>setCode(''),[status?.device?.id]);
 return <>{mode==='search'&&<><h3>Pesquisa web</h3>
 <p>{status?.search?.length?'Pesquisa indisponível: configure o serviço abaixo.':status?'Serviço de pesquisa configurado':'Carregando…'}</p>
 <details><summary>Configurar serviço de pesquisa</summary><p className="settings-help">TAVILY_API_KEY fica somente no .env do backend. Reinicie serviços após mudar a chave. Use plano gratuito sem cobrança automática. Instale Pesquisa web abaixo e autorize execução.</p></details>
 </>}{mode==='tabs'&&<><p><strong>{status?.device?.connected?'Navegador conectado':'Navegador desconectado'}</strong> {status?.device?.browser} · {status?.device?.device}</p>
 <p className="settings-help">Edge: abra edge://extensions, ative Modo de desenvolvedor, Carregar sem compactação e selecione browser-extension do Harvey-live. Abra o popup da extensão e cole o código abaixo.</p>
 <button className="secondary-button" onClick={async()=>{try{setCode((await responseData(await api.browserPairCode())).code);}catch{setError('Falha ao gerar código.');}}}>Gerar código de vínculo</button>
 {code&&<p>Código válido por 2 minutos: <code>{code}</code></p>}
 <button className="text-button" onClick={async()=>{try{await responseData(await api.browserRevoke());setCode('');await load();}catch{setError('Falha ao revogar vínculo.');}}}>Revogar vínculo</button>
 <p className="settings-help">Tabs permite títulos e URLs; storage guarda vínculo; alarms reconecta. Rede limitada ao backend local. Sem acesso a conteúdo, cookies ou scripts. Autorizações individuais no catálogo abaixo.</p>
 </>}{error&&<p role="alert">{error}</p>}
 {mode==='tabs'&&<details><summary>Estado dos comandos</summary>{status?.commands?.map((c:any)=><p key={c.id}>{c.operation} · {({requested:'Solicitada',dispatched:'Entregue; aguardando',completed:'Concluída',failed:'Falhou',unknown:'Resultado desconhecido',confirmation_required:'Confirmação necessária',confirmed:'Confirmação recebida'} as Record<string,string>)[c.state]||c.state} · {c.id}</p>)}</details>}
 <details><summary>Resultados de pesquisa e ações recentes</summary><IntegrationResults api={api}/></details></>;
}
