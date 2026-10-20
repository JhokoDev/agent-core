from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from typing import Optional, List, Dict, Any

from app.services.life_os import (
    life_os_service,
    TarefaCreate, TarefaUpdate,
    FinancaTransacaoCreate,
    BancoNotificacaoWebhook,
    MetaCreate,
    HabitoCreate,
    AcaoNtfyWebhook
)
from app.services.life_os.models import (
    PostponeRequest, ProofOfWorkSubmit,
    InboxInput, EmergencyPauseRequest, SensorContextRequest,
    EventoCreate, MultaRequest, FechamentoNoturnoRequest
)

life_os_router = APIRouter(prefix="/api/life", tags=["Life OS"])

# ==========================================
# STATUS GERAL DO LIFE OS
# ==========================================

@life_os_router.get("/status")
def obter_status_life_os():
    """Retorna o resumo do dia: 3 tarefas críticas, saldo livre, hábitos e modo emergência."""
    return life_os_service.obter_resumo_dashboard()

# ==========================================
# INBOX COGNITIVO ZERO-FRICÇÃO
# ==========================================

@life_os_router.post("/inbox")
async def processar_inbox_life(payload: InboxInput):
    """
    Endpoint de Captura Rápida Zero-Fricção:
    Recebe texto livre ou áudio base64, processa via LLM e aplica as travas:
    - Trava Anti-Limbo (obriga horário se for crítica/importante)
    - Trava Regra dos 3 (máximo 3 críticas por dia)
    """
    res = await life_os_service.inbox.processar_entrada(
        texto=payload.texto,
        audio_base64=payload.audio_base64,
        forcar_sem_trava=payload.forcar_sem_trava
    )
    return res

# ==========================================
# ROTAS DE TAREFAS COMPORTAMENTAIS
# ==========================================

@life_os_router.get("/tarefas")
def listar_tarefas(
    status: Optional[str] = Query(None),
    criticidade: Optional[str] = Query(None),
    data: Optional[str] = Query(None)
):
    return life_os_service.listar_tarefas(status=status, criticidade=criticidade, data_prevista=data)

@life_os_router.post("/tarefas")
def criar_tarefa(tarefa: TarefaCreate):
    return life_os_service.criar_tarefa(tarefa.model_dump())

@life_os_router.get("/tarefas/{tarefa_id}")
def obter_tarefa(tarefa_id: int):
    t = life_os_service.db.obter_tarefa_com_impacto_meta(tarefa_id)
    if not t:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    return t

@life_os_router.put("/tarefas/{tarefa_id}")
def atualizar_tarefa(tarefa_id: int, payload: TarefaUpdate):
    campos = {k: v for k, v in payload.model_dump().items() if v is not None}
    sucesso = life_os_service.db.atualizar_tarefa(tarefa_id, campos)
    if not sucesso:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada ou sem alterações.")
    return life_os_service.obter_tarefa(tarefa_id)

@life_os_router.delete("/tarefas/{tarefa_id}")
def remover_tarefa(tarefa_id: int):
    sucesso = life_os_service.db.remover_tarefa(tarefa_id)
    if not sucesso:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    return {"ok": True, "removido": tarefa_id}

@life_os_router.post("/tarefas/{tarefa_id}/iniciar")
def iniciar_tarefa(tarefa_id: int):
    res = life_os_service.iniciar_tarefa(tarefa_id)
    if not res:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    return res

@life_os_router.post("/tarefas/{tarefa_id}/adiar")
def adiar_tarefa(tarefa_id: int, req: PostponeRequest):
    try:
        res = life_os_service.adiar_tarefa(tarefa_id, motivo=req.motivo, minutos=req.minutos_adiamento)
        if not res:
            raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@life_os_router.post("/tarefas/{tarefa_id}/concluir")
def concluir_tarefa(tarefa_id: int, req: ProofOfWorkSubmit):
    try:
        res = life_os_service.concluir_tarefa(tarefa_id, prova=req.evidencia)
        if not res:
            raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@life_os_router.post("/tarefas/{tarefa_id}/auto-tetris")
def acionar_auto_tetris(tarefa_id: int, minutos_estouro: int = Query(30)):
    return life_os_service.escalation.executar_auto_tetris(tarefa_id, minutos_estouro)

# ==========================================
# AGENDA FIXA (EVENTOS E REUNIÕES)
# ==========================================

@life_os_router.get("/events")
def listar_eventos_agenda(data: Optional[str] = Query(None)):
    return life_os_service.db.listar_eventos(data=data)

@life_os_router.post("/events")
def criar_evento_agenda(evento: EventoCreate):
    eid = life_os_service.db.criar_evento(
        title=evento.title,
        start_at=evento.start_at,
        end_at=evento.end_at,
        is_busy_block=evento.is_busy_block,
        external_calendar_id=evento.external_calendar_id
    )
    return {"sucesso": True, "event_id": eid}

# ==========================================
# ROTAS DE FINANÇAS, CAIXAS E MULTAS
# ==========================================

@life_os_router.get("/financas")
def listar_financas(limite: int = Query(50)):
    return life_os_service.db.listar_transacoes(limite=limite)

@life_os_router.get("/financas/caixas")
def obter_saldo_caixas_financeiras():
    """Retorna saldo e totais separados para as 4 Caixas Financeiras."""
    return life_os_service.obter_saldo_caixas()

@life_os_router.post("/financas/multa")
def aplicar_multa_procrastinacao(req: MultaRequest):
    """Nível 5 (Contrato de Ulisses): transfere multa da caixa Lazer para Reserva."""
    return life_os_service.aplicar_multa(valor=req.valor, motivo=req.motivo, tarefa_id=req.tarefa_id)

@life_os_router.get("/financas/orcamento-lazer")
def obter_orcamento_lazer():
    return life_os_service.calcular_orcamento_lazer_semanal()

@life_os_router.post("/financas/transacao")
def registrar_transacao_manual(transacao: FinancaTransacaoCreate):
    tid = life_os_service.db.registrar_transacao(
        tipo=transacao.tipo,
        valor=transacao.valor,
        categoria=transacao.categoria,
        descricao=transacao.descricao,
        origem=transacao.origem,
        raw_payload=transacao.raw_payload,
        ma=transacao.ma or ""
    )
    return {"sucesso": True, "transacao_id": tid}

@life_os_router.post("/financas/webhook-banco")
async def webhook_notificacao_banco(notif: BancoNotificacaoWebhook):
    """Webhook chamado pelo MacroDroid no Android ao chegar notificação de banco."""
    return await life_os_service.processar_notificacao_bancaria(
        app_origem=notif.app_origem,
        texto=notif.texto,
        titulo=notif.titulo or ""
    )

@life_os_router.post("/financas/pedagio")
def calcular_pedagio_compra(valor: float = Query(...), item: str = Query("Item")):
    return life_os_service.finance.calcular_pedagio_compra(valor_compra=valor, nome_item=item)

@life_os_router.get("/financas/config")
def obter_configs_financas():
    return life_os_service.db.obter_todas_configs()

@life_os_router.post("/financas/config")
def definir_config_financas(payload: Dict[str, str]):
    for k, v in payload.items():
        life_os_service.db.definir_config(k, str(v))
    return {"ok": True, "configs": life_os_service.db.obter_todas_configs()}

# ==========================================
# SISTEMA, MODO EMERGÊNCIA E SENSORES
# ==========================================

@life_os_router.post("/sistema/modo-emergencia")
def ativar_modo_emergencia(req: EmergencyPauseRequest):
    """Pausa as cobranças por motivo de imprevisto e reagenda tarefas de rotina."""
    try:
        return life_os_service.ativar_modo_emergencia(motivo=req.motivo, duracao_horas=req.duracao_horas)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@life_os_router.post("/sistema/modo-emergencia/desativar")
def desativar_modo_emergencia():
    return life_os_service.desativar_modo_emergencia()

@life_os_router.post("/sensores/contexto")
async def atualizar_contexto_sensores(req: SensorContextRequest):
    """Recebe telemetria mobile do MacroDroid (Wi-Fi, em_casa, carregador, bateria)."""
    return await life_os_service.atualizar_contexto_sensores(req.model_dump())

# ==========================================
# RITUAIS AGENDADOS
# ==========================================

@life_os_router.post("/rituais/briefing-matinal")
async def disparar_briefing_matinal():
    return await life_os_service.executar_briefing_matinal()

@life_os_router.post("/rituais/fechamento-noturno")
async def disparar_fechamento_noturno(req: FechamentoNoturnoRequest):
    return await life_os_service.executar_fechamento_noturno(
        audio_transcript=req.audio_transcript,
        energy_score=req.energy_score
    )

@life_os_router.get("/rituais/conselho-semanal")
def obter_conselho_semanal():
    return life_os_service.gerar_conselho_semanal()

# ==========================================
# ROTAS DE METAS E HÁBITOS
# ==========================================

@life_os_router.get("/metas")
def listar_metas(pilar: Optional[str] = Query(None)):
    return life_os_service.db.listar_metas(pilar=pilar)

@life_os_router.post("/metas")
def criar_meta(meta: MetaCreate):
    mid = life_os_service.db.criar_meta(meta.model_dump())
    return {"sucesso": True, "meta_id": mid}

@life_os_router.put("/metas/{meta_id}/progresso")
def atualizar_progresso_meta(meta_id: int, progresso: float = Query(..., ge=0.0, le=100.0)):
    sucesso = life_os_service.db.atualizar_progresso_meta(meta_id, progresso)
    if not sucesso:
        raise HTTPException(status_code=404, detail="Meta não encontrada.")
    return {"ok": True, "meta_id": meta_id, "progresso_pct": progresso}

@life_os_router.get("/habitos")
def listar_habitos():
    return life_os_service.db.listar_habitos()

@life_os_router.post("/habitos")
def criar_habito(habito: HabitoCreate):
    hid = life_os_service.db.criar_habito(habito.nome, habito.pilar, habito.frequencia)
    return {"sucesso": True, "habito_id": hid}

@life_os_router.post("/habitos/{habito_id}/checkin")
def checkin_habito(habito_id: int):
    res = life_os_service.db.checkin_habito(habito_id)
    if not res:
        raise HTTPException(status_code=404, detail="Hábito não encontrado.")
    return res

# ==========================================
# ROTAS DE INTEGRAÇÃO NTFY E HEARTBEAT
# ==========================================

@life_os_router.post("/acoes-ntfy")
async def webhook_acoes_ntfy(payload: AcaoNtfyWebhook):
    params = {}
    if payload.motivo:
        params["motivo"] = payload.motivo
    if payload.minutos:
        params["minutos"] = payload.minutos

    res = await life_os_service.executar_acao_ntfy(
        acao=payload.acao,
        tarefa_id=payload.tarefa_id,
        parametros=params
    )
    return res

@life_os_router.post("/heartbeat/tick")
async def disparar_tick_heartbeat():
    acoes = await life_os_service.escalation.processar_heartbeat()
    return {"status": "ok", "acoes_disparadas": acoes}
