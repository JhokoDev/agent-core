from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime

CriticidadeTipo = Literal["rotina", "importante", "critica"]
StatusTarefaTipo = Literal["pendente", "em_andamento", "concluida", "adiada", "cancelada"]
ContextoExecucaoTipo = Literal["pc", "rua", "qualquer"]
ProofOfWorkTipo = Literal["click", "texto", "audio", "sistema"]

CategoriaFinanceiraTipo = Literal[
    "custos_fixos",
    "construcao_futuro",
    "autoaperfeicoamento",
    "livre_lazer",
    "outros"
]

PilarMetaTipo = Literal["carreira_dev", "financas", "saude_fisico", "estudos", "geral"]
NivelMetaTipo = Literal["macro", "meso", "micro"]

# ==========================================
# MODELOS DE TAREFAS
# ==========================================

class TarefaBase(BaseModel):
    titulo: str = Field(..., min_length=2, max_length=255)
    descricao: Optional[str] = ""
    criticidade: CriticidadeTipo = "rotina"
    data_prevista: Optional[str] = None  # Formato YYYY-MM-DD
    horario_previsto: Optional[str] = None  # Formato HH:MM
    duracao_estimada_min: int = Field(default=30, ge=1, le=1440)
    contexto_execucao: ContextoExecucaoTipo = "qualquer"
    proof_of_work_type: ProofOfWorkTipo = "click"
    micro_step_sugerido: Optional[str] = ""
    meta_id: Optional[int] = None

class TarefaCreate(TarefaBase):
    pass

class TarefaUpdate(BaseModel):
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    criticidade: Optional[CriticidadeTipo] = None
    status: Optional[StatusTarefaTipo] = None
    data_prevista: Optional[str] = None
    horario_previsto: Optional[str] = None
    duracao_estimada_min: Optional[int] = None
    contexto_execucao: Optional[ContextoExecucaoTipo] = None
    proof_of_work_type: Optional[ProofOfWorkTipo] = None
    proof_of_work_data: Optional[str] = None
    micro_step_sugerido: Optional[str] = None
    meta_id: Optional[int] = None

class PostponeRequest(BaseModel):
    motivo: str = Field(..., min_length=2, description="Justificativa do adiamento para alimentar a memória comportamental")
    minutos_adiamento: int = Field(default=15, ge=5, le=1440)

class ProofOfWorkSubmit(BaseModel):
    evidencia: str = Field(..., min_length=1, description="Texto, link, resumo ou confirmação do que foi realizado")

class TarefaOut(TarefaBase):
    id: int
    status: StatusTarefaTipo
    postpone_count: int = 0
    postpone_reasons: List[Dict[str, Any]] = []
    proof_of_work_data: Optional[str] = None
    escalation_level: int = 0
    ultimo_aviso_ts: Optional[float] = None
    proximo_aviso_ts: Optional[float] = None
    criado_em: str

# ==========================================
# MODELOS FINANCEIROS
# ==========================================

class FinancaTransacaoCreate(BaseModel):
    tipo: Literal["despesa", "receita"] = "despesa"
    valor: float = Field(..., gt=0)
    categoria: CategoriaFinanceiraTipo = "livre_lazer"
    descricao: str = Field(default="", max_length=255)
    origem: str = Field(default="manual_texto")
    raw_payload: Optional[str] = None
    ma: Optional[str] = Field(default="", description="Campo customizado MA")

class FinancaTransacaoOut(FinancaTransacaoCreate):
    id: int
    data_hora: str
    horas_vida: float = 0.0

class BancoNotificacaoWebhook(BaseModel):
    app_origem: str = Field(..., description="Identificador do app bancário (ex: com.nu.production, inter)")
    texto: str = Field(..., description="Corpo da notificação recebida pelo MacroDroid")
    titulo: Optional[str] = ""
    destinatario: Optional[str] = ""
    valor_extraido: Optional[float] = None

# ==========================================
# MODELOS DE METAS E HÁBITOS
# ==========================================

class MetaCreate(BaseModel):
    titulo: str = Field(..., min_length=2, max_length=255)
    pilar: PilarMetaTipo = "carreira_dev"
    nivel: NivelMetaTipo = "macro"
    meta_pai_id: Optional[int] = None
    prazo: Optional[str] = None  # YYYY-MM-DD
    progresso_pct: float = Field(default=0.0, ge=0.0, le=100.0)

class MetaOut(MetaCreate):
    id: int
    status: str
    criado_em: str

class HabitoCreate(BaseModel):
    nome: str = Field(..., min_length=2, max_length=255)
    pilar: PilarMetaTipo = "saude_fisico"
    frequencia: str = Field(default="diario")

class HabitoOut(HabitoCreate):
    id: int
    streak_atual: int = 0
    melhor_streak: int = 0
    ultimo_checkin: Optional[str] = None

# ==========================================
# AÇÕES E WEBHOOKS NTFY
# ==========================================

class AcaoNtfyWebhook(BaseModel):
    acao: Literal["estou_a_caminho", "iniciar", "adiar_15m", "concluir", "abrir_pc", "renegociar"]
    tarefa_id: int
    motivo: Optional[str] = None
    minutos: Optional[int] = 15

# ==========================================
# MODELOS DE INBOX, SENSORES E RITUAIS
# ==========================================

class InboxInput(BaseModel):
    texto: Optional[str] = None
    audio_base64: Optional[str] = None
    forcar_sem_trava: bool = False

class EmergencyPauseRequest(BaseModel):
    motivo: str = Field(..., min_length=4, description="Justificativa obrigatória do imprevisto")
    duracao_horas: int = Field(default=4, ge=1, le=72)

class SensorContextRequest(BaseModel):
    wifi: Optional[str] = None
    em_casa: Optional[bool] = None
    carregador: Optional[bool] = None
    bateria: Optional[int] = None
    tela_ligada: Optional[bool] = None

class EventoCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    start_at: str = Field(..., description="Data/hora ISO: YYYY-MM-DDTHH:MM:SS")
    end_at: str = Field(..., description="Data/hora ISO: YYYY-MM-DDTHH:MM:SS")
    is_busy_block: int = 1
    external_calendar_id: Optional[str] = None

class MultaRequest(BaseModel):
    valor: float = Field(default=10.0, gt=0)
    motivo: str = Field(..., min_length=3)
    tarefa_id: Optional[int] = None

class FechamentoNoturnoRequest(BaseModel):
    audio_transcript: str = Field(default="", description="Transcrição do áudio de 30s de vitória do dia")
    energy_score: int = Field(default=5, ge=1, le=10)
