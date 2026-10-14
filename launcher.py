import os
import sys
import json
import subprocess
import socket
import psutil
import urllib.request
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Agent Core Launcher")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Definição Global dos Diretórios
BASE_DIR = Path(__file__).resolve().parent
CAMINHO_PROJETO = r"C:\Projetos\agent-core-main"
CAMINHO_DADOS = BASE_DIR / "data"
CAMINHO_COMANDOS = BASE_DIR / "comandos_pc.json"
CAMINHO_SKILLS = BASE_DIR / "skills"
CAMINHO_UPLOADS = BASE_DIR / "uploads"
CAMINHO_MEMORY_DB = BASE_DIR / "memory.db"
CAMINHO_DATA_MEMORY = BASE_DIR / "data" / "memory"

# Garante que as pastas essenciais existam
CAMINHO_DADOS.mkdir(exist_ok=True)
CAMINHO_SKILLS.mkdir(exist_ok=True)
CAMINHO_UPLOADS.mkdir(exist_ok=True)
CAMINHO_DATA_MEMORY.mkdir(parents=True, exist_ok=True)

# Ficheiro de configuração global
ARQUIVO_CONFIG = CAMINHO_DADOS / "config.json"

CONFIG_PADRAO = {
    "modelo_ativo": "llama3.2:1b",
    "url_servidor": "http://127.0.0.1:11434",
    "temperatura": 0.7,
    "contexto_maximo": 4096,
    "prompt_sistema": "És um assistente de IA lógico e conciso.",
    "streaming": True,
    "gpu_layers": 35,
    "cpu_threads": 4,
    "memoria_ttl": 10
}

def is_port_in_use(port: int) -> bool:
    """Verifica diretamente no hardware se a porta está ocupada."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def get_local_ip():
    """Descobre o IP da máquina na rede local para acesso via telemóvel."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def get_dir_size(path: Path) -> str:
    """Calcula o peso de uma pasta inteira."""
    if not path.exists(): return "0 B"
    try:
        if path.is_file():
            total = path.stat().st_size
        else:
            total = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
        if total < 1024: return f"{total} B"
        elif total < 1024**2: return f"{total/1024:.1f} KB"
        else: return f"{total/(1024**2):.1f} MB"
    except Exception:
        return "0 B"

def registrar_log(mensagem: str):
    """Escreve uma linha formatada no server_log.txt de forma segura."""
    try:
        log_path = BASE_DIR / "server_log.txt"
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {mensagem}\n")
    except Exception:
        pass

@app.get("/api/system/status")
def status_agente():
    """Retorna se o motor principal está ligado."""
    return {"online": is_port_in_use(8000)}

@app.post("/api/system/start")
def iniciar_agente():
    """Liga o Agent Core com saída não-bufferizada gravada em tempo real em server_log.txt."""
    if is_port_in_use(8000):
        return {"status": "ja_em_execucao", "mensagem": "O Agente já está online."}
    
    log_file_path = BASE_DIR / "server_log.txt"
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(f"\n======================================================\n")
            f.write(f"[{timestamp}] [SISTEMA] Motor Agent Core acionado na porta 8000...\n")
            f.write(f"======================================================\n")
    except Exception:
        pass

    try:
        log_out = open(log_file_path, "a", encoding="utf-8", buffering=1)
        subprocess.Popen(
            [sys.executable, "-u", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--env-file", ".env"],
            cwd=CAMINHO_PROJETO,
            stdout=log_out,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except Exception as e:
        registrar_log(f"[ERRO] Falha ao iniciar Agent Core: {e}")
        return {"status": "erro", "mensagem": f"Falha ao iniciar: {e}"}

    return {"status": "iniciado", "mensagem": "Motor de IA acionado."}

@app.post("/api/system/stop")
def parar_agente():
    """Derruba a IA caçando e matando o processo da porta 8000."""
    if not is_port_in_use(8000):
        return {"status": "ja_parado", "mensagem": "O Agente já estava offline."}
        
    comando_ps = "(Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue).OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force }"
    subprocess.run(["powershell", "-Command", comando_ps], capture_output=True)
    
    registrar_log("[SISTEMA] Motor Agent Core desligado.")
    return {"status": "parado", "mensagem": "Motor de IA desligado com sucesso."}

@app.get("/api/system/monitor")
def monitoramento():
    """Lê o estado do Hardware e os últimos Logs do servidor."""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory()
    
    ollama_ram_mb = 0
    for proc in psutil.process_iter(['name', 'memory_info']):
        try:
            if proc.info['name'] and 'ollama' in proc.info['name'].lower():
                ollama_ram_mb += proc.info['memory_info'].rss / (1024 * 1024)
        except (psutil.NoSuchProcess, psutil.AccessDenied): 
            pass

    log_path = BASE_DIR / "server_log.txt"
    logs = ""
    if log_path.exists():
        try:
            conteudo = log_path.read_text(encoding="utf-8", errors="replace").replace('\x00', '')
            linhas = [l for l in conteudo.splitlines(True) if l.strip()]
            logs = "".join(linhas[-120:])
        except Exception as e:
            logs = f"Erro ao ler logs: {e}\n"

    # Se server_log estiver vazio, fallback amigável ou launcher_log
    if not logs.strip():
        launcher_log_path = BASE_DIR / "launcher_log.txt"
        if launcher_log_path.exists():
            try:
                l_linhas = launcher_log_path.read_text(encoding="utf-8", errors="replace").splitlines(True)
                if l_linhas:
                    logs = "[PAINEL LAUNCHER - PORTA 8001]\n" + "".join(l_linhas[-60:])
            except Exception:
                pass

        if not logs.strip():
            online = is_port_in_use(8000)
            status_txt = "ONLINE (Porta 8000)" if online else "OFFLINE"
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logs = f"[{timestamp}] Motor Agent Core: {status_txt}\nAguardando novas requisições e eventos do sistema...\n"
        
    return {
        "cpu": cpu_percent,
        "ram_percent": ram.percent,
        "ram_used_gb": round(ram.used / (1024**3), 1),
        "ram_total_gb": round(ram.total / (1024**3), 1),
        "ollama_ram_mb": round(ollama_ram_mb, 1),
        "logs": logs,
        "log_size": get_dir_size(log_path) if log_path.exists() else "0 B",
        "engine_online": is_port_in_use(8000)
    }

@app.get("/api/system/advanced")
def sistema_avancado():
    """Retorna telemetria avançada de rede, armazenamento e configuração."""
    ip = get_local_ip()
    env_path = BASE_DIR / ".env"
    log_path = BASE_DIR / "server_log.txt"

    dirs = [
        {"id": "data", "nome": "Data (Histórico)", "caminho": str(CAMINHO_DADOS), "tamanho": get_dir_size(CAMINHO_DADOS)},
        {"id": "skills", "nome": "Skills (Prompts)", "caminho": str(BASE_DIR / "skills"), "tamanho": get_dir_size(BASE_DIR / "skills")},
        {"id": "tools", "nome": "Tools (Funções)", "caminho": str(BASE_DIR / "tools"), "tamanho": get_dir_size(BASE_DIR / "tools")},
        {"id": "projetos", "nome": "Projetos (Sandbox)", "caminho": str(BASE_DIR / "projetos"), "tamanho": get_dir_size(BASE_DIR / "projetos")}
    ]

    return {
        "network": {
            "ip_local": ip,
            "porta_api": 8001,
            "porta_motor": 8000
        },
        "storage": dirs,
        "config": {
            "env_exists": env_path.exists(),
            "log_size": get_dir_size(log_path) if log_path.exists() else "0 B"
        }
    }

@app.post("/api/system/clear-logs")
def limpar_logs():
    """Esvazia o ficheiro de logs do servidor."""
    log_path = BASE_DIR / "server_log.txt"
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_path.write_text(f"[{timestamp}] [SISTEMA] Logs reinicializados pelo usuário.\n", encoding="utf-8")
    except Exception:
        pass
    return {"status": "ok"}

@app.get("/api/config")
def ler_configuracoes():
    """Lê as definições do agente do ficheiro local."""
    if not ARQUIVO_CONFIG.exists():
        return CONFIG_PADRAO
    try:
        with ARQUIVO_CONFIG.open("r", encoding="utf-8") as f:
            dados_salvos = json.load(f)
            # Funde os padrões com os guardados para evitar chaves em falta
            return {**CONFIG_PADRAO, **dados_salvos}
    except Exception:
        return CONFIG_PADRAO

@app.post("/api/config")
async def salvar_configuracoes(request: dict):
    """Guarda as novas definições no disco."""
    try:
        with ARQUIVO_CONFIG.open("w", encoding="utf-8") as f:
            json.dump(request, f, indent=2, ensure_ascii=False)
        modelo = request.get('modelo_ativo', '')
        registrar_log(f"[CONFIG] Definições salvas com sucesso (Modelo: {modelo}).")
        return {"status": "ok", "mensagem": "Configurações guardadas com sucesso."}
    except Exception as e:
        registrar_log(f"[ERRO-CONFIG] Falha ao guardar definições: {e}")
        return {"status": "erro", "mensagem": str(e)}

@app.get("/api/analytics")
def obter_analytics_web():
    """Lê os chats locais e calcula o uso de tokens, com estimativa para versões antigas."""
    if not CAMINHO_DADOS.exists():
        return {"dados": [], "total_prompt": 0, "total_resposta": 0}

    dados = []
    total_prompt = 0
    total_resp = 0
    
    for path in CAMINHO_DADOS.glob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as f:
                chat = json.load(f)
                
            chat_prompt = 0
            chat_resp = 0
            
            mensagens = chat.get("mensagens") or chat.get("messages") or []
            if not mensagens:
                continue
                
            titulo = chat.get("titulo") or chat.get("title") or ""
            if not titulo:
                for msg in mensagens:
                    if msg.get("role") == "user":
                        titulo = str(msg.get("content", ""))[:30] + "..."
                        break
                if not titulo:
                    titulo = path.stem

            for msg in mensagens:
                role = msg.get("role")
                content = msg.get("content", "")
                meta = msg.get("meta") or msg.get("metadata") or {}
                
                p = meta.get("tokens_prompt", 0) or meta.get("prompt_tokens", 0) or meta.get("tokens_input", 0)
                r = meta.get("tokens_resposta", 0) or meta.get("completion_tokens", 0) or meta.get("tokens_output", 0)
                
                if p == 0 and r == 0 and "total_tokens" in meta:
                    total_t = meta.get("total_tokens", 0)
                    p = int(total_t * 0.5)
                    r = total_t - p

                if p == 0 and r == 0 and content:
                    estimativa = max(1, len(str(content)) // 4)
                    if role == "user":
                        p = estimativa
                    elif role == "assistant":
                        r = estimativa

                chat_prompt += p
                chat_resp += r
            
            if chat_prompt > 0 or chat_resp > 0:
                dados.append({
                    "Chat": titulo,
                    "Tokens_Prompt": chat_prompt,
                    "Tokens_Resposta": chat_resp,
                    "Total": chat_prompt + chat_resp
                })
                total_prompt += chat_prompt
                total_resp += chat_resp
        except Exception:
            continue
            
    dados.sort(key=lambda x: x["Total"], reverse=True)
            
    return {
        "dados": dados, 
        "total_prompt": total_prompt, 
        "total_resposta": total_resp
    }

@app.get("/api/system/models")
def listar_modelos():
    """Consulta a API local do Ollama para listar os modelos instalados na máquina."""
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            modelos = [m["name"] for m in data.get("models", [])]
            return {"modelos": modelos}
    except Exception:
        # Se o Ollama estiver desligado, devolve um fallback vazio
        return {"modelos": []}

@app.get("/api/chats")
def listar_chats_launcher():
    """Retorna a lista de conversas salvas no disco (mesmo com o motor IA offline)."""
    chats = []
    if CAMINHO_DADOS.exists():
        for p in CAMINHO_DADOS.glob("*.json"):
            try:
                with p.open("r", encoding="utf-8") as f:
                    dados = json.load(f)
                msgs = dados.get("messages") or dados.get("mensagens") or []
                titulo = dados.get("titulo") or dados.get("title")
                if not titulo and msgs and msgs[0].get("content"):
                    c_txt = str(msgs[0]["content"]).strip().replace("\n", " ")
                    titulo = c_txt[:40] + ("..." if len(c_txt) > 40 else "")
                chats.append({
                    "id": p.stem,
                    "titulo": titulo or f"Conversa {p.stem[:8]}",
                    "atualizado_em": p.stat().st_mtime,
                    "message_count": len(msgs)
                })
            except Exception:
                pass
    chats.sort(key=lambda x: x["atualizado_em"], reverse=True)
    return chats

@app.get("/api/chats/{chat_id}")
def obter_chat_launcher(chat_id: str):
    """Retorna o histórico de uma conversa específica."""
    clean_id = chat_id[:-5] if chat_id.endswith(".json") else chat_id
    p = CAMINHO_DADOS / f"{clean_id}.json"
    if p.exists():
        try:
            with p.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    if CAMINHO_DADOS.exists():
        for fpath in CAMINHO_DADOS.glob("*.json"):
            try:
                with fpath.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("id") == chat_id or data.get("id") == clean_id:
                    return data
            except Exception:
                pass
    return {"id": chat_id, "messages": []}

@app.post("/api/chats/{chat_id}/rename")
def renomear_chat_launcher(chat_id: str, payload: dict):
    """Atualiza o título de uma conversa."""
    clean_id = chat_id[:-5] if chat_id.endswith(".json") else chat_id
    title = payload.get("title") or payload.get("titulo") or "Conversa"
    p = CAMINHO_DADOS / f"{clean_id}.json"
    if p.exists():
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            data["titulo"] = title
            with p.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return {"status": "ok", "title": title}
        except Exception:
            pass
    return {"status": "error"}

@app.delete("/api/chats/{chat_id}")
def deletar_chat_launcher(chat_id: str):
    """Exclui uma conversa do disco."""
    clean_id = chat_id[:-5] if chat_id.endswith(".json") else chat_id
    p = CAMINHO_DADOS / f"{clean_id}.json"
    if p.exists():
        try:
            p.unlink()
            return {"status": "removido"}
        except Exception:
            pass
    if CAMINHO_DADOS.exists():
        for fpath in CAMINHO_DADOS.glob("*.json"):
            try:
                with fpath.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("id") == chat_id or data.get("id") == clean_id:
                    fpath.unlink()
                    return {"status": "removido"}
            except Exception:
                pass
    return {"status": "nao_encontrado"}

@app.post("/api/client-events")
def receber_client_events(evento: dict):
    """Recebe eventos de telemetria do frontend."""
    return {"status": "ok"}

@app.get("/api/desktop/channel")
def desktop_channel():
    """Canal de autenticação para desktop / ferramentas locais."""
    return {"token": "agent-core-desktop-token"}

@app.get("/api/desktop/status")
@app.post("/api/desktop/status")
def desktop_status():
    """Retorna o status do controle de desktop para a interface."""
    return {
        "state": "ready",
        "observing": False,
        "grants": [
            {"capability": "desktop.observe", "scope": "local_device", "allowed": 1},
            {"capability": "desktop.control", "scope": "local_device", "allowed": 1},
            {"capability": "desktop.vision", "scope": "local_device", "allowed": 1}
        ],
        "groups": {
            "observe": "Observação de tela",
            "control": "Controle de mouse e teclado",
            "vision": "Análise visual"
        },
        "capture": {
            "monitor": 1,
            "fps": 2,
            "backend": "auto",
            "region": None
        },
        "monitors": [{"index": 1, "width": 1920, "height": 1080, "left": 0, "top": 0}]
    }

@app.get("/api/desktop/monitors")
def desktop_monitors():
    return [{"index": 1, "width": 1920, "height": 1080, "left": 0, "top": 0}]

@app.post("/api/desktop/control")
def desktop_control(payload: dict):
    return {"status": "ok", "state": "ready"}

# ============================================================
# ENDPOINTS: AUTOMAÇÃO, NAVEGADOR & PLAYWRIGHT MCP
# ============================================================

@app.get("/api/capability-runs")
def listar_capability_runs(limit: int = 100, session_id: str = None):
    from app.services.playwright_mcp_service import playwright_service
    return playwright_service.capability_history[-limit:]

@app.get("/api/browser/status")
def browser_status():
    from app.services.playwright_mcp_service import playwright_service
    return playwright_service.get_browser_status()

@app.post("/api/browser/pair-code")
def browser_pair_code():
    from app.services.playwright_mcp_service import playwright_service
    return {"code": playwright_service.generate_pair_code()}

@app.delete("/api/browser/pair")
def browser_revoke():
    from app.services.playwright_mcp_service import playwright_service
    playwright_service.revoke_device()
    return {"status": "ok"}

@app.get("/api/automation/status")
def automation_status():
    from app.services.playwright_mcp_service import playwright_service
    return playwright_service.get_status()

@app.post("/api/automation/connect")
def automation_connect():
    from app.services.playwright_mcp_service import playwright_service
    playwright_service.connection_phase = "ready"
    return {"status": "ok", "state": "ready"}

@app.delete("/api/automation/connect")
def automation_disconnect():
    from app.services.playwright_mcp_service import playwright_service
    playwright_service.revoke_device()
    return {"status": "ok"}

@app.post("/api/automation/probe")
def automation_probe():
    from app.services.playwright_mcp_service import playwright_service
    status = playwright_service.get_status()
    return {"status": "ok", "tab_count": status.get("tab_count", 0), "tabs": status.get("tabs", [])}

@app.post("/api/automation/cancel")
def automation_cancel():
    from app.services.playwright_mcp_service import playwright_service
    playwright_service.current_task = None
    return {"status": "cancelled"}

@app.post("/api/automation/approve/{action_id}")
def automation_approve(action_id: str):
    return {"status": "approved", "id": action_id}

@app.post("/api/automation/sites/revoke")
def automation_revoke_site(payload: dict):
    from app.services.playwright_mcp_service import playwright_service
    host = payload.get("host")
    group = payload.get("group")
    playwright_service.site_grants = [
        g for g in playwright_service.site_grants
        if not (host in g.get("scope", "") and group in g.get("capability", ""))
    ]
    return {"status": "ok"}

@app.websocket("/ws/browser")
async def websocket_browser(websocket: WebSocket):
    from app.services.playwright_mcp_service import playwright_service
    await playwright_service.handle_websocket(websocket)

@app.post("/api/browser/extension/sync")
def extension_sync(payload: dict):
    from app.services.playwright_mcp_service import playwright_service
    return playwright_service.extension_sync(payload)

@app.post("/api/browser/extension/result")
def extension_result(payload: dict):
    from app.services.playwright_mcp_service import playwright_service
    return playwright_service.extension_report_result(payload)

@app.put("/api/authorizations")
def set_authorizations(payload: dict = None):
    return {"status": "ok"}

@app.post("/api/capabilities/{name}/execute")
def execute_cap(name: str, payload: dict = None):
    from app.services.playwright_mcp_service import playwright_service
    payload = payload or {}
    if name == "pw_browser_snapshot":
        cmd = playwright_service.dispatch_command("snapshot", {})
        return {"success": True, "result": {"state": "completed", "command_id": cmd["id"]}}
    elif name == "pw_browser_navigate":
        url = payload.get("url", "https://google.com")
        cmd = playwright_service.dispatch_command("navigate", {"url": url})
        return {"success": True, "result": {"state": "completed", "url": url}}
    return {"success": True, "result": {"name": name, "state": "completed"}}



# ============================================================
# ENDPOINTS: AUTOMAÇÃO & PC (comandos_pc.json)
# ============================================================

def carregar_comandos_pc_dict() -> dict:
    if CAMINHO_COMANDOS.exists():
        try:
            with CAMINHO_COMANDOS.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def salvar_comandos_pc_dict(dados: dict):
    with CAMINHO_COMANDOS.open("w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

@app.get("/api/pc/commands")
def obter_comandos_pc():
    return {"comandos": carregar_comandos_pc_dict()}

@app.post("/api/pc/commands")
def atualizar_comandos_pc(payload: dict):
    chave = (payload.get("chave") or "").strip()
    comando = (payload.get("comando") or "").strip()
    acao = payload.get("acao", "salvar")
    
    if not chave:
        raise HTTPException(status_code=400, detail="Chave do comando é obrigatória.")
        
    cmds = carregar_comandos_pc_dict()
    if acao == "remover":
        if chave in cmds:
            del cmds[chave]
            salvar_comandos_pc_dict(cmds)
            return {"status": "removido", "chave": chave}
        return {"status": "nao_encontrado"}
    
    if not comando:
        raise HTTPException(status_code=400, detail="Linha de comando do Windows é obrigatória.")
        
    cmds[chave] = comando
    salvar_comandos_pc_dict(cmds)
    return {"status": "salvo", "chave": chave, "comando": comando}

def resolver_caminho_vscode() -> str | None:
    """Localiza o binário nativo Code.exe para evitar rodar code.cmd (que causa pop-up de terminal cmd.exe)."""
    # 1. A partir de code.cmd no PATH (ex: C:\...\Microsoft VS Code\bin\code.cmd -> C:\...\Microsoft VS Code\Code.exe)
    cmd_path = shutil.which("code")
    if cmd_path:
        p_exe = Path(cmd_path).parent.parent / "Code.exe"
        if p_exe.exists():
            return str(p_exe)
        p_exe_bin = Path(cmd_path).parent / "Code.exe"
        if p_exe_bin.exists():
            return str(p_exe_bin)

    # 2. Pastas padrão de instalação no Windows
    locais = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Microsoft VS Code" / "Code.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft VS Code" / "Code.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft VS Code" / "Code.exe",
    ]
    for loc in locais:
        if loc.exists():
            return str(loc)
    return None

def executar_no_windows(cmd_str: str) -> dict:
    """Executa comandos, programas, pastas ou URLs de forma limpa e nativa no Windows, sem abrir janelas indesejadas do CMD."""
    import re
    cmd = cmd_str.strip()
    cmd_lower = cmd.lower()
    
    # 1. Comandos explicitamente interativos de Terminal (onde a janela de console É desejada)
    is_terminal_visivel = (
        cmd_lower.startswith("start cmd") or
        cmd_lower.startswith("cmd /k") or
        " cmd /k" in cmd_lower or
        "cmd.exe /k" in cmd_lower or
        cmd_lower.startswith("start powershell") or
        "powershell -noexit" in cmd_lower or
        cmd_lower in ("cmd", "cmd.exe", "powershell", "powershell.exe")
    )
    if is_terminal_visivel:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        return {"modo": "terminal_visivel", "alvo": cmd, "pid": proc.pid}

    # 2. URLs e Navegação Web (Roteamento exclusivo via Playwright MCP Bridge / Extensão)
    url_match = re.search(r'https?://[^\s"\']+', cmd)
    if url_match:
        url = url_match.group(0)
        from app.services.playwright_mcp_service import playwright_service
        playwright_service.dispatch_command("navigate", {"url": url})
        return {"modo": "playwright_mcp", "alvo": url}

    # 3. Atalhos do Windows (.lnk) do Menu Iniciar ou Desktop
    cmd_limpo = cmd.strip('"\'')
    if cmd_limpo.lower().endswith(".lnk") and Path(cmd_limpo).exists():
        os.startfile(cmd_limpo)
        return {"modo": "atalho_lnk", "alvo": cmd_limpo}

        
    # 3. Protocolos do Windows (ex: ms-settings:, minecraft:, mailto:)
    if "ms-settings:" in cmd_lower:
        match = re.search(r'ms-settings:[^\s"\']*', cmd, re.IGNORECASE)
        protocol = match.group(0) if match else "ms-settings:"
        os.startfile(protocol)
        return {"modo": "protocolo", "alvo": protocol}
    if "minecraft:" in cmd_lower:
        os.startfile("minecraft:")
        return {"modo": "protocolo", "alvo": "minecraft:"}

    # 4. Explorador de Arquivos e Pastas do Usuário
    user_home = os.environ.get("USERPROFILE") or str(Path.home())
    if "shell:downloads" in cmd_lower:
        p = Path(user_home) / "Downloads"
        alvo_pasta = str(p) if p.exists() else user_home
        os.startfile(alvo_pasta)
        return {"modo": "pasta", "alvo": "Downloads"}

    if "shell:personal" in cmd_lower or "shell:documents" in cmd_lower:
        p = Path(user_home) / "Documents"
        alvo_pasta = str(p) if p.exists() else user_home
        os.startfile(alvo_pasta)
        return {"modo": "pasta", "alvo": "Documentos"}

    if "shell:my pictures" in cmd_lower or "shell:pictures" in cmd_lower:
        p = Path(user_home) / "Pictures"
        alvo_pasta = str(p) if p.exists() else user_home
        os.startfile(alvo_pasta)
        return {"modo": "pasta", "alvo": "Imagens"}

    if "shell:recyclebinfolder" in cmd_lower:
        try:
            os.startfile("shell:RecycleBinFolder")
            return {"modo": "lixeira", "alvo": "RecycleBinFolder"}
        except Exception:
            subprocess.Popen("explorer.exe shell:RecycleBinFolder", shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
            return {"modo": "lixeira", "alvo": "RecycleBinFolder"}

    if "shell:mycomputerfolder" in cmd_lower:
        try:
            os.startfile("shell:MyComputerFolder")
            return {"modo": "explorer", "alvo": "MyComputerFolder"}
        except Exception:
            os.startfile(user_home)
            return {"modo": "explorer", "alvo": user_home}

    if cmd_lower in ("start explorer", "explorer", "explorer.exe"):
        os.startfile(user_home)
        return {"modo": "explorer", "alvo": user_home}

    # 5. Normalização do alvo de execução (remover 'start ' prefixo se existir)
    alvo = cmd
    if cmd_lower.startswith("start "):
        alvo = cmd[6:].strip().strip('"').strip("'")

    # 6. Detecção especial do VS Code (executa Code.exe diretamente sem cmd.exe)
    if alvo.lower() in ("code", "vscode", "vs code", "code.exe"):
        vscode_exe = resolver_caminho_vscode()
        if vscode_exe:
            os.startfile(vscode_exe)
            return {"modo": "vscode_nativo", "alvo": vscode_exe}

    # 7. Ferramentas nativas do Windows via os.startfile (janela GUI direta)
    alvos_nativos = {
        "notepad": "notepad.exe",
        "notepad.exe": "notepad.exe",
        "calc": "calc.exe",
        "calc.exe": "calc.exe",
        "mspaint": "mspaint.exe",
        "mspaint.exe": "mspaint.exe",
        "taskmgr": "taskmgr.exe",
        "taskmgr.exe": "taskmgr.exe",
        "snippingtool": "snippingtool.exe",
        "cleanmgr": "cleanmgr.exe",
        "cleanmgr.exe": "cleanmgr.exe",
        "devmgmt.msc": "devmgmt.msc",
        "services.msc": "services.msc",
        "write": "write.exe",
        "wordpad": "write.exe",
        "regedit": "regedit.exe"
    }
    if alvo.lower() in alvos_nativos:
        try:
            os.startfile(alvos_nativos[alvo.lower()])
            return {"modo": "startfile", "alvo": alvos_nativos[alvo.lower()]}
        except Exception:
            pass

    # 8. Verificação de executável na máquina via shutil.which (.exe)
    which_bin = shutil.which(alvo)
    if which_bin and which_bin.lower().endswith(".exe"):
        try:
            os.startfile(which_bin)
            return {"modo": "executavel_direto", "alvo": which_bin}
        except Exception:
            pass

    # 9. Para comandos do sistema (shutdown, rundll32, PowerShell em lote, etc.):
    # Executa de forma SILENCIOSA (CREATE_NO_WINDOW) para não piscar tela preta do CMD
    proc = subprocess.Popen(
        cmd,
        shell=True,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    return {"modo": "silencioso", "alvo": cmd, "pid": proc.pid}

@app.post("/api/pc/execute")
def executar_comando_pc(payload: dict):
    chave = payload.get("chave")
    comando_direto = payload.get("comando")
    
    cmd_para_rodar = None
    if chave:
        cmds = carregar_comandos_pc_dict()
        cmd_para_rodar = cmds.get(chave)
    if not cmd_para_rodar and comando_direto:
        cmd_para_rodar = comando_direto
        
    if not cmd_para_rodar:
        raise HTTPException(status_code=404, detail="Comando não encontrado para execução.")

    try:
        resultado = executar_no_windows(cmd_para_rodar)
        registrar_log(f"[PC-CONTROL] Comando executado no Windows: {cmd_para_rodar} ({resultado.get('modo')})")
        return {"status": "executado", "comando": cmd_para_rodar, "detalhes": resultado}
    except Exception as e:
        registrar_log(f"[PC-CONTROL ERRO] Falha ao executar '{cmd_para_rodar}': {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao executar no Windows: {e}")

@app.post("/api/pc/discover")
def descobrir_comando_pc(payload: dict):
    nome = payload.get("nome", "").strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Nome do programa é obrigatório.")
    from app.services.discovery_service import aprender_e_registrar_comando
    resultado = aprender_e_registrar_comando(nome)
    return resultado


# ============================================================
# ENDPOINTS: SKILLS & ESPECIALISTAS (skills/*.md)
# ============================================================

def extrair_dados_skill_md(caminho: Path) -> dict:
    texto = caminho.read_text(encoding="utf-8")
    partes = texto.split("---")
    frontmatter = {}
    instrucoes = texto
    if len(partes) >= 3:
        for linha in partes[1].strip().split("\n"):
            if ":" in linha:
                k, v = linha.split(":", 1)
                frontmatter[k.strip()] = v.strip().strip('"').strip("'")
        instrucoes = "---".join(partes[2:]).strip()
        
    skill_id = frontmatter.get("id") or caminho.stem
    nome = frontmatter.get("nome") or caminho.stem.replace("_", " ").title()
    icone = frontmatter.get("icone") or "✨"
    tipo = frontmatter.get("tipo") or "skill"
    modelo = frontmatter.get("modelo") or "llama3.2"
    try:
        temperatura = float(frontmatter.get("temperatura", 0.2))
    except Exception:
        temperatura = 0.2
        
    return {
        "id": skill_id,
        "nome": nome,
        "icone": icone,
        "tipo": tipo,
        "modelo": modelo,
        "temperatura": temperatura,
        "instrucoes": instrucoes,
        "arquivo": caminho.name,
        "tamanho": f"{caminho.stat().st_size / 1024:.1f} KB"
    }

@app.get("/api/skills/list")
def listar_skills_completas():
    lista = []
    if CAMINHO_SKILLS.exists():
        for p in CAMINHO_SKILLS.glob("*.md"):
            try:
                lista.append(extrair_dados_skill_md(p))
            except Exception:
                pass
    lista.sort(key=lambda s: s["nome"].lower())
    return {"skills": lista}

@app.post("/api/skills/save")
def salvar_skill_md(payload: dict):
    skill_id = (payload.get("id") or "").strip().lower().replace(" ", "_")
    nome = (payload.get("nome") or "").strip()
    icone = payload.get("icone") or "✨"
    modelo = payload.get("modelo") or "llama3.2"
    try:
        temperatura = float(payload.get("temperatura", 0.2))
    except Exception:
        temperatura = 0.2
    instrucoes = payload.get("instrucoes") or ""
    
    if not skill_id or not nome:
        raise HTTPException(status_code=400, detail="ID e Nome da Skill são obrigatórios.")
        
    caminho = CAMINHO_SKILLS / f"{skill_id}.md"
    conteudo = f"""---
id: {skill_id}
nome: {nome}
icone: "{icone}"
tipo: skill
modelo: {modelo}
temperatura: {temperatura}
---

{instrucoes}
"""
    caminho.write_text(conteudo, encoding="utf-8")
    registrar_log(f"[SKILLS] Especialista salvo: {nome} ({skill_id})")
    return {"status": "salvo", "id": skill_id, "arquivo": caminho.name}

@app.delete("/api/skills/{skill_id}")
def excluir_skill_md(skill_id: str):
    caminho = CAMINHO_SKILLS / f"{skill_id}.md"
    if caminho.exists():
        caminho.unlink()
        registrar_log(f"[SKILLS] Especialista removido: {skill_id}")
        return {"status": "removido", "id": skill_id}
    for p in CAMINHO_SKILLS.glob("*.md"):
        if p.stem == skill_id:
            p.unlink()
            registrar_log(f"[SKILLS] Especialista removido: {skill_id}")
            return {"status": "removido", "id": skill_id}
    return {"status": "nao_encontrado"}


# ============================================================
# ENDPOINTS: MEMÓRIA RAG & ARQUIVOS (memory.db e uploads/)
# ============================================================

def formatar_tamanho(bytes_qty: int) -> str:
    if bytes_qty < 1024:
        return f"{bytes_qty} B"
    elif bytes_qty < 1024 * 1024:
        return f"{bytes_qty / 1024:.1f} KB"
    else:
        return f"{bytes_qty / (1024 * 1024):.1f} MB"

@app.get("/api/memory/stats")
def obter_stats_memoria():
    db_size = "0 B"
    if CAMINHO_MEMORY_DB.exists():
        db_size = formatar_tamanho(CAMINHO_MEMORY_DB.stat().st_size)
        
    total_memorias = 0
    if CAMINHO_DATA_MEMORY.exists():
        total_memorias = len(list(CAMINHO_DATA_MEMORY.glob("*.json")))
        
    arquivos_upload = []
    if CAMINHO_UPLOADS.exists():
        for p in CAMINHO_UPLOADS.iterdir():
            if p.is_file():
                arquivos_upload.append({
                    "nome": p.name,
                    "tamanho": formatar_tamanho(p.stat().st_size),
                    "data": datetime.fromtimestamp(p.stat().st_mtime).strftime("%d/%m/%Y %H:%M")
                })
    arquivos_upload.sort(key=lambda x: x["nome"].lower())
    
    return {
        "db_size": db_size,
        "total_memorias": total_memorias,
        "total_arquivos": len(arquivos_upload),
        "arquivos": arquivos_upload
    }

@app.post("/api/memory/upload")
async def upload_arquivo_memoria(file: UploadFile = File(...)):
    try:
        destino = CAMINHO_UPLOADS / file.filename
        with destino.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        registrar_log(f"[RAG] Documento carregado na base: {file.filename}")
        return {"status": "ok", "nome": file.filename, "tamanho": formatar_tamanho(destino.stat().st_size)}
    except Exception as e:
        registrar_log(f"[RAG ERRO] Falha ao enviar {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo: {e}")

@app.delete("/api/memory/files/{nome_arquivo}")
def remover_arquivo_memoria(nome_arquivo: str):
    destino = CAMINHO_UPLOADS / nome_arquivo
    if destino.exists() and destino.is_file():
        destino.unlink()
        registrar_log(f"[RAG] Documento removido: {nome_arquivo}")
        return {"status": "removido", "nome": nome_arquivo}
    return {"status": "nao_encontrado"}

@app.post("/api/memory/clear")
def limpar_memoria_rag():
    removidos = 0
    if CAMINHO_DATA_MEMORY.exists():
        for f in CAMINHO_DATA_MEMORY.glob("*.json"):
            try:
                f.unlink()
                removidos += 1
            except Exception:
                pass
                
    if CAMINHO_MEMORY_DB.exists():
        try:
            with sqlite3.connect(CAMINHO_MEMORY_DB) as conn:
                cur = conn.cursor()
                tables = [t[0] for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
                for t in tables:
                    if t != "app_metadata":
                        cur.execute(f"DELETE FROM {t};")
                conn.commit()
                cur.execute("VACUUM;")
        except Exception:
            pass
            
    registrar_log(f"[RAG] Base vetorial limpa ({removidos} fragmentos removidos)")
    return {"status": "sucesso", "memorias_removidas": removidos}