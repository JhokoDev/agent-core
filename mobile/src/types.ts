export type Criticidade = 'rotina' | 'importante' | 'critica';
export type StatusTarefa = 'pendente' | 'em_andamento' | 'concluida' | 'adiada' | 'cancelada';
export type ContextoExecucao = 'pc' | 'rua' | 'qualquer';
export type ProofOfWorkType = 'click' | 'texto' | 'audio' | 'sistema';

export interface PostponeReason {
  timestamp: string;
  motivo: string;
  minutos: number;
}

export interface Tarefa {
  id: number;
  titulo: string;
  descricao?: string;
  criticidade: Criticidade;
  status: StatusTarefa;
  data_prevista: string;
  horario_previsto?: string;
  duracao_estimada_min: number;
  postpone_count: number;
  postpone_reasons: PostponeReason[];
  contexto_execucao: ContextoExecucao;
  proof_of_work_type: ProofOfWorkType;
  proof_of_work_data?: string;
  micro_step_sugerido?: string;
  escalation_level: number;
  meta_id?: number;
  criado_em: string;
}

export interface DashboardFinancas {
  teto_diario_livre: number;
  gastos_hoje: number;
  saldo_restante_hoje: number;
  estourou: boolean;
}

export interface DashboardStatus {
  data: string;
  tarefas_total_hoje: number;
  tarefas_concluidas_hoje: number;
  tarefas_criticas_hoje: Tarefa[];
  financas: DashboardFinancas;
  habitos: Habito[];
}

export type CategoriaCaixa = 'custos_fixos' | 'construcao_futuro' | 'autoaperfeicoamento' | 'livre_lazer' | 'apenas_recebimento';

export interface CaixaItem {
  despesas: number;
  receitas: number;
  saldo: number;
}

export interface SaldoCaixasResponse {
  caixas: {
    custos_fixos: CaixaItem;
    construcao_futuro: CaixaItem;
    autoaperfeicoamento: CaixaItem;
    livre_lazer: CaixaItem;
    apenas_recebimento?: CaixaItem;
  };
  teto_diario_livre: number;
  gastos_hoje: number;
  saldo_diario_restante: number;
  multas_procrastinacao_total: number;
}

export interface TransacaoFinanceira {
  id: number;
  data_hora: string;
  tipo: 'despesa' | 'receita' | 'multa_procrastinacao';
  valor: number;
  categoria: string;
  descricao?: string;
  horas_vida: number;
  origem: string;
  ma?: string;
}

export interface Meta {
  id: number;
  titulo: string;
  pilar: string;
  nivel: 'macro' | 'meso' | 'micro';
  meta_pai_id?: number;
  progresso_pct: number;
  prazo?: string;
  status: string;
  criado_em: string;
}

export interface Habito {
  id: number;
  nome: string;
  pilar: string;
  frequencia: string;
  streak_atual: number;
  melhor_streak: number;
  ultimo_checkin?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  model?: string;
  route?: string;
  isThinking?: boolean;
  reasoning?: string;
  toolCalls?: any[];
}
