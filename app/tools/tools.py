import os
import json
import subprocess
import pyautogui
import base64
import requests

from io import BytesIO
from datetime import datetime
from abc import ABC, abstractmethod


# ============================================================
# CONFIGURAÇÃO DO COMPUTADOR
# ============================================================

# Configuração atual do PyAutoGUI.
pyautogui.FAILSAFE = False


# ============================================================
# COMANDOS AUTORIZADOS DO COMPUTADOR
# ============================================================

CAMINHO_COMANDOS = "comandos_pc.json"


def carregar_comandos_pc() -> dict:
    """
    Carrega as ações autorizadas do computador a partir
    do arquivo comandos_pc.json.
    """

    if os.path.exists(CAMINHO_COMANDOS):

        try:
            with open(
                CAMINHO_COMANDOS,
                "r",
                encoding="utf-8"
            ) as arquivo:

                return json.load(arquivo)

        except Exception:
            pass

    return {}


ACOES_PERMITIDAS = carregar_comandos_pc()

CHAVES_ACOES = (
    list(ACOES_PERMITIDAS.keys())
    if ACOES_PERMITIDAS
    else ["nenhum_comando_configurado"]
)


# ============================================================
# CONTRATO BASE DAS FERRAMENTAS
# ============================================================

class FerramentaBase(ABC):
    """
    Interface base para todas as ferramentas do Agent Core.

    Cada ferramenta deve implementar:

        executar(argumentos: dict) -> str
    """

    @abstractmethod
    def executar(
        self,
        argumentos: dict
    ) -> str:
        pass


# ============================================================
# FERRAMENTA — HORA
# ============================================================

class FerramentaHora(FerramentaBase):

    def executar(
        self,
        argumentos: dict
    ) -> str:

        agora = datetime.now().strftime(
            "%A, %d de %B de %Y às %H:%M:%S"
        )

        return (
            "A data e hora exata do sistema "
            f"neste momento é: {agora}"
        )


# ============================================================
# FERRAMENTA — CALCULADORA
# ============================================================

class FerramentaCalculadora(FerramentaBase):

    def executar(
        self,
        argumentos: dict
    ) -> str:

        expressao = argumentos.get(
            "expressao",
            ""
        )

        # Mantém a sanitização existente.
        expressao_limpa = "".join(
            caractere
            for caractere in expressao
            if caractere in "0123456789+-*/(). "
        )

        try:

            resultado = eval(
                expressao_limpa
            )

            return (
                "O resultado matemático da "
                f"expressão {expressao_limpa} é: "
                f"{str(resultado)}"
            )

        except Exception as erro:

            return (
                "Erro ao calcular a expressão "
                f"'{expressao_limpa}': {erro}"
            )


# ============================================================
# FERRAMENTA — LEITOR DE ARQUIVOS
# ============================================================

class FerramentaLerArquivo(FerramentaBase):

    def executar(
        self,
        argumentos: dict
    ) -> str:

        nome_arquivo = argumentos.get(
            "nome_arquivo",
            ""
        )

        caminho_completo = os.path.join(
            "projetos",
            nome_arquivo
        )

        try:

            if os.path.exists(
                caminho_completo
            ):

                with open(
                    caminho_completo,
                    "r",
                    encoding="utf-8"
                ) as arquivo:

                    resultado = arquivo.read()

                # Proteção do contexto do modelo.
                if len(resultado) > 6000:

                    return (
                        resultado[:6000]
                        + "\n\n"
                        "[Conteúdo truncado por segurança. "
                        "O arquivo é muito grande.]"
                    )

                return resultado

            return (
                f"Erro: Arquivo '{nome_arquivo}' "
                "não encontrado. "
                "Verifique o nome ou coloque o arquivo "
                "na pasta projetos/."
            )

        except Exception as erro:

            return (
                f"Erro de leitura do arquivo "
                f"'{nome_arquivo}': {erro}"
            )


# ============================================================
# FERRAMENTA — CONTROLE DO COMPUTADOR
# ============================================================

