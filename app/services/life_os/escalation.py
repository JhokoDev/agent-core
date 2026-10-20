import time
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional

from app.services.life_os.database import LifeOSDatabase
from app.services.life_os.notifier import LifeOSNotifier

logger = logging.getLogger("LifeOSEscalation")

class LifeOSEscalationEngine:
    """
    Motor de Escalonamento e Máquina de Estados da Proatividade.
    Controla o Heartbeat (ciclo de 1 minuto), sobe os níveis de cobrança (1 a 4)
    e executa o Auto-Tetris para reorganizar o dia quando imprevistos acontecem.
    """

    def __init__(self, db: LifeOSDatabase, notifier: LifeOSNotifier):
        self.db = db
        self.notifier = notifier

    def calcular_minutos_diferenca(self, data_str: Optional[str], horario_str: Optional[str]) -> Optional[int]:
        """Calcula a diferença em minutos entre agora e o horário agendado (positivo = atrasado)."""
        if not horario_str:
            return None
        data_ref = data_str or date.today().isoformat()
        try:
            previsto_dt = datetime.fromisoformat(f"{data_ref}T{horario_str}:00")
            agora_dt = datetime.now()
            diff_segundos = (agora_dt - previsto_dt).total_seconds()
            return int(diff_segundos // 60)
        except Exception:
            return None

    async def verificar_janelas_distracao(self) -> Optional[str]:
        """Consulta o Windows MCP para verificar se o usuário está em aplicativos de distração."""
        try:
            from app.services.windows_mcp_service import windows_mcp
            janelas = windows_mcp.listar_janelas_ativas()
            termos_distracao = ["youtube", "twitch", "netflix", "steam", "discord", "twitter", "reddit", "instagram", "tiktok"]
            for j in janelas:
                titulo_lower = j.get("titulo", "").lower()
                exec_lower = j.get("processo", "").lower()
                for termo in termos_distracao:
                    if termo in titulo_lower or termo in exec_lower:
                        return j.get("titulo")
        except Exception as e:
            logger.debug(f"[Escalation] Verificação de janelas indisponível: {e}")
        return None

    async def processar_heartbeat(self, host_base: str = "http://127.0.0.1:8000") -> List[Dict[str, Any]]:
        """
        Executado a cada 1 minuto pelo loop em background.
        Avalia tarefas pendentes e escala a cobrança conforme necessário.
        """
        hoje = date.today().isoformat()
        tarefas = self.db.listar_tarefas(status="pendente", data_prevista=hoje)
        tarefas_em_andamento = self.db.listar_tarefas(status="em_andamento", data_prevista=hoje)
        tarefas_ativas = tarefas + tarefas_em_andamento

        acoes_disparadas = []
        agora_ts = time.time()

        for tarefa in tarefas_ativas:
            tarefa_id = tarefa["id"]
            criticidade = tarefa.get("criticidade", "rotina")
            escalation = tarefa.get("escalation_level", 0)
            ultimo_aviso = tarefa.get("ultimo_aviso_ts") or 0.0
            postpone_count = tarefa.get("postpone_count", 0)

            # Redução do intervalo de insistência conforme o número de adiamentos
            # Padrão: 5 min. Com 1 adiamento: 2.5 min. Com 2 adiamentos: ~1.2 min
            intervalo_minimo_segundos = max(60.0, 300.0 / (2 ** min(postpone_count, 3)))
            tempo_desde_ultimo_aviso = agora_ts - ultimo_aviso

            minutos_diff = self.calcular_minutos_diferenca(
                tarefa.get("data_prevista"),
                tarefa.get("horario_previsto")
            )

            if minutos_diff is None:
                continue

            # ==========================================
            # NÍVEL 1: Lembrete Amigável (-10min até 5min de atraso)
            # ==========================================
            if -10 <= minutos_diff < 10 and escalation == 0:
                msg = f"Olá! A tarefa '{tarefa['titulo']}' está agendada para {tarefa.get('horario_previsto')}."
                botoes = self.notifier.gerar_botoes_tarefa(tarefa_id, host_base)
                await self.notifier.enviar(
                    mensagem=msg,
                    titulo=f"⏰ Lembrete: {tarefa['titulo']}",
                    prioridade=3,
                    tags=["calendar", "clock1"],
                    acoes=botoes
                )
                self.db.atualizar_tarefa(tarefa_id, {
                    "escalation_level": 1,
                    "ultimo_aviso_ts": agora_ts
                })
                acoes_disparadas.append({"tarefa_id": tarefa_id, "nivel": 1, "tipo": "lembrete_amigavel"})

            # ==========================================
            # NÍVEL 2: Cobrança Firme + Micro-Passo (10 a 20 min atrasada)
            # ==========================================
            elif 10 <= minutos_diff < 20 and (escalation < 2 or tempo_desde_ultimo_aviso >= intervalo_minimo_segundos):
                micro_step = tarefa.get("micro_step_sugerido") or "Abra o ambiente e dê o primeiro clique."
                justificativas = tarefa.get("postpone_reasons", [])
                extra_cobrança = ""
                if postpone_count > 0 and justificativas:
                    ultima_desculpa = justificativas[-1].get("motivo", "")
                    extra_cobrança = f"\n⚠️ Você já adiou {postpone_count}x ('{ultima_desculpa}'). Chega de adiar."

                msg = (
                    f"A tarefa '{tarefa['titulo']}' está atrasada há {minutos_diff} minutos.{extra_cobrança}\n"
                    f"🎯 Micro-passo sugerido de 2 min: {micro_step}"
                )
                botoes = self.notifier.gerar_botoes_tarefa(tarefa_id, host_base)
                await self.notifier.enviar(
                    mensagem=msg,
                    titulo=f"⚡ Cobrança: {tarefa['titulo']}",
                    prioridade=4,
                    tags=["warning", "dart"],
                    acoes=botoes
                )
                self.db.atualizar_tarefa(tarefa_id, {
                    "escalation_level": 2,
                    "ultimo_aviso_ts": agora_ts
                })
                acoes_disparadas.append({"tarefa_id": tarefa_id, "nivel": 2, "tipo": "cobranca_micro_passo"})

            # ==========================================
            # NÍVEL 3: Alarme Urgente / Furando Silencioso (20 a 30 min atrasada)
            # ==========================================
            elif 20 <= minutos_diff < 30 and criticidade in ("importante", "critica") and (escalation < 3 or tempo_desde_ultimo_aviso >= intervalo_minimo_segundos):
                msg = (
                    f"🚨 ATENÇÃO: A tarefa crítica '{tarefa['titulo']}' está estourando o cronograma há {minutos_diff} minutos!\n"
                    f"Pare o que estiver fazendo e inicie agora."
                )
                botoes = self.notifier.gerar_botoes_tarefa(tarefa_id, host_base)
                await self.notifier.enviar(
                    mensagem=msg,
                    titulo=f"🚨 URGENTE: {tarefa['titulo']}",
                    prioridade=5,  # Fura o modo silencioso no Android!
                    tags=["rotating_light", "fire"],
                    acoes=botoes
                )
                self.db.atualizar_tarefa(tarefa_id, {
                    "escalation_level": 3,
                    "ultimo_aviso_ts": agora_ts
                })
                acoes_disparadas.append({"tarefa_id": tarefa_id, "nivel": 3, "tipo": "alarme_insistente"})

            # ==========================================
            # NÍVEL 4: Intervenção Ativa no PC (30+ min de atraso em crítica)
            # ==========================================
            elif minutos_diff >= 30 and criticidade == "critica" and tempo_desde_ultimo_aviso >= intervalo_minimo_segundos:
                janela_distracao = await self.verificar_janelas_distracao()
                extra_bronca = ""
                if janela_distracao:
                    extra_bronca = f"\n🎮 Detectei que você está com '{janela_distracao}' aberta no PC em vez de estar focando!"

                msg = (
                    f"🛑 INTERVENÇÃO TOTAL: '{tarefa['titulo']}' está atrasada há mais de {minutos_diff} minutos.{extra_bronca}\n"
                    f"O agente está acionando o bloqueio de foco."
                )
                botoes = self.notifier.gerar_botoes_tarefa(tarefa_id, host_base)
                await self.notifier.enviar(
                    mensagem=msg,
                    titulo=f"🛑 INTERVENÇÃO NO PC: {tarefa['titulo']}",
                    prioridade=5,
                    tags=["skull", "warning"],
                    acoes=botoes
                )
                self.db.atualizar_tarefa(tarefa_id, {
                    "escalation_level": 4,
                    "ultimo_aviso_ts": agora_ts
                })
                acoes_disparadas.append({"tarefa_id": tarefa_id, "nivel": 4, "tipo": "intervencao_pc"})

        return acoes_disparadas

    def executar_auto_tetris(self, tarefa_critica_id: int, minutos_estouro: int) -> Dict[str, Any]:
        """
        Agenda Elástica (Auto-Tetris):
        Quando uma tarefa crítica estoura o tempo, empurra as tarefas de 'rotina'
        subsequentes para mais tarde ou para o dia seguinte, preservando o foco.
        """
        hoje = date.today().isoformat()
        tarefas_rotina = self.db.listar_tarefas(status="pendente", criticidade="rotina", data_prevista=hoje)

        reorganizadas = []
        for t in tarefas_rotina:
            if t["id"] == tarefa_critica_id:
                continue
            horario = t.get("horario_previsto")
            if horario:
                try:
                    h, m = map(int, horario.split(":"))
                    novo_dt = datetime.combine(date.today(), datetime.min.time()) + timedelta(hours=h, minutes=m + minutos_estouro)
                    novo_horario = novo_dt.strftime("%H:%M")
                    self.db.atualizar_tarefa(t["id"], {"horario_previsto": novo_horario})
                    reorganizadas.append({"id": t["id"], "titulo": t["titulo"], "novo_horario": novo_horario})
                except Exception:
                    pass

        return {
            "sucesso": True,
            "minutos_empurrados": minutos_estouro,
            "tarefas_reorganizadas": reorganizadas
        }
