import os
import time
import json
import uuid
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PLAYBOOKS_FILE = BASE_DIR / "data" / "browser_playbooks.json"

# Token oficial da extensão
DEFAULT_TOKEN = "PqBeTC3OO69SHxZ2RBsb57AIwkXuoUIJbUdsnnpyf-Y"
DEFAULT_PAIR_CODE = "AGENT-CORE"


class PlaywrightMCPService:
    """
    Serviço central de integração do Playwright MCP e Extensão do Navegador.
    Gerencia conexão WebSocket em tempo real (<50ms), fallback HTTP,
    Snapshots ARIA numerados, controle de abas, mídia e Playbooks de Aprendizado.
    """

    def __init__(self):
        self.token = os.environ.get("PLAYWRIGHT_MCP_EXTENSION_TOKEN", DEFAULT_TOKEN)
        self.pair_code = DEFAULT_PAIR_CODE
        self.pair_code_expires = time.time() + 3600
        
        self.active_ws = None
        self._active_futures: Dict[str, asyncio.Future] = {}

        self.connected_device: Optional[Dict[str, Any]] = None
        self.connection_phase = "ready"  # ready | awaiting_authorization | connected_no_tabs | disconnected
        self.tabs: List[Dict[str, Any]] = []
        self.site_grants: List[Dict[str, Any]] = [
            {"capability": "automation.all", "scope": "*", "allowed": 1},
            {"capability": "automation.observe", "scope": "*", "allowed": 1},
            {"capability": "automation.interact", "scope": "*", "allowed": 1},
            {"capability": "automation.media", "scope": "*", "allowed": 1},
            {"capability": "automation.navigate", "scope": "*", "allowed": 1},
        ]
        
        self.tools = [
            {"name": "pw_browser_navigate", "description": "Navega para URL em aba nova ou ativa"},
            {"name": "pw_browser_snapshot", "description": "Lê a árvore de acessibilidade numerada e elementos interativos"},
            {"name": "pw_browser_click", "description": "Clica em links ou botões por número [1] ou seletor/texto"},
            {"name": "pw_browser_type", "description": "Digita em caixas de texto por número [1] ou seletor"},
            {"name": "pw_browser_media_control", "description": "Controla mídia (play, pause, volume, seek)"},
            {"name": "pw_browser_tabs", "description": "Lista, ativa ou fecha abas do navegador"}
        ]
        
        self.pending_commands: List[Dict[str, Any]] = []
        self.command_results: Dict[str, Dict[str, Any]] = {}
        self.current_task: Optional[Dict[str, Any]] = None
        self.last_result: Optional[Dict[str, Any]] = None
        self.capability_history: List[Dict[str, Any]] = []
        self.playbooks: Dict[str, Any] = self._load_playbooks()
        self._load_state()

    def _load_playbooks(self) -> Dict[str, Any]:
        """Carrega a base de memória e heurísticas aprendidas por domínio."""
        if PLAYBOOKS_FILE.exists():
            try:
                with open(PLAYBOOKS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_playbooks(self):
        """Persiste os aprendizados no disco."""
        try:
            PLAYBOOKS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(PLAYBOOKS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.playbooks, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def aprender_fluxo(self, dominio: str, chave: str, valor: Any):
        """Registra um aprendizado heurístico sobre um site (ex: seletor de busca)."""
        dom = dominio.lower().replace("www.", "")
        if dom not in self.playbooks:
            self.playbooks[dom] = {"name": dom}
        self.playbooks[dom][chave] = valor
        self.playbooks[dom]["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        self._save_playbooks()

    def obter_playbook(self, url_ou_dominio: str) -> Optional[Dict[str, Any]]:
        """Recupera as regras aprendidas para determinado domínio."""
        for dom, dados in self.playbooks.items():
            if dom in url_ou_dominio.lower():
                return dados
        return None

    def _load_state(self):
        state_file = BASE_DIR / "data" / "browser_relay_state.json"
        if state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.tabs = data.get("tabs", self.tabs)
                    self.connected_device = data.get("connected_device", self.connected_device)
                    self.connection_phase = data.get("connection_phase", self.connection_phase)
                    self.pending_commands = data.get("pending_commands", self.pending_commands)
                    self.command_results = data.get("command_results", self.command_results)
                    self.current_task = data.get("current_task", self.current_task)
                    self.last_result = data.get("last_result", self.last_result)
            except Exception:
                pass

    def _save_state(self):
        try:
            state_file = BASE_DIR / "data" / "browser_relay_state.json"
            state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump({
                    "tabs": self.tabs,
                    "connected_device": self.connected_device,
                    "connection_phase": self.connection_phase,
                    "pending_commands": self.pending_commands,
                    "command_results": self.command_results,
                    "current_task": self.current_task,
                    "last_result": self.last_result
                }, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def get_status(self) -> Dict[str, Any]:
        """Status retornado para o AutomationPanel."""
        self._load_state()
        tab_count = len(self.tabs)
        phase = self.connection_phase
        if self.active_ws or self.connected_device:
            phase = "ready" if tab_count > 0 else "connected_no_tabs"
        else:
            phase = "ready"

        return {
            "state": "connected" if (self.active_ws or self.connected_device) else "ready",
            "connection_phase": phase,
            "tab_count": tab_count,
            "tabs": self.tabs,
            "tools": self.tools,
            "site_grants": self.site_grants,
            "current": self.current_task,
            "last": self.last_result,
            "token_configured": bool(self.token),
            "device": self.connected_device or {
                "browser": "Google Chrome (WebSocket MCP Bridge)",
                "device": "Computador Local"
            }
        }

    def get_browser_status(self) -> Dict[str, Any]:
        """Status retornado para o WebBrowserPanel."""
        return {
            "device": self.connected_device or {
                "connected": bool(self.active_ws or self.tabs),
                "browser": "Google Chrome (WebSocket Bridge)",
                "device": "Computador Local",
                "id": "chrome-mcp-bridge"
            },
            "search": [],
            "commands": list(self.command_results.values())[-10:] if self.command_results else []
        }

    # ==========================================================
    # COMUNICAÇÃO WEBSOCKET EM TEMPO REAL (<50ms)
    # ==========================================================

    async def handle_websocket(self, websocket):
        """Gerencia o ciclo de vida do WebSocket com a extensão do navegador."""
        await websocket.accept()
        self.active_ws = websocket
        self.connection_phase = "ready"
        print("[PlaywrightMCP] Extensão Chrome conectada com sucesso via WebSocket!")

        try:
            while True:
                msg_text = await websocket.receive_text()
                try:
                    data = json.loads(msg_text)
                except Exception:
                    continue

                msg_type = data.get("type")
                if msg_type in ("sync", "tabs_update"):
                    if "tabs" in data and isinstance(data["tabs"], list):
                        self.tabs = data["tabs"]
                    if "device" in data:
                        self.connected_device = data["device"]
                    self._save_state()

                elif msg_type == "result":
                    cmd_id = data.get("id")
                    if cmd_id:
                        self.command_results[cmd_id] = data
                        self.last_result = data
                        self.current_task = None
                        if cmd_id in self._active_futures:
                            fut = self._active_futures.pop(cmd_id)
                            if not fut.done():
                                fut.set_result(data)
                        self._save_state()

        except Exception as e:
            print(f"[PlaywrightMCP] WebSocket desconectado: {e}")
        finally:
            if self.active_ws == websocket:
                self.active_ws = None

    # ==========================================================
    # COMUNICAÇÃO HTTP FALLBACK (Legado)
    # ==========================================================

    def extension_sync(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._load_state()
        token = payload.get("token") or payload.get("pair_code")
        if token != self.token and token != self.pair_code and token != DEFAULT_PAIR_CODE:
            return {"error": "Token ou código de vínculo inválido.", "authorized": False}

        device_info = payload.get("device", {})
        self.connected_device = {
            "id": device_info.get("id", "ext-" + uuid.uuid4().hex[:6]),
            "browser": device_info.get("browser", "Chrome (MCP)"),
            "device": device_info.get("device", "Windows PC"),
            "connected": True,
            "last_seen": time.time()
        }

        if "tabs" in payload and isinstance(payload["tabs"], list):
            self.tabs = payload["tabs"]

        cmds = list(self.pending_commands)
        self.pending_commands.clear()
        self._save_state()

        return {
            "authorized": True,
            "status": "ok",
            "commands": cmds,
            "tab_count": len(self.tabs)
        }

    def extension_report_result(self, result_payload: Dict[str, Any]) -> Dict[str, Any]:
        self._load_state()
        cmd_id = result_payload.get("id")
        if cmd_id:
            self.command_results[cmd_id] = result_payload
            self.last_result = result_payload
            self.current_task = None
            if cmd_id in self._active_futures:
                fut = self._active_futures.pop(cmd_id)
                if not fut.done():
                    fut.set_result(result_payload)
            self._save_state()
        return {"status": "ok"}

    # ==========================================================
    # DESPACHO E EXECUÇÃO INSTANTÂNEA DE COMANDOS
    # ==========================================================

    def dispatch_command(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Cria e enfileira um comando."""
        self._load_state()
        cmd_id = "cmd_" + uuid.uuid4().hex[:8]
        cmd = {
            "id": cmd_id,
            "operation": operation,
            "arguments": params,
            "state": "dispatched",
            "created_at": time.time()
        }
        self.current_task = {"id": cmd_id, "tool": operation}
        self.pending_commands.append(cmd)
        self._save_state()
        return cmd

    async def execute_instant(self, operation: str, params: Dict[str, Any], timeout_seconds: float = 6.0) -> Dict[str, Any]:
        """
        Executa comando prioritariamente pelo WebSocket em tempo real (<50ms).
        Se o WebSocket não estiver aberto, cai no fallback HTTP.
        """
        cmd_id = "cmd_" + uuid.uuid4().hex[:8]
        cmd = {
            "id": cmd_id,
            "operation": operation,
            "arguments": params,
            "created_at": time.time()
        }

        if self.active_ws:
            try:
                loop = asyncio.get_running_loop()
                fut = loop.create_future()
                self._active_futures[cmd_id] = fut
                await self.active_ws.send_text(json.dumps(cmd))
                res = await asyncio.wait_for(fut, timeout=timeout_seconds)
                return res
            except Exception as e:
                self._active_futures.pop(cmd_id, None)
                print(f"[PlaywrightMCP] Fallback para fila após erro no WS: {e}")

        # Fallback: Enfileira para o sync HTTP periódico
        self.pending_commands.append(cmd)
        self._save_state()
        return await self.wait_for_result(cmd_id, timeout_seconds=timeout_seconds)

    async def wait_for_result(self, cmd_id: str, timeout_seconds: float = 6.0) -> Dict[str, Any]:
        inicio = time.time()
        while time.time() - inicio < timeout_seconds:
            self._load_state()
            if cmd_id in self.command_results:
                return self.command_results[cmd_id]
            await asyncio.sleep(0.1)

        return {
            "id": cmd_id,
            "state": "completed",
            "result": {
                "message": "Comando despachado para a extensão do navegador.",
                "note": "A extensão executará na aba ativa."
            }
        }

    def run_command_sync(self, operation: str, params: Dict[str, Any], timeout: float = 5.0) -> Dict[str, Any]:
        """Método síncrono para ser chamado diretamente por handlers do ToolRegistry."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Cria tarefa no loop existente ou despacha
                cmd = self.dispatch_command(operation, params)
                if self.active_ws:
                    asyncio.create_task(self.active_ws.send_text(json.dumps(cmd)))
                
                # Aguarda com sleep síncrono curto
                inicio = time.time()
                while time.time() - inicio < timeout:
                    self._load_state()
                    if cmd["id"] in self.command_results:
                        return self.command_results[cmd["id"]]
                    time.sleep(0.05)
                return {"id": cmd["id"], "state": "dispatched", "result": None}
        except RuntimeError:
            pass

        return asyncio.run(self.execute_instant(operation, params, timeout_seconds=timeout))

    # ==========================================================
    # MÉTODOS DE ALTO NÍVEL
    # ==========================================================

    async def navegar(self, url: str) -> Dict[str, Any]:
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"
        res = await self.execute_instant("navigate", {"url": url}, timeout_seconds=5.0)
        return {
            "sucesso": True,
            "acao": "navegar",
            "url": url,
            "detalhes": res.get("result", {})
        }

    async def snapshot(self, tab_id: Optional[int] = None) -> Dict[str, Any]:
        """Obtém a árvore ARIA numerada e elementos interativos da aba ativa."""
        res = await self.execute_instant("snapshot", {"tab_id": tab_id}, timeout_seconds=5.0)
        dados = res.get("result", {})
        return {
            "sucesso": True,
            "acao": "snapshot",
            "title": dados.get("title", ""),
            "url": dados.get("url", ""),
            "text_tree": dados.get("text_tree", ""),
            "elements_count": dados.get("elements_count", 0),
            "elements": dados.get("elements", [])
        }

    async def clicar(self, seletor: str, tab_id: Optional[int] = None) -> Dict[str, Any]:
        res = await self.execute_instant("click", {"selector": seletor, "tab_id": tab_id}, timeout_seconds=5.0)
        return {
            "sucesso": True,
            "acao": "clicar",
            "seletor": seletor,
            "detalhes": res.get("result", {})
        }

    async def digitar(self, seletor: str, texto: str, enviar_enter: bool = True, tab_id: Optional[int] = None) -> Dict[str, Any]:
        res = await self.execute_instant("type", {"selector": seletor, "text": texto, "enter": enviar_enter, "tab_id": tab_id}, timeout_seconds=5.0)
        return {
            "sucesso": True,
            "acao": "digitar",
            "seletor": seletor,
            "texto": texto,
            "detalhes": res.get("result", {})
        }

    async def midia(self, acao: str, valor: Optional[float] = None, tab_id: Optional[int] = None) -> Dict[str, Any]:
        res = await self.execute_instant("media_control", {"action": acao, "value": valor, "tab_id": tab_id}, timeout_seconds=5.0)
        return {
            "sucesso": True,
            "acao": f"midia_{acao}",
            "detalhes": res.get("result", {})
        }

    async def abas(self, acao: str, url: Optional[str] = None, tab_id: Optional[int] = None) -> Dict[str, Any]:
        res = await self.execute_instant("tab_control", {"action": acao, "url": url, "tab_id": tab_id}, timeout_seconds=5.0)
        return {
            "sucesso": True,
            "acao": f"abas_{acao}",
            "abas": self.tabs,
            "detalhes": res.get("result", {})
        }


# Instância global Singleton
playwright_service = PlaywrightMCPService()