class FerramentaControlarPC(FerramentaBase):

    def __init__(
        self,
        acoes_permitidas: dict
    ):
        self.__acoes = acoes_permitidas

    def executar(
        self,
        argumentos: dict
    ) -> str:

        acao = str(argumentos.get("acao", "") or argumentos.get("comando", "")).strip().lower()

        acoes = carregar_comandos_pc() or self.__acoes

        # Mapeamento / normalização inteligente de sinônimos
        sinonimos = {
            "vscode": "abrir_vscode",
            "vs_code": "abrir_vscode",
            "code": "abrir_vscode",
            "vs code": "abrir_vscode",
            "visual studio code": "abrir_vscode",
            "explorador": "abrir_explorador",
            "explorer": "abrir_explorador",
            "pastas": "abrir_explorador",
            "bloco_de_notas": "abrir_bloco_de_notas",
            "bloco de notas": "abrir_bloco_de_notas",
            "notepad": "abrir_bloco_de_notas",
            "calculadora": "abrir_calculadora",
            "calc": "abrir_calculadora",
            "downloads": "abrir_downloads",
            "documentos": "abrir_documentos",
            "imagens": "abrir_imagens",
            "lixeira": "abrir_lixeira",
            "terminal": "abrir_terminal",
            "cmd": "abrir_terminal",
            "prompt": "abrir_terminal",
            "powershell": "abrir_powershell",
            "paint": "abrir_paint",
            "mspaint": "abrir_paint",
            "taskmgr": "abrir_gerenciador_tarefas",
            "gerenciador_tarefas": "abrir_gerenciador_tarefas",
            "youtube": "abrir_youtube",
            "google": "abrir_google",
            "bloquear": "bloquear_ecra",
            "bloquear_pc": "bloquear_ecra"
        }
        if acao in sinonimos and sinonimos[acao] in acoes:
            acao = sinonimos[acao]

        # Normalização inteligente de prefixos verbais
        nome_alvo = acao
        for pfx in ["abrir_", "abrir ", "abrir", "abra_", "abra ", "abra", "iniciar_", "iniciar ", "iniciar", "inicie ", "execute_", "execute ", "execute", "executar "]:
            if nome_alvo.startswith(pfx) and len(nome_alvo) > len(pfx):
                nome_alvo = nome_alvo[len(pfx):].strip(" _-")
                break

        # Limpeza adicional de artigos e termos comuns ("o site do", "o site", "site do")
        for artigo in ["o site do ", "o site ", "site do ", "site ", "o aplicativo do ", "o app do ", "o app ", "o "]:
            if nome_alvo.startswith(artigo) and len(nome_alvo) > len(artigo):
                nome_alvo = nome_alvo[len(artigo):].strip()
                break

        from app.services.discovery_service import PROGRAMAS_WEB
        from app.services.playwright_mcp_service import playwright_service

        # Tratamento especial ultra-robusto para YouTube (incluindo canais e buscas)
        if "youtube" in nome_alvo or "youtube" in acao:
            termo_extra = (nome_alvo if "youtube" in nome_alvo else acao)
            for lixo in ["https://", "http://", "www.", "youtube.com", "youtube", ".com", ".br", "site do", "site", "web", "abrir"]:
                termo_extra = termo_extra.replace(lixo, "")
            termo_extra = termo_extra.strip(" /_-")
            for prefixo_busca in ["no canal do", "no canal", "canal do", "canal", "pesquise", "busque", "de", "do", "da"]:
                if termo_extra.startswith(prefixo_busca):
                    termo_extra = termo_extra[len(prefixo_busca):].strip()
            
            if termo_extra and termo_extra not in [".com", "web", "site"]:
                if "7minutoz" in termo_extra.lower():
                    url_web = "https://www.youtube.com/@7minutoz"
                else:
                    url_web = f"https://www.youtube.com/results?search_query={termo_extra.replace(' ', '+')}"
            else:
                url_web = "https://www.youtube.com"

            playwright_service.dispatch_command("navigate", {"url": url_web})
            return (
                f"Sucesso: O YouTube ({url_web}) foi aberto com êxito através da "
                f"extensão Playwright MCP Bridge no Google Chrome."
            )

        # Verificação prioritária de serviços web conhecidos
        for servico, url_padrao in PROGRAMAS_WEB.items():
            if servico == nome_alvo or servico == acao or (len(servico) > 3 and servico in nome_alvo.split()):
                playwright_service.dispatch_command("navigate", {"url": url_padrao})
                return (
                    f"Sucesso: O serviço web '{servico}' ({url_padrao}) foi acionado com êxito através da "
                    f"extensão Playwright MCP Bridge no navegador oficial (sem comandos de terminal)."
                )

        if acao.startswith("http://") or acao.startswith("https://") or nome_alvo.startswith("http://") or nome_alvo.startswith("https://"):
            url_web = acao if acao.startswith("http") else nome_alvo
            playwright_service.dispatch_command("navigate", {"url": url_web})
            return (
                f"Sucesso: A URL '{url_web}' foi acionada com êxito através da "
                f"extensão Playwright MCP Bridge no navegador oficial."
            )

        if acao not in acoes:
            # ============================================================
            # ETAPA 3.2: Motor de Descoberta Autônoma
            # ============================================================
            try:
                from app.services.discovery_service import aprender_e_registrar_comando
                descoberta = aprender_e_registrar_comando(nome_alvo)
                if descoberta.get("sucesso"):
                    tipo_desc = descoberta.get("tipo", "auto_descoberto")
                    if tipo_desc == "web_playwright_mcp":
                        url_web = descoberta.get("comando")
                        playwright_service.dispatch_command("navigate", {"url": url_web})
                        return (
                            f"Sucesso: O programa '{nome_alvo}' é um serviço web oficial ({url_web}) e foi acionado "
                            f"com êxito através da extensão Playwright MCP Bridge no navegador oficial (sem comandos de terminal)."
                        )
                    # ETAPA 3.4: Recarrega a lista de comandos atualizada do disco
                    acoes = carregar_comandos_pc() or self.__acoes
                    nova_chave = descoberta.get("chave")
                    if nova_chave and nova_chave in acoes:
                        acao = nova_chave
                        # ETAPA 3.5: Executa o comando recém-aprendido
                        from launcher import executar_no_windows
                        res = executar_no_windows(acoes[acao])
                        alvo_nome = res.get("alvo", acoes[acao])
                        return (
                            f"Sucesso: O programa '{nome_alvo}' não estava nos comandos conhecidos, mas foi localizado "
                            f"com êxito ({tipo_desc}: {alvo_nome}), registrado na lista permanente de automações e executado!"
                        )
            except Exception as erro_desc:
                print(f"[Discovery Warning] Falha na descoberta autônoma: {erro_desc}")

            return (
                f"Erro: A ação '{acao}' não foi encontrada nos comandos autorizados e não pôde ser descoberta automaticamente no sistema nem na web. "
                f"Ações válidas disponíveis: {', '.join(list(acoes.keys())[:15])}..."
            )

        try:
            from launcher import executar_no_windows
            res = executar_no_windows(acoes[acao])
            alvo_nome = res.get("alvo", acoes[acao])
            return (
                f"Sucesso: O comando '{acao}' ({alvo_nome}) foi executado com êxito na máquina física."
            )

        except Exception as erro:
            return (
                "Erro interno ao tentar executar no sistema: "
                f"{erro}"
            )


# ============================================================
# FERRAMENTA — TERMINAL
# ============================================================

class FerramentaTerminal(FerramentaBase):

    def executar(
        self,
        argumentos: dict
    ) -> str:

        comando = argumentos.get(
            "comando",
            ""
        )

        try:

            resultado = subprocess.run(
                comando,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )

            saida = resultado.stdout.strip()
            erro = resultado.stderr.strip()

            if erro and not saida:

                return (
                    "Comando executado com "
                    "código de erro:\n"
                    f"{erro}"
                )

            elif erro and saida:

                return (
                    f"Saída:\n{saida}\n\n"
                    "Erros/Avisos gerados:\n"
                    f"{erro}"
                )

            elif saida:

                if len(saida) > 4000:

                    return (
                        "Saída do terminal "
                        "(truncada por segurança):\n"
                        f"{saida[:4000]}..."
                    )

                return (
                    f"Saída do terminal:\n"
                    f"{saida}"
                )

            else:

                return (
                    f"O comando '{comando}' "
                    "foi executado com sucesso, "
                    "mas não retornou texto."
                )

        except subprocess.TimeoutExpired:

            return (
                "Erro: O comando demorou mais "
                "de 30 segundos e foi interrompido."
            )

        except Exception as erro:

            return (
                "Erro fatal ao tentar usar "
                f"o terminal: {erro}"
            )


# ============================================================
# FERRAMENTA — INTERAÇÃO COM A TELA
# ============================================================

class FerramentaInteragirEcra(FerramentaBase):

    def executar(
        self,
        argumentos: dict
    ) -> str:

        acao = argumentos.get(
            "acao"
        )

        try:

            # ------------------------------------------------
            # Digitar texto
            # ------------------------------------------------

            if acao == "escrever":

                texto = argumentos.get(
                    "texto",
                    ""
                )

                pyautogui.write(
                    texto,
                    interval=0.05
                )

                return (
                    f"Texto '{texto}' "
                    "digitado fisicamente com sucesso."
                )

            # ------------------------------------------------
            # Pressionar tecla
            # ------------------------------------------------

            elif acao == "tecla":

                tecla = argumentos.get(
                    "texto",
                    "enter"
                )

                pyautogui.press(
                    tecla
                )

                return (
                    f"Tecla '{tecla}' "
                    "pressionada fisicamente."
                )

            # ------------------------------------------------
            # Clicar
            # ------------------------------------------------

            elif acao == "clicar":

                largura, altura = (
                    pyautogui.size()
                )

                pyautogui.click(
                    largura / 2,
                    altura / 2
                )

                return (
                    "Clique realizado no "
                    "centro da tela."
                )

            # ------------------------------------------------
            # Analisar tela
            # ------------------------------------------------

            elif acao == "analisar_tela":

                screenshot = (
                    pyautogui.screenshot()
                )

                buffered = BytesIO()

                screenshot.save(
                    buffered,
                    format="JPEG",
                    quality=80
                )

                imagem_base64 = (
                    base64.b64encode(
                        buffered.getvalue()
                    ).decode("utf-8")
                )

                payload = {
                    "model": "llava",
                    "prompt": (
                        "Descreva o que está visível "
                        "na tela de forma objetiva. "
                        "Quais janelas ou programas "
                        "estão abertos?"
                    ),
                    "images": [
                        imagem_base64
                    ],
                    "stream": False
                }

                resposta = requests.post(
                    "http://127.0.0.1:11434/api/generate",
                    json=payload,
                    timeout=120
                )

                if resposta.status_code == 200:

                    dados = resposta.json()

                    return (
                        "Visão da Tela: "
                        f"{dados.get('response', '')}"
                    )

                return (
                    "Falha na visão. "
                    f"Status: {resposta.status_code}"
                )

            # ------------------------------------------------
            # Ação desconhecida
            # ------------------------------------------------

            else:

                return (
                    f"Ação '{acao}' "
                    "não reconhecida pela "
                    "ferramenta de tela."
                )

        except Exception as erro:

            return (
                "Erro físico ao interagir "
                f"com a interface gráfica: {erro}"
            )


# ============================================================
# FERRAMENTA — GERENCIAR JANELAS & APPS DO WINDOWS (MCP NATIVO)
# ============================================================

