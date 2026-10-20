import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import date, datetime, timedelta

from app.services.life_os.database import LifeOSDatabase
from app.services.life_os.notifier import LifeOSNotifier
from app.services.life_os.finance import LifeOSFinanceEngine
from app.services.life_os.escalation import LifeOSEscalationEngine
from app.services.life_os.inbox import LifeOSInboxEngine

logger = logging.getLogger("LifeOSService")

class LifeOSService:
    """
    Serviço Central do Life OS para o Agent Core.
    Unifica Persistência Comportamental, Heartbeat de Escalonamento,
    Motor Financeiro Zero-Planilha, Inbox Cognitivo e Ações Cross-Device.
    """

    def __init__(self):
        self.db = LifeOSDatabase()
        topico = self.db.obter_config("topico_ntfy", "agent-core-alertas")
        url_ntfy = self.db.obter_config("url_ntfy", "https://ntfy.sh")
        self.notifier = LifeOSNotifier(topico=topico, base_url=url_ntfy)
        self.finance = LifeOSFinanceEngine(self.db)
        self.escalation = LifeOSEscalationEngine(self.db, self.notifier)
        self.inbox = LifeOSInboxEngine(self.db, self.finance)

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
                # Verifica se modo emergência expirou
                expira_str = self.db.obter_config("modo_emergencia_expira")
                if expira_str:
                    try:
                        expira_dt = datetime.fromisoformat(expira_str)
                        if datetime.now() >= expira_dt:
                            self.db.definir_config("modo_emergencia_ativo", "0")
                            self.db.definir_config("modo_emergencia_expira", "")
                            logger.info("[LifeOS] Modo emergência expirado. Cobranças reativadas.")
                    except Exception:
                        pass

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
    # GESTÃO DE TAREFAS & FRICÇÃO ASSIMÉTRICA
    # ==========================================

    def criar_tarefa(self, dados: Dict[str, Any]) -> Dict[str, Any]:
        """Cria uma nova tarefa garantindo a regra de no máximo 3 tarefas críticas no dia."""
        hoje = dados.get("data_prevista") or date.today().isoformat()
        criticidade = dados.get("criticidade", "rotina")

        if criticidade == "critica":
            limite = int(self.db.obter_config("limite_tarefas_criticas_dia", "3"))
            criticas_atuais = self.db.listar_tarefas(status="pendente", criticidade="critica", data_prevista=hoje)
            if len(criticas_atuais) >= limite:
                logger.warning(f"[LifeOS] Limite diário de 3 tarefas críticas atingido para {hoje}!")
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

    def iniciar_tarefa(self, tarefa_id: int) -> Optional[Dict[str, Any]]:
        """Marca tarefa em execução, pausa o escalonamento e ativa ferramentas do PC se necessário."""
        tarefa = self.db.obter_tarefa(tarefa_id)
        if not tarefa:
            return None

        self.db.atualizar_tarefa(tarefa_id, {"status": "em_andamento", "escalation_level": 0})

        # Preparação ativa do ambiente via workspace_service
        if tarefa.get("contexto_execucao") in ("pc", "qualquer"):
            try:
                from app.services.workspace_service import workspace_service
                workspace_service.preparar_ambiente("dev")
                logger.info(f"[LifeOS] Ambiente VS Code / Dev preparado para a tarefa #{tarefa_id}!")
            except Exception as e:
                logger.debug(f"[LifeOS] Workspace service aviso: {e}")

        self.db.registrar_telemetria("tarefa_iniciada", {"tarefa_id": tarefa_id, "titulo": tarefa.get("titulo")})
        return self.db.obter_tarefa(tarefa_id)

    def adiar_tarefa(self, tarefa_id: int, motivo: str, minutos: int = 15) -> Optional[Dict[str, Any]]:
        """Aplica fricção assimétrica: tarefas críticas exigem justificativa fundamentada."""
        tarefa = self.db.obter_tarefa(tarefa_id)
        if not tarefa:
            return None

        if tarefa.get("criticidade") == "critica" and (not motivo or len(motivo.strip()) < 3):
            raise ValueError("Tarefas críticas exigem uma justificativa obrigatória e substantiva para serem adiadas.")

        res = self.db.adiar_tarefa(tarefa_id, motivo, minutos)
        if res:
            self.db.registrar_telemetria("tarefa_adiada", {"tarefa_id": tarefa_id, "motivo": motivo, "minutos": minutos})
        return res

    def concluir_tarefa(self, tarefa_id: int, prova: str = "") -> Optional[Dict[str, Any]]:
        """Validação de Proof of Work: tarefas críticas exigem comprovação real."""
        tarefa = self.db.obter_tarefa(tarefa_id)
        if not tarefa:
            return None

        if tarefa.get("criticidade") == "critica" and (not prova or len(prova.strip()) < 2):
            raise ValueError("Tarefas críticas exigem envio de comprovação (Proof of Work: resumo do que fez, link ou áudio) para serem concluídas.")

        res = self.db.concluir_tarefa(tarefa_id, prova)
        if res:
            self.db.registrar_telemetria("tarefa_concluida", {"tarefa_id": tarefa_id, "prova": prova})
        return res

    # ==========================================
    # PROCESSAMENTO DE AÇÕES VIA BOTÕES NTFY / CELULAR
    # ==========================================

    async def executar_acao_ntfy(self, acao: str, tarefa_id: int, parametros: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Recebe cliques nos botões da notificação do Android: 'estou_a_caminho', 'adiar_15m', 'concluir'."""
        parametros = parametros or {}
        tarefa = self.db.obter_tarefa(tarefa_id)
        if not tarefa:
            return {"sucesso": False, "erro": "Tarefa não encontrada."}

        if acao in ("estou_a_caminho", "iniciar"):
            self.iniciar_tarefa(tarefa_id)
            await self.notifier.enviar(
                mensagem=f"Ambiente configurado no seu monitor! Foco na tarefa '{tarefa['titulo']}'.",
                titulo="🚀 Modo de Ação Ativado",
                prioridade=3,
                tags=["rocket"]
            )
            return {"sucesso": True, "acao": acao, "status": "em_andamento"}

        elif acao == "adiar_15m":
            motivo = parametros.get("motivo") or "Adiado pelo botão de notificação"
            minutos = parametros.get("minutos") or 15
            self.adiar_tarefa(tarefa_id, motivo=motivo, minutos=minutos)
            return {"sucesso": True, "acao": "adiar_15m", "minutos": minutos}

        elif acao == "concluir":
            prova = parametros.get("prova") or "Concluído via botão de notificação rápida"
            self.concluir_tarefa(tarefa_id, prova=prova)
            await self.notifier.enviar(
                mensagem=f"Excelente! A tarefa '{tarefa['titulo']}' foi marcada como concluída.",
                titulo="🎉 Concluído!",
                prioridade=3,
                tags=["tada", "white_check_mark"]
            )
            return {"sucesso": True, "acao": "concluir"}

        return {"sucesso": False, "erro": f"Ação não reconhecida: {acao}"}

    # ==========================================
    # GESTÃO FINANCEIRA E CAIXAS
    # ==========================================

    async def processar_notificacao_bancaria(self, app_origem: str, texto: str, titulo: str = "") -> Dict[str, Any]:
        resultado = self.finance.processar_notificacao_bancaria(app_origem, texto, titulo)
        if resultado.get("sucesso") and resultado.get("tipo") == "despesa":
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

    def obter_saldo_caixas(self) -> Dict[str, Any]:
        return self.db.obter_saldo_caixas()

    def aplicar_multa(self, valor: float, motivo: str, tarefa_id: Optional[int] = None) -> Dict[str, Any]:
        return self.db.aplicar_multa_procrastinacao(valor, motivo, tarefa_id)

    def calcular_orcamento_lazer_semanal(self) -> Dict[str, Any]:
        """Libera o saldo disponível na caixa lazer proporcionalmente à % de tarefas críticas concluídas."""
        hoje = date.today()
        segunda = hoje - timedelta(days=hoje.weekday())
        todas_semana = self.db.listar_tarefas(criticidade="critica")
        
        # Filtra tarefas da semana
        criticas_semana = [
            t for t in todas_semana
            if t.get("data_prevista") and t.get("data_prevista") >= segunda.isoformat()
        ]

        total = len(criticas_semana)
        concluidas = len([t for t in criticas_semana if t.get("status") == "concluida"])
        taxa = round((concluidas / total) * 100, 1) if total > 0 else 100.0

        caixas_info = self.db.obter_saldo_caixas()
        saldo_lazer_bruto = caixas_info["caixas"]["livre_lazer"]["saldo"]
        lazer_liberado = round(saldo_lazer_bruto * (taxa / 100.0), 2) if saldo_lazer_bruto > 0 else 0.0

        return {
            "semana_inicio": segunda.isoformat(),
            "tarefas_criticas_total": total,
            "tarefas_criticas_concluidas": concluidas,
            "taxa_aproveitamento_pct": taxa,
            "saldo_lazer_total": saldo_lazer_bruto,
            "saldo_lazer_liberado": lazer_liberado,
            "feedback": (
                f"Você concluiu {concluidas}/{total} tarefas críticas ({taxa}%). "
                f"Liberado R$ {lazer_liberado:.2f} do seu saldo de lazer para este fim de semana!"
            )
        }

    # ==========================================
    # MODO EMERGÊNCIA / IMPREVISTO
    # ==========================================

    def ativar_modo_emergencia(self, motivo: str, duracao_horas: int = 4) -> Dict[str, Any]:
        """Pausa o motor de cobrança mediante justificativa e reagendamento automático."""
        if not motivo or len(motivo.strip()) < 4:
            raise ValueError("O modo de emergência exige o registro de uma justificativa detalhada.")

        agora = datetime.now()
        expira = agora + timedelta(hours=duracao_horas)
        self.db.definir_config("modo_emergencia_ativo", "1")
        self.db.definir_config("modo_emergencia_motivo", motivo.strip())
        self.db.definir_config("modo_emergencia_expira", expira.isoformat())

        # Empurra tarefas de rotina para amanhã
        hoje = date.today().isoformat()
        amanha = (date.today() + timedelta(days=1)).isoformat()
        rotinas = self.db.listar_tarefas(status="pendente", criticidade="rotina", data_prevista=hoje)
        for r in rotinas:
            self.db.atualizar_tarefa(r["id"], {"data_prevista": amanha})

        self.db.registrar_telemetria("modo_emergencia_ativado", {
            "motivo": motivo,
            "duracao_horas": duracao_horas,
            "expira_em": expira.isoformat()
        })

        return {
            "sucesso": True,
            "modo_emergencia": True,
            "motivo": motivo,
            "duracao_horas": duracao_horas,
            "expira_em": expira.isoformat(),
            "mensagem": f"Cobranças suspensas por {duracao_horas} horas. Tarefas de rotina reagendadas para amanhã."
        }

    def desativar_modo_emergencia(self) -> Dict[str, Any]:
        self.db.definir_config("modo_emergencia_ativo", "0")
        self.db.definir_config("modo_emergencia_expira", "")
        return {"sucesso": True, "modo_emergencia": False, "mensagem": "Modo de emergência desativado. Cobranças reativadas."}

    # ==========================================
    # SENSORES & CONTEXTO MOBILE (MACRODROID)
    # ==========================================

    async def atualizar_contexto_sensores(self, dados: Dict[str, Any]) -> Dict[str, Any]:
        """Recebe telemetria do smartphone (Wi-Fi, carregador, em_casa, bateria)."""
        em_casa = dados.get("em_casa")
        wifi = dados.get("wifi", "")
        carregador = dados.get("carregador")

        contexto = "pc"
        if em_casa is False or "4G" in wifi or "5G" in wifi:
            contexto = "rua"
        elif em_casa is True:
            contexto = "pc"

        self.db.definir_config("contexto_usuario", contexto)
        self.db.registrar_telemetria("sensores_mobile", dados)

        # Se desconectou do carregador pela manhã (entre 06h e 10h), dispara Briefing Matinal
        hora_atual = datetime.now().hour
        if carregador is False and 6 <= hora_atual <= 10:
            asyncio.create_task(self.executar_briefing_matinal())

        return {"sucesso": True, "contexto_usuario": contexto, "telemetria_registrada": True}

    # ==========================================
    # RITUAIS AUTOMÁTICOS AGENDADOS
    # ==========================================

    async def executar_briefing_matinal(self) -> Dict[str, Any]:
        """Ritual 1: Briefing Matinal (agenda, teto diário e 3 tarefas críticas)."""
        hoje = date.today().isoformat()
        tarefas_criticas = self.db.listar_tarefas(status="pendente", criticidade="critica", data_prevista=hoje)
        eventos = self.db.listar_eventos(data=hoje)
        teto_livre = float(self.db.obter_config("teto_diario_livre", "50.0"))

        titulos_criticos = "\n".join([f"• {t['titulo']} ({t.get('horario_previsto') or 'Sem horário'})" for t in tarefas_criticas[:3]]) or "• Nenhuma tarefa crítica definida ainda!"
        eventos_str = "\n".join([f"• {e['title']} às {e['start_at'][11:16]}" for e in eventos]) or "• Nenhum evento com hora fixa hoje."

        msg = (
            f"☀️ BOM DIA! Briefing de {hoje}:\n\n"
            f"🎯 TOP 3 CRÍTICAS:\n{titulos_criticos}\n\n"
            f"📅 AGENDA FIXA:\n{eventos_str}\n\n"
            f"💰 Teto Livre de Hoje: R$ {teto_livre:.2f}\n"
            f"Mantenha o foco no essencial!"
        )

        await self.notifier.enviar(
            mensagem=msg,
            titulo="☀️ Briefing Matinal Agent Core",
            prioridade=4,
            tags=["sunny", "dart"]
        )

        return {"sucesso": True, "briefing_enviado": True, "data": hoje}

    async def executar_fechamento_noturno(self, audio_transcript: str = "", energy_score: int = 5) -> Dict[str, Any]:
        """Ritual 2: Fechamento Noturno + Diário de 30s + Aplicação de Multa se houver crítica abandonada."""
        hoje = date.today().isoformat()
        criticas_pendentes = self.db.listar_tarefas(status="pendente", criticidade="critica", data_prevista=hoje)

        multas_aplicadas = []
        # Se houver tarefa crítica não concluída e modo emergência desligado, aplica penalidade
        if criticas_pendentes and self.db.obter_config("modo_emergencia_ativo") != "1":
            for t in criticas_pendentes:
                res_multa = self.db.aplicar_multa_procrastinacao(
                    valor=10.0,
                    motivo=f"Tarefa crítica '{t['titulo']}' não concluída no fechamento noturno",
                    tarefa_id=t["id"]
                )
                multas_aplicadas.append(res_multa)

        # Salva o diário de vitória do dia
        self.db.registrar_telemetria("diario_fechamento_noturno", {
            "data": hoje,
            "audio_transcript": audio_transcript,
            "energy_score": energy_score,
            "multas": multas_aplicadas
        })

        msg = (
            f"🌙 FECHAMENTO DO DIA {hoje}:\n"
            f"• Críticas concluídas: {len(self.db.listar_tarefas(status='concluida', criticidade='critica', data_prevista=hoje))}\n"
            f"• Multas aplicadas: {len(multas_aplicadas)}\n"
            f"Descanse a mente. O agente guardou o seu progresso."
        )

        await self.notifier.enviar(
            mensagem=msg,
            titulo="🌙 Fechamento Noturno Agent Core",
            prioridade=3,
            tags=["crescent_moon", "book"]
        )

        return {
            "sucesso": True,
            "multas_aplicadas": multas_aplicadas,
            "criticas_pendentes": len(criticas_pendentes),
            "diario_registrado": bool(audio_transcript)
        }

    def gerar_conselho_semanal(self) -> Dict[str, Any]:
        """Ritual 3: Conselho Semanal e Dossiê Comportamental."""
        caixas = self.db.obter_saldo_caixas()
        orcamento = self.calcular_orcamento_lazer_semanal()
        metas = self.db.listar_metas()
        habitos = self.db.listar_habitos()

        return {
            "periodo": "semanal",
            "orcamento_lazer": orcamento,
            "balanco_4_caixas": caixas,
            "metas_ativas": metas,
            "habitos_streaks": habitos,
            "diagnostico": "Conselho compilado. Foque em manter a consistência nas tarefas críticas diárias."
        }

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
        modo_emergencia = self.db.obter_config("modo_emergencia_ativo") == "1"

        return {
            "data": hoje,
            "modo_emergencia_ativo": modo_emergencia,
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
