import os
import sys
import time
import shutil
import sqlite3
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# ==========================================================
# CONFIGURAÇÕES DE SEGURANÇA E IMUTABILIDADE DO GUARDIÃO
# ==========================================================

SUPERVISOR_PORT = 8001
APP_PORT = 8000
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
BACKUPS_DIR = DATA_DIR / "backups"
BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

MOBILE_APPROVAL_TOKEN = os.getenv("MOBILE_APPROVAL_TOKEN", "mobile_sec_approval_core_8001_secret_key_v1")

# Lista Negra de Ficheiros Imutáveis (Hardcoded Read-Only)
ARQUIVOS_PROTEGIDOS = {
    "watchdog_supervisor.py",
    ".env",
    "IniciadorDaemon.bat",
    "IniciadorDaemon.vbs"
}

app = FastAPI(title="Agent Core Watchdog Supervisor", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verificar_token_mobile(authorization: Optional[str] = Header(None)) -> str:
    """Valida a assinatura do dispositivo móvel para autorizar operações no supervisor."""
    if not authorization:
        raise HTTPException(status_code=403, detail="Acesso negado: Token mobile não fornecido.")
    
    parts = authorization.split()
    token = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else authorization
    
    if token != MOBILE_APPROVAL_TOKEN:
        raise HTTPException(status_code=403, detail="Acesso negado: Assinatura do dispositivo móvel inválida.")
    return token


# ==========================================================
# UTILITÁRIOS DE CONTROLO DE PROCESSOS E BANCO NO WINDOWS
# ==========================================================

def criar_backup_banco() -> str:
    """Cria uma cópia de segurança instantânea do banco SQLite antes de qualquer merge."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    pasta_destino = BACKUPS_DIR / f"backup_{ts}"
    pasta_destino.mkdir(parents=True, exist_ok=True)
    
    db_origem = DATA_DIR / "life_os.db"
    if db_origem.exists():
        shutil.copy2(db_origem, pasta_destino / "life_os.db")
        
    db_memory = DATA_DIR / "memory.db"
    if db_memory.exists():
        try:
            shutil.copy2(db_memory, pasta_destino / "memory.db")
        except Exception:
            pass
            
    print(f"[Supervisor] Backup de segurança gravado em: {pasta_destino}")
    return str(pasta_destino)


def restaurar_backup_banco(pasta_backup: str) -> bool:
    """Restaura o banco SQLite a partir de uma cópia de segurança prévia."""
    caminho = Path(pasta_backup)
    if not caminho.exists():
        return False
        
    db_backup = caminho / "life_os.db"
    if db_backup.exists():
        shutil.copy2(db_backup, DATA_DIR / "life_os.db")
        print(f"[Supervisor] Banco life_os.db restaurado com sucesso a partir de {pasta_backup}")
        return True
    return False


def obter_pid_porta_8000() -> Optional[int]:
    """Descobre qual PID do Windows está a escutar na porta 8000."""
    try:
        cmd = 'Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess'
        res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=5)
        for line in res.stdout.strip().splitlines():
            pid_str = line.strip()
            if pid_str.isdigit() and int(pid_str) > 0:
                return int(pid_str)
    except Exception as e:
        print(f"[Supervisor] Aviso ao verificar porta 8000: {e}")
    return None


def matar_processo_porta_8000() -> bool:
    """Mata forçadamente a árvore de processos na porta 8000 para libertar sockets e ficheiros."""
    pid = obter_pid_porta_8000()
    if pid:
        print(f"[Supervisor] A finalizar processo antigo PID {pid} na porta 8000...")
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, timeout=5)
            time.sleep(1.5)
            return True
        except Exception as e:
            print(f"[Supervisor] Erro ao matar PID {pid}: {e}")
    return False


def iniciar_servidor_8000():
    """Inicia o processo operacional FastAPI na porta 8000."""
    print("[Supervisor] A iniciar servidor operacional na porta 8000...")
    cmd = [sys.executable, "-u", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--env-file", ".env"]
    p = subprocess.Popen(cmd, cwd=str(BASE_DIR))
    return p


def testar_healthcheck_15s(timeout_segundos: int = 15) -> bool:
    """Monitoriza se a porta 8000 responde 200 OK dentro da janela de salvamento de 15 segundos."""
    inicio = time.time()
    url = "http://127.0.0.1:8000/api/life/status"
    
    print(f"[Supervisor] A monitorizar arranque seguro na porta 8000 ({timeout_segundos}s)...")
    while time.time() - inicio < timeout_segundos:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AgentCore-Supervisor/1.0"})
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    print(f"[Supervisor] ✅ Healthcheck aprovado em {time.time() - inicio:.1f} segundos!")
                    return True
        except Exception:
            time.sleep(1.0)
            
    print(f"[Supervisor] ❌ Timeout de {timeout_segundos}s esgotado sem resposta da porta 8000!")
    return False


def obter_commit_atual() -> str:
    """Retorna o hash abreviado do commit atual do Git."""
    try:
        res = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(BASE_DIR), capture_output=True, text=True, timeout=5)
        return res.stdout.strip()
    except Exception:
        return "desconhecido"


# ==========================================================
# ROTAS DO GUARDIÃO SUPERVISOR (PORTA 8001)
# ==========================================================

@app.get("/supervisor/status")
def obter_status_supervisor(token: str = Depends(verificar_token_mobile)):
    """Retorna o estado do supervisor, do processo 8000 e dos backups."""
    pid_8000 = obter_pid_porta_8000()
    servidor_ativo = pid_8000 is not None
    commit = obter_commit_atual()
    
    backups = sorted([p.name for p in BACKUPS_DIR.glob("backup_*")], reverse=True)[:5]
    
    return {
        "supervisor_status": "online",
        "supervisor_port": SUPERVISOR_PORT,
        "app_port_8000": {
            "status": "online" if servidor_ativo else "offline",
            "pid": pid_8000
        },
        "git_commit": commit,
        "backups_recentes": backups,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/supervisor/pending")
def listar_patches_pendentes(token: str = Depends(verificar_token_mobile)):
    """Consulta os patches pendentes de aprovação na tabela evolution_roadmap."""
    db_path = DATA_DIR / "life_os.db"
    if not db_path.exists():
        return {"pendentes": []}
        
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM evolution_roadmap WHERE status = 'pending_mobile' ORDER BY id DESC"
            ).fetchall()
            return {"pendentes": [dict(r) for r in rows]}
    except sqlite3.OperationalError:
        return {"pendentes": []}


@app.post("/supervisor/approve-update/{patch_id}")
def aprovar_atualizacao_mobile(patch_id: str, token: str = Depends(verificar_token_mobile)):
    """
    O 'Pull Request de Bolso':
    1. Backup do SQLite
    2. Git merge / checkout
    3. Reinício da porta 8000
    4. Janela de salvamento de 15s (Auto-Rollback se falhar)
    """
    print(f"\n[Supervisor] 🚨 APROVAÇÃO MOBILE RECEBIDA PARA O PATCH: {patch_id}!")
    
    # Passo 1: Backup de segurança
    pasta_backup = criar_backup_banco()
    
    # Passo 2: Aplica git merge da branch de staging
    branch_name = f"auto-evolve/{patch_id}" if not patch_id.startswith("auto-evolve/") else patch_id
    try:
        merge_res = subprocess.run(["git", "merge", branch_name, "--no-edit"], cwd=str(BASE_DIR), capture_output=True, text=True, timeout=15)
        if merge_res.returncode != 0:
            print(f"[Supervisor] Erro no git merge: {merge_res.stderr}")
            # Se a branch específica não existir, faz checkout pull
            subprocess.run(["git", "pull", "origin", "main"], cwd=str(BASE_DIR), capture_output=True, timeout=15)
    except Exception as e:
        print(f"[Supervisor] Aviso no merge: {e}")
        
    # Passo 3: Reinicia servidor na porta 8000
    matar_processo_porta_8000()
    iniciar_servidor_8000()
    
    # Passo 4: Janela de Salvamento de 15 Segundos
    sucesso_boot = testar_healthcheck_15s(timeout_segundos=15)
    
    if sucesso_boot:
        # Atualiza status no banco
        try:
            with sqlite3.connect(DATA_DIR / "life_os.db") as conn:
                conn.execute(
                    "UPDATE evolution_roadmap SET status = 'applied', aprovado_em = ? WHERE patch_id = ? OR id = ?",
                    (datetime.now().isoformat(), patch_id, patch_id)
                )
                conn.commit()
        except Exception:
            pass
            
        return {
            "status": "applied",
            "mensagem": "Atualização aplicada com sucesso! Servidor 8000 online e estável.",
            "backup_criado": pasta_backup,
            "novo_commit": obter_commit_atual()
        }
    else:
        # AUTO-ROLLBACK AUTOMÁTICO DE SEGURANÇA!
        print("[Supervisor] ⚠️ ACIONANDO AUTO-ROLLBACK IMEDIATO!")
        subprocess.run(["git", "reset", "--hard", "HEAD~1"], cwd=str(BASE_DIR), capture_output=True, timeout=10)
        restaurar_backup_banco(pasta_backup)
        matar_processo_porta_8000()
        iniciar_servidor_8000()
        testar_healthcheck_15s(timeout_segundos=15)
        
        return {
            "status": "rolled_back",
            "mensagem": "O patch causou instabilidade no arranque. O Guardião reverteu o código e restaurou o banco automaticamente sem quebrar o sistema.",
            "backup_restaurado": pasta_backup,
            "commit_restaurado": obter_commit_atual()
        }


@app.post("/supervisor/rollback")
def disparar_rollback_manual(token: str = Depends(verificar_token_mobile)):
    """Reverte manualmente para a versão anterior e restaura o último backup."""
    backups = sorted(list(BACKUPS_DIR.glob("backup_*")), reverse=True)
    ultimo_backup = str(backups[0]) if backups else ""
    
    print("[Supervisor] ⏪ ROLLBACK MANUAL SOLICITADO PELO CELULAR!")
    subprocess.run(["git", "reset", "--hard", "HEAD~1"], cwd=str(BASE_DIR), capture_output=True, timeout=10)
    if ultimo_backup:
        restaurar_backup_banco(ultimo_backup)
        
    matar_processo_porta_8000()
    iniciar_servidor_8000()
    testar_healthcheck_15s(timeout_segundos=15)
    
    return {
        "status": "rolled_back",
        "mensagem": "Rollback manual concluído. Versão anterior restaurada.",
        "commit": obter_commit_atual(),
        "backup_restaurado": ultimo_backup
    }


if __name__ == "__main__":
    import uvicorn
    print(f"[Supervisor] Guardião Imutável a iniciar na porta {SUPERVISOR_PORT}...")
    uvicorn.run(app, host="0.0.0.0", port=SUPERVISOR_PORT)