class FerramentaGerenciarJanelasWindows(FerramentaBase):
    def executar(self, argumentos: dict) -> str:
        from app.services.windows_mcp_service import windows_mcp_service
        acao = str(argumentos.get("acao", "listar") or "listar").lower().strip()
        alvo = str(argumentos.get("alvo", "") or argumentos.get("programa", "")).strip()
        texto = str(argumentos.get("texto", "")).strip()

        if acao in ("listar", "list", "ver", "abertas", "ativas"):
            janelas = windows_mcp_service.listar_janelas_ativas()
            if not janelas:
                return "Nenhuma janela de aplicativo detectada no momento."
            linhas = [f"Janelas e Aplicativos abertos no Windows ({len(janelas)}):"]
            for i, j in enumerate(janelas, 1):
                linhas.append(f"{i}. [{j['titulo']}] — Processo: {j['processo']} (PID {j['pid']}, Memória: {j['memoria_mb']} MB)")
            return "\n".join(linhas)

        elif acao in ("focar", "abrir", "trazer_frente", "ativar"):
            if not alvo:
                return "Erro: Parâmetro 'alvo' (título do programa ou PID) é obrigatório para focar."
            res = windows_mcp_service.focar_janela(alvo)
            return res.get("mensagem") or res.get("erro", "Janela focada.")

        elif acao in ("fechar", "encerrar", "kill"):
            if not alvo:
                return "Erro: Parâmetro 'alvo' é obrigatório para fechar."
            res = windows_mcp_service.fechar_janela(alvo, forcar="forcar" in acao or "kill" in acao)
            return res.get("mensagem") or res.get("erro", "Janela fechada.")

        elif acao in ("minimizar",):
            if not alvo:
                return "Erro: Parâmetro 'alvo' é obrigatório para minimizar."
            res = windows_mcp_service.minimizar_janela(alvo)
            return res.get("mensagem") or res.get("erro", "Janela minimizada.")

        elif acao in ("maximizar",):
            if not alvo:
                return "Erro: Parâmetro 'alvo' é obrigatório para maximizar."
            res = windows_mcp_service.maximizar_janela(alvo)
            return res.get("mensagem") or res.get("erro", "Janela maximizada.")

        elif acao in ("digitar", "escrever", "sendkeys"):
            if not alvo or not texto:
                return "Erro: Parâmetros 'alvo' (janela) e 'texto' são obrigatórios para digitar."
            res = windows_mcp_service.enviar_teclas_janela(alvo, texto)
            return res.get("mensagem") or res.get("erro", "Texto enviado.")

        elif acao in ("inspecionar", "controles", "botoes"):
            if not alvo:
                return "Erro: Parâmetro 'alvo' é obrigatório para inspecionar controles."
            res = windows_mcp_service.inspecionar_elementos(alvo)
            if not res.get("sucesso"):
                return res.get("erro", "Falha na inspeção.")
            elementos = res.get("elementos", [])
            if not elementos:
                return f"Janela '{alvo}' encontrada, mas não retornou controles acessíveis via UIAutomation."
            linhas = [f"Controles detectados na janela '{alvo}' ({len(elementos)}):"]
            for el in elementos:
                auto_id_info = f" [ID: {el['automation_id']}]" if el.get('automation_id') else ""
                linhas.append(f"- {el['tipo']}: \"{el['nome']}\"{auto_id_info}")
            return "\n".join(linhas)

        return f"Ação '{acao}' não reconhecida. Ações disponíveis: listar, focar, fechar, minimizar, maximizar, digitar, inspecionar."


# ============================================================
# FERRAMENTAS — PLAYWRIGHT MCP & EXTENSÃO HARVEY
# ============================================================

class FerramentaPlaywrightNavegar(FerramentaBase):
    def executar(self, argumentos: dict) -> str:
        from app.services.playwright_mcp_service import playwright_service
        url = argumentos.get("url", "").strip()
        if not url:
            return "Erro: Parâmetro 'url' é obrigatório."
        
        # Inteligência de formatação de URL
        if not url.startswith("http://") and not url.startswith("https://"):
            url_lower = url.lower()
            if "youtube" in url_lower:
                partes = url_lower
                for lixo in ["www.", "youtube.com", "youtube", ".com", ".br", "site do", "site", "web", "abrir"]:
                    partes = partes.replace(lixo, "")
                partes = partes.strip(" /_-")
                for prefixo_busca in ["no canal do", "no canal", "canal do", "canal", "pesquise", "busque", "de", "do", "da"]:
                    if partes.startswith(prefixo_busca):
                        partes = partes[len(prefixo_busca):].strip()

                if "7minutoz" in partes:
                    url = "https://www.youtube.com/@7minutoz"
                elif partes and partes not in [".com", "web", "site"]:
                    url = f"https://www.youtube.com/results?search_query={partes.replace(' ', '+')}"
                else:
                    url = "https://www.youtube.com"
            elif any(d in url for d in [".com", ".org", ".net", ".io", ".br"]):
                url = f"https://{url}"
            else:
                from app.services.discovery_service import PROGRAMAS_WEB
                url = PROGRAMAS_WEB.get(url_lower, f"https://www.google.com/search?q={url.replace(' ', '+')}")

        # Intercepta pesquisas inválidas ou alucinações (como .com, Rickroll ou slugs inventados no watch?v=)
        if "search_query=.com" in url or "search_query=com" in url or "search_query=site" in url:
            url = "https://www.youtube.com"
        elif "dQw4w9WgXcQ" in url:
            termo = "Trabalho Sujo" if "trabalho" in url.lower() else "musica"
            url = f"https://www.youtube.com/results?search_query={termo.replace(' ', '+')}"
        elif "watch?v=" in url:
            vid_id = url.split("watch?v=")[-1].split("&")[0]
            # IDs reais do YouTube tem exatamente 11 caracteres base64 sem palavras completas em português
            if len(vid_id) > 11 or "_" in vid_id or any(w in vid_id.lower() for w in ["mim", "mix", "chamando", "trabalho", "sujo", "musica"]):
                termo_slug = vid_id.replace("_", " ").replace("-", " ")
                playwright_service._load_state()
                aba_ativa = next((t for t in playwright_service.tabs if t.get("active")), None)
                if aba_ativa and "youtube.com" in aba_ativa.get("url", "").lower():
                    cmd = playwright_service.dispatch_command("click", {"selector": termo_slug})
                    return f"Sucesso: Clique no elemento ou vídeo '{termo_slug}' despachado para a aba ativa no Google Chrome."
                else:
                    url = f"https://www.youtube.com/results?search_query={termo_slug.replace(' ', '+')}"

        playwright_service.dispatch_command("navigate", {"url": url})
        return f"Sucesso: Navegando para '{url}' via Playwright MCP Bridge no Google Chrome."


