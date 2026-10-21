import os
import re
import json
from datetime import datetime
from typing import Any
from dotenv import load_dotenv
load_dotenv()
from pydantic import BaseModel

from app.infrastructure import storage
from app.core.config import Settings
from app.models.registry import create_provider
from app.models.base import Message

from app.routing.router import Router
from app.planning.planner import Planner

from app.services.chat_service import ChatService
from app.services.memory_service import MemoryService
from app.services.tool_service import ToolService
from app.tools.tools import carregar_comandos_pc

from app.events import event_bus
from app.events.event_contract import AgentChunkEvent, AgentMessageEvent, AgentDoneEvent
from app.events.command_contract import ProcessMessageCommand

class OrchestratorService:
    """Orquestra o ciclo de vida completo de uma requisição de IA de forma reativa e blindada."""

    def __init__(self):
        self.chat_service = ChatService()
        self.memory_service = MemoryService()
        self.tool_service = ToolService()
        
        self.router = Router()
        self.planner = Planner()
        
        self.settings = Settings()
        self.model_provider = create_provider(self.settings)

        self.modelo_padrao = getattr(self.settings, "model_padrao", None) or os.getenv("AGENT_MODEL_PADRAO", "hf.co/unsloth/gpt-oss-20b-GGUF:Q4_K_M")
        self.mapa_modelos = {
            "simples": getattr(self.settings, "model_simples", None) or os.getenv("AGENT_MODEL_SIMPLES", "llama3.2:1b"),
            "codigo": getattr(self.settings, "model_codigo", None) or os.getenv("AGENT_MODEL_CODIGO", self.modelo_padrao),
            "complexo": getattr(self.settings, "model_complexo", None) or os.getenv("AGENT_MODEL_COMPLEXO", self.modelo_padrao),
        }

    def _serializar_plano(self, plano: Any) -> dict | None:
        if plano is None: return None
        if hasattr(plano, "model_dump"): return plano.model_dump()
        if hasattr(plano, "__dict__"):
            resultado = {}
            for chave, valor in plano.__dict__.items():
                if hasattr(valor, "__dict__"):
                    resultado[chave] = valor.__dict__
                elif isinstance(valor, list):
                    resultado[chave] = [item.__dict__ if hasattr(item, "__dict__") else item for item in valor]
                else:
                    resultado[chave] = valor
            return resultado
        return None

    async def handle_process_message(self, command: ProcessMessageCommand) -> None:
        """Processa a mensagem em background e emite os resultados via Event Bus."""
        
        # Guarda o ID provisório caso exista, para o finally não dar erro
        chat_id = command.chat_id 
        
        try:
            chat = self.chat_service.obter_ou_criar_chat(chat_id)
            chat_id = chat["id"] # Atualiza com o ID definitivo
            
            mensagem = command.conteudo
            skill_id = command.skill_id
            imagem_base64 = command.imagem_base64

            mensagens_chat = chat.get("messages", [])

            skill_prompt = None
            ferramentas_permitidas: list[str] = []

            if skill_id and skill_id != "default":
                try:
                    skill = storage.obter_agente(skill_id)
                    if skill:
                        skill_prompt = skill.get("prompt", skill.get("system_prompt"))
                        ferramentas_permitidas = skill.get("ferramentas_permitidas", skill.get("tools", [])) or []
                except Exception as e:
                    print(f"[Orchestrator] Aviso: Falha ao carregar skill '{skill_id}': {e}")

            contexto_id = f"chat:{chat_id}"
            self.tool_service.carregar_permissoes_skill(contexto_id, ferramentas_permitidas)

            conteudo_usuario = mensagem if not imagem_base64 else f"{mensagem}\n\n[Imagem anexada em Base64]"
            mensagens_chat.append({"role": "user", "content": conteudo_usuario})

            # Verifica se o pedido do usuário requer ferramentas do sistema / interação com a máquina
            interage_maquina = (
                self.router._parece_interacao_maquina(mensagem)
                or (skill_id and skill_id != "default")
                or any(termo in mensagem.lower() for termo in [
                    "abra", "abrir", "inicie", "iniciar", "execute", "executar", "rode", "rodar",
                    "feche", "fechar", "bloqueie", "bloquear", "suspenda", "desligue",
                    "computador", "pc", "windows", "programa", "aplicativo", "app",
                    "calculadora", "calc", "vscode", "bloco de notas", "notepad", "explorer", "pasta",
                    "hora", "horas", "horário", "calcule", "calcular", "quanto é", "ler arquivo", "leia",
                    "site", "web", "navegador", "link", "url", "youtube", "discord", "google",
                    "pesquise", "pesquisar", "busca", "buscar", "notícia", "noticia", "notícias",
                    "tempo", "clima", "previsão", "previsao", "chuva", "temperatura",
                    "nota", "notas", "anote", "lembrete", "objetivo", "meta",
                    "clique", "clicar", "digite", "digitar", "aba", "abas", "play", "pause", "mídia", "midia", "volume",
                    "gastei", "comprei", "paguei", "ganhei", "receita", "despesa", "gasto", "saldo", "caixa", "caixas",
                    "reserva", "dinheiro", "pedágio", "pedagio", "comprar", "tarefa", "tarefas", "agendar", "agende",
                    "preciso", "fazer", "adiar", "concluir", "posso gastar", "quanto tenho"
                ])
            )

            # Roteia a solicitação
            rota = self.router.rotear(mensagem)
            
            # Se envolver interação com a máquina, SEMPRE utiliza o modelo de requisições complexas
            if interage_maquina or rota.rota == "complexo":
                modelo_complexo = self.mapa_modelos.get("complexo", os.getenv("AGENT_MODEL_COMPLEXO", self.modelo_padrao))
                modelo_selecionado = modelo_complexo
                rota.rota = "complexo"
                if not rota.motivo or "Solicitação geral" in rota.motivo:
                    rota.motivo = "A solicitação envolve interação ou controle da máquina/sistema."
            else:
                modelo_selecionado = self.mapa_modelos.get(rota.rota, self.modelo_padrao)

            rota.modelo = modelo_selecionado
            self.settings.model = modelo_selecionado

            memoria_contexto = self.memory_service.formatar_contexto(mensagem, limite=5)
            
            plano = None
            if rota.rota == "complexo":
                try:
                    plano = self.planner.planejar(objetivo=mensagem)
                except Exception as e:
                    print(f"[Orchestrator] Erro no Planner: {e}")

            precisa_ferramentas = interage_maquina

            system_parts = ["Você é o Agent Core, um assistente pessoal inteligente.", "Responda de forma objetiva, precisa e útil em Português do Brasil."]
            if skill_prompt:
                system_parts.append(f"\nInstruções da Skill:\n{skill_prompt}")
            elif precisa_ferramentas:
                system_parts.append(
                    "\nFERRAMENTAS DISPONÍVEIS:\n"
                    "- Para abrir aplicativos do computador ou serviços web, chame 'controlar_computador' com a ação ou nome do programa.\n"
                    "- Para listar programas abertos, focar janelas, fechar ou minimizar apps no Windows, chame 'gerenciar_janelas_windows' (ex: acao='listar' ou acao='focar', alvo='vscode').\n"
                    "- Para preparar estações de trabalho e ambientes com foco, dev ou estudo, chame 'preparar_ambiente_trabalho' (perfil='dev', 'foco', ou 'estudo').\n"
                    "- Para organizar, categorizar e limpar arquivos soltos na pasta Downloads, chame 'organizar_downloads'.\n"
                    "- Para navegar, ler páginas ou interagir com o navegador, chame as ferramentas Playwright MCP ('pw_navegar', 'pw_snapshot', 'pw_clicar', 'pw_digitar', 'pw_midia', 'gerenciar_abas').\n"
                    "- Para notícias e pesquisa de links na web, chame 'pesquisar_web'.\n"
                    "- Para previsão meteorológica e probabilidade de chuva, chame 'previsao_tempo'.\n"
                    "- Para notas e metas de conversa, chame 'gerenciar_notas' e 'gerenciar_objetivo'.\n"
                    "- Para hora atual e capacidades, chame 'obter_hora_atual' e 'obter_capacidades'.\n"
                    "- Para cálculos matemáticos, chame 'calcular'.\n"
                    "- Para tarefas, lembretes, compromissos e alarmes com data/hora (ex: 'me lembre de levar encomenda amanhã às 6:40', 'lembrar 5 min antes'), chame 'gerenciar_life_os' (acao='criar_tarefa', titulo=..., horario='06:35' ou '06:40', data_prevista='amanha', antecedencia_minutos=5, criticidade='critica' ou 'importante'). NUNCA recuse ou diga que não pode lembrar de horários!\n"
                    "- Para finanças, registro de gastos/ganhos, consultar as 4 caixas e calcular pedágio anti-impulso, chame 'gerenciar_financas_life_os' (acao='registrar_gasto', 'registrar_receita', 'consultar_saldo', 'pedagio_compra').\n"
                )
            else:
                system_parts.append(
                    "\nDIRETRIZES:\n"
                    "Responda diretamente à pergunta ou conversa do usuário com seu conhecimento em texto claro e bem formatado em Português. Não use nem mencione nomes de ferramentas ou códigos JSON."
                )

            if memoria_contexto: system_parts.append(f"\n{memoria_contexto}")

            # Injeção de Contexto Real-time do Life OS e Finanças
            try:
                from app.services.life_os import life_os_service
                status_life = life_os_service.obter_resumo_dashboard()
                caixas_life = life_os_service.obter_saldo_caixas()

                criticas_lista = [t['titulo'] + (f" ({t.get('horario_previsto')})" if t.get('horario_previsto') else "") for t in status_life.get('tarefas_criticas_hoje', [])]
                criticas_str = ", ".join(criticas_lista) if criticas_lista else "Nenhuma tarefa crítica definida para hoje"

                saldo_livre = caixas_life.get('saldo_diario_restante', 0.0)
                gastos_hoje = caixas_life.get('gastos_hoje', 0.0)
                teto_diario = caixas_life.get('teto_diario_livre', 50.0)
                c_data = caixas_life.get('caixas', {})
                reserva_metas = c_data.get('construcao_futuro', {}).get('saldo', 0.0)
                caixa_lazer = c_data.get('livre_lazer', {}).get('saldo', 0.0)
                custos_fixos = c_data.get('custos_fixos', {}).get('saldo', 0.0)

                system_parts.append(
                    f"\n[ESTADO EM TEMPO REAL DO LIFE OS & FINANÇAS]:\n"
                    f"- Data de hoje: {status_life.get('data')}\n"
                    f"- Top 3 Tarefas Críticas de Hoje: {criticas_str}\n"
                    f"- Finanças de Hoje: Teto diário = R$ {teto_diario:.2f} | Gastos hoje = R$ {gastos_hoje:.2f} | Saldo livre restante hoje = R$ {saldo_livre:.2f}\n"
                    f"- Saldos das Caixas: Reserva/Metas: R$ {reserva_metas:.2f} | Livre/Lazer: R$ {caixa_lazer:.2f} | Fixos: R$ {custos_fixos:.2f}\n"
                    f"DIRETRIZES DE ASSISTÊNCIA INTEGRAL:\n"
                    f"1. Você é o assistente pessoal integral e consultor estratégico. Preste total atenção na intenção financeira:\n"
                    f"   - POSSE OU RECEBIMENTO: Se o usuário falar sobre dinheiro que TEM, RECEBEU, GUARDOU ou ESTÁ EM CAIXA (ex: 'tenho 200 reais em caixa', 'estou com 300 na caixinha', 'guardado no banco', 'em dinheiro/espécie'), use acao='registrar_receita' (categoria='apenas_recebimento' ou 'construcao_futuro'). NUNCA chame 'registrar_gasto' para dinheiro que o usuário possui ou tem em caixa!\n"
                    f"   - PLANEJAMENTO FUTURO: Se ele disser que tem dinheiro 'para gastar em um evento dia 25', isso é um orçamento futuro, e NÃO uma despesa realizada hoje. Registre o valor disponível como receita/caixa ou adicione um lembrete no Life OS, mas NUNCA debite como gasto de hoje.\n"
                    f"   - GASTO REALIZADO: Use acao='registrar_gasto' EXCLUSIVAMENTE quando o usuário afirmar que já gastou, comprou ou pagou algo (ex: 'gastei 50', 'comprei almoço', 'paguei conta').\n"
                    f"2. COMPROMISSOS, TAREFAS E LEMBRETES (Motion & Alarmy style): Sempre que o usuário mencionar algo que precisa fazer, levar, buscar, acordar ou ser lembrado com data ou horário (ex: 'Amanhã levar encomenda ao IFTO às 6:40, me lembre 5 min antes'):\n"
                    f"   - Calcule o horário exato do alerta subtraindo a antecedência pedida (ex: 6:40 - 5 min = 06:35).\n"
                    f"   - Chame 'gerenciar_life_os' com acao='criar_tarefa', titulo=..., horario='06:35', data_prevista='amanha', antecedencia_minutos=5, criticidade='importante' ou 'critica'.\n"
                    f"   - Confirme ativamente ao usuário o agendamento do lembrete, data e horário exato do disparo (06:35) e sugira um micro-passo de 2 minutos para iniciar.\n"
                    f"   - NUNCA recuse ou diga que não pode lembrar de datas ou horários futuros!\n"
                    f"3. Dê conselhos reais e personalizados, nunca apenas respostas genéricas."
                )
            except Exception as e:
                pass


            # Contexto em tempo real do navegador aberto (Google Chrome)
            try:
                from app.services.playwright_mcp_service import playwright_service
                playwright_service._load_state()
                aba_ativa = next((t for t in playwright_service.tabs if t.get("active")), None)
                if aba_ativa:
                    url_ativa = aba_ativa.get('url', '')
                    playbook = playwright_service.obter_playbook(url_ativa)
                    playbook_info = ""
                    if playbook:
                        playbook_info = f"- Regras aprendidas para este site: {playbook.get('name')}.\n"

                    system_parts.append(
                        f"\n[ESTADO ATUAL DO NAVEGADOR (CHROME)]:\n"
                        f"- Aba ativa no momento: '{aba_ativa.get('title')}' ({url_ativa})\n"
                        f"{playbook_info}"
                        f"- Para interagir com a página, chame 'pw_snapshot' para ler os elementos numerados [1], [2], etc., e 'pw_clicar' passando o número do elemento (ex: '1', '3') ou texto.\n"
                        f"- Se o usuário pedir para tocar, reproduzir ou clicar em um item da página, chame 'pw_clicar' com o número ou texto do item diretamente.\n"
                        f"- Só use 'pw_navegar' se for para abrir um site ou endereço diferente."
                    )
            except Exception:
                pass
            
            plano_serializado = self._serializar_plano(plano)
            if plano_serializado:
                system_parts.append("\nPlano de execução:\n" + json.dumps(plano_serializado, ensure_ascii=False))

            mensagens_modelo = [{"role": "system", "content": "\n".join(system_parts)}]
            mensagens_modelo.extend(self.chat_service.preparar_contexto_limpo(mensagens_chat))
            
            ferramentas = self.tool_service.obter_schemas_da_skill(ferramentas_permitidas) if precisa_ferramentas else None
            mensagens_pydantic = [Message(**m) for m in mensagens_modelo]


            conteudo_texto = ""
            conteudo_thinking = ""
            tool_calls = []

            # Notifica a linha de raciocínio da rota escolhida
            info_rota = f"[Roteador: rota '{rota.rota}' ({rota.modelo}) - {rota.motivo}]\n"
            conteudo_thinking += info_rota
            await event_bus.publish(AgentChunkEvent(chat_id=chat_id, thinking=info_rota))
            if plano_serializado and len(plano_serializado.get('etapas', [])) > 0:
                msg_plano = f"[Plano de execução: {len(plano_serializado.get('etapas', []))} etapas]\n"
                conteudo_thinking += msg_plano
                await event_bus.publish(AgentChunkEvent(chat_id=chat_id, thinking=msg_plano))

            # ==========================================
            # 1ª CHAMADA COM CASCATA (Streaming Inicial)
            # ==========================================
            async for chunk in self.model_provider.chat_stream(messages=mensagens_pydantic, tools=ferramentas or None):
                if chunk["tipo"] == "thinking":
                    conteudo_thinking += chunk["conteudo"]
                    await event_bus.publish(AgentChunkEvent(chat_id=chat_id, thinking=chunk["conteudo"]))
                elif chunk["tipo"] == "texto":
                    conteudo_texto += chunk["conteudo"]
                    # Emite o chunk imediatamente para o EventBus (A MÁGICA DO STREAMING!)
                    await event_bus.publish(AgentChunkEvent(chat_id=chat_id, content=chunk["conteudo"]))
                elif chunk["tipo"] == "tools":
                    tool_calls = chunk["conteudo"]

            print(f"[Orchestrator DEBUG] Mensagem: '{mensagem}' | tool_calls da IA: {tool_calls}")

            # Fallback 1: Se o modelo retornou JSON de tool call no corpo do texto (comum em modelos locais compactos)
            if not tool_calls and "{" in conteudo_texto and "}" in conteudo_texto:
                try:
                    json_matches = re.findall(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", conteudo_texto, re.DOTALL)
                    for raw_j in json_matches:
                        try:
                            parsed_j = json.loads(raw_j)
                            if isinstance(parsed_j, dict):
                                if parsed_j.get("type") == "function" and "function" in parsed_j:
                                    fn = parsed_j["function"]
                                    tool_calls = [{
                                        "function": {
                                            "name": fn.get("name"),
                                            "arguments": fn.get("arguments") or fn.get("parameters", {}).get("properties", {}) or {}
                                        }
                                    }]
                                    break
                                elif "name" in parsed_j and ("arguments" in parsed_j or "parameters" in parsed_j or "properties" in parsed_j):
                                    tool_calls = [{
                                        "function": {
                                            "name": parsed_j["name"],
                                            "arguments": parsed_j.get("arguments", parsed_j.get("parameters", {}))
                                        }
                                    }]
                                    break
                        except Exception:
                            pass
                except Exception:
                    pass

            texto_m = mensagem.lower()

            # Fallback 2: Intenção direta de listar ou gerenciar abas do navegador
            if not tool_calls:
                termos_abas = ["aba", "abas", "guia", "guias", "tabs", "tab"]
                termos_listar = ["liste", "listar", "quais", "mostre", "mostrar", "ver", "todas", "aberta", "abertas", "aberto", "abertos"]
                if any(t in texto_m for t in termos_abas) and any(l in texto_m for l in termos_listar):
                    tool_calls = [{
                        "function": {
                            "name": "gerenciar_abas",
                            "arguments": {"acao": "listar"}
                        }
                    }]

            # Fallback 2.5: Intenção direta de pausar / retomar / controlar mídia
            termos_pause = ["pause", "pausar", "pare o vídeo", "pare o video", "pare a música", "pare a musica", "parar o vídeo", "parar a música", "despause", "despausar", "continue o vídeo", "continue a música", "retome a música", "retome o vídeo", "mute", "mutar", "desmute"]
            if not tool_calls and any(p in texto_m for p in termos_pause):
                acao_m = "play" if any(c in texto_m for c in ["despause", "continue", "retome"]) else "pause"
                from app.services.playwright_mcp_service import playwright_service
                playwright_service._load_state()
                target_tab_id = None
                for t in playwright_service.tabs:
                    t_title = t.get("title", "").lower()
                    if any(w in t_title for w in ["luan", "santana", "youtube", "spotify"]) or t.get("audible"):
                        target_tab_id = t.get("tab_id")
                        break
                args_m = {"acao": acao_m}
                if target_tab_id:
                    args_m["tab_id"] = target_tab_id
                tool_calls = [{
                    "function": {
                        "name": "pw_midia",
                        "arguments": args_m
                    }
                }]

            # Fallback 2.8: Intenção direta de gerenciar janelas e programas abertos no Windows
            if not tool_calls:
                termos_janela = ["janela", "janelas", "programa aberto", "programas abertos", "aplicativo aberto", "aplicativos abertos"]
                termos_listar_j = ["liste", "listar", "quais", "mostre", "mostrar", "ver", "todas", "aberta", "abertas", "aberto", "abertos"]
                if any(j in texto_m for j in termos_janela) and any(l in texto_m for l in termos_listar_j):
                    tool_calls = [{
                        "function": {
                            "name": "gerenciar_janelas_windows",
                            "arguments": {"acao": "listar"}
                        }
                    }]
                elif any(f in texto_m for f in ["foque na janela", "foque no", "mude para o", "alterne para", "traga para frente"]):
                    for pref in ["foque na janela ", "foque no ", "foque na ", "mude para o ", "mude para a ", "alterne para o ", "alterne para a ", "traga para frente o ", "traga para frente "]:
                        if pref in texto_m:
                            alvo_j = texto_m.split(pref)[-1].strip()
                            tool_calls = [{
                                "function": {
                                    "name": "gerenciar_janelas_windows",
                                    "arguments": {"acao": "focar", "alvo": alvo_j}
                                }
                            }]
                            break

            # Fallback 2.9: Intenção direta de ambiente de trabalho (dev/foco/estudo) ou organizar downloads
            if not tool_calls:
                termos_dev = ["modo dev", "modo desenvolvimento", "ambiente dev", "ambiente de dev", "ambiente de desenvolvimento", "workspace dev"]
                termos_foco = ["modo foco", "modo concentracao", "modo concentração", "ambiente foco", "ambiente de foco"]
                termos_estudo = ["modo estudo", "modo estudos", "ambiente estudo", "ambiente de estudo", "workspace estudo"]
                
                if any(t in texto_m for t in termos_dev):
                    tool_calls = [{
                        "function": {
                            "name": "preparar_ambiente_trabalho",
                            "arguments": {"perfil": "dev"}
                        }
                    }]
                elif any(t in texto_m for t in termos_foco):
                    tool_calls = [{
                        "function": {
                            "name": "preparar_ambiente_trabalho",
                            "arguments": {"perfil": "foco"}
                        }
                    }]
                elif any(t in texto_m for t in termos_estudo):
                    tool_calls = [{
                        "function": {
                            "name": "preparar_ambiente_trabalho",
                            "arguments": {"perfil": "estudo"}
                        }
                    }]
                elif any(t in texto_m for t in ["organizar download", "organizar downloads", "organize meus downloads", "organize os downloads", "limpar download", "limpar downloads", "arrumar downloads", "arrumar a pasta downloads"]):
                    tool_calls = [{
                        "function": {
                            "name": "organizar_downloads",
                            "arguments": {}
                        }
                    }]

            # Fallback 3: Intenção de reproduzir/tocar música ou vídeo no YouTube
            if not tool_calls:
                termos_musica = ["reproduzir", "reproduza", "tocar", "toque", "ouvir", "coloquei para reproduzir", "coloque para reproduzir", "coloque para tocar"]
                if any(m_termo in texto_m for m_termo in termos_musica):
                    termo_busca = texto_m
                    for m_termo in termos_musica:
                        if m_termo in termo_busca:
                            idx = termo_busca.find(m_termo) + len(m_termo)
                            termo_busca = termo_busca[idx:].strip()
                            break
                    for pref in ["a música", "a musica", "o vídeo", "o video", "o som", "a canção", "a cancao", "o ", "a "]:
                        if termo_busca.startswith(pref):
                            termo_busca = termo_busca[len(pref):].strip()
                            break
                    for suf in ["no youtube", "no chrome", "no navegador", "por favor"]:
                        if termo_busca.endswith(suf):
                            termo_busca = termo_busca[:-len(suf)].strip()
                    
                    if termo_busca:
                        url_busca = f"https://www.youtube.com/results?search_query={termo_busca.replace(' ', '+')}"
                        tool_calls = [{
                            "function": {
                                "name": "pw_navegar",
                                "arguments": {"url": url_busca}
                            }
                        }]

            # Fallback 3.5: Intenção direta de clicar em algo na página ("clique em X", "clique no vídeo X")
            if not tool_calls and any(c in texto_m for c in ["clique", "clicar", "selecione", "selecionar"]):
                termo_click = texto_m
                for c in ["clique no vídeo ", "clique no video ", "clique na música ", "clique na musica ", "clique em ", "clique no ", "clique na ", "clique ", "clicar em ", "clicar no "]:
                    if c in termo_click:
                        idx = termo_click.find(c) + len(c)
                        termo_click = termo_click[idx:].strip()
                        break
                for suf in ["por favor", "na tela", "na página", "no youtube", "no chrome", "no navegador"]:
                    if termo_click.endswith(suf):
                        termo_click = termo_click[:-len(suf)].strip()
                if termo_click:
                    tool_calls = [{
                        "function": {
                            "name": "pw_clicar",
                            "arguments": {"seletor": termo_click}
                        }
                    }]

            # Fallback 4: Intenção de abrir programas no computador ou serviços web
            if not tool_calls and any(p in texto_m for p in ["abra", "abrir", "inicie", "iniciar", "execute", "executar", "bloqueie", "bloquear"]):
                acoes = carregar_comandos_pc()
                acao_encontrada = None
                print(f"[Orchestrator DEBUG] Testando fallback PC. Ações carregadas: {len(acoes)}")
                
                mapa_intencoes = {
                    ("vs code", "vscode", "code"): "abrir_vscode",
                    ("explorador", "explorer", "meus arquivos", "pastas"): "abrir_explorador",
                    ("bloco de notas", "notepad"): "abrir_bloco_de_notas",
                    ("calculadora", "calc"): "abrir_calculadora",
                    ("terminal", "cmd", "prompt"): "abrir_terminal",
                    ("powershell",): "abrir_powershell",
                    ("paint", "mspaint"): "abrir_paint",
                    ("gerenciador de tarefas", "task manager", "taskmgr"): "abrir_gerenciador_tarefas",
                    ("downloads",): "abrir_downloads",
                    ("documentos",): "abrir_documentos",
                    ("imagens", "fotos"): "abrir_imagens",
                    ("lixeira",): "abrir_lixeira",
                    ("youtube",): "abrir_youtube",
                    ("google",): "abrir_google",
                    ("whatsapp",): "abrir_whatsapp_web",
                    ("bloquear", "bloqueie"): "bloquear_ecra",
                }
                for termos, chave in mapa_intencoes.items():
                    if any(t in texto_m for t in termos):
                        if chave == "abrir_youtube" and any(k in texto_m for k in ["canal", "busca", "pesquise", "vídeo", "video", "7minutoz"]):
                            acao_encontrada = texto_m
                            break
                        if chave in acoes or "abrir_" in chave:
                            acao_encontrada = chave
                            break

                # Se não for uma das intenções fixas, extrai dinamicamente o alvo do comando para auto-aprendizado
                if not acao_encontrada:
                    padroes = [
                        r"(?:abra|abrir|inicie|iniciar|execute|executar)\s+(?:o|a|os|as)?\s*([a-zA-Z0-9_\-\.\s]+)",
                    ]
                    for padrao in padroes:
                        m = re.search(padrao, texto_m)
                        if m:
                            alvo_extraido = m.group(1).strip()
                            for sufixo in ["no meu computador", "no meu pc", "no computador", "no pc", "por favor", "no windows"]:
                                if alvo_extraido.endswith(sufixo):
                                    alvo_extraido = alvo_extraido[:-len(sufixo)].strip()
                            if alvo_extraido and len(alvo_extraido) >= 2:
                                acao_encontrada = alvo_extraido
                                break
                        
                if acao_encontrada:
                    tool_calls = [{
                        "function": {
                            "name": "controlar_computador",
                            "arguments": {"acao": acao_encontrada}
                        }
                    }]

            resultados_tools = []

            # ==========================================
            # EXECUÇÃO DAS TOOLS (Caso o LLM peça ou fallback)
            # ==========================================
            if tool_calls:
                msg_tools = f"\n[Executando ações no computador: {len(tool_calls)} ferramenta(s)...]\n"
                conteudo_thinking += msg_tools
                await event_bus.publish(AgentChunkEvent(chat_id=chat_id, thinking=msg_tools))

            # Sanitização e correção de alucinações de navegação em pedidos de clique
            for tc in tool_calls:
                if not isinstance(tc, dict): continue
                fn = tc.get("function", {})
                fn_name = fn.get("name")
                fn_args = fn.get("arguments", {})
                if isinstance(fn_args, str):
                    try: fn_args = json.loads(fn_args)
                    except: fn_args = {}

                if fn_name == "pw_navegar":
                    url_val = fn_args.get("url", "")
                    e_comando_clique = any(c in texto_m for c in ["clique no", "clique na", "clique em", "clique "])
                    e_url_falsa = ("watch?v=" in url_val and ("_" in url_val.split("watch?v=")[-1] or len(url_val.split("watch?v=")[-1]) > 11))
                    
                    if e_comando_clique or e_url_falsa:
                        alvo_c = None
                        prefixos = [
                            "clique no vídeo ", "clique no video ", "clique na música ", "clique na musica ", 
                            "clique em ", "clique no ", "clique na ", "clique ",
                            "coloque para reproduzir o ", "coloque para reproduzir a ", "coloque para reproduzir ",
                            "coloque para tocar o ", "coloque para tocar a ", "coloque para tocar ",
                            "reproduza o vídeo ", "reproduza a música ", "reproduza o ", "reproduza a ", "reproduza ",
                            "toque a música ", "toque o vídeo ", "toque o ", "toque a ", "toque ",
                            "ouvir a música ", "ouvir o ", "ouvir ", "ponha para tocar ", "ponha para reproduzir ", "ponha "
                        ]
                        for c_pref in prefixos:
                            if c_pref in texto_m:
                                idx = texto_m.find(c_pref) + len(c_pref)
                                alvo_c = texto_m[idx:].strip()
                                break
                        if not alvo_c and e_url_falsa:
                            alvo_c = "Meu mix" if "meu mix" in texto_m else texto_m
                        if alvo_c:
                            for noise in ["o vídeo ", "o video ", "a música ", "a musica ", "o mix ", "o ", "a "]:
                                if alvo_c.startswith(noise):
                                    alvo_c = alvo_c[len(noise):].strip()
                                    break
                            for suf in ["por favor", "na tela", "no youtube", "no chrome", "no navegador"]:
                                if alvo_c.endswith(suf): alvo_c = alvo_c[:-len(suf)].strip()
                            tc["function"]["name"] = "pw_clicar"
                            tc["function"]["arguments"] = {"seletor": alvo_c}

                if fn_name == "pw_clicar":
                    seletor_val = str(fn_args.get("seletor", ""))
                    # Se o modelo gerou seletor de player de vídeo ou a intenção do usuário foi pausar/parar vídeo
                    e_pausa = any(ind in seletor_val for ind in ["movie_player", "play-pause-button", "ytp-play-button"]) or any(p in texto_m for p in ["pause", "pausar", "pare o vídeo", "pare a música", "parar o vídeo", "parar a música"])
                    if e_pausa:
                        tc["function"]["name"] = "pw_midia"
                        acao_m = "play" if any(c in texto_m for c in ["despause", "continue", "retome"]) else "pause"
                        from app.services.playwright_mcp_service import playwright_service
                        playwright_service._load_state()
                        target_tab_id = None
                        for t in playwright_service.tabs:
                            t_title = t.get("title", "").lower()
                            if any(w in t_title for w in ["luan", "santana", "youtube", "spotify"]) or t.get("audible"):
                                target_tab_id = t.get("tab_id")
                                break
                        args_m = {"acao": acao_m}
                        if target_tab_id:
                            args_m["tab_id"] = target_tab_id
                        tc["function"]["arguments"] = args_m
                    elif "text=" in seletor_val:
                        limpo = seletor_val.replace("text=", "").replace('"', '').replace("'", "").strip()
                        tc["function"]["arguments"]["seletor"] = limpo

                if fn_name == "pw_midia" and not fn_args.get("tab_id"):
                    from app.services.playwright_mcp_service import playwright_service
                    playwright_service._load_state()
                    for t in playwright_service.tabs:
                        t_title = t.get("title", "").lower()
                        if any(w in t_title for w in ["luan", "santana", "youtube", "spotify"]) or t.get("audible"):
                            tc["function"]["arguments"]["tab_id"] = t.get("tab_id")
                            break

            for tool_call in tool_calls:
                if not isinstance(tool_call, dict): continue
                
                function_data = tool_call.get("function", {})
                ferramenta_id = function_data.get("name")
                argumentos = function_data.get("arguments", {})

                if isinstance(argumentos, str):
                    try: argumentos = json.loads(argumentos)
                    except json.JSONDecodeError: argumentos = {}

                if not ferramenta_id: continue

                try:
                    resultado = self.tool_service.executar(contexto_id, ferramenta_id, argumentos)
                    resultados_tools.append({"tool_call": tool_call, "resultado": resultado, "erro": None})
                    msg_ok = f"[Ação concluída: {ferramenta_id} | Resultado: {str(resultado)[:80]}]\n"
                    conteudo_thinking += msg_ok
                    await event_bus.publish(AgentChunkEvent(chat_id=chat_id, thinking=msg_ok))
                except Exception as erro:
                    resultados_tools.append({"tool_call": tool_call, "resultado": None, "erro": str(erro)})
                    msg_err = f"[Erro na ação {ferramenta_id}: {erro}]\n"
                    conteudo_thinking += msg_err
                    await event_bus.publish(AgentChunkEvent(chat_id=chat_id, thinking=msg_err))

            # ==========================================
            # 2ª CHAMADA OU RESPOSTA IMEDIATA
            # ==========================================
            if resultados_tools:
                primeiro_res = resultados_tools[0].get("resultado", "")
                if isinstance(primeiro_res, str) and any(ind in primeiro_res for ind in ["Sucesso:", "Abas abertas", "Nenhuma aba", "Data:", "Visão da Tela:"]):
                    conteudo_final = primeiro_res.strip()
                    await event_bus.publish(AgentChunkEvent(chat_id=chat_id, content=conteudo_final))
                else:
                    mensagens_modelo.append({
                        "role": "assistant", 
                        "content": conteudo_texto, 
                        "tool_calls": tool_calls
                    })

                    for resultado_tool in resultados_tools:
                        ferramenta_id = resultado_tool["tool_call"].get("function", {}).get("name", "")
                        erro = resultado_tool["erro"]
                        resultado = resultado_tool["resultado"]
                        conteudo_tool = json.dumps({"erro": erro}, ensure_ascii=False) if erro else json.dumps(resultado, ensure_ascii=False)
                        mensagens_modelo.append({
                            "role": "tool",
                            "content": conteudo_tool,
                            "name": ferramenta_id,
                        })

                    mensagens_pydantic = [Message(**m) for m in mensagens_modelo]
                    conteudo_final = ""
                    async for chunk in self.model_provider.chat_stream(messages=mensagens_pydantic, tools=ferramentas or None):
                        if chunk["tipo"] == "thinking":
                            conteudo_thinking += chunk["conteudo"]
                            await event_bus.publish(AgentChunkEvent(chat_id=chat_id, thinking=chunk["conteudo"]))
                        elif chunk["tipo"] == "texto":
                            conteudo_final += chunk["conteudo"]
                            await event_bus.publish(AgentChunkEvent(chat_id=chat_id, content=chunk["conteudo"]))
                    
                    if not (conteudo_final or "").strip() and isinstance(primeiro_res, str):
                        conteudo_final = primeiro_res.strip()
                        await event_bus.publish(AgentChunkEvent(chat_id=chat_id, content=conteudo_final))
            else:
                conteudo_final = conteudo_texto




            if not isinstance(conteudo_final, str): 
                conteudo_final = str(conteudo_final)

            # ==========================================
            # REGISTO FINAL NO CHAT E EMISSÃO DA MENSAGEM
            # ==========================================
            mensagem_assistente_final = {
                "role": "assistant",
                "content": conteudo_final,
                "model": rota.modelo,
                "skill": skill_id,
                "route": rota.rota,
                "confidence": rota.confianca,
                "reason": rota.motivo,
                "reasoning": conteudo_thinking,
                "router_metadata": rota.metadata,
                "plan": plano_serializado,
                "timestamp": datetime.now().isoformat(),
            }

            mensagens_chat.append(mensagem_assistente_final)
            chat["messages"] = mensagens_chat
            self.chat_service.salvar_chat(chat)

            # Emissão do evento final condensado para o histórico/frontend
            evento_msg = AgentMessageEvent(
                chat_id=chat_id,
                content=conteudo_final,
                model=rota.modelo,
                route=rota.rota,
                skill=skill_id,
                confidence=rota.confianca,
                reason=rota.motivo,
                reasoning=conteudo_thinking,
                router_metadata=rota.metadata,
                plan=plano_serializado
            )
            await event_bus.publish(evento_msg)


        except Exception as e:
            print(f"\n[Orchestrator] [ERRO CRITICO] no processamento: {e}")
            
            evento_erro = AgentMessageEvent(
                chat_id=chat_id,
                content=f"**Erro Interno do Agente:** `{str(e)}`\nVerifique os logs do servidor FastAPI.",
                model="erro",
                route="erro"
            )
            await event_bus.publish(evento_erro)

        finally:
            evento_done = AgentDoneEvent(chat_id=chat_id)
            await event_bus.publish(evento_done)