import re
import json
import base64
import tempfile
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional

import requests

from app.services.life_os.database import LifeOSDatabase
from app.services.life_os.finance import LifeOSFinanceEngine

logger = logging.getLogger("LifeOSInbox")


class LifeOSInboxEngine:
    """
    Inbox Cognitivo "Zero-Fricção" do Life OS.
    Recebe entradas brutas (texto livre ou áudio transcrito),
    utiliza LLM com fallback heurístico para classificação multimodal,
    e aplica as travas comportamentais:
    1. Trava Anti-Limbo (obriga horário em tarefas importantes/críticas).
    2. Trava de Foco Diário (Regra dos 3 focos diários).
    """

    def __init__(self, db: LifeOSDatabase, finance: LifeOSFinanceEngine):
        self.db = db
        self.finance = finance

    def parse_natural_language(self, texto: str) -> Dict[str, Any]:
        """Extrai intenção, criticidade, horário e micro-passo via LLM ou heurística."""
        hoje_str = date.today().isoformat()
        prompt = (
            f"Você é o Inbox Cognitivo do Life OS. Analise a seguinte fala/texto do usuário:\n"
            f"\"{texto}\"\n\n"
            f"Hoje é {hoje_str}.\n"
            f"Extraia e responda ESTRITAMENTE em formato JSON sem markdown com as seguintes chaves:\n"
            f"- tipo: ('tarefa', 'evento', 'gasto', 'meta')\n"
            f"- titulo: título conciso da ação\n"
            f"- descricao: detalhes extras ou string vazia\n"
            f"- criticidade: ('rotina', 'importante', 'critica')\n"
            f"- data_prevista: 'YYYY-MM-DD' (assuma hoje se não dito)\n"
            f"- horario_previsto: 'HH:MM' (ou null se nenhum horário foi mencionado explicitamente)\n"
            f"- duracao_estimada_min: int (padrão 30)\n"
            f"- contexto_execucao: ('pc', 'rua', 'qualquer')\n"
            f"- proof_of_work_type: ('click', 'texto', 'audio', 'sistema')\n"
            f"- micro_step_sugerido: ação de até 2 minutos para vencer a inércia\n"
            f"- valor: float (apenas se for gasto/dinheiro, senão null)\n"
            f"- categoria: ('custos_fixos', 'construcao_futuro', 'autoaperfeicoamento', 'livre_lazer') (se gasto)\n"
            f"- pilar: ('carreira_dev', 'financas', 'saude_fisico', 'estudos') (se meta)\n"
        )

        try:
            resp = requests.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": "llama3.2:latest",
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"temperature": 0.1}
                },
                timeout=4.0
            )
            if resp.status_code == 200:
                content = resp.json().get("message", {}).get("content", "").strip()
                # Remove possíveis backticks de markdown
                content_clean = re.sub(r"^```(?:json)?|```$", "", content, flags=re.MULTILINE).strip()
                dados = json.loads(content_clean)
                if isinstance(dados, dict) and "tipo" in dados and "titulo" in dados:
                    if not dados.get("data_prevista"):
                        dados["data_prevista"] = hoje_str
                    return dados
        except Exception as e:
            logger.debug(f"[Inbox] Falha ou timeout no parser LLM ({e}), aplicando parser heurístico.")

        # Fallback Heurístico Robusto
        return self._parser_heuristico(texto, hoje_str)

    def _parser_heuristico(self, texto: str, hoje_str: str) -> Dict[str, Any]:
        """Parser determinístico para alta resiliência e testes rápidos."""
        texto_lower = texto.lower()

        # Detecção de tipo
        tipo = "tarefa"
        if any(w in texto_lower for w in ["reunião", "consulta", "compromisso", "alinhamento", "call"]):
            tipo = "evento"
        elif any(w in texto_lower for w in ["gastei", "comprei", "paguei", "compra", "débito", "crédito", "pix"]):
            tipo = "gasto"
        elif any(w in texto_lower for w in ["meta", "objetivo", "até o final do ano", "patrimônio"]):
            tipo = "meta"

        # Detecção de criticidade
        criticidade = "rotina"
        if any(w in texto_lower for w in ["sem falta", "urgente", "crítica", "crítico", "prioridade máxima", "imprescindível"]):
            criticidade = "critica"
        elif any(w in texto_lower for w in ["importante", "preciso", "necessário", "relevante"]):
            criticidade = "importante"

        # Detecção de horário (ex: 17h, 17:00, 17h30, às 14:00)
        horario = None
        match_hora = re.search(r"(?:às\s+|as\s+|até\s+as\s+|até\s+às\s+|até\s+)?([0-1]?[0-9]|2[0-3])(?:h|:)([0-5][0-9])?", texto_lower)
        if match_hora:
            h = int(match_hora.group(1))
            m = match_hora.group(2) or "00"
            horario = f"{h:02d}:{m}"

        # Detecção de contexto
        contexto = "qualquer"
        if any(w in texto_lower for w in ["api", "código", "programar", "login", "pc", "computador", "vs code", "deploy", "sistema"]):
            contexto = "pc"
        elif any(w in texto_lower for w in ["mercado", "farmácia", "rua", "banco", "comprar"]):
            contexto = "rua"

        # Micro-passo sugerido
        micro_step = f"Abra o editor e prepare o primeiro arquivo para {texto[:40]}..." if contexto == "pc" else "Dê o primeiro passo em 2 minutos."

        # Extração de valor financeiro se aplicável
        valor = None
        match_val = re.search(r"R\$\s*([0-9]+(?:[.,][0-9]{2})?)", texto, re.IGNORECASE)
        if match_val:
            try:
                valor = float(match_val.group(1).replace(",", "."))
            except Exception:
                valor = None

        return {
            "tipo": tipo,
            "titulo": texto[:120].strip(),
            "descricao": texto,
            "criticidade": criticidade,
            "data_prevista": hoje_str,
            "horario_previsto": horario,
            "duracao_estimada_min": 30,
            "contexto_execucao": contexto,
            "proof_of_work_type": "sistema" if contexto == "pc" else "click",
            "micro_step_sugerido": micro_step,
            "valor": valor,
            "categoria": "livre_lazer",
            "pilar": "carreira_dev"
        }

    async def processar_entrada(
        self,
        texto: Optional[str] = None,
        audio_base64: Optional[str] = None,
        forcar_sem_trava: bool = False
    ) -> Dict[str, Any]:
        """
        Ponto central do Zero-Fricção:
        Recebe áudio bruto ou texto livre, processa, aplica as travas comportamentais
        e persiste a entidade no Life OS.
        """
        texto_final = (texto or "").strip()

        # 1. Se recebido áudio base64, transcreve com Whisper
        if audio_base64 and not texto_final:
            try:
                import os
                from app.infrastructure import audio
                audio_bytes = base64.b64decode(audio_base64)
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                    temp_audio.write(audio_bytes)
                    temp_path = temp_audio.name
                
                texto_transcrito = audio.transcrever_audio(temp_path)
                if texto_transcrito and not texto_transcrito.startswith("[Erro"):
                    texto_final = texto_transcrito
            except Exception as e:
                logger.error(f"[Inbox] Erro ao transcrever áudio recebido: {e}")

        if not texto_final:
            return {
                "status": "erro",
                "mensagem": "Nenhum conteúdo de texto ou áudio válido fornecido."
            }

        parsed = self.parse_natural_language(texto_final)
        tipo = parsed.get("tipo", "tarefa")
        criticidade = parsed.get("criticidade", "rotina")
        horario = parsed.get("horario_previsto")
        hoje = parsed.get("data_prevista") or date.today().isoformat()

        # ==========================================
        # TRAVA 1: TRAVA ANTI-LIMBO
        # ==========================================
        if not forcar_sem_trava and tipo == "tarefa" and criticidade in ("importante", "critica") and not horario:
            return {
                "status": "aguardando_confirmacao",
                "trava": "anti_limbo",
                "mensagem": (
                    f"A tarefa '{parsed['titulo']}' foi identificada como {criticidade.upper()}, "
                    f"portanto não pode ficar no limbo sem prazo definido. Para que horas de hoje você vai agendá-la?"
                ),
                "dados_parciais": parsed
            }

        # ==========================================
        # TRAVA 2: TRAVA DE FOCO DIÁRIO (REGRA DOS 3)
        # ==========================================
        if not forcar_sem_trava and tipo == "tarefa" and criticidade == "critica":
            criticas_hoje = self.db.listar_tarefas(status="pendente", criticidade="critica", data_prevista=hoje)
            if len(criticas_hoje) >= 3:
                titulos_atuais = [t["titulo"] for t in criticas_hoje]
                return {
                    "status": "aguardando_confirmacao",
                    "trava": "regra_dos_3",
                    "mensagem": (
                        f"Limite de 3 tarefas CRÍTICAS atingido para {hoje}! "
                        f"Foco diluído não é executado. Qual das tarefas atuais você deseja substituir ou rebaixar?"
                    ),
                    "tarefas_criticas_atuais": titulos_atuais,
                    "dados_parciais": parsed
                }

        # ==========================================
        # PERSISTÊNCIA DAS ENTIDADES
        # ==========================================
        if tipo == "tarefa":
            tarefa_id = self.db.criar_tarefa(parsed)
            tarefa_criada = self.db.obter_tarefa(tarefa_id)
            self.db.registrar_telemetria("inbox_tarefa_criada", {"tarefa_id": tarefa_id, "titulo": parsed.get("titulo")})
            return {
                "status": "criado",
                "tipo": "tarefa",
                "tarefa_id": tarefa_id,
                "registro": tarefa_criada,
                "feedback": f"Tarefa '{parsed['titulo']}' agendada com sucesso para {horario or 'hoje'} ({criticidade})."
            }

        elif tipo == "evento":
            horario_ini = horario or "09:00"
            start_at = f"{hoje}T{horario_ini}:00"
            duracao = parsed.get("duracao_estimada_min", 60)
            end_dt = datetime.fromisoformat(start_at) + timedelta(minutes=duracao)
            end_at = end_dt.isoformat()

            evento_id = self.db.criar_evento(
                title=parsed.get("titulo", "Compromisso"),
                start_at=start_at,
                end_at=end_at,
                is_busy_block=1
            )
            self.db.registrar_telemetria("inbox_evento_criado", {"evento_id": evento_id, "titulo": parsed.get("titulo")})
            return {
                "status": "criado",
                "tipo": "evento",
                "evento_id": evento_id,
                "start_at": start_at,
                "end_at": end_at,
                "feedback": f"Compromisso '{parsed['titulo']}' bloqueado na agenda das {horario_ini} às {end_dt.strftime('%H:%M')}."
            }

        elif tipo == "gasto":
            res_fin = self.finance.processar_notificacao_bancaria(
                app_origem="inbox_voz",
                texto=texto_final,
                titulo=parsed.get("titulo", "")
            )
            return {
                "status": "criado",
                "tipo": "gasto",
                "resultado": res_fin,
                "feedback": res_fin.get("feedback", "Gasto processado.")
            }

        elif tipo == "meta":
            meta_id = self.db.criar_meta(parsed)
            self.db.registrar_telemetria("inbox_meta_criada", {"meta_id": meta_id, "titulo": parsed.get("titulo")})
            return {
                "status": "criado",
                "tipo": "meta",
                "meta_id": meta_id,
                "feedback": f"Nova meta '{parsed['titulo']}' cadastrada no pilar {parsed.get('pilar', 'carreira_dev')}."
            }

        return {
            "status": "erro",
            "mensagem": f"Tipo de entrada não reconhecido: {tipo}"
        }