class FerramentaPlaywrightSnapshot(FerramentaBase):
    def executar(self, argumentos: dict) -> str:
        from app.services.playwright_mcp_service import playwright_service
        tab_id = argumentos.get("tab_id")
        res = playwright_service.run_command_sync("snapshot", {"tab_id": tab_id}, timeout=4.0)
        dados = res.get("result", {})
        if dados and "text_tree" in dados and dados["text_tree"]:
            titulo = dados.get("title", "Aba Ativa")
            url = dados.get("url", "")
            return (
                f"Página: '{titulo}' ({url})\n"
                f"Elementos interativos detectados na tela (Use os IDs [1], [2], etc. para clicar ou digitar):\n"
                f"{dados['text_tree']}"
            )
        return "Aviso: A página foi inspecionada, mas não foram detectados novos elementos interativos no momento."


class FerramentaPlaywrightClicar(FerramentaBase):
    def executar(self, argumentos: dict) -> str:
        from app.services.playwright_mcp_service import playwright_service
        seletor = str(argumentos.get("seletor", "")).strip()
        tab_id = argumentos.get("tab_id")
        if not seletor:
            return "Erro: Parâmetro 'seletor' é obrigatório (pode ser o ID numérico [1] ou texto do elemento)."
        
        res = playwright_service.run_command_sync("click", {"selector": seletor, "tab_id": tab_id}, timeout=4.0)
        detalhes = res.get("result", {})
        if detalhes and detalhes.get("clicked"):
            texto_alvo = detalhes.get("text", seletor)
            elem_id = detalhes.get("id")
            id_info = f" [ID {elem_id}]" if elem_id else ""
            return f"Sucesso: Clique realizado no elemento{id_info} '{texto_alvo}' no Google Chrome."
        elif detalhes and detalhes.get("error"):
            return f"Erro ao clicar: {detalhes['error']}"
        return f"Sucesso: Ação de clique em '{seletor}' despachada para o navegador."


class FerramentaPlaywrightDigitar(FerramentaBase):
    def executar(self, argumentos: dict) -> str:
        from app.services.playwright_mcp_service import playwright_service
        seletor = str(argumentos.get("seletor", "")).strip()
        texto = argumentos.get("texto", "")
        enter = argumentos.get("enviar_enter", True)
        if not seletor and not texto:
            return "Erro: 'seletor' e 'texto' são necessários."
        res = playwright_service.run_command_sync("type", {"selector": seletor, "text": texto, "enter": enter}, timeout=4.0)
        detalhes = res.get("result", {})
        if detalhes and detalhes.get("typed"):
            return f"Sucesso: Texto '{texto}' digitado no campo '{seletor}' (Enter={'Sim' if enter else 'Não'})."
        return f"Sucesso: Digitação no campo '{seletor}' despachada para o Google Chrome."


class FerramentaPlaywrightMidia(FerramentaBase):
    def executar(self, argumentos: dict) -> str:
        from app.services.playwright_mcp_service import playwright_service
        acao = argumentos.get("acao", "play").lower().strip()
        valor = argumentos.get("valor")
        tab_id = argumentos.get("tab_id")
        res = playwright_service.run_command_sync("media_control", {"action": acao, "value": valor, "tab_id": tab_id}, timeout=3.5)
        detalhes = res.get("result", {})
        if detalhes and detalhes.get("found"):
            return f"Sucesso: Mídia ({acao}) executada com sucesso no player do Google Chrome."
        return f"Sucesso: Controle de mídia '{acao}' despachado para o Google Chrome."


class FerramentaPlaywrightAbas(FerramentaBase):
    def executar(self, argumentos: dict) -> str:
        from app.services.playwright_mcp_service import playwright_service
        playwright_service._load_state()
        acao = str(argumentos.get("acao", "listar") or "listar").lower().strip()
        url = argumentos.get("url")
        tab_id = argumentos.get("tab_id")

        if acao in ("listar", "list", "ver", "consultar", ""):
            playwright_service.dispatch_command("tab_control", {"action": "list"})
            tabs = playwright_service.tabs
            if not tabs:
                return "Nenhuma aba HTTP/HTTPS aberta no Google Chrome no momento."
            
            linhas = [f"Abas abertas no Google Chrome ({len(tabs)}):"]
            for i, t in enumerate(tabs, 1):
                status = " (Aba Ativa)" if t.get("active") else ""
                linhas.append(f"{i}. [{t.get('title', 'Sem título')}] — {t.get('url', '')}{status}")
            return "\n".join(linhas)

        cmd = playwright_service.dispatch_command("tab_control", {"action": acao, "url": url, "tab_id": tab_id})
        tabs = playwright_service.tabs
        info = f"{len(tabs)} abas registradas no navegador."
        return f"Sucesso: Comando de abas '{acao}' despachado. {info}"


