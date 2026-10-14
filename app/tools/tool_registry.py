from app.tools.tool_contract import ToolContract
from app.tools.tools import (
    FerramentaHora,
    FerramentaCalculadora,
    FerramentaLerArquivo,
    FerramentaControlarPC,
    FerramentaTerminal,
    FerramentaInteragirEcra,
    FerramentaPlaywrightNavegar,
    FerramentaPlaywrightSnapshot,
    FerramentaPlaywrightClicar,
    FerramentaPlaywrightDigitar,
    FerramentaPlaywrightMidia,
    FerramentaPlaywrightAbas,
    FerramentaInformacoesGerais,
    FerramentaPesquisaWeb,
    FerramentaPrevisaoTempo,
    FerramentaGerenciarNotas,
    FerramentaGerenciarObjetivo,
    FerramentaGerenciarJanelasWindows,
    FerramentaAmbienteTrabalho,
    FerramentaOrganizarArquivos,
    ACOES_PERMITIDAS,
    CHAVES_ACOES,
)


class ToolRegistry:
    """
    Registro central de todas as ferramentas disponíveis
    no Agent Core.

    Responsabilidades:
    - registrar ferramentas
    - localizar ferramentas
    - listar ferramentas
    - remover ferramentas
    - gerar schemas para o Ollama
    """

    def __init__(self):
        self._ferramentas: dict[str, ToolContract] = {}

    # ==========================================================
    # REGISTRO
    # ==========================================================

    def registrar(
        self,
        ferramenta: ToolContract
    ) -> None:

        if not ferramenta.id:
            raise ValueError(
                "A ferramenta precisa possuir um ID."
            )

        if ferramenta.id in self._ferramentas:
            raise ValueError(
                f"A ferramenta '{ferramenta.id}' "
                "já está registrada."
            )

        self._ferramentas[ferramenta.id] = ferramenta

    # ==========================================================
    # CONSULTA
    # ==========================================================

    def obter(
        self,
        ferramenta_id: str
    ) -> ToolContract | None:

        return self._ferramentas.get(
            ferramenta_id
        )

    def existe(
        self,
        ferramenta_id: str
    ) -> bool:

        return ferramenta_id in self._ferramentas

    def listar(self) -> list[ToolContract]:

        return list(
            self._ferramentas.values()
        )

    # ==========================================================
    # REMOÇÃO
    # ==========================================================

    def remover(
        self,
        ferramenta_id: str
    ) -> bool:

        if ferramenta_id not in self._ferramentas:
            return False

        del self._ferramentas[
            ferramenta_id
        ]

        return True

    def limpar(self) -> None:

        self._ferramentas.clear()

    # ==========================================================
    # SCHEMA OLLAMA
    # ==========================================================

    def gerar_schema_ollama(
        self,
        ferramenta: ToolContract
    ) -> dict:

        propriedades = {}

        obrigatorios = []

        for nome, configuracao in (
            ferramenta.argumentos or {}
        ).items():

            if not isinstance(
                configuracao,
                dict
            ):
                continue

            propriedade = {
                "type": configuracao.get(
                    "tipo",
                    "string"
                )
            }

            descricao = configuracao.get(
                "descricao"
            )

            if descricao:
                propriedade[
                    "description"
                ] = descricao

            enum = configuracao.get(
                "enum"
            )

            if enum:
                propriedade[
                    "enum"
                ] = enum

            propriedades[
                nome
            ] = propriedade

            if configuracao.get(
                "obrigatorio",
                False
            ):
                obrigatorios.append(
                    nome
                )

        parameters = {
            "type": "object",
            "properties": propriedades,
        }

        if obrigatorios:
            parameters[
                "required"
            ] = obrigatorios

        return {
            "type": "function",
            "function": {
                "name": ferramenta.id,
                "description": ferramenta.descricao,
                "parameters": parameters,
            },
        }

    # ==========================================================
    # SCHEMAS DE VÁRIAS FERRAMENTAS
    # ==========================================================

    def gerar_schemas_ollama(
        self,
        ferramenta_ids: list[str] | None = None
    ) -> list[dict]:
        """
        Gera os schemas Ollama das ferramentas solicitadas.

        Se nenhuma lista for informada, gera o schema
        de todas as ferramentas registradas.
        """

        if ferramenta_ids is None:

            ferramentas = self.listar()

        else:

            ferramentas = []

            for ferramenta_id in ferramenta_ids:

                ferramenta = self.obter(
                    ferramenta_id
                )

                if ferramenta is not None:
                    ferramentas.append(
                        ferramenta
                    )

        return [
            self.gerar_schema_ollama(
                ferramenta
            )
            for ferramenta in ferramentas
        ]


