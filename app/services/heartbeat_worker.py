import asyncio
import logging
from datetime import datetime
from typing import Optional

from app.infrastructure.db import get_db_connection
from app.services.task_service import task_service

logger = logging.getLogger("HeartbeatWorker")


class HeartbeatWorker:
    def __init__(self, intervalo_segundos: int = 60):
        self.intervalo = intervalo_segundos
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Inicia o loop assíncrono do Heartbeat."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(f"Heartbeat Worker iniciado (intervalo: {self.intervalo}s).")

    async def stop(self):
        """Para o Heartbeat suavemente."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Heartbeat Worker encerrado.")

    async def _loop(self):
        while self._running:
            try:
                await self.executar_ciclo()
            except Exception as e:
                logger.error(f"Erro no ciclo do Heartbeat: {e}")
            await asyncio.sleep(self.intervalo)

    async def executar_ciclo(self):
        """Avalia todas as tarefas ativas e ajusta os níveis de insistência."""
        agora = datetime.now()
        hoje_str = agora.strftime("%Y-%m-%d")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tarefas 
                WHERE status IN ('pendente', 'executando')
            """)
            tarefas = cursor.fetchall()

        for t_row in tarefas:
            tarefa = task_service._row_to_dict(t_row)
            try:
                planejada = datetime.fromisoformat(tarefa["data_hora_planejada"])
            except Exception:
                continue

            nivel_atual = tarefa.get("nivel_cobranca_atual", 0)
            criticidade = tarefa.get("criticidade", "rotina")
            segundos_restantes = (planejada - agora).total_seconds()
            atraso_segundos = (agora - planejada).total_seconds()

            # Nível 1: Aviso amigável (faltam menos de 15 minutos para o horário)
            if 0 <= segundos_restantes <= 15 * 60 and nivel_atual < 1:
                logger.info(f"[NÍVEL 1] Aviso prévio: '{tarefa['titulo']}' em {int(segundos_restantes / 60)} min.")
                task_service.atualizar_nivel_cobranca(tarefa["id"], 1)

            # Nível 2: Cobrança direta (horário atingido/atrasado até 10 minutos)
            elif 0 < atraso_segundos <= 10 * 60 and nivel_atual < 2:
                logger.warning(f"[NÍVEL 2] Cobrança direta: '{tarefa['titulo']}' venceu agora!")
                task_service.atualizar_nivel_cobranca(tarefa["id"], 2)

            # Nível 3: Alarme & Notificações intensas (atraso entre 10 e 25 minutos)
            elif 10 * 60 < atraso_segundos <= 25 * 60 and nivel_atual < 3:
                logger.warning(f"[NÍVEL 3] Alarme/Insistência: '{tarefa['titulo']}' atrasada há {int(atraso_segundos / 60)} min.")
                task_service.atualizar_nivel_cobranca(tarefa["id"], 3)

            # Nível 4: Intervenção ativa no PC (para tarefas 'critica' ou 'importante' com > 25 min de atraso)
            elif atraso_segundos > 25 * 60 and criticidade in ("critica", "importante") and nivel_atual < 4:
                logger.error(f"[NÍVEL 4] Intervenção PC: '{tarefa['titulo']}' muito atrasada.")
                task_service.atualizar_nivel_cobranca(tarefa["id"], 4)

            # Nível 5: Penalidade / Contrato de Ulisses (apenas 'critica' com > 45 min de atraso)
            elif atraso_segundos > 45 * 60 and criticidade == "critica" and nivel_atual < 5:
                logger.critical(f"[NÍVEL 5] Contrato de Ulisses: Falha crítica em '{tarefa['titulo']}'. Aplicando penalidade.")
                task_service.atualizar_nivel_cobranca(tarefa["id"], 5)


heartbeat_worker = HeartbeatWorker()
