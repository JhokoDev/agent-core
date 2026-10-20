import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = Path("data") / "agent_core.db"


def get_db_connection() -> sqlite3.Connection:
    """Retorna uma conexão SQLite configurada com Row factory e WAL mode."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Cria e atualiza o esquema do banco relacional do Agent Core."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Tabela de Metadados / Versão
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # 2. Tabela de Metas (Árvore Macro -> Meso -> Micro)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                descricao TEXT DEFAULT '',
                nivel TEXT NOT NULL DEFAULT 'macro',
                meta_pai_id INTEGER DEFAULT NULL,
                prazo_final TEXT DEFAULT NULL,
                progresso_pct INTEGER DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'em_progresso',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (meta_pai_id) REFERENCES metas(id) ON DELETE SET NULL
            )
        """)

        # 3. Tabela de Tarefas e Compromissos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tarefas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                descricao TEXT DEFAULT '',
                tipo TEXT NOT NULL DEFAULT 'tarefa',
                criticidade TEXT NOT NULL DEFAULT 'rotina',
                status TEXT NOT NULL DEFAULT 'pendente',
                data_hora_planejada TEXT NOT NULL,
                duracao_estimada_min INTEGER DEFAULT 30,
                contexto_execucao TEXT NOT NULL DEFAULT 'qualquer',
                nivel_cobranca_atual INTEGER DEFAULT 0,
                postpone_count INTEGER DEFAULT 0,
                postpone_reasons TEXT DEFAULT '[]',
                proof_of_work_type TEXT DEFAULT 'click',
                proof_of_work_data TEXT DEFAULT '',
                micro_step_sugerido TEXT DEFAULT '',
                meta_pai_id INTEGER DEFAULT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                concluida_em TEXT DEFAULT NULL,
                FOREIGN KEY (meta_pai_id) REFERENCES metas(id) ON DELETE SET NULL
            )
        """)

        # Índices para busca ultrarrápida do Heartbeat
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tarefas_status ON tarefas(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tarefas_planejada ON tarefas(data_hora_planejada)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tarefas_criticidade ON tarefas(criticidade)")

        # 4. Tabela de Caixas Financeiras
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS caixas_financeiras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                titulo_exibicao TEXT NOT NULL,
                saldo_alocado REAL DEFAULT 0.0,
                percentual_alvo REAL DEFAULT 25.0,
                updated_at TEXT NOT NULL
            )
        """)

        # Popula caixas padrão caso tabela esteja vazia
        now_iso = datetime.now().isoformat()
        cursor.execute("SELECT COUNT(*) FROM caixas_financeiras")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("""
                INSERT INTO caixas_financeiras (nome, titulo_exibicao, saldo_alocado, percentual_alvo, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, [
                ("custo_fixo", "Custos Fixos Essenciais", 0.0, 50.0, now_iso),
                ("futuro", "Construção de Futuro (Reserva/Investimento)", 0.0, 30.0, now_iso),
                ("estudo", "Autoaperfeiçoamento (Livros/Cursos/PC)", 0.0, 10.0, now_iso),
                ("lazer", "Livre & Lazer de Fim de Semana", 0.0, 10.0, now_iso),
            ])

        # 5. Tabela de Transações Financeiras
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transacoes_financeiras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                valor REAL NOT NULL,
                descricao TEXT NOT NULL,
                categoria TEXT DEFAULT 'geral',
                origem TEXT DEFAULT 'manual',
                caixa TEXT DEFAULT 'lazer',
                horas_de_vida REAL DEFAULT 0.0,
                created_at TEXT NOT NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transacoes_created ON transacoes_financeiras(created_at)")

        # 6. Tabela de Hábitos e Streaks
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS habitos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                descricao TEXT DEFAULT '',
                meta_dias_semana INTEGER DEFAULT 7,
                streak_atual INTEGER DEFAULT 0,
                maior_streak INTEGER DEFAULT 0,
                ultimo_registro TEXT DEFAULT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # Popula hábitos fundamentais
        cursor.execute("SELECT COUNT(*) FROM habitos")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("""
                INSERT INTO habitos (nome, descricao, meta_dias_semana, streak_atual, maior_streak, created_at)
                VALUES (?, ?, ?, 0, 0, ?)
            """, [
                ("codigo_diario", "Codificar pelo menos 1 hora em projetos próprios", 6, now_iso),
                ("leitura_estudo", "Ler ou estudar documentação técnica por 30 minutos", 5, now_iso),
                ("sono_pontual", "Encerrar o computador e deitar antes das 23h30", 7, now_iso),
                ("exercicio_fisico", "Atividade física ou treino de mobilidade", 4, now_iso),
            ])

        # 7. Telemetria de Dispositivo Móvel
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetria_dispositivo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dispositivo TEXT NOT NULL DEFAULT 'android',
                carregador_conectado INTEGER DEFAULT 0,
                rede_wifi TEXT DEFAULT '',
                em_casa INTEGER DEFAULT 1,
                bateria_pct INTEGER DEFAULT 100,
                ultimo_ping TEXT NOT NULL
            )
        """)

        cursor.execute("INSERT OR REPLACE INTO app_metadata (key, value) VALUES ('schema_version', '2')")
        conn.commit()
