import { useEffect, useRef, useState } from 'react';
import type { Notify } from '../contracts';
import type { audioDevices } from './devices';

/** Testes explícitos de entrada e saída. A captura sempre termina ou é cancelada ao sair. */
export default function AudioDiagnostics({devices, inputId, outputId, onNotice}: {
  devices: typeof audioDevices; inputId: string; outputId: string; onNotice: Notify;
}) {
  const [testing, setTesting] = useState(false);
  const [level, setLevel] = useState(0);
  const [result, setResult] = useState('');
  const cleanup = useRef<() => void>(() => {});
  const generation = useRef(0);
  const player = useRef<HTMLAudioElement | null>(null);
  const audioUrl = useRef<string | null>(null);
  const outputGeneration = useRef(0);
  const releaseOutput = () => {
    player.current?.pause(); player.current = null;
    if (audioUrl.current) URL.revokeObjectURL(audioUrl.current);
    audioUrl.current = null;
  };
  useEffect(() => () => { generation.current++; outputGeneration.current++; cleanup.current(); releaseOutput(); }, []);

  const testInput = async () => {
    generation.current++;
    const id = generation.current;
    cleanup.current();
    setTesting(true); setLevel(0); setResult('Fale durante cinco segundos.');
    let stream: MediaStream | undefined;
    let context: AudioContext | undefined;
    let timer = 0; let frame = 0; let peak = 0;
    const stop = () => { clearTimeout(timer); cancelAnimationFrame(frame); stream?.getTracks().forEach(t => t.stop()); if(context && context.state !== 'closed') void context.close(); };
    cleanup.current = stop;
    try {
      stream = await devices.acquire(inputId);
      if (id !== generation.current) { stop(); return; }
      context = new AudioContext();
      await context.resume();
      if (id !== generation.current) { stop(); return; }
      const analyser = context.createAnalyser(); analyser.fftSize = 256;
      context.createMediaStreamSource(stream).connect(analyser);
      const samples = new Uint8Array(analyser.fftSize);
      const tick = () => {
        analyser.getByteTimeDomainData(samples);
        const rms = Math.sqrt(samples.reduce((sum, x) => sum + ((x-128)/128)**2, 0)/samples.length);
        peak = Math.max(peak, rms); setLevel(Math.min(100, Math.round(rms * 500)));
        frame = requestAnimationFrame(tick);
      };
      tick();
      const label = stream.getAudioTracks()[0]?.label || 'Microfone autorizado';
      timer = window.setTimeout(() => {
        stop(); setTesting(false); setLevel(0);
        setResult(`${label}: ${peak > 0.008 ? 'sinal de áudio detectado' : 'nenhum sinal significativo detectado'}. A captura foi encerrada.`);
      }, 5000);
    } catch {
      stop(); if(id !== generation.current) return;
      setTesting(false); setResult('Não foi possível acessar o microfone. Verifique a permissão no navegador.');
      onNotice('Teste de microfone falhou.', 'error');
    }
  };
  const testOutput = async () => {
    const id=++outputGeneration.current;
    releaseOutput();
    // Tom curto e moderado em WAV, reproduzido no dispositivo escolhido.
    const sampleRate=24000, count=sampleRate/2, data=new ArrayBuffer(44+count*2), view=new DataView(data);
    const text=(offset:number,value:string)=>[...value].forEach((c,i)=>view.setUint8(offset+i,c.charCodeAt(0)));
    text(0,'RIFF'); view.setUint32(4,36+count*2,true); text(8,'WAVE'); text(12,'fmt ');
    view.setUint32(16,16,true); view.setUint16(20,1,true); view.setUint16(22,1,true);
    view.setUint32(24,sampleRate,true); view.setUint32(28,sampleRate*2,true);
    view.setUint16(32,2,true); view.setUint16(34,16,true); text(36,'data'); view.setUint32(40,count*2,true);
    for(let i=0;i<count;i++) view.setInt16(44+i*2,Math.sin(2*Math.PI*440*i/sampleRate)*3200*Math.min(1,i/240,(count-i)/240),true);
    audioUrl.current=URL.createObjectURL(new Blob([data],{type:'audio/wav'}));
    const audio=new Audio(audioUrl.current); player.current=audio;
    try {
      const sink=audio as HTMLAudioElement & {setSinkId?: (id:string)=>Promise<void>};
      if(outputId) { if(!sink.setSinkId) throw new Error('unsupported'); await sink.setSinkId(outputId); }
      if(id!==outputGeneration.current){audio.pause();return;}
      audio.onended=()=>{if(id===outputGeneration.current)releaseOutput();}; await audio.play();
      if(id!==outputGeneration.current){audio.pause();return;}
      setResult('Tom enviado à saída selecionada. Confirme se você ouviu.');
    } catch { if(id===outputGeneration.current){releaseOutput();onNotice('Não foi possível testar a saída selecionada neste navegador.', 'error');} }
  };
  return <div className="audio-diagnostics">
    <div className="device-actions"><button className="secondary-button" disabled={testing} onClick={() => void testInput()}>Testar microfone</button>
      {testing && <button className="text-button" onClick={() => { generation.current++; cleanup.current(); setTesting(false); setLevel(0); setResult('Captura encerrada.'); }}>Parar teste</button>}
      <button className="secondary-button" onClick={() => void testOutput()}>Testar saída</button></div>
    <meter min={0} max={100} value={level} aria-label="Sinal do microfone" />
    <p role="status">{result || 'Os testes só usam áudio quando você os inicia.'}</p>
  </div>;
}