# ============================================================
# FERRAMENTAS — ÁREAS OPERACIONAIS DO HUB
# ============================================================

class FerramentaInformacoesGerais(FerramentaBase):
    def executar(self, argumentos: dict) -> str:
        from app.services.capability_hub_service import capability_hub
        info = capability_hub.obter_informacoes_gerais()
        return (
            f"Data: {info['data']} ({info['dia_semana']}) | Hora: {info['hora']} | Fuso: {info['fuso_horario']}\n"
            f"Capacidades ativas no sistema: {len(info['capacidades'])} áreas operacionais integradas."
        )


class FerramentaPesquisaWeb(FerramentaBase):
    def executar(self, argumentos: dict) -> str:
        from app.services.capability_hub_service import capability_hub
        import asyncio
        query = argumentos.get("query", "").strip()
        idioma = argumentos.get("idioma", "pt-br")
        if not query:
            return "Erro: Consulta de pesquisa vazia."
        try:
            res = asyncio.run(capability_hub.pesquisar_web(query, idioma))
            resultados = res.get("results", [])
            if not resultados:
                return f"Nenhum resultado encontrado para '{query}'."
            texto = f"Resultados para '{query}' (Fonte: {res.get('source')}):\n"
            for r in resultados[:3]:
                texto += f"- {r.get('title')}: {r.get('snippet')} ({r.get('url')})\n"
            return texto.strip()
        except Exception as e:
            return f"Erro na pesquisa web: {e}"


class FerramentaPrevisaoTempo(FerramentaBase):
    def executar(self, argumentos: dict) -> str:
        from app.services.capability_hub_service import capability_hub
        import asyncio
        cidade = argumentos.get("cidade", "Sao Paulo").strip()
        periodo = argumentos.get("periodo", "hoje").strip()
        try:
            res = asyncio.run(capability_hub.consultar_previsao_tempo(cidade, periodo))
            if res.get("sucesso"):
                return (
                    f"Previsão do Tempo em {res['cidade']} ({res['periodo']}): "
                    f"Condição: {res['condicao']} | Atual: {res['temperatura_atual']} "
                    f"(Sensação: {res['sensacao_termica']}) | Mín/Máx: {res['temperatura_min']} a {res['temperatura_max']} | "
                    f"Chance de Chuva: {res['probabilidade_chuva']} | Umidade: {res['umidade']}"
                )
            return f"Erro: {res.get('erro', 'Falha ao consultar clima')}"
        except Exception as e:
            return f"Erro ao consultar clima: {e}"


class FerramentaGerenciarNotas(FerramentaBase):
    def executar(self, argumentos: dict) -> str:
        from app.services.capability_hub_service import capability_hub
        acao = argumentos.get("acao", "listar").lower().strip()
        texto = argumentos.get("texto")
        query = argumentos.get("query")
        nota_id = argumentos.get("nota_id")
        if nota_id is not None:
            try:
                nota_id = int(nota_id)
            except (ValueError, TypeError):
                nota_id = None

        res = capability_hub.gerenciar_nota(acao=acao, texto=texto, query=query, nota_id=nota_id)
        if acao == "salvar":
            return f"Sucesso: Nota salva com o conteúdo: '{texto}'"
        elif acao == "ultima":
            nota = res.get("nota")
            return f"Última nota: {nota.get('text')}" if nota else "Nenhuma nota registrada."
        elif acao == "listar":
            notas = res.get("notas", [])
            return f"Total de {res.get('total')} notas. Principais: " + "; ".join([f"[{n.get('id')}] {n.get('text')}" for n in notas[:5]])
        elif acao == "pesquisar":
            notas = res.get("notas", [])
            return f"Encontradas {len(notas)} notas para '{query}': " + "; ".join([f"[{n.get('id')}] {n.get('text')}" for n in notas[:3]])
        elif acao in ("editar", "atualizar"):
            if res.get("sucesso"):
                return f"Nota [{nota_id}] atualizada com sucesso para: '{texto}'"
            return f"Erro ao atualizar nota: {res.get('erro')}"
        elif acao == "excluir":
            if res.get("sucesso"):
                return f"Nota [{nota_id}] excluída com sucesso."
            return f"Erro ao excluir nota: {res.get('erro')}"
        return "Operação de nota realizada com sucesso."


class FerramentaGerenciarObjetivo(FerramentaBase):
    def executar(self, argumentos: dict) -> str:
        from app.services.capability_hub_service import capability_hub
        acao = argumentos.get("acao", "consultar").lower().strip()
        descricao = argumentos.get("descricao")
        condicoes = argumentos.get("condicoes")
        objetivo_id = argumentos.get("objetivo_id", "ativo")
        res = capability_hub.gerenciar_objetivo(acao, descricao, condicoes, objetivo_id)
        if res.get("sucesso"):
            if acao == "registrar":
                return f"Sucesso: Objetivo registrado: '{descricao}' (Critérios: {condicoes or 'Padrão'})."
            elif acao == "consultar":
                obj = res.get("objetivo_ativo")
                return f"Objetivo ativo: '{obj['descricao']}' ({obj['status']})" if obj else "Nenhum objetivo ativo no momento."
            else:
                return f"Sucesso: Objetivo marcado como '{res.get('novo_status')}'."
        return "Falha ao processar objetivo."


