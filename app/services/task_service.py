import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.infrastructure.db import get_db_connection


class TaskService:
    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        d = dict(row)
        if "postpone_reasons" in d and isinstance(d["postpone_reasons"], str):
            try:
                d["postpone_reasons"] = json.loads(d["postpone_reasons"])
            except Exception:
                d["postpone_reasons"] = []
        return d

    def criar_tarefa(
        self,
        titulo: str,
        data_hora_planejada: str,
        descricao: str = "",
        tipo: str = "tarefa",
        criticidade: str = "rotina",
        duracao_estimada_min: int = 30,
        contexto_execucao: str = "qualquer",
        proof_of_work_type: str = "click",
        meta_pai_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Cria uma nova tarefa com validações de domínio."""
        if criticidade not in ("rotina", "importante", "critica"):
            criticidade = "rotina"
        if tipo not in ("compromisso", "tarefa", "lembrete"):
            tipo = "tarefa"
        if contexto_execucao not in ("pc", "rua", "qualquer"):
            contexto_execucao = "qualquer"

        now_iso = datetime.now().isoformat()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tarefas (
                    titulo, descricao, tipo, criticidade, status, data_hora_planejada,
                    duracao_estimada_min, contexto_execucao, nivel_cobranca_atual,
                    postpone_count, postpone_reasons, proof_of_work_type, proof_of_work_data,
                    micro_step_sugerido, meta_pai_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'pendente', ?, ?, ?, 0, 0, '[]', ?, '', '', ?, ?, ?)
            """, (
                titulo.strip(),
                descricao.strip(),
                tipo,
                criticidade,
                data_hora_planejada,
                duracao_estimada_min,
                contexto_execucao,
                proof_of_work_type,
                meta_pai_id,
                now_iso,
                now_iso
            ))
            conn.commit()
            tarefa_id = cursor.lastrowid
            return self.obter_tarefa(tarefa_id)

    def obter_tarefa(self, tarefa_id: int) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tarefas WHERE id = ?", (tarefa_id,))
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None

    def listar_tarefas(
        self,
        status: Optional[str] = None,
        criticidade: Optional[str] = None,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        query = "SELECT * FROM tarefas WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)
        if criticidade:
            query += " AND criticidade = ?"
            params.append(criticidade)
        if data_inicio:
            query += " AND data_hora_planejada >= ?"
            params.append(data_inicio)
        if data_fim:
            query += " AND data_hora_planejada <= ?"
            params.append(data_fim)

        query += " ORDER BY data_hora_planejada ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Total
            count_query = "SELECT COUNT(*) FROM tarefas WHERE 1=1"
            cursor.execute(count_query)
            total = cursor.fetchone()[0]

            return {
                "tarefas": [self._row_to_dict(r) for r in rows],
                "total": total
            }

    def obter_top3_focos_do_dia(self) -> List[Dict[str, Any]]:
        """
        Retorna as 3 tarefas prioritárias do dia (Regra dos 3).
        Prioriza 'critica', seguido de 'importante' com status pendente ou executando.
        """
        hoje_inicio = datetime.now().strftime("%Y-%m-%d 00:00:00")
        hoje_fim = datetime.now().strftime("%Y-%m-%d 23:59:59")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tarefas 
                WHERE status IN ('pendente', 'executando')
                  AND data_hora_planejada BETWEEN ? AND ?
                ORDER BY 
                  CASE criticidade 
                    WHEN 'critica' THEN 1 
                    WHEN 'importante' THEN 2 
                    ELSE 3 
                  END ASC,
                  data_hora_planejada ASC
                LIMIT 3
            """, (hoje_inicio, hoje_fim))
            rows = cursor.fetchall()
            return [self._row_to_dict(r) for r in rows]

    def adiar_tarefa(self, tarefa_id: int, motivo: str, novos_minutos: int = 15) -> Dict[str, Any]:
        """Adia a tarefa, incrementa postpone_count e registra a justificativa."""
        tarefa = self.obter_tarefa(tarefa_id)
        if not tarefa:
            raise ValueError(f"Tarefa {tarefa_id} não encontrada.")

        reasons = tarefa.get("postpone_reasons", [])
        postpone_count = tarefa.get("postpone_count", 0) + 1
        now_dt = datetime.now()
        nova_hora = (now_dt + timedelta(minutes=novos_minutos)).isoformat()

        reasons.append({
            "timestamp": now_dt.isoformat(),
            "motivo": motivo.strip() or "Sem motivo informado",
            "minutos": novos_minutos
        })

        # Se já adiou 3 ou mais vezes e não tem micro-passo, define um micro-passo sugerido
        micro_step = tarefa.get("micro_step_sugerido", "")
        if postpone_count >= 3 and not micro_step:
            micro_step = f"Abrir a tarefa '{tarefa['titulo']}' e executar apenas os primeiros 2 minutos agora."

        now_iso = now_dt.isoformat()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tarefas 
                SET data_hora_planejada = ?,
                    postpone_count = ?,
                    postpone_reasons = ?,
                    micro_step_sugerido = ?,
                    status = 'pendente',
                    updated_at = ?
                WHERE id = ?
            """, (nova_hora, postpone_count, json.dumps(reasons, ensure_ascii=False), micro_step, now_iso, tarefa_id))
            conn.commit()

        return self.obter_tarefa(tarefa_id)

    def concluir_tarefa(self, tarefa_id: int, proof_data: str = "") -> Dict[str, Any]:
        """Conclui a tarefa. Para tarefas críticas com prova obrigatória, valida se foi enviada."""
        tarefa = self.obter_tarefa(tarefa_id)
        if not tarefa:
            raise ValueError(f"Tarefa {tarefa_id} não encontrada.")

        if tarefa["criticidade"] == "critica" and tarefa["proof_of_work_type"] in ("texto", "audio") and not proof_data.strip():
            raise ValueError("Esta é uma tarefa crítica e exige envio de comprovação (Proof of Work).")

        now_iso = datetime.now().isoformat()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tarefas 
                SET status = 'concluida',
                    concluida_em = ?,
                    proof_of_work_data = ?,
                    nivel_cobranca_atual = 0,
                    updated_at = ?
                WHERE id = ?
            """, (now_iso, proof_data.strip(), now_iso, tarefa_id))
            conn.commit()

        return self.obter_tarefa(tarefa_id)

    def atualizar_nivel_cobranca(self, tarefa_id: int, novo_nivel: int) -> None:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tarefas 
                SET nivel_cobranca_atual = ?,
                    updated_at = ?
                WHERE id = ?
            """, (novo_nivel, datetime.now().isoformat(), tarefa_id))
            conn.commit()

    def excluir_tarefa(self, tarefa_id: int) -> bool:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tarefas WHERE id = ?", (tarefa_id,))
            conn.commit()
            return cursor.rowcount > 0


task_service = TaskService()
