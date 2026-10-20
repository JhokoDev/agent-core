from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from app.core.security import verificar_token
from app.services.task_service import task_service

tasks_router = APIRouter(prefix="/api/tasks", tags=["Tarefas & Heartbeat"])


class CriarTarefaSchema(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=200)
    data_hora_planejada: str
    descricao: Optional[str] = ""
    tipo: Optional[str] = "tarefa"
    criticidade: Optional[str] = "rotina"
    duracao_estimada_min: Optional[int] = 30
    contexto_execucao: Optional[str] = "qualquer"
    proof_of_work_type: Optional[str] = "click"
    meta_pai_id: Optional[int] = None


class AdiarTarefaSchema(BaseModel):
    motivo: str = Field(..., min_length=1)
    novos_minutos: Optional[int] = 15


class ConcluirTarefaSchema(BaseModel):
    proof_data: Optional[str] = ""


@tasks_router.get("", dependencies=[Depends(verificar_token)])
async def listar_tarefas(
    status: Optional[str] = None,
    criticidade: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """Lista tarefas com suporte a filtros e paginação."""
    return task_service.listar_tarefas(
        status=status,
        criticidade=criticidade,
        data_inicio=data_inicio,
        data_fim=data_fim,
        limit=limit,
        offset=offset
    )


@tasks_router.get("/top3", dependencies=[Depends(verificar_token)])
async def obter_top3_focos():
    """Retorna os 3 focos prioritários do dia para o Cockpit Mobile."""
    return task_service.obter_top3_focos_do_dia()


@tasks_router.get("/{tarefa_id}", dependencies=[Depends(verificar_token)])
async def obter_tarefa(tarefa_id: int):
    tarefa = task_service.obter_tarefa(tarefa_id)
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    return tarefa


@tasks_router.post("", dependencies=[Depends(verificar_token)])
async def criar_tarefa(dados: CriarTarefaSchema):
    try:
        return task_service.criar_tarefa(
            titulo=dados.titulo,
            data_hora_planejada=dados.data_hora_planejada,
            descricao=dados.descricao or "",
            tipo=dados.tipo or "tarefa",
            criticidade=dados.criticidade or "rotina",
            duracao_estimada_min=dados.duracao_estimada_min or 30,
            contexto_execucao=dados.contexto_execucao or "qualquer",
            proof_of_work_type=dados.proof_of_work_type or "click",
            meta_pai_id=dados.meta_pai_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@tasks_router.post("/{tarefa_id}/postpone", dependencies=[Depends(verificar_token)])
async def adiar_tarefa(tarefa_id: int, dados: AdiarTarefaSchema):
    try:
        return task_service.adiar_tarefa(
            tarefa_id=tarefa_id,
            motivo=dados.motivo,
            novos_minutos=dados.novos_minutos or 15
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@tasks_router.post("/{tarefa_id}/complete", dependencies=[Depends(verificar_token)])
async def concluir_tarefa(tarefa_id: int, dados: ConcluirTarefaSchema):
    try:
        return task_service.concluir_tarefa(
            tarefa_id=tarefa_id,
            proof_data=dados.proof_data or ""
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@tasks_router.delete("/{tarefa_id}", dependencies=[Depends(verificar_token)])
async def excluir_tarefa(tarefa_id: int):
    sucesso = task_service.excluir_tarefa(tarefa_id)
    if not sucesso:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    return {"status": "removido", "id": tarefa_id}