# ============================================================
# FERRAMENTAS — UTILIDADE REAL: AMBIENTES E CURADORIA DE ARQUIVOS
# ============================================================

class FerramentaAmbienteTrabalho(FerramentaBase):
    def executar(self, argumentos: dict) -> str:
        from app.services.workspace_service import workspace_service
        perfil = str(argumentos.get("perfil", "dev") or "dev").strip()
        res = workspace_service.preparar_ambiente(perfil)
        if res.get("sucesso"):
            return res.get("mensagem", "Ambiente preparado.")
        return f"Erro: {res.get('erro', 'Falha ao preparar ambiente.')}"


class FerramentaOrganizarArquivos(FerramentaBase):
    def executar(self, argumentos: dict) -> str:
        from app.services.workspace_service import workspace_service
        res = workspace_service.organizar_downloads()
        if res.get("sucesso"):
            return res.get("mensagem", "Downloads organizados.")
        return f"Erro: {res.get('erro', 'Falha ao organizar downloads.')}"



# ============================================================
# FERRAMENTAS — LIFE OS: TAREFAS PROATIVAS & CONSULTORIA FINANCEIRA
# ============================================================

class FerramentaGerenciarLifeOS(FerramentaBase):
    """Permite ao assistente criar, listar, adiar e concluir tarefas diárias no Life OS diretamente pelo chat."""
    def executar(self, argumentos: dict) -> str:
        from app.services.life_os import life_os_service
        acao = str(argumentos.get("acao", "criar_tarefa")).lower().strip()
        titulo = str(argumentos.get("titulo", "")).strip()
        horario = str(argumentos.get("horario", "")).strip()
        criticidade = str(argumentos.get("criticidade", "rotina")).lower().strip()
        motivo = str(argumentos.get("motivo", "")).strip()
        tarefa_id = argumentos.get("tarefa_id")
        prova = str(argumentos.get("prova", "")).strip()

        try:
            if acao in ("criar_tarefa", "agendar"):
                if not titulo:
                    return "Erro: Título da tarefa é obrigatório para agendamento."
                dados = {
                    "titulo": titulo,
                    "criticidade": criticidade if criticidade in ("rotina", "importante", "critica") else "rotina",
                    "horario_previsto": horario or None
                }
                res = life_os_service.criar_tarefa(dados)
                micro = res.get("micro_step_sugerido") or "Dê o primeiro passo de 2 minutos."
                crit_label = res.get("criticidade", "rotina").upper()
                horario_label = res.get("horario_previsto") or "hoje"
                return (
                    f"Sucesso: Tarefa '{titulo}' agendada para {horario_label} (Nível: {crit_label})! "
                    f"Micro-passo de 2 minutos sugerido: {micro}"
                )

            elif acao in ("listar_tarefas", "listar"):
                tarefas = life_os_service.listar_tarefas(status="pendente")
                if not tarefas:
                    return "Você não tem nenhuma tarefa pendente no momento. Parabéns!"
                linhas = [f"- [#{t['id']}] {t['titulo']} ({t.get('horario_previsto') or 'sem horário'}) [{t.get('criticidade')}]" for t in tarefas[:8]]
                return "Tarefas pendentes:\n" + "\n".join(linhas)

            elif acao in ("adiar_tarefa", "adiar"):
                if not tarefa_id:
                    return "Erro: O ID da tarefa é obrigatório para adiar."
                res = life_os_service.adiar_tarefa(int(tarefa_id), motivo=motivo or "Adiado pelo chat", minutos=15)
                return f"Sucesso: Tarefa #{tarefa_id} adiada em 15 minutos. Justificativa registrada: '{motivo}'."

            elif acao in ("concluir_tarefa", "concluir"):
                if not tarefa_id:
                    return "Erro: O ID da tarefa é obrigatório para concluir."
                res = life_os_service.concluir_tarefa(int(tarefa_id), prova=prova or "Concluído via conversa no chat")
                return f"Sucesso: Parabéns! Tarefa #{tarefa_id} marcada como concluída e arquivada."

            return f"Ação '{acao}' não suportada para gerenciar_life_os."
        except Exception as e:
            return f"Erro ao gerenciar tarefa no Life OS: {e}"


class FerramentaConsultorFinanceiroLifeOS(FerramentaBase):
    """Permite ao assistente registrar gastos, ganhos, consultar saldo das 4 caixas e dar conselhos de compra."""
    def executar(self, argumentos: dict) -> str:
        from app.services.life_os import life_os_service
        acao = str(argumentos.get("acao", "consultar_saldo")).lower().strip()
        valor = float(argumentos.get("valor") or 0.0)
        descricao = str(argumentos.get("descricao", "")).strip()
        categoria = str(argumentos.get("categoria", "livre_lazer")).lower().strip()
        item = str(argumentos.get("item", "")).strip()
        ma = str(argumentos.get("ma", "")).strip()

        try:
            # Heurística de proteção anti-inversão:
            # Se a IA enviar acao="registrar_gasto", mas a descrição indicar dinheiro que o usuário POSSUI/TEM/GUARDOU,
            # redireciona automaticamente para registro de entrada/receita.
            termos_posse = ["guardado", "em caixa", "tenho", "recebi", "ganhei", "na caixinha", "em conta", "poupado", "saldo", "em espécie", "em dinheiro"]
            desc_lower = (descricao + " " + item).lower()
            if acao in ("registrar_gasto", "gasto", "despesa") and any(t in desc_lower for t in termos_posse):
                acao = "registrar_receita"
                if categoria == "livre_lazer":
                    categoria = "apenas_recebimento"

            if acao in ("registrar_gasto", "gasto", "despesa"):
                if valor <= 0:
                    return "Erro: Informe um valor numérico positivo para registrar o gasto."
                tid = life_os_service.db.registrar_transacao(
                    tipo="despesa",
                    valor=valor,
                    categoria=categoria if categoria in ("custos_fixos", "construcao_futuro", "autoaperfeicoamento", "livre_lazer") else "livre_lazer",
                    descricao=descricao or "Gasto Chat",
                    origem="chat_assistente",
                    ma=ma
                )
                valor_hora = float(life_os_service.db.obter_config("valor_hora_trabalho", "25.0"))
                horas_vida = round(valor / valor_hora, 1) if valor_hora > 0 else 0.0
                caixas = life_os_service.obter_saldo_caixas()
                ma_info = f" (ma: '{ma}')" if ma else ""
                return (
                    f"Sucesso: Gasto de R$ {valor:.2f} ('{descricao or 'Despesa'}'){ma_info} registrado! "
                    f"Horas de vida/esforço equivalentes: {horas_vida}h. "
                    f"Saldo livre restante hoje: R$ {caixas.get('saldo_diario_restante', 0):.2f}. "
                    f"{'⚠️ ATENÇÃO: Teto diário estourado!' if caixas.get('saldo_diario_restante', 0) < 0 else 'Limite diário sob controle.'}"
                )

            elif acao in ("registrar_receita", "receita", "ganho", "ganhei"):
                if valor <= 0:
                    return "Erro: Informe um valor positivo para a receita."
                if categoria not in ("custos_fixos", "construcao_futuro", "autoaperfeicoamento", "livre_lazer", "apenas_recebimento"):
                    categoria = "apenas_recebimento"
                tid = life_os_service.db.registrar_transacao(
                    tipo="receita",
                    valor=valor,
                    categoria=categoria,
                    descricao=descricao or "Entrada / Recebimento",
                    origem="chat_assistente",
                    ma=ma
                )
                caixas = life_os_service.obter_saldo_caixas()
                ma_info = f" (ma: '{ma}')" if ma else ""
                cat_label = "Apenas Recebimento" if categoria == "apenas_recebimento" else categoria
                return (
                    f"Sucesso: Entrada de R$ {valor:.2f} ('{descricao or 'Receita'}'){ma_info} registrada com sucesso na categoria '{cat_label}'! "
                    f"Saldo total e fluxo financeiro atualizados no Life OS."
                )

            elif acao in ("consultar_saldo", "saldo", "caixas", "consultar_caixas"):
                caixas = life_os_service.obter_saldo_caixas()
                c = caixas.get("caixas", {})
                return (
                    f"Diagnóstico Financeiro em Tempo Real:\n"
                    f"- 🎯 Disponível para gastar hoje: R$ {caixas.get('saldo_diario_restante', 0):.2f} (Gastos hoje: R$ {caixas.get('gastos_hoje', 0):.2f} / Teto: R$ {caixas.get('teto_diario_livre', 50):.2f})\n"
                    f"- 🍕 Caixa Livre/Lazer: R$ {c.get('livre_lazer', {}).get('saldo', 0):.2f}\n"
                    f"- 🚀 Caixa Reserva & Metas de Longo Prazo: R$ {c.get('construcao_futuro', {}).get('saldo', 0):.2f}\n"
                    f"- 🏢 Caixa Custos Fixos: R$ {c.get('custos_fixos', {}).get('saldo', 0):.2f}\n"
                    f"- 📚 Caixa Estudos & Dev: R$ {c.get('autoaperfeicoamento', {}).get('saldo', 0):.2f}\n"
                    f"- ⚠️ Multas por procrastinação acumuladas: R$ {caixas.get('multas_procrastinacao_total', 0):.2f}"
                )

            elif acao in ("pedagio_compra", "avaliar_compra", "posso_comprar"):
                nome_alvo = item or descricao or "Item"
                if valor <= 0:
                    return "Erro: Informe o valor da compra para calcular o pedágio."
                res = life_os_service.finance.calcular_pedagio_compra(valor_compra=valor, nome_item=nome_alvo)
                caixas = life_os_service.obter_saldo_caixas()
                saldo_lazer = caixas.get("caixas", {}).get("livre_lazer", {}).get("saldo", 0)
                
                impacto_lazer = ""
                if valor > saldo_lazer:
                    impacto_lazer = f" ⚠️ O valor (R$ {valor:.2f}) supera o seu saldo de Lazer livre (R$ {saldo_lazer:.2f}) e invadirá sua reserva de futuro ou custos fixos!"
                else:
                    impacto_lazer = f" ✅ O valor cabe no seu saldo de Lazer livre atual (R$ {saldo_lazer:.2f})."

                return f"{res.get('conselho')}{impacto_lazer}"

            return f"Ação '{acao}' não suportada para gerenciar_financas_life_os."
        except Exception as e:
            return f"Erro na consultoria financeira: {e}"
