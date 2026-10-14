import { useCallback, useEffect, useRef, useState } from 'react';
import {
  AudioLines,
  Clock3,
  Mic,
  MicOff,
  PhoneOff,
  SlidersHorizontal,
  X,
  ShieldCheck,
  Send,
  RefreshCw,
  Volume2,
  VolumeX,
  Sparkles,
} from 'lucide-react';
import type { ConversationProps, Speaker, TranscriptEntry, SessionMetrics } from '../contracts';
import { StatusDot, DeviceFields, TranscriptToolbar, TranscriptList } from '../ui/shared';
import { formatClock } from '../ui/format';
import { IntegrationResults } from '../ui/WebBrowserPanel';

interface AgenteOpt {
  id: string;
  nome: string;
  tipo: string;
}

export default function LocalConversation({
  recordEvent,
  api,
  roomName,
  visible,
  devices,
  inputId,
  outputId,
  onInput,
  onOutput,
  onRefreshDevices,
  onEnd,
  onReturn,
  onNotice,
  onConnected,
  onError,
}: ConversationProps) {
  const [entries, setEntries] = useState<TranscriptEntry[]>([]);
  const [query, setQuery] = useState('');
  const [inputText, setInputText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [isUserSpeaking, setIsUserSpeaking] = useState(false);
  const [transcribingAudio, setTranscribingAudio] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [deviceOpen, setDeviceOpen] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [skills, setSkills] = useState<AgenteOpt[]>([]);
  const [selectedSkill, setSelectedSkill] = useState<string>('default');
  const [metrics, setMetrics] = useState<SessionMetrics | null>(null);
  const [micLevel, setMicLevel] = useState(0);
  const [micMuted, setMicMuted] = useState(false);
  const [autoTts, setAutoTts] = useState(true);
  const [vadEnabled, setVadEnabled] = useState(true);
  const [vadSensitivity, setVadSensitivity] = useState<'normal' | 'alta' | 'baixa'>('normal');
  const [silenceDelay, setSilenceDelay] = useState<number>(1000); // 1000ms silêncio padrão
  const [activeModel, setActiveModel] = useState('Agent Core');

  const startedAt = useRef(Date.now());
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const activeStreamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const ttsAnimIntervalRef = useRef<number | null>(null);

  // Refs de estado síncronos para o loop de áudio VAD
  const isUserSpeakingRef = useRef(false);
  const speechStartRef = useRef(0);
  const lastSoundTimeRef = useRef(0);
  const isStreamingRef = useRef(false);
  const transcribingRef = useRef(false);
  const isSpeakingRef = useRef(false);
  const micMutedRef = useRef(false);
  const vadEnabledRef = useRef(true);
  const silenceDelayRef = useRef(1000);
  const sensitivityThresholdRef = useRef(0.08);

  const appliedInputId = useRef(inputId);
  const appliedOutputId = useRef(outputId);

  // Mantém refs síncronas atualizadas
  useEffect(() => {
    isStreamingRef.current = isStreaming;
  }, [isStreaming]);

  useEffect(() => {
    transcribingRef.current = transcribingAudio;
  }, [transcribingAudio]);

  useEffect(() => {
    isSpeakingRef.current = isSpeaking;
  }, [isSpeaking]);

  useEffect(() => {
    micMutedRef.current = micMuted;
  }, [micMuted]);

  useEffect(() => {
    vadEnabledRef.current = vadEnabled;
  }, [vadEnabled]);

  useEffect(() => {
    silenceDelayRef.current = silenceDelay;
  }, [silenceDelay]);

  useEffect(() => {
    if (vadSensitivity === 'alta') sensitivityThresholdRef.current = 0.05;
    else if (vadSensitivity === 'baixa') sensitivityThresholdRef.current = 0.13;
    else sensitivityThresholdRef.current = 0.08;
  }, [vadSensitivity]);

  // Notifica conexão ativa
  useEffect(() => {
    onConnected();
    recordEvent('room_connected', 'local_voice_room', roomName);
  }, [onConnected, recordEvent, roomName]);

  // Carrega lista de skills/agentes para seleção
  useEffect(() => {
    let alive = true;
    fetch('/agentes')
      .then((res) => (res.ok ? res.json() : []))
      .then((data: AgenteOpt[]) => {
        if (alive) {
          setSkills(data);
          const hasDefault = data.some((d) => d.id === 'default');
          if (hasDefault) setSelectedSkill('default');
          else if (data.length > 0) setSelectedSkill(data[0].id);
        }
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  // Contador de tempo da sessão
  useEffect(() => {
    const tick = window.setInterval(() => {
      setElapsed((Date.now() - startedAt.current) / 1000);
    }, 500);
    return () => window.clearInterval(tick);
  }, []);

  // Atualiza métricas locais da sessão
  useEffect(() => {
    const userTurns = entries.filter((e) => e.speaker === 'user').length;
    const agentTurns = entries.filter((e) => e.speaker === 'agent').length;
    setMetrics({
      duration_seconds: Math.floor(elapsed),
      user_turns: userTurns,
      agent_turns: agentTurns,
      interruptions: 0,
      status: 'active',
      end_reason: null,
    });
  }, [entries, elapsed]);

  // Limpeza de áudio e fala ao desmontar
  const stopAudioTracks = useCallback(() => {
    if (activeStreamRef.current) {
      activeStreamRef.current.getTracks().forEach((t) => t.stop());
      activeStreamRef.current = null;
    }
    if (audioCtxRef.current) {
      try {
        void audioCtxRef.current.close();
      } catch {}
      audioCtxRef.current = null;
    }
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    if (ttsAnimIntervalRef.current) {
      clearInterval(ttsAnimIntervalRef.current);
      ttsAnimIntervalRef.current = null;
    }
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
  }, []);

  useEffect(() => {
    return () => {
      stopAudioTracks();
    };
  }, [stopAudioTracks]);

  // Função para falar resposta (TTS local no navegador)
  const speakResponse = useCallback((textToSpeak: string) => {
    if (!autoTts || !('speechSynthesis' in window)) return;

    window.speechSynthesis.cancel();

    // Limpa Markdown, blocos de código e tags think da fala
    const clean = textToSpeak
      .replace(/<think>[\s\S]*?<\/think>/g, '')
      .replace(/```[\s\S]*?```/g, 'Bloco de código executado.')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .replace(/[#*_~>]/g, '')
      .replace(/\s+/g, ' ')
      .trim();

    if (!clean) return;

    const utterance = new SpeechSynthesisUtterance(clean);
    utterance.lang = 'pt-BR';
    utterance.rate = 1.05;
    utterance.pitch = 1.0;

    const voices = window.speechSynthesis.getVoices();
    const ptVoice =
      voices.find((v) => v.lang === 'pt-BR' && (v.name.includes('Natural') || v.name.includes('Google'))) ||
      voices.find((v) => v.lang.startsWith('pt'));
    if (ptVoice) utterance.voice = ptVoice;

    setIsSpeaking(true);
    isSpeakingRef.current = true;

    // Animação de VU meter simulada durante a fala do agente
    if (ttsAnimIntervalRef.current) clearInterval(ttsAnimIntervalRef.current);
    ttsAnimIntervalRef.current = window.setInterval(() => {
      setMicLevel(0.25 + Math.random() * 0.55);
    }, 120);

    utterance.onend = () => {
      setIsSpeaking(false);
      isSpeakingRef.current = false;
      setMicLevel(0);
      if (ttsAnimIntervalRef.current) {
        clearInterval(ttsAnimIntervalRef.current);
        ttsAnimIntervalRef.current = null;
      }
    };

    utterance.onerror = () => {
      setIsSpeaking(false);
      isSpeakingRef.current = false;
      setMicLevel(0);
      if (ttsAnimIntervalRef.current) {
        clearInterval(ttsAnimIntervalRef.current);
        ttsAnimIntervalRef.current = null;
      }
    };

    window.speechSynthesis.speak(utterance);
  }, [autoTts]);

  function parseStreamContent(rawContent: string, explicitThinking: string) {
    let combinedThinking = explicitThinking || '';
    let cleanText = rawContent || '';
    let isThinkingState = false;

    if (cleanText.includes('<think>')) {
      const parts = cleanText.split('<think>');
      const beforeThink = parts[0];
      const rest = parts.slice(1).join('<think>');

      if (rest.includes('</think>')) {
        const thinkSplit = rest.split('</think>');
        const thinkContent = thinkSplit[0];
        const afterThink = thinkSplit.slice(1).join('</think>');

        combinedThinking = combinedThinking
          ? `${combinedThinking.trim()}\n${thinkContent.trim()}`
          : thinkContent.trim();
        cleanText = `${beforeThink}${afterThink}`.trim();
        isThinkingState = false;
      } else {
        combinedThinking = combinedThinking
          ? `${combinedThinking.trim()}\n${rest.trim()}`
          : rest.trim();
        cleanText = beforeThink.trim();
        isThinkingState = true;
      }
    }

    return {
      cleanText,
      reasoning: combinedThinking.trim(),
      isThinking: isThinkingState || (!!explicitThinking && !cleanText),
    };
  }

  // Enviar mensagem de texto e receber stream SSE do Agent Core
  const enviarMensagem = useCallback(async (textoParaEnviar: string) => {
    const texto = textoParaEnviar.trim();
    if (!texto || isStreamingRef.current) return;

    // Se o agente estiver falando, interrompe a fala imediatamente
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      isSpeakingRef.current = false;
    }

    const userEntryId = `user-${Date.now()}`;
    const agentEntryId = `agent-${Date.now()}`;

    setEntries((prev) => [
      ...prev,
      { id: userEntryId, speaker: 'user' as Speaker, text: texto, timestamp: Date.now(), final: true },
      { id: agentEntryId, speaker: 'agent' as Speaker, text: '', timestamp: Date.now(), final: false, isThinking: true },
    ]);

    setInputText('');
    setIsStreaming(true);
    isStreamingRef.current = true;

    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer minhasenha_super_segura_de_32_caracteres_minimo_aqui',
        },
        body: JSON.stringify({
          texto,
          skill_id: selectedSkill,
          chat_id: roomName,
        }),
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      if (!response.body) throw new Error('Sem corpo de resposta para streaming.');

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let rawText = '';
      let accumulatedThinking = '';
      let modelInUse = '';
      let routeInUse = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const blocos = buffer.split(/\r?\n\r?\n/);
        buffer = blocos.pop() || '';

        for (const bloco of blocos) {
          const trimmed = bloco.trim();
          if (!trimmed) continue;

          const lines = trimmed.split(/\r?\n/);
          for (const line of lines) {
            if (line.startsWith('data:')) {
              const jsonStr = line.replace(/^data:\s*/, '').trim();
              if (!jsonStr) continue;

              try {
                const dados = JSON.parse(jsonStr);

                if (dados.type === 'chunk') {
                  if (dados.thinking) {
                    accumulatedThinking += dados.thinking;
                  }
                  if (dados.content) {
                    rawText += dados.content;
                  }

                  const parsed = parseStreamContent(rawText, accumulatedThinking);
                  setEntries((prev) => {
                    const updated = [...prev];
                    const idx = updated.findIndex((e) => e.id === agentEntryId);
                    if (idx !== -1) {
                      updated[idx] = {
                        ...updated[idx],
                        text: parsed.cleanText,
                        reasoning: parsed.reasoning,
                        isThinking: parsed.isThinking,
                        model: modelInUse || updated[idx].model,
                        route: routeInUse || updated[idx].route,
                        final: false,
                      };
                    }
                    return updated;
                  });
                } else if (dados.type === 'message') {
                  if (dados.model) {
                    modelInUse = dados.model;
                    setActiveModel(dados.model);
                  }
                  if (dados.route) routeInUse = dados.route;
                  if (dados.reasoning && !accumulatedThinking) {
                    accumulatedThinking = dados.reasoning;
                  }
                  if (dados.content !== undefined) {
                    rawText = dados.content;
                  }

                  const parsed = parseStreamContent(rawText, accumulatedThinking);
                  setEntries((prev) => {
                    const updated = [...prev];
                    const idx = updated.findIndex((e) => e.id === agentEntryId);
                    if (idx !== -1) {
                      updated[idx] = {
                        ...updated[idx],
                        text: parsed.cleanText,
                        reasoning: parsed.reasoning,
                        isThinking: false,
                        model: modelInUse,
                        route: routeInUse,
                        final: false,
                      };
                    }
                    return updated;
                  });
                } else if (dados.type === 'done') {
                  const parsed = parseStreamContent(rawText, accumulatedThinking);
                  setEntries((prev) => {
                    const updated = [...prev];
                    const idx = updated.findIndex((e) => e.id === agentEntryId);
                    if (idx !== -1) {
                      updated[idx] = {
                        ...updated[idx],
                        text: parsed.cleanText || updated[idx].text,
                        reasoning: parsed.reasoning || updated[idx].reasoning,
                        isThinking: false,
                        final: true,
                      };
                    }
                    return updated;
                  });
                }
              } catch {}
            }
          }
        }
      }

      // Marcar como final e acionar TTS
      const parsedFinal = parseStreamContent(rawText, accumulatedThinking);
      const finalText = parsedFinal.cleanText || rawText;

      setEntries((prev) => {
        const updated = [...prev];
        const lastIdx = updated.findIndex((e) => e.id === agentEntryId);
        if (lastIdx !== -1) {
          updated[lastIdx] = {
            ...updated[lastIdx],
            text: finalText || updated[lastIdx].text,
            reasoning: parsedFinal.reasoning || updated[lastIdx].reasoning,
            isThinking: false,
            final: true,
          };
        }
        return updated;
      });

      if (finalText) {
        speakResponse(finalText);
      }
    } catch (err) {
      const msg = (err as Error).message;
      setEntries((prev) => {
        const updated = [...prev];
        const lastIdx = updated.findIndex((e) => e.id === agentEntryId);
        if (lastIdx !== -1) {
          updated[lastIdx] = {
            ...updated[lastIdx],
            text: `Erro ao comunicar com o modelo: ${msg}`,
            final: true,
          };
        }
        return updated;
      });
      onError(err as Error);
      onNotice('Falha na resposta do modelo.', 'error');
    } finally {
      setIsStreaming(false);
      isStreamingRef.current = false;
    }
  }, [selectedSkill, roomName, onError, onNotice, speakResponse]);

  // Processa áudio gravado e envia para Whisper
  const processAndTranscribeBlob = useCallback(async (blob: Blob) => {
    if (blob.size < 800) return;

    setTranscribingAudio(true);
    transcribingRef.current = true;

    try {
      const formData = new FormData();
      formData.append('arquivo', blob, 'gravacao.webm');

      const res = await fetch('/transcrever', {
        method: 'POST',
        headers: {
          Authorization: 'Bearer minhasenha_super_segura_de_32_caracteres_minimo_aqui',
        },
        body: formData,
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const textoTranscrito = data.texto?.trim();

      if (textoTranscrito && textoTranscrito.length > 1) {
        onNotice('Voz reconhecida pelo Whisper!');
        void enviarMensagem(textoTranscrito);
      }
    } catch {
      onNotice('Falha ao transcrever áudio com Whisper.', 'error');
    } finally {
      setTranscribingAudio(false);
      transcribingRef.current = false;
    }
  }, [enviarMensagem, onNotice]);

  // Inicializa o fluxo contínuo de áudio com VAD (Detecção de Atividade de Voz)
  const initAudioSystem = useCallback(async () => {
    try {
      stopAudioTracks();

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: inputId
          ? {
              deviceId: { exact: inputId },
              echoCancellation: true,
              noiseSuppression: true,
              autoGainControl: true,
            }
          : {
              echoCancellation: true,
              noiseSuppression: true,
              autoGainControl: true,
            },
      });
      activeStreamRef.current = stream;

      // AudioContext para medição de energia e silêncio em tempo real
      const audioCtx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
      audioCtxRef.current = audioCtx;
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 64;
      analyserRef.current = analyser;

      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);

      const dataArray = new Uint8Array(analyser.frequencyBinCount);

      // Loop do VAD executado a cada frame
      const checkAudioLevel = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);

        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const avg = sum / dataArray.length;
        const normalized = Math.min(1, avg / 110);
        setMicLevel(normalized);

        const now = Date.now();
        const threshold = sensitivityThresholdRef.current;
        const isLoud = normalized > threshold;

        // Se o Agent estiver falando e o usuário falar alto, ativa Interrupção imediata (Barge-in)
        if (isSpeakingRef.current) {
          if (normalized > threshold * 1.5) {
            if (window.speechSynthesis) {
              window.speechSynthesis.cancel();
              setIsSpeaking(false);
              isSpeakingRef.current = false;
            }
          }
        }

        // Se VAD estiver ativado e o microfone não estiver mutado e não estivermos transcrevendo ou processando
        if (
          vadEnabledRef.current &&
          !micMutedRef.current &&
          !transcribingRef.current &&
          !isStreamingRef.current &&
          !isSpeakingRef.current
        ) {
          if (!isUserSpeakingRef.current) {
            // DETECÇÃO DE INÍCIO DA FALA DO USUÁRIO
            if (isLoud) {
              isUserSpeakingRef.current = true;
              setIsUserSpeaking(true);
              speechStartRef.current = now;
              lastSoundTimeRef.current = now;
              audioChunksRef.current = [];

              // Inicia gravação imediatamente
              try {
                const rec = new MediaRecorder(stream, { mimeType: 'audio/webm' });
                mediaRecorderRef.current = rec;
                rec.ondataavailable = (e) => {
                  if (e.data.size > 0) audioChunksRef.current.push(e.data);
                };
                rec.onstop = () => {
                  const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
                  audioChunksRef.current = [];
                  void processAndTranscribeBlob(blob);
                };
                rec.start(100);
              } catch {}
            }
          } else {
            // USUÁRIO ESTÁ FALANDO: atualiza último momento de som
            if (isLoud) {
              lastSoundTimeRef.current = now;
            } else {
              // DETECÇÃO DE SILÊNCIO / FIM DA FALA (Endpointing automático)
              const silenceDuration = now - lastSoundTimeRef.current;
              const totalSpeechTime = lastSoundTimeRef.current - speechStartRef.current;

              if (silenceDuration >= silenceDelayRef.current) {
                isUserSpeakingRef.current = false;
                setIsUserSpeaking(false);

                if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
                  mediaRecorderRef.current.stop();
                }

                // Se a fala foi menor que 300ms (ruído rápido), descarta
                if (totalSpeechTime < 300) {
                  audioChunksRef.current = [];
                }
              }
            }
          }
        }

        animFrameRef.current = requestAnimationFrame(checkAudioLevel);
      };

      checkAudioLevel();
    } catch {
      onNotice('Permissão de microfone necessária para conversa por voz.', 'error');
      setMicMuted(true);
    }
  }, [inputId, stopAudioTracks, processAndTranscribeBlob, onNotice]);

  // Inicia sistema de áudio ao montar componente
  useEffect(() => {
    void initAudioSystem();
    return () => {
      stopAudioTracks();
    };
  }, [initAudioSystem, stopAudioTracks]);

  // Alternar mudo do microfone
  const toggleMute = useCallback(() => {
    const nextMuted = !micMuted;
    setMicMuted(nextMuted);
    micMutedRef.current = nextMuted;

    if (nextMuted) {
      if (isUserSpeakingRef.current) {
        isUserSpeakingRef.current = false;
        setIsUserSpeaking(false);
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
          mediaRecorderRef.current.stop();
        }
      }
      onNotice('Microfone silenciado.', 'info');
    } else {
      onNotice('Microfone ativado. Pode falar à vontade!');
    }
  }, [micMuted, onNotice]);

  // Atalhos de teclado: 'M' para alternar mudo, Escape para fechar dispositivos
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!visible || e.altKey || e.ctrlKey || e.metaKey || e.repeat) return;
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      if (tag === 'input' || tag === 'textarea' || (e.target as HTMLElement)?.isContentEditable) return;

      if (e.key === 'm' || e.key === 'M') {
        e.preventDefault();
        toggleMute();
      }
      if (e.key === 'Escape') {
        setDeviceOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [visible, toggleMute]);

  // Troca de dispositivos
  const changeInput = async (value: string) => {
    appliedInputId.current = value;
    onInput(value);
    onNotice('Microfone atualizado.');
    setTimeout(() => {
      void initAudioSystem();
    }, 300);
  };

  const changeOutput = async (value: string) => {
    appliedOutputId.current = value;
    onOutput(value);
    onNotice('Saída de áudio atualizada.');
  };

  // Estados dinâmicos do palco de voz
  const stageTone = isSpeaking ? 'speaking' : isUserSpeaking ? 'listening' : 'waiting';

  const stageTitle = isSpeaking
    ? 'Agent Core está falando'
    : isStreaming
    ? 'Preparando resposta...'
    : transcribingAudio
    ? 'Transcrevendo sua fala com Whisper...'
    : isUserSpeaking
    ? 'Ouvindo sua fala...'
    : micMuted
    ? 'Microfone silenciado'
    : 'Agent Core está ouvindo';

  const stageHint = isSpeaking
    ? 'Fale a qualquer momento para interromper o Agent Core.'
    : isStreaming
    ? 'Processando resposta e executando comandos no computador...'
    : transcribingAudio
    ? 'Convertendo áudio em texto na máquina local...'
    : isUserSpeaking
    ? 'Fale naturalmente. Quando pausar, a resposta será enviada automaticamente.'
    : micMuted
    ? 'Ative o microfone pelo botão abaixo ou pressione M para falar.'
    : 'Fale naturalmente sem precisar clicar em nada. A detecção automática de voz está ativa!';

  const stageStatusText = isSpeaking
    ? 'Reproduzindo voz'
    : isUserSpeaking
    ? 'Detectando sua voz'
    : isStreaming
    ? 'Processando'
    : transcribingAudio
    ? 'Whisper Local'
    : 'Voz Contínua Ativa';

  if (!visible) return null;

  return (
    <section className="conversation-layout" aria-label="Sala de Voz do Agent Core">
      {/* Coluna da Esquerda: Palco de Voz (Voice Stage) com VAD Automático */}
      <div className="voice-column">
        <div className="section-heading">
          <div>
            <p className="eyebrow">SALA ATIVA</p>
            <h1>Conversa ao vivo</h1>
          </div>
          <div className="session-timer">
            <Clock3 size={15} /> {formatClock(elapsed)}
          </div>
        </div>

        <div className="voice-stage">
          <div className="stage-topline">
            <span>
              <StatusDot tone={isSpeaking ? 'blue' : isUserSpeaking ? 'green' : micMuted ? 'red' : 'green'} />{' '}
              {stageStatusText}
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {skills.length > 0 && (
                <select
                  className="skill-select"
                  value={selectedSkill}
                  onChange={(e) => setSelectedSkill(e.target.value)}
                  title="Especialista / Skill ativa"
                  style={{
                    background: '#1d1d1d',
                    color: '#c6c6c6',
                    border: '1px solid #3d3d3d',
                    borderRadius: '5px',
                    padding: '2px 8px',
                    fontSize: '11px',
                    outline: 'none',
                  }}
                >
                  {skills.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.nome}
                    </option>
                  ))}
                </select>
              )}
              <span>AGENT CORE LIVE</span>
            </div>
          </div>

          {/* Símbolo central de voz com anéis concêntricos animados */}
          <div className={`voice-symbol voice-symbol--${stageTone}`} aria-hidden="true">
            <span className="voice-ring voice-ring--outer" />
            <span className="voice-ring voice-ring--inner" />
            <AudioLines size={43} strokeWidth={1.6} />
          </div>

          <div className="stage-copy" aria-live="polite">
            <h2>{stageTitle}</h2>
            <p>{stageHint}</p>
          </div>

          {/* Medidor de nível de áudio dinâmico (8 barras verticais) */}
          <div className="level-meter" aria-label="Nível do microfone">
            {[0.4, 0.75, 1, 0.7, 0.45, 0.9, 0.55, 0.35].map((factor, index) => (
              <span
                key={index}
                style={{
                  height: `${Math.max(5, Math.min(32, 5 + micLevel * factor * 70))}px`,
                  background: isSpeaking ? '#a78bfa' : isUserSpeaking ? '#fa4d56' : '#78a9ff',
                  transition: 'height 0.08s ease-out',
                }}
              />
            ))}
          </div>

          {/* Controles principais do palco */}
          <div className="stage-controls">
            {!visible && (
              <button className="text-button" onClick={onReturn}>
                Voltar à chamada
              </button>
            )}

            <button
              className={`control-circle ${
                isUserSpeaking ? 'control-circle--active' : micMuted ? 'control-circle--muted' : ''
              }`}
              onClick={toggleMute}
              title={micMuted ? 'Ativar microfone (M)' : 'Silenciar microfone (M)'}
              aria-label={micMuted ? 'Ativar microfone' : 'Silenciar microfone'}
              style={
                isUserSpeaking
                  ? { background: '#fa4d56', borderColor: '#fa4d56', color: '#fff' }
                  : micMuted
                  ? { color: '#fa4d56', borderColor: 'rgba(250,77,86,0.5)' }
                  : { background: '#263956', borderColor: '#78a9ff', color: '#78a9ff' }
              }
            >
              {transcribingAudio ? (
                <RefreshCw className="spin" size={20} />
              ) : micMuted ? (
                <MicOff size={21} />
              ) : (
                <Mic size={21} />
              )}
            </button>

            <button
              className="control-end"
              onClick={() => {
                stopAudioTracks();
                onEnd();
              }}
              title="Encerrar conversa"
            >
              <PhoneOff size={18} /> Encerrar conversa
            </button>

            <button
              className={`control-circle ${deviceOpen ? 'control-circle--active' : ''}`}
              onClick={() => setDeviceOpen(!deviceOpen)}
              title="Dispositivos de áudio"
              aria-label="Configurar dispositivos de áudio"
            >
              <SlidersHorizontal size={19} />
            </button>
          </div>

          {/* Barra de Ajustes Inteligentes VAD */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexWrap: 'wrap',
              gap: '12px',
              marginTop: '18px',
              padding: '8px 14px',
              background: '#202020',
              borderRadius: '8px',
              border: '1px solid #333',
            }}
          >
            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '11px',
                color: vadEnabled ? '#22c55e' : '#888',
                cursor: 'pointer',
              }}
              title="Detecta quando você fala e para de falar automaticamente"
            >
              <input
                type="checkbox"
                checked={vadEnabled}
                onChange={(e) => setVadEnabled(e.target.checked)}
                style={{ accentColor: '#22c55e' }}
              />
              <Sparkles size={13} />
              <span>Voz Mãos Livres (VAD)</span>
            </label>

            <span style={{ color: '#444' }}>•</span>

            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '11px',
                color: '#aaa',
              }}
            >
              Pausa de fala:
              <select
                value={silenceDelay}
                onChange={(e) => setSilenceDelay(Number(e.target.value))}
                style={{
                  background: '#181818',
                  color: '#fff',
                  border: '1px solid #444',
                  borderRadius: '4px',
                  padding: '2px 6px',
                  fontSize: '11px',
                }}
              >
                <option value={800}>0.8s (Rápida)</option>
                <option value={1000}>1.0s (Normal)</option>
                <option value={1400}>1.4s (Relaxada)</option>
              </select>
            </label>

            <span style={{ color: '#444' }}>•</span>

            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '11px',
                color: '#aaa',
              }}
            >
              Sensibilidade:
              <select
                value={vadSensitivity}
                onChange={(e) => setVadSensitivity(e.target.value as 'normal' | 'alta' | 'baixa')}
                style={{
                  background: '#181818',
                  color: '#fff',
                  border: '1px solid #444',
                  borderRadius: '4px',
                  padding: '2px 6px',
                  fontSize: '11px',
                }}
              >
                <option value="alta">Alta</option>
                <option value="normal">Normal</option>
                <option value="baixa">Baixa (anti-ruído)</option>
              </select>
            </label>

            <span style={{ color: '#444' }}>•</span>

            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '11px',
                color: autoTts ? '#78a9ff' : '#888',
                cursor: 'pointer',
              }}
              title="Ativa ou desativa a reprodução de voz da IA"
            >
              <input
                type="checkbox"
                checked={autoTts}
                onChange={(e) => setAutoTts(e.target.checked)}
                style={{ accentColor: '#78a9ff' }}
              />
              {autoTts ? <Volume2 size={13} /> : <VolumeX size={13} />}
              Voz do Robô (TTS)
            </label>
          </div>
        </div>

        {/* Gaveta de dispositivos de áudio */}
        {deviceOpen && (
          <div className="inline-device-panel">
            <div className="panel-title-row">
              <h3>Dispositivos de áudio</h3>
              <button
                className="icon-button"
                onClick={() => setDeviceOpen(false)}
                aria-label="Fechar dispositivos"
              >
                <X size={17} />
              </button>
            </div>
            <DeviceFields
              devices={devices}
              inputId={inputId}
              outputId={outputId}
              onInput={(val) => void changeInput(val)}
              onOutput={(val) => void changeOutput(val)}
              onRefresh={onRefreshDevices}
            />
          </div>
        )}

        {/* Estatísticas da chamada */}
        <div className="call-stats">
          <div>
            <span>Conexão</span>
            <strong>Conectado (Local)</strong>
          </div>
          <div>
            <span>Suas falas</span>
            <strong>{metrics?.user_turns ?? entries.filter((entry) => entry.speaker === 'user').length}</strong>
          </div>
          <div>
            <span>Respostas</span>
            <strong>{metrics?.agent_turns ?? entries.filter((entry) => entry.speaker === 'agent').length}</strong>
          </div>
          <div>
            <span>Modelo</span>
            <strong>{activeModel || 'Agent Core'}</strong>
          </div>
        </div>
      </div>

      {/* Coluna da Direita: Transcrição em Tempo Real & Envio de Mensagens */}
      <div className="transcript-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">EM TEMPO REAL</p>
            <h2>Transcrição</h2>
          </div>
          <span className="count-badge">{entries.filter((entry) => entry.final).length}</span>
        </div>

        <TranscriptToolbar
          entries={entries}
          query={query}
          onQuery={setQuery}
          room={roomName}
          onNotice={onNotice}
        />

        <TranscriptList
          live
          entries={entries}
          query={query}
          emptyText="Fale pelo microfone a qualquer momento. A IA detectará sua voz automaticamente."
        />

        <IntegrationResults api={api} room={roomName} />

        {/* Barra de input direto para digitar sem sair da sala de voz */}
        <div
          style={{
            padding: '12px 14px',
            background: '#1a1a1a',
            borderTop: '1px solid #333',
            display: 'flex',
            gap: '8px',
            alignItems: 'center',
          }}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void enviarMensagem(inputText);
            }}
            style={{ display: 'flex', flex: 1, gap: '8px' }}
          >
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Digite uma mensagem ou fale ao microfone..."
              disabled={isStreaming || transcribingAudio}
              style={{
                flex: 1,
                background: '#282828',
                border: '1px solid #404040',
                borderRadius: '6px',
                color: '#f4f4f4',
                padding: '9px 13px',
                fontSize: '12px',
                outline: 'none',
              }}
            />
            <button
              type="submit"
              disabled={isStreaming || transcribingAudio || !inputText.trim()}
              className="primary-button"
              style={{ height: '36px', padding: '0 14px', borderRadius: '6px' }}
            >
              {isStreaming ? <RefreshCw className="spin" size={14} /> : <Send size={14} />}
              <span>{isStreaming ? 'Gerando...' : 'Enviar'}</span>
            </button>
          </form>
        </div>

        <div className="transcript-foot">
          <ShieldCheck size={15} /> Inferência Local · Whisper &amp; Ollama
        </div>
      </div>
    </section>
  );
}
