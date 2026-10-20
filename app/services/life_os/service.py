import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import date

from app.services.life_os.database import LifeOSDatabase
from app.services.life_os.notifier import LifeOSNotifier
from app.services.life_os.finance import LifeOSFinanceEngine
from app.services.life_os.escalation import LifeOSEscalationEngine

logger = logging.getLogger("LifeOSService")

class LifeOSService:
    """
    Serviço Central do Life OS para o Agent Core.
    Unifica Persistência Comportamental, Heartbeat de Escalonamento,
    Motor Financeiro Zero-Planilha e Ações do Windows MCP.
    """

    def __init__(self):
        self.db = LifeOSDatabase()
        topico = self.db.obter_config("topico_ntfy", "agent-core-alertas")
        url_ntfy = self.db.obter_config("url_ntfy", "https://ntfy.sh")
        self.notifier = LifeOSNotifier(topico=topico, base_url=url_ntfy)
        self.finance = LifeOSFinanceEngine(self.db)
        self.escalation = LifeOSEscalationEngine(self.db, self.notifier)

        self._heartbeat_task: Optional[asyncio.Task] = None
        self._rodando = False

    # ==========================================
    # CICLO DE VIDA DO HEARTBEAT EM BACKGROUND
    # ==========================================

    async def iniciar_heartbeat(self, intervalo_segundos: int = 60):
        """Inicia a rotina assíncrona de 1 minuto em background."""
        if self._rodando:
            return
        self._rodando = True
        logger.info("[LifeOS] Heartbeat proativo iniciado (intervalo: 60s)")

        while self._rodando:
            try:
                await self.escalation.processar_heartbeat()
            except Exception as e:
                logger.error(f"[LifeOS] Erro no ciclo de heartbeat: {e}")
            await asyncio.sleep(intervalo_segundos)

    def parar_heartbeat(self):
        """Interrompe o heartbeat."""
        self._rodando = False
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
        logger.info("[LifeOS] Heartbeat proativo parado.")

    # ==========================================
    # GESTÃO DE TAREFAS
    # ==========================================

    def criar_tarefa(self, dados: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cria uma nova tarefa garantindo a regra de no máximo 3 tarefas críticas no dia.
        """
        hoje = dados.get("data_prevista") or date.today().isoformat()
        criticidade = dados.get("criticidade", "rotina")

        if criticidade == "critica":
            limite = int(self.db.obter_config("limite_tarefas_criticas_dia", "3"))
            criticas_atuais = self.db.listar_tarefas(status="pendente", criticidade="critica", data_prevista=hoje)
            if len(criticas_atuais) >= limite:
                logger.warning(f"[LifeOS] Limite diário de 3 tarefas críticas atingido para {hoje}!")
                # Em vez de bloquear, alerta e categoriza como 'importante' para preservar a integridade da escada
                dados["criticidade"] = "importante"

        tarefa_id = self.db.criar_tarefa(dados)
        self.db.registrar_telemetria("tarefa_criada", {"tarefa_id": tarefa_id, "titulo": dados.get("titulo")})
        return self.db.obter_tarefa(tarefa_id)

    def listar_tarefas(
        self,
        status: Optional[str] = None,
        criticidade: Optional[str] = None,
        data_prevista: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return self.db.listar_tarefas(status, criticidade, data_prevista)

    def obter_tarefa(self, tarefa_id: int) -> Optional[Dict[str, Any]]:
        return self.db.obter_tarefa(tarefa_id)

    def adiar_tarefa(self, tarefa_id: int, motivo: str, minutos: int = 15) -> Optional[Dict[str, Any]]:
        res = self.db.adiar_tarefa(tarefa_id, motivo, minutos)
        if res:
            self.db.registrar_telemetria("tarefa_adiada", {"tarefa_id": tarefa_id, "motivo": motivo, "minutos": minutos})
        return res

    def concluir_tarefa(self, tarefa_id: int, prova: str = "") -> Optional[Dict[str, Any]]:
        res = self.db.concluir_tarefa(tarefa_id, prova)
        if res:
            self.db.registrar_telemetria("tarefa_concluida", {"tarefa_id": tarefa_id, "prova": prova})
        return res

    # ==========================================
    # PROCESSAMENTO DE AÇÕES VIA BOTÕES NTFY / CELULAR
    # ==========================================

    async def executar_acao_ntfy(self, acao: str, tarefa_id: int, parametros: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Recebe cliques nos botões da notificação do Android:
        'estou_a_caminho', 'adiar_15m', 'concluir', etc.
        """
        parametros = parametros or {}
        tarefa = self.db.obter_tarefa(tarefa_id)
        if not tarefa:
            return {"sucesso": False, "erro": "Tarefa não encontrada."}

        if acao == "estou_a_caminho":
            # Marca tarefa como em andamento
            self.db.atualizar_tarefa(tarefa_id, {"status": "em_andamento"})
            # Se a tarefa requer o PC, dispara a preparação ativa do ambiente!
            if tarefa.get("contexto_execucao") in ("pc", "qualquer"):
                try:
                    from app.services.workspace_service import workspace_service
                    workspace_service.preparar_ambiente("dev")
                    logger.info(f"[LifeOS] Ambiente preparado para a tarefa #{tarefa_id}!")
                except Exception as e:
                    logger.warning(f"[LifeOS] Falha ao acionar workspace_service: {e}")

            await self.notifier.enviar(
                mensagem=f"Ambiente configurado no seu monitor! Foco na tarefa '{tarefa['titulo']}'.",
                titulo="🚀 Modo de Ação Ativado",
                prioridade=3,
                tags=["rocket"]
            )
            return {"sucesso": True, "acao": "estou_a_caminho", "status": "em_andamento"}

        elif acao == "adiar_15m":
            motivo = parametros.get("motivo") or "Adiado pelo botão de notificação"
            minutos = parametros.get("minutos") or 15
            self.db.adiar_tarefa(tarefa_id, motivo=motivo, minutos=minutos)
            return {"sucesso": True, "acao": "adiar_15m", "minutos": minutos}

        elif acao == "concluir":
            prova = parametros.get("prova") or "Concluído via botão de notificação"
            self.db.concluir_tarefa(tarefa_id, prova=prova)
            await self.notifier.enviar(
                mensagem=f"Excelente! A tarefa '{tarefa['titulo']}' foi marcada como concluída.",
                titulo="🎉 Concluído!",
                prioridade=3,
                tags=["tada", "white_check_mark"]
            )
            return {"sucesso": True, "acao": "concluir"}

        return {"sucesso": False, "erro": f"Ação não reconhecida: {acao}"}

    # ==========================================
    # GESTÃO FINANCEIRA
    # ==========================================

    async def processar_notificacao_bancaria(self, app_origem: str, texto: str, titulo: str = "") -> Dict[str, Any]:
        resultado = self.finance.processar_notificacao_bancaria(app_origem, texto, titulo)
        if resultado.get("sucesso") and resultado.get("tipo") == "despesa":
            # Dispara alerta de feedback financeiro no ntfy
            tags = ["money_with_wings"]
            prioridade = 3
            if resultado.get("estourou_teto"):
                tags = ["rotating_light", "moneybag"]
                prioridade = 5

            await self.notifier.enviar(
                mensagem=resultado["feedback"],
                titulo="💸 Radar Financeiro",
                prioridade=prioridade,
                tags=tags
            )
        return resultado

    # ==========================================
    # RESUMO DASHBOARD (LIFE OS STATUS)
    # ==========================================

    def obter_resumo_dashboard(self) -> Dict[str, Any]:
        """Compila o estado atual do Life OS para visualização no painel ou via API."""
        hoje = date.today().isoformat()
        tarefas_hoje = self.db.listar_tarefas(data_prevista=hoje)
        criticas_hoje = [t for t in tarefas_hoje if t.get("criticidade") == "critica"]
        concluidas_hoje = [t for t in tarefas_hoje if t.get("status") == "concluida"]

        gastos_hoje = self.db.obter_gastos_hoje()
        teto_diario = float(self.db.obter_config("teto_diario_livre", "50.0"))
        saldo_livre = round(teto_diario - gastos_hoje, 2)

        habitos = self.db.listar_habitos()

        return {
            "data": hoje,
            "tarefas_total_hoje": len(tarefas_hoje),
            "tarefas_concluidas_hoje": len(concluidas_hoje),
            "tarefas_criticas_hoje": criticas_hoje,
            "financas": {
                "teto_diario_livre": teto_diario,
                "gastos_hoje": gastos_hoje,
                "saldo_restante_hoje": saldo_livre,
                "estourou": saldo_livre < 0
            },
            "habitos": habitos
        }

# Instância singleton global
life_os_service = LifeOSService()
