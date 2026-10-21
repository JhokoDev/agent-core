import * as Battery from 'expo-battery';
import * as Clipboard from 'expo-clipboard';
import * as Notifications from 'expo-notifications';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { agentApi } from './api';
import { Tarefa } from '../types';

const STORAGE_KEYS = {
  LAST_BRIEFING_DATE: '@agent_core_last_briefing_date',
  LAST_CLIPBOARD_HASH: '@agent_core_last_clipboard_hash',
  SCHEDULED_TASKS_IDS: '@agent_core_scheduled_tasks_ids'
};

export interface PixDetectionResult {
  text: string;
  valor?: number;
}

class DeviceSensorsService {
  private batterySubscription: any = null;
  private onPixDetectedCallback: ((res: PixDetectionResult) => void) | null = null;
  private onMorningBriefingCallback: (() => void) | null = null;

  async init() {
    try {
      Notifications.setNotificationHandler({
        handleNotification: async () => ({
          shouldShowAlert: true,
          shouldShowBanner: true,
          shouldShowList: true,
          shouldPlaySound: true,
          shouldSetBadge: true,
          priority: Notifications.AndroidNotificationPriority.MAX
        })
      });
      await Notifications.requestPermissionsAsync();
    } catch {}

    this.setupBatteryListener();
  }

  // ==========================================================
  // 1. SENSOR DE BATERIA (Substituto MacroDroid: Despertar Matinal)
  // ==========================================================
  private setupBatteryListener() {
    try {
      this.batterySubscription = Battery.addBatteryStateListener(async ({ batteryState }) => {
        // Se foi desconectado do carregador
        if (
          batteryState === Battery.BatteryState.UNPLUGGED ||
          batteryState === Battery.BatteryState.NOT_CHARGING
        ) {
          const agora = new Date();
          const hora = agora.getHours();
          const hojeStr = agora.toISOString().split('T')[0];

          // Verifica se está no intervalo matinal (05:00 até 11:30)
          if (hora >= 5 && hora <= 11) {
            const lastDate = await AsyncStorage.getItem(STORAGE_KEYS.LAST_BRIEFING_DATE);
            if (lastDate !== hojeStr) {
              await AsyncStorage.setItem(STORAGE_KEYS.LAST_BRIEFING_DATE, hojeStr);
              
              // Notifica backend sobre o contexto matinal
              try {
                const batteryLevel = await Battery.getBatteryLevelAsync();
                await agentApi.enviarContextoSensores({
                  em_casa: true,
                  carregador: false,
                  bateria: Math.round(batteryLevel * 100)
                });
              } catch {}

              // Dispara alerta local e notifica UI
              try {
                await Notifications.scheduleNotificationAsync({
                  content: {
                    title: '☀️ Bom Dia! Seu Foco de Hoje está Pronto',
                    body: 'Você desconectou o celular do carregador. Abra o Agent Core para ver seu teto financeiro e as 3 prioridades.',
                    sound: true
                  },
                  trigger: null // Imediato
                });
              } catch {}

              if (this.onMorningBriefingCallback) {
                this.onMorningBriefingCallback();
              }
            }
          }
        }
      });
    } catch (err) {
      console.warn('[DeviceSensors] Erro ao iniciar listener de bateria:', err);
    }
  }

  onMorningBriefing(cb: () => void) {
    this.onMorningBriefingCallback = cb;
  }

  // ==========================================================
  // 2. DETECTOR DE PIX / NOTIFICAÇÃO BANCÁRIA (Substituto MacroDroid)
  // ==========================================================
  onPixDetected(cb: (res: PixDetectionResult) => void) {
    this.onPixDetectedCallback = cb;
  }

  async verificarClipboardParaGastos(): Promise<PixDetectionResult | null> {
    try {
      const text = await Clipboard.getStringAsync();
      if (!text || text.trim().length < 8) return null;

      // Regex para identificar comprovantes de Pix, banco ou pagamentos
      const padroes = [
        /(?:pix|transfer[eê]ncia|comprovante|pagamento|pago|compra|d[eé]bito)/i,
        /r\$\s*(\d+(?:[\.,]\d{2})?)/i
      ];

      const ehGastoOuPix = padroes[0].test(text) && padroes[1].test(text);
      if (!ehGastoOuPix) return null;

      // Gera hash simples para não alertar repetidamente sobre o mesmo comprovante
      const hash = text.trim().slice(0, 80);
      const ultimoHash = await AsyncStorage.getItem(STORAGE_KEYS.LAST_CLIPBOARD_HASH);
      if (ultimoHash === hash) return null;

      const matchValor = text.match(/r\$\s*(\d+(?:[\.,]\d{2})?)/i);
      const valor = matchValor ? parseFloat(matchValor[1].replace(',', '.')) : undefined;

      const result: PixDetectionResult = { text: text.trim(), valor };

      if (this.onPixDetectedCallback) {
        this.onPixDetectedCallback(result);
      }

      return result;
    } catch {
      return null;
    }
  }

  async marcarClipboardProcessado(text: string) {
    const hash = text.trim().slice(0, 80);
    await AsyncStorage.setItem(STORAGE_KEYS.LAST_CLIPBOARD_HASH, hash);
  }

  // ==========================================================
  // 3. SINCRONIZADOR DE ALARMES E NOTIFICAÇÕES LOCAIS (Substituto MacroDroid)
  // ==========================================================
  async sincronizarAlarmesTarefas(tarefas: Tarefa[]) {
    try {
      const hojeStr = new Date().toISOString().split('T')[0];
      const tarefasComHorario = tarefas.filter(
        (t) => t.status === 'pendente' && t.data_prevista && t.horario_previsto
      );

      for (const t of tarefasComHorario) {
        const [h, m] = t.horario_previsto!.split(':').map(Number);
        if (isNaN(h) || isNaN(m)) continue;

        const dataAlvo = new Date(t.data_prevista + 'T00:00:00');
        dataAlvo.setHours(h, m, 0, 0);

        const agora = new Date();
        const diffSegundos = Math.floor((dataAlvo.getTime() - agora.getTime()) / 1000);

        // Se o alarme está no futuro (entre 10 segundos e 7 dias)
        if (diffSegundos > 10 && diffSegundos < 7 * 86400) {
          await Notifications.scheduleNotificationAsync({
            content: {
              title: `⏰ Lembrete: ${t.titulo}`,
              body: `Horário previsto: ${t.horario_previsto} · Contexto: ${t.contexto_execucao === 'rua' ? '📍 Rua' : '💻 PC'}${t.micro_step_sugerido ? ` · Passo: ${t.micro_step_sugerido}` : ''}`,
              sound: true,
              data: { tarefaId: t.id }
            },
            trigger: {
              type: Notifications.SchedulableTriggerInputTypes.DATE,
              date: dataAlvo
            }
          });
        }
      }
    } catch (err) {
      console.warn('[DeviceSensors] Erro ao sincronizar alarmes locais:', err);
    }
  }
}

export const deviceSensors = new DeviceSensorsService();
