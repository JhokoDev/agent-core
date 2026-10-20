from fastapi import APIRouter, HTTPException, Depends, Query
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
from app.services.life_os.models import PostponeRequest, ProofOfWorkSubmit

life_os_router = APIRouter(prefix="/api/life", tags=["Life OS"])

# ==========================================
# STATUS GERAL DO LIFE OS
# ==========================================

@life_os_router.get("/status")
def obter_status_life_os():
    """Retorna o resumo do dia: 3 tarefas críticas, saldo livre e hábitos."""
    return life_os_service.obter_resumo_dashboard()

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
    t = life_os_service.obter_tarefa(tarefa_id)
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

@life_os_router.post("/tarefas/{tarefa_id}/adiar")
def adiar_tarefa(tarefa_id: int, req: PostponeRequest):
    res = life_os_service.adiar_tarefa(tarefa_id, motivo=req.motivo, minutos=req.minutos_adiamento)
    if not res:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    return res

@life_os_router.post("/tarefas/{tarefa_id}/concluir")
def concluir_tarefa(tarefa_id: int, req: ProofOfWorkSubmit):
    res = life_os_service.concluir_tarefa(tarefa_id, prova=req.evidencia)
    if not res:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    return res

@life_os_router.post("/tarefas/{tarefa_id}/auto-tetris")
def acionar_auto_tetris(tarefa_id: int, minutos_estouro: int = Query(30)):
    return life_os_service.escalation.executar_auto_tetris(tarefa_id, minutos_estouro)

# ==========================================
# ROTAS DE FINANÇAS ZERO-PLANILHA
# ==========================================

@life_os_router.get("/financas")
def listar_financas(limite: int = Query(50)):
    return life_os_service.db.listar_transacoes(limite=limite)

@life_os_router.post("/financas/transacao")
def registrar_transacao_manual(transacao: FinancaTransacaoCreate):
    tid = life_os_service.db.registrar_transacao(
        tipo=transacao.tipo,
        valor=transacao.valor,
        categoria=transacao.categoria,
        descricao=transacao.descricao,
        origem=transacao.origem,
        raw_payload=transacao.raw_payload
    )
    return {"sucesso": True, "transacao_id": tid}

@life_os_router.post("/financas/webhook-banco")
async def webhook_notificacao_banco(notif: BancoNotificacaoWebhook):
    """
    Webhook chamado pelo MacroDroid no Android quando chega notificação de banco.
    """
    res = await life_os_service.processar_notificacao_bancaria(
        app_origem=notif.app_origem,
        texto=notif.texto,
        titulo=notif.titulo or ""
    )
    return res

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
    """
    Recebe os cliques nos botões de notificação do ntfy no Android:
    'estou_a_caminho', 'adiar_15m', 'concluir'.
    """
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
    """Disparo manual do ciclo de heartbeat para testes imediatos."""
    acoes = await life_os_service.escalation.processar_heartbeat()
    return {"status": "ok", "acoes_disparadas": acoes}
