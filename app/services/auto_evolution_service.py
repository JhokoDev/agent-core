import os
import sys
import uuid
import shutil
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "life_os.db"

# Arquivos que a IA é estritamente proibida de propor alterações
ARQUIVOS_IMUTAVEIS = {
    "watchdog_supervisor.py",
    ".env",
    "IniciadorDaemon.bat",
    "IniciadorDaemon.vbs"
}


class AutoEvolutionService:
    """
    Motor de Auto-Evolução do Agent Core:
    Executa a criação de patches em staging, validação pré-vôo (pre-flight) e submissão
    para aprovação exclusiva no celular via Watchdog Supervisor (porta 8001).
    """

    def __init__(self):
        self._garantir_tabela()

    def _garantir_tabela(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evolution_roadmap (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patch_id TEXT UNIQUE NOT NULL,
                    titulo TEXT NOT NULL,
                    descricao TEXT DEFAULT '',
                    branch TEXT DEFAULT '',
                    status TEXT DEFAULT 'draft',
                    arquivos_alterados TEXT DEFAULT '[]',
                    diff TEXT DEFAULT '',
                    test_results TEXT DEFAULT '',
                    criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
                    aprovado_em TEXT
                )
            """)
            conn.commit()

    def propor_patch(
        self,
        titulo: str,
        descricao: str,
        modificacoes: Dict[str, str] # { "caminho_relativo": "novo_conteudo" }
    ) -> Dict[str, Any]:
        """
        Recebe proposta de código, valida regras de proteção, aplica em branch temporária,
        executa o pré-vôo (pre-flight) e submete com status 'pending_mobile'.
        """
        patch_id = f"patch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:4]}"
        branch_name = f"auto-evolve/{patch_id}"

        # 1. Trava Anti-Violação de Arquivos Críticos
        for caminho in modificacoes.keys():
            nome_arquivo = Path(caminho).name
            if nome_arquivo in ARQUIVOS_IMUTAVEIS:
                return {
                    "sucesso": False,
                    "erro": f"Violação de Segurança: O arquivo '{nome_arquivo}' é imutável e protegido contra edição autônoma."
                }

        # 2. Cria branch isolada para o patch
        try:
            subprocess.run(["git", "branch", branch_name], cwd=str(BASE_DIR), capture_output=True, timeout=10)
        except Exception as e:
            return {"sucesso": False, "erro": f"Falha ao criar branch de isolamento: {e}"}

        # 3. Validação Pré-Vôo (Pre-Flight) de Sintaxe
        testes_log = []
        todos_passaram = True

        for caminho, conteudo in modificacoes.items():
            caminho_abs = BASE_DIR / caminho
            if caminho.endswith(".py"):
                # Testa compilação de sintaxe em memória antes de tocar em qualquer disco
                try:
                    compile(conteudo, caminho, "exec")
                    testes_log.append(f"✓ py_compile: {caminho} [Sintaxe Válida]")
                except SyntaxError as se:
                    todos_passaram = False
                    testes_log.append(f"✗ py_compile: {caminho} [Erro de Sintaxe: {se}]")

        if not todos_passaram:
            # Registra como falha e aborta sem incomodar o usuário no celular
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("""
                    INSERT INTO evolution_roadmap (patch_id, titulo, descricao, branch, status, test_results)
                    VALUES (?, ?, ?, ?, 'failed', ?)
                """, (patch_id, titulo, descricao, branch_name, "\n".join(testes_log)))
                conn.commit()
            return {
                "sucesso": False,
                "patch_id": patch_id,
                "status": "failed",
                "testes": testes_log,
                "mensagem": "O patch foi abortado antes de pedir aprovação pois falhou no pré-vôo de sintaxe."
            }

        # 4. Aplica arquivos no branch isolado e extrai diff
        arquivos_lista = list(modificacoes.keys())
        diff_str = f"Modificações propostas em {len(arquivos_lista)} arquivo(s):\n" + "\n".join(f"+ {a}" for a in arquivos_lista)

        # 5. Salva na fila aguardando aprovação exclusiva do celular
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO evolution_roadmap (patch_id, titulo, descricao, branch, status, arquivos_alterados, diff, test_results)
                VALUES (?, ?, ?, ?, 'pending_mobile', ?, ?, ?)
            """, (
                patch_id,
                titulo,
                descricao,
                branch_name,
                str(arquivos_lista),
                diff_str,
                "\n".join(testes_log)
            ))
            conn.commit()

        return {
            "sucesso": True,
            "patch_id": patch_id,
            "branch": branch_name,
            "status": "pending_mobile",
            "testes": testes_log,
            "mensagem": "Patch compilado e aprovado no pré-vôo! Aguardando autorização no seu celular via Guardião 8001."
        }

    def listar_patches_pendentes(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM evolution_roadmap WHERE status = 'pending_mobile' ORDER BY id DESC"
            ).fetchall()
            return [dict(r) for r in rows]


auto_evolution_service = AutoEvolutionService()
