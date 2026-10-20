import httpx
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger("LifeOSNotifier")

class LifeOSNotifier:
    """
    Adaptador de notificações acionáveis e prioritárias via ntfy.sh.
    Utiliza envio via payload JSON oficial para suporte nativo a UTF-8,
    emojis, prioridades de 1 a 5 e botões de ação HTTP.
    """

    def __init__(self, topico: str = "agent-core-alertas", base_url: str = "https://ntfy.sh"):
        self.topico = topico
        self.base_url = base_url.rstrip("/")

    async def enviar(
        self,
        mensagem: str,
        titulo: str = "Agent Core",
        prioridade: int = 3,
        tags: Optional[List[str]] = None,
        acoes: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Dispara notificação push via ntfy usando JSON payload.
        :param mensagem: Corpo do alerta.
        :param titulo: Título destacado (suporta emojis e caracteres UTF-8).
        :param prioridade: 1 (baixa) a 5 (urgente - fura silencioso no Android).
        :param tags: Emojis ou tags (ex: ['rotating_light', 'warning']).
        :param acoes: Botões de ação ntfy (lista de dicionários de ação).
        """
        url = self.base_url

        payload: Dict[str, Any] = {
            "topic": self.topico,
            "message": mensagem,
            "title": titulo,
            "priority": min(max(prioridade, 1), 5)
        }

        if tags:
            payload["tags"] = tags

        if acoes:
            payload["actions"] = acoes

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    logger.info(f"[ntfy] Alerta enviado com sucesso ({prioridade}): {titulo}")
                    return True
                else:
                    logger.warning(f"[ntfy] Falha ao enviar alerta ({resp.status_code}): {resp.text}")
                    return False
        except Exception as e:
            logger.error(f"[ntfy] Erro de rede ao disparar alerta: {e}")
            return False

    def gerar_botoes_tarefa(self, tarefa_id: int, host_base: str = "http://127.0.0.1:8000") -> List[Dict[str, Any]]:
        """Gera os botões de ação HTTP padrões para notificações de tarefas no ntfy."""
        webhook_url = f"{host_base}/api/life/acoes-ntfy"
        return [
            {
                "action": "http",
                "label": "⚡ Estou a caminho",
                "url": webhook_url,
                "body": f'{{"acao":"estou_a_caminho","tarefa_id":{tarefa_id}}}',
                "method": "POST",
                "headers": {"Content-Type": "application/json"}
            },
            {
                "action": "http",
                "label": "⏳ Adiar 15m",
                "url": webhook_url,
                "body": f'{{"acao":"adiar_15m","tarefa_id":{tarefa_id},"motivo":"adiado_via_notificacao"}}',
                "method": "POST",
                "headers": {"Content-Type": "application/json"}
            },
            {
                "action": "http",
                "label": "✅ Concluído",
                "url": webhook_url,
                "body": f'{{"acao":"concluir","tarefa_id":{tarefa_id}}}',
                "method": "POST",
                "headers": {"Content-Type": "application/json"}
            }
        ]