# ==============================================================
# REGISTRY PADRÃO
# ==============================================================

def criar_registry_padrao() -> ToolRegistry:

    registry = ToolRegistry()

    # ----------------------------------------------------------
    # Hora
    # ----------------------------------------------------------

    ferramenta_hora = FerramentaHora()

    registry.registrar(
        ToolContract(
            id="obter_hora_atual",
            nome="Obter hora atual",
            descricao=(
                "Obtém a data e hora atual do sistema."
            ),
            categoria="sistema",
            risco="baixo",
            argumentos={},
            requer_confirmacao=False,
            handler=ferramenta_hora.executar,
        )
    )

    # ----------------------------------------------------------
    # Calculadora
    # ----------------------------------------------------------

    ferramenta_calculadora = (
        FerramentaCalculadora()
    )

    registry.registrar(
        ToolContract(
            id="calcular",
            nome="Calculadora",
            descricao=(
                "Executa cálculos matemáticos."
            ),
            categoria="matematica",
            risco="baixo",
            argumentos={
                "expressao": {
                    "tipo": "string",
                    "obrigatorio": True,
                    "descricao": (
                        "Expressão matemática "
                        "a ser calculada."
                    ),
                }
            },
            requer_confirmacao=False,
            handler=ferramenta_calculadora.executar,
        )
    )

    # ----------------------------------------------------------
    # Leitura de arquivo
    # ----------------------------------------------------------

    ferramenta_arquivo = (
        FerramentaLerArquivo()
    )

    registry.registrar(
        ToolContract(
            id="ler_arquivo_codigo",
            nome="Ler arquivo",
            descricao=(
                "Lê o conteúdo de um arquivo "
                "de código ou texto localizado "
                "na pasta projetos/."
            ),
            categoria="arquivos",
            risco="baixo",
            argumentos={
                "nome_arquivo": {
                    "tipo": "string",
                    "obrigatorio": True,
                    "descricao": (
                        "Nome exato do arquivo "
                        "dentro da pasta projetos/."
                    ),
                }
            },
            requer_confirmacao=False,
            handler=ferramenta_arquivo.executar,
        )
    )

    # ----------------------------------------------------------
    # Controle do computador
    # ----------------------------------------------------------

    ferramenta_pc = FerramentaControlarPC(ACOES_PERMITIDAS)

    registry.registrar(
        ToolContract(
            id="controlar_computador",
            nome="Controlar computador",
            descricao=(
                "Executa uma ação autorizada no computador do usuário, como abrir o VS Code, Bloco de Notas, Explorador de Arquivos, Calculadora, navegador ou pastas. "
                f"Ações disponíveis: {', '.join(CHAVES_ACOES[:15])}..."
            ),
            categoria="computador",
            risco="baixo",
            argumentos={
                "acao": {
                    "tipo": "string",
                    "obrigatorio": True,
                    "descricao": (
                        "Nome da ação, programa ou serviço a ser executado ou aberto (ex: 'abrir_youtube', 'youtube', 'vscode', 'discord', 'calculadora', 'bloco_de_notas')."
                    ),
                }
            },
            requer_confirmacao=False,
            handler=ferramenta_pc.executar,
        )
    )

    # ----------------------------------------------------------
    # Terminal
    # ----------------------------------------------------------

    ferramenta_terminal = (
        FerramentaTerminal()
    )

    registry.registrar(
        ToolContract(
            id="terminal_dinamico",
            nome="Terminal dinâmico",
            descricao=(
                "Executa um comando no terminal "
                "do computador."
            ),
            categoria="terminal",
            risco="alto",
            argumentos={
                "comando": {
                    "tipo": "string",
                    "obrigatorio": True,
                    "descricao": (
                        "Comando de terminal "
                        "a ser executado."
                    ),
                }
            },
            requer_confirmacao=True,
            handler=ferramenta_terminal.executar,
        )
    )

    # ----------------------------------------------------------
    # Interação com tela
    # ----------------------------------------------------------

    ferramenta_tela = (
        FerramentaInteragirEcra()
    )

    registry.registrar(
        ToolContract(
            id="interagir_ecra",
            nome="Interagir com a tela",
            descricao=(
                "Permite analisar a tela e "
                "interagir com mouse e teclado."
            ),
            categoria="interface",
            risco="alto",
            argumentos={
                "acao": {
                    "tipo": "string",
                    "obrigatorio": True,
                    "descricao": (
                        "Ação a executar na interface."
                    ),
                    "enum": [
                        "analisar_tela",
                        "escrever",
                        "tecla",
                        "clicar",
                    ],
                },
                "texto": {
                    "tipo": "string",
                    "obrigatorio": False,
                    "descricao": (
                        "Texto a digitar ou "
                        "tecla a pressionar."
                    ),
                },
            },
            requer_confirmacao=True,
            handler=ferramenta_tela.executar,
        )
    )

    # ----------------------------------------------------------
    # Playwright MCP — Navegação
    # ----------------------------------------------------------
    pw_nav = FerramentaPlaywrightNavegar()
    registry.registrar(
        ToolContract(
            id="pw_navegar",
            nome="Navegar no Navegador (Playwright MCP)",
            descricao="Navega para URLs no navegador via Playwright MCP Bridge sem abrir janelas de terminal.",
            categoria="navegador",
            risco="baixo",
            argumentos={
                "url": {"tipo": "string", "obrigatorio": True, "descricao": "Endereço web ou link (HTTP/HTTPS)."}
            },
            requer_confirmacao=False,
            handler=pw_nav.executar,
        )
    )

    # ----------------------------------------------------------
    # Playwright MCP — Snapshot & Acessibilidade
    # ----------------------------------------------------------
    pw_snap = FerramentaPlaywrightSnapshot()
    registry.registrar(
        ToolContract(
            id="pw_snapshot",
            nome="Ler Página Web (Playwright Snapshot)",
            descricao="Lê a árvore de acessibilidade, links, botões e campos de texto da aba ativa.",
            categoria="navegador",
            risco="baixo",
            argumentos={
                "tab_id": {"tipo": "number", "obrigatorio": False, "descricao": "ID opcional da aba."}
            },
            requer_confirmacao=False,
            handler=pw_snap.executar,
        )
    )

    # ----------------------------------------------------------
    # Playwright MCP — Clique e Digitação
    # ----------------------------------------------------------
    pw_click = FerramentaPlaywrightClicar()
    registry.registrar(
        ToolContract(
            id="pw_clicar",
            nome="Clicar em Elemento Web",
            descricao="Clica em links ou botões usando o ID numérico da tela (ex: '1', '2') ou texto/seletor visível.",
            categoria="navegador",
            risco="medio",
            argumentos={
                "seletor": {"tipo": "string", "obrigatorio": True, "descricao": "Número do elemento retornado pelo snapshot (ex: '1', '3') ou texto/seletor."}
            },
            requer_confirmacao=False,
            handler=pw_click.executar,
        )
    )

    pw_type = FerramentaPlaywrightDigitar()
    registry.registrar(
        ToolContract(
            id="pw_digitar",
            nome="Digitar em Campo Web",
            descricao="Digita texto em inputs e formulários no navegador pelo número do campo ou seletor.",
            categoria="navegador",
            risco="medio",
            argumentos={
                "seletor": {"tipo": "string", "obrigatorio": True, "descricao": "Número do campo (ex: '1') ou seletor do campo."},
                "texto": {"tipo": "string", "obrigatorio": True, "descricao": "Texto a preencher."},
                "enviar_enter": {"tipo": "boolean", "obrigatorio": False, "descricao": "Submeter com Enter."}
            },
            requer_confirmacao=False,
            handler=pw_type.executar,
        )
    )

    # ----------------------------------------------------------
    # Playwright MCP — Controle de Mídia
    # ----------------------------------------------------------
    pw_media = FerramentaPlaywrightMidia()
    registry.registrar(
        ToolContract(
            id="pw_midia",
            nome="Controle de Mídia Web (Playwright)",
            descricao="Controla reprodução (play, pause, volume, seek) em vídeos e áudios na página.",
            categoria="navegador",
            risco="baixo",
            argumentos={
                "acao": {"tipo": "string", "obrigatorio": True, "descricao": "Ação: 'play', 'pause', 'volume', 'seek', 'inspect'."},
                "valor": {"tipo": "number", "obrigatorio": False, "descricao": "Valor para volume (0 a 1) ou seek em segundos."}
            },
            requer_confirmacao=False,
            handler=pw_media.executar,
        )
    )

    # ----------------------------------------------------------
    # Abas do Navegador (Extensão Harvey)
    # ----------------------------------------------------------
    pw_tabs = FerramentaPlaywrightAbas()
    registry.registrar(
        ToolContract(
            id="gerenciar_abas",
            nome="Gerenciar Abas do Navegador",
            descricao="Lista títulos e URLs, identifica, ativa, abre e fecha abas na extensão conectada.",
            categoria="navegador",
            risco="baixo",
            argumentos={
                "acao": {"tipo": "string", "obrigatorio": True, "descricao": "Ação: 'listar', 'abrir', 'ativar', 'fechar'."},
                "url": {"tipo": "string", "obrigatorio": False, "descricao": "URL para nova aba."},
                "tab_id": {"tipo": "number", "obrigatorio": False, "descricao": "ID da aba a ativar ou fechar."}
            },
            requer_confirmacao=False,
            handler=pw_tabs.executar,
        )
    )

    # ----------------------------------------------------------
    # Informações Gerais & Matriz de Capacidades
    # ----------------------------------------------------------
    info_gerais = FerramentaInformacoesGerais()
    registry.registrar(
        ToolContract(
            id="obter_capacidades",
            nome="Informações Gerais e Capacidades",
            descricao="Informa a data, hora, fuso horário e as 17 áreas operacionais do ecossistema.",
            categoria="sistema",
            risco="baixo",
            argumentos={},
            requer_confirmacao=False,
            handler=info_gerais.executar,
        )
    )

    # ----------------------------------------------------------
    # Pesquisa Web
    # ----------------------------------------------------------
    web_search = FerramentaPesquisaWeb()
    registry.registrar(
        ToolContract(
            id="pesquisar_web",
            nome="Pesquisa Web",
            descricao="Pesquisa informações atuais, notícias e retorna fontes, links e trechos.",
            categoria="web",
            risco="baixo",
            argumentos={
                "query": {"tipo": "string", "obrigatorio": True, "descricao": "Termo de busca."},
                "idioma": {"tipo": "string", "obrigatorio": False, "descricao": "Idioma da pesquisa."}
            },
            requer_confirmacao=False,
            handler=web_search.executar,
        )
    )

    # ----------------------------------------------------------
    # Previsão do Tempo
    # ----------------------------------------------------------
    clima = FerramentaPrevisaoTempo()
    registry.registrar(
        ToolContract(
            id="previsao_tempo",
            nome="Previsão do Tempo",
            descricao="Consulta temperatura, condição e probabilidade de chuva para hoje ou amanhã.",
            categoria="clima",
            risco="baixo",
            argumentos={
                "cidade": {"tipo": "string", "obrigatorio": False, "descricao": "Cidade desejada."},
                "periodo": {"tipo": "string", "obrigatorio": False, "descricao": "'hoje' ou 'amanha'."}
            },
            requer_confirmacao=False,
            handler=clima.executar,
        )
    )

    # ----------------------------------------------------------
    # Notas
    # ----------------------------------------------------------
    notas = FerramentaGerenciarNotas()
    registry.registrar(
        ToolContract(
            id="gerenciar_notas",
            nome="Gerenciar Notas",
            descricao="Salva notas por voz ou texto, pesquisa, lista e consulta a última nota.",
            categoria="notas",
            risco="baixo",
            argumentos={
                "acao": {"tipo": "string", "obrigatorio": True, "descricao": "'salvar', 'listar', 'ultima', 'pesquisar'."},
                "texto": {"tipo": "string", "obrigatorio": False, "descricao": "Texto da nota."},
                "query": {"tipo": "string", "obrigatorio": False, "descricao": "Termo de busca."}
            },
            requer_confirmacao=False,
            handler=notas.executar,
        )
    )

    # ----------------------------------------------------------
    # Objetivos da Conversa
    # ----------------------------------------------------------
    objetivos = FerramentaGerenciarObjetivo()
    registry.registrar(
        ToolContract(
            id="gerenciar_objetivo",
            nome="Objetivos da Conversa",
            descricao="Registra meta da conversa, condições de conclusão, consulta progresso ou finaliza.",
            categoria="objetivos",
            risco="baixo",
            argumentos={
                "acao": {"tipo": "string", "obrigatorio": True, "descricao": "'registrar', 'consultar', 'concluir', 'bloquear', 'cancelar'."},
                "descricao": {"tipo": "string", "obrigatorio": False, "descricao": "Descrição do objetivo."},
                "condicoes": {"tipo": "string", "obrigatorio": False, "descricao": "Critérios de conclusão."}
            },
            requer_confirmacao=False,
            handler=objetivos.executar,
        )
    )

    # ----------------------------------------------------------
    # Gerenciamento de Janelas e UI do Windows (MCP Nativo)
    # ----------------------------------------------------------
    janelas_win = FerramentaGerenciarJanelasWindows()
    registry.registrar(
        ToolContract(
            id="gerenciar_janelas_windows",
            nome="Gerenciamento de Janelas e Apps (Windows MCP)",
            descricao="Lista programas abertos, foca janelas, minimiza, fecha, inspeciona botões e envia texto.",
            categoria="computador",
            risco="medio",
            argumentos={
                "acao": {"tipo": "string", "obrigatorio": True, "descricao": "'listar', 'focar', 'fechar', 'minimizar', 'maximizar', 'digitar', 'inspecionar'."},
                "alvo": {"tipo": "string", "obrigatorio": False, "descricao": "Título da janela, processo (ex: 'notepad', 'vscode') ou PID."},
                "texto": {"tipo": "string", "obrigatorio": False, "descricao": "Texto a digitar na janela se a ação for 'digitar'."}
            },
            requer_confirmacao=False,
            handler=janelas_win.executar,
        )
    )
    # ----------------------------------------------------------
    # Ambientes de Trabalho (Macro Inteligente)
    # ----------------------------------------------------------
    amb_trab = FerramentaAmbienteTrabalho()
    registry.registrar(
        ToolContract(
            id="preparar_ambiente_trabalho",
            nome="Preparar Ambiente de Trabalho",
            descricao="Prepara a estação de trabalho para modos específicos: 'dev' (VS Code + Chrome localhost), 'foco' (Lo-Fi + minimiza distrações), 'estudo'.",
            categoria="computador",
            risco="baixo",
            argumentos={
                "perfil": {"tipo": "string", "obrigatorio": True, "descricao": "Perfil desejado: 'dev', 'foco', 'estudo'."}
            },
            requer_confirmacao=False,
            handler=amb_trab.executar,
        )
    )

    # ----------------------------------------------------------
    # Curadoria e Organização de Arquivos (Downloads)
    # ----------------------------------------------------------
    org_arq = FerramentaOrganizarArquivos()
    registry.registrar(
        ToolContract(
            id="organizar_downloads",
            nome="Organizar Pasta Downloads",
            descricao="Varre a pasta Downloads e move arquivos soltos para subpastas categorizadas (PDFs, Documentos, Instaladores, Imagens) com segurança.",
            categoria="arquivos",
            risco="baixo",
            argumentos={},
            requer_confirmacao=False,
            handler=org_arq.executar,
        )
    )

    return registry