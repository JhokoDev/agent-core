import {useEffect,useState} from 'react';
import {desktopRequest} from '../services/desktop';
import {taskLabels} from './taskState';
export default function DesktopStatus(){
 const [state,setState]=useState<any>(null);
 useEffect(()=>{let alive=true;const timer=setInterval(()=>{void desktopRequest('status').then(s=>{if(alive)setState(s);}).catch(()=>{if(alive)setState(null);});},1500);return()=>{alive=false;clearInterval(timer);};},[]);
 if(!state?.observing&&!['executing','waiting','paused'].includes(state?.state))return null;
 return <aside className="desktop-status" aria-label="Tarefa no computador"><div role="status"><strong>{taskLabels[state.state]||'Verificando tarefa'}</strong>{state.task?.stage&&<small>{state.task.stage}</small>}{state.task?.plan&&<small>Etapa {Math.min((state.task.cursor||0)+1,state.task.plan.length)} de {state.task.plan.length}</small>}</div>{state.state!=='paused'&&<button onClick={()=>void desktopRequest('control',{operation:'pause'}).then(()=>desktopRequest('status')).then(setState)}>Pausar tarefa</button>}<button onClick={()=>void desktopRequest('control',{operation:'stop'}).then(()=>desktopRequest('status')).then(setState)}>Parar controle</button><a href="#settings/computer">Ver tarefa</a></aside>;
}
