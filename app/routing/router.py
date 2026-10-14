from app.routing.router_contract import RouterContract

ROTAS_VALIDAS = {
    "simples",
    "codigo",
    "complexo",
}


class Router:
    """
    Roteador central do Agent Core.

    O Router decide qual fluxo (rota) deve processar
    uma solicitação com base na intenção do texto.
    A seleção do modelo deixou de ser responsabilidade
    deste componente.
    """

    def __init__(self):
        # O construtor está agora limpo, pois o Router 
        # não precisa de conhecer os modelos disponíveis.
        pass

    # ==========================================================
    # API PRINCIPAL
    # ==========================================================

    def rotear(
        self,
        texto: str,
        skill_id: str | None = None,
    ) -> RouterContract:

        texto_normalizado = self._normalizar(texto)

        if not texto_normalizado:
            return self._criar_resultado(
                rota="simples",
                skill_id=skill_id,
                motivo="Mensagem vazia ou sem conteúdo.",
                confianca=1.0,
            )

        rota, confianca, motivo = self._determinar_rota(texto_normalizado)

        return self._criar_resultado(
            rota=rota,
            skill_id=skill_id,
            motivo=motivo,
            confianca=confianca,
        )

    # ==========================================================
    # NORMALIZAÇÃO
    # ==========================================================

    def _normalizar(self, texto: str) -> str:
        if not isinstance(texto, str):
            return ""

        return texto.strip().lower()

    # ==========================================================
    # DETERMINAÇÃO DA ROTA
    # ==========================================================

    def _determinar_rota(self, texto: str) -> tuple[str, float, str]:
        if self._parece_codigo(texto):
            return (
                "codigo",
                0.9,
                "A solicitação aparenta envolver programação.",
            )

        if self._parece_interacao_maquina(texto):
            return (
                "complexo",
                0.95,
                "A solicitação envolve interação ou controle da máquina/sistema.",
            )

        if self._parece_complexo(texto):
            return (
                "complexo",
                0.7,
                "A solicitação aparenta exigir processamento mais complexo.",
            )

        return (
            "simples",
            0.8,
            "Solicitação geral sem indicação de complexidade elevada.",
        )

    # ==========================================================
    # RESULTADO
    # ==========================================================

    def _criar_resultado(
        self,
        rota: str,
        skill_id: str | None,
        motivo: str,
        confianca: float,
    ) -> RouterContract:

        if rota not in ROTAS_VALIDAS:
            raise ValueError(f"Rota inválida: '{rota}'.")

        metadata = {
            "router_version": "4.0",
            "deterministico": True,
            # Metadados de modelo foram removidos daqui
        }

        return RouterContract(
            rota=rota,
            modelo=None, # O modelo será preenchido pelo Model Selector
            skill_id=skill_id,
            motivo=motivo,
            confianca=confianca,
            metadata=metadata,
        )

    # ==========================================================
    # DETECÇÃO DE CÓDIGO
    # ==========================================================

    def _parece_codigo(self, texto: str) -> bool:
        indicadores = (
            "python", "java", "javascript", "typescript", "kotlin",
            "php", "c++", "c#", "html", "css", "sql", "debug", "debugar",
            "erro no código", "erro no codigo", "stack trace", "exception",
            "traceback", "função", "funcao", "classe", "método", "metodo",
            "api", "endpoint", "fastapi", "android", "gradle", "docker", "git",
        )

        return any(indicador in texto for indicador in indicadores)

    # ==========================================================
    # DETECÇÃO DE COMPLEXIDADE
    # ==========================================================

    def _parece_complexo(self, texto: str) -> bool:
        indicadores = (
            "arquitetura", "refatore todo", "refatorar todo",
            "analise profundamente", "analisar profundamente",
            "projeto completo", "planeje uma arquitetura",
            "planejar uma arquitetura", "compare detalhadamente",
            "investigue", "pesquisa completa", "multi etapa", "multi-etapa",
        )

        return any(indicador in texto for indicador in indicadores)

    # ==========================================================
    # DETECÇÃO DE INTERAÇÃO COM A MÁQUINA / SISTEMA
    # ==========================================================

    def _parece_interacao_maquina(self, texto: str) -> bool:
        """
        Identifica se a mensagem solicita controle do computador,
        sistema operacional, navegador, multimídia ou ferramentas do hub.
        """
        indicadores = (
            # Ações diretas no SO e janelas
            "abra", "abrir", "inicie", "iniciar", "execute", "executar", "rode", "rodar",
            "feche", "fechar", "encerre", "encerrar", "mate", "matar",
            "bloqueie", "bloquear", "suspenda", "suspender", "desligue", "desligar", "reinicie", "reiniciar",
            "computador", "pc", "windows", "sistema", "máquina", "maquina", "desktop", "tela", "screenshot", "print",
            "programa", "programas", "aplicativo", "aplicativos", "app", "apps",
            # Aplicativos conhecidos
            "calculadora", "calc", "vscode", "vs code", "bloco de notas", "notepad", "explorer", "explorador", "pasta", "pastas", "arquivos",
            "terminal", "cmd", "prompt", "powershell", "paint", "mspaint", "gerenciador de tarefas", "task manager", "taskmgr",
            "downloads", "documentos", "imagens", "lixeira",
            # Navegador e Web / Playwright
            "chrome", "edge", "navegador", "browser", "site", "web", "link", "url", "página", "pagina",
            "aba", "abas", "guia", "guias", "tab", "tabs",
            "youtube", "spotify", "whatsapp", "google", "discord",
            "clique", "clicar", "selecione", "selecionar", "digite", "digitar", "snapshot", "leia a página", "leia a pagina",
            "reproduzir", "reproduza", "tocar", "toque", "ouvir", "ouça", "pause", "pausar", "mídia", "midia", "volume", "vídeo", "video", "música", "musica",
            # Hub operacional e ferramentas
            "pesquise", "pesquisar", "busca", "buscar", "notícia", "noticia", "notícias",
            "previsão", "previsao", "clima", "tempo", "temperatura", "chuva",
            "nota", "notas", "anote", "anotar", "lembrete", "objetivo", "meta",
            "hora atual", "que horas", "horário", "horario", "data de hoje", "dia de hoje",
            "calcule", "calcular", "quanto é", "ler arquivo", "leia arquivo", "salvar arquivo",
            "mouse", "teclado", "atalho", "atalhos", "arraste", "arrastar", "rolar", "duplo clique",
        )

        return any(indicador in texto for indicador in indicadores)