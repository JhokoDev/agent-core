import sqlite3
import json
from pathlib import Path
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

class LifeOSDatabase:
    """
    Gerenciador SQLite dedicado à persistência comportamental do Life OS.
    Armazena tarefas com metadados de insistência, transações financeiras,
    árvore de metas e logs de hábitos/telemetria.
    """

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            caminho_base = Path(__file__).resolve().parent.parent.parent.parent
            self.db_path = caminho_base / "data" / "life_os.db"
        else:
            self.db_path = db_path

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.inicializar()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def inicializar(self):
        """Cria as tabelas necessárias se não existirem."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Tabela de Tarefas Comportamentais
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tarefas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                descricao TEXT,
                criticidade TEXT CHECK(criticidade IN ('rotina', 'importante', 'critica')) DEFAULT 'rotina',
                status TEXT CHECK(status IN ('pendente', 'em_andamento', 'concluida', 'adiada', 'cancelada')) DEFAULT 'pendente',
                data_prevista TEXT,
                horario_previsto TEXT,
                duracao_estimada_min INTEGER DEFAULT 30,
                postpone_count INTEGER DEFAULT 0,
                postpone_reasons TEXT DEFAULT '[]',
                contexto_execucao TEXT CHECK(contexto_execucao IN ('pc', 'rua', 'qualquer')) DEFAULT 'qualquer',
                proof_of_work_type TEXT CHECK(proof_of_work_type IN ('click', 'texto', 'audio', 'sistema')) DEFAULT 'click',
                proof_of_work_data TEXT,
                micro_step_sugerido TEXT,
                escalation_level INTEGER DEFAULT 0,
                ultimo_aviso_ts REAL,
                proximo_aviso_ts REAL,
                meta_id INTEGER,
                criado_em TEXT NOT NULL
            )
            """)

            # 2. Tabela de Transações Financeiras (com suporte a multas de procrastinação)
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='financas_transacoes'")
            row_fin = cursor.fetchone()
            if row_fin and "multa_procrastinacao" not in row_fin[0]:
                cursor.execute("ALTER TABLE financas_transacoes RENAME TO financas_transacoes_old")
                cursor.execute("""
                CREATE TABLE financas_transacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_hora TEXT NOT NULL,
                    tipo TEXT CHECK(tipo IN ('despesa', 'receita', 'multa_procrastinacao')) NOT NULL,
                    valor REAL NOT NULL,
                    categoria TEXT NOT NULL,
                    descricao TEXT,
                    horas_vida REAL DEFAULT 0.0,
                    origem TEXT DEFAULT 'manual_texto',
                    raw_payload TEXT
                )
                """)
                cursor.execute("""
                INSERT INTO financas_transacoes (id, data_hora, tipo, valor, categoria, descricao, horas_vida, origem, raw_payload)
                SELECT id, data_hora, tipo, valor, categoria, descricao, horas_vida, origem, raw_payload FROM financas_transacoes_old
                """)
                cursor.execute("DROP TABLE financas_transacoes_old")
            else:
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS financas_transacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_hora TEXT NOT NULL,
                    tipo TEXT CHECK(tipo IN ('despesa', 'receita', 'multa_procrastinacao')) NOT NULL,
                    valor REAL NOT NULL,
                    categoria TEXT NOT NULL,
                    descricao TEXT,
                    horas_vida REAL DEFAULT 0.0,
                    origem TEXT DEFAULT 'manual_texto',
                    raw_payload TEXT
                )
                """)

            # 3. Tabela de Configurações Financeiras e Limites
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS financas_config (
                chave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            )
            """)

            # 4. Tabela de Metas
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS metas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                pilar TEXT NOT NULL,
                nivel TEXT CHECK(nivel IN ('macro', 'meso', 'micro')) DEFAULT 'macro',
                meta_pai_id INTEGER,
                progresso_pct REAL DEFAULT 0.0,
                prazo TEXT,
                status TEXT DEFAULT 'em_andamento',
                criado_em TEXT NOT NULL
            )
            """)

            # 5. Tabela de Hábitos
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS habitos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                pilar TEXT NOT NULL,
                frequencia TEXT DEFAULT 'diario',
                streak_atual INTEGER DEFAULT 0,
                melhor_streak INTEGER DEFAULT 0,
                ultimo_checkin TEXT
            )
            """)

            # 6. Tabela de Telemetria e Comportamento
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_hora TEXT NOT NULL,
                tipo_evento TEXT NOT NULL,
                detalhes TEXT
            )
            """)

            # 7. Tabela de Agenda Fixa (Eventos / Reuniões)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                start_at TEXT NOT NULL,
                end_at TEXT NOT NULL,
                is_busy_block INTEGER DEFAULT 1,
                external_calendar_id TEXT,
                created_at TEXT NOT NULL
            )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_start ON events(start_at)")

            # Inserir configurações padrão se não existirem
            config_padroes = {
                "teto_diario_livre": "50.0",
                "valor_hora_trabalho": "25.0",
                "multa_procrastinacao_acumulada": "0.0",
                "limite_tarefas_criticas_dia": "3",
                "topico_ntfy": "agent-core-alertas",
                "url_ntfy": "https://ntfy.sh"
            }
            for chave, valor in config_padroes.items():
                cursor.execute(
                    "INSERT OR IGNORE INTO financas_config (chave, valor) VALUES (?, ?)",
                    (chave, valor)
                )

            conn.commit()

    # ==========================================
    # MÉTODOS DE TAREFAS
    # ==========================================

    def criar_tarefa(self, dados: Dict[str, Any]) -> int:
        agora = datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO tarefas (
                titulo, descricao, criticidade, status, data_prevista, horario_previsto,
                duracao_estimada_min, contexto_execucao, proof_of_work_type,
                micro_step_sugerido, meta_id, criado_em, postpone_reasons
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dados.get("titulo"),
                dados.get("descricao", ""),
                dados.get("criticidade", "rotina"),
                dados.get("status", "pendente"),
                dados.get("data_prevista") or date.today().isoformat(),
                dados.get("horario_previsto"),
                dados.get("duracao_estimada_min", 30),
                dados.get("contexto_execucao", "qualquer"),
                dados.get("proof_of_work_type", "click"),
                dados.get("micro_step_sugerido", ""),
                dados.get("meta_id"),
                agora,
                json.dumps([])
            ))
            conn.commit()
            return cursor.lastrowid

    def obter_tarefa(self, tarefa_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM tarefas WHERE id = ?", (tarefa_id,)).fetchone()
            if not row:
                return None
            tarefa = dict(row)
            try:
                tarefa["postpone_reasons"] = json.loads(tarefa.get("postpone_reasons") or "[]")
            except Exception:
                tarefa["postpone_reasons"] = []
            return tarefa

    def listar_tarefas(
        self,
        status: Optional[str] = None,
        criticidade: Optional[str] = None,
        data_prevista: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM tarefas WHERE 1=1"
        params: List[Any] = []

        if status:
            query += " AND status = ?"
            params.append(status)
        if criticidade:
            query += " AND criticidade = ?"
            params.append(criticidade)
        if data_prevista:
            query += " AND data_prevista = ?"
            params.append(data_prevista)

        query += " ORDER BY data_prevista ASC, horario_previsto ASC, id ASC"

        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            resultado = []
            for r in rows:
                t = dict(r)
                try:
                    t["postpone_reasons"] = json.loads(t.get("postpone_reasons") or "[]")
                except Exception:
                    t["postpone_reasons"] = []
                resultado.append(t)
            return resultado

    def atualizar_tarefa(self, tarefa_id: int, campos: Dict[str, Any]) -> bool:
        if not campos:
            return False
        clausulas = []
        valores = []
        for chave, val in campos.items():
            if chave == "postpone_reasons" and isinstance(val, list):
                val = json.dumps(val)
            clausulas.append(f"{chave} = ?")
            valores.append(val)
        valores.append(tarefa_id)

        query = f"UPDATE tarefas SET {', '.join(clausulas)} WHERE id = ?"
        with self.get_connection() as conn:
            cur = conn.execute(query, valores)
            conn.commit()
            return cur.rowcount > 0

    def adiar_tarefa(self, tarefa_id: int, motivo: str, minutos: int = 15) -> Optional[Dict[str, Any]]:
        tarefa = self.obter_tarefa(tarefa_id)
        if not tarefa:
            return None

        # Adicionar motivo à lista histórica
        historico = tarefa.get("postpone_reasons", [])
        historico.append({
            "timestamp": datetime.now().isoformat(),
            "motivo": motivo,
            "minutos": minutos
        })

        nova_contagem = tarefa.get("postpone_count", 0) + 1

        # Reset do nível de escalação para recomeçar o ciclo com o novo prazo
        campos_atualizacao = {
            "postpone_count": nova_contagem,
            "postpone_reasons": historico,
            "escalation_level": 0,
            "status": "adiada"
        }

        self.atualizar_tarefa(tarefa_id, campos_atualizacao)
        return self.obter_tarefa(tarefa_id)

    def concluir_tarefa(self, tarefa_id: int, prova: str = "") -> Optional[Dict[str, Any]]:
        tarefa = self.obter_tarefa(tarefa_id)
        if not tarefa:
            return None

        campos = {
            "status": "concluida",
            "proof_of_work_data": prova,
            "escalation_level": 0
        }
        self.atualizar_tarefa(tarefa_id, campos)
        return self.obter_tarefa(tarefa_id)

    def remover_tarefa(self, tarefa_id: int) -> bool:
        with self.get_connection() as conn:
            cur = conn.execute("DELETE FROM tarefas WHERE id = ?", (tarefa_id,))
            conn.commit()
            return cur.rowcount > 0

    # ==========================================
    # MÉTODOS DE FINANÇAS
    # ==========================================

    def registrar_transacao(
        self,
        tipo: str,
        valor: float,
        categoria: str,
        descricao: str,
        origem: str = "manual_texto",
        raw_payload: Optional[str] = None
    ) -> int:
        agora = datetime.now().isoformat()
        valor_hora = float(self.obter_config("valor_hora_trabalho", "25.0"))
        horas_vida = round(valor / valor_hora, 2) if valor_hora > 0 else 0.0

        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO financas_transacoes (
                data_hora, tipo, valor, categoria, descricao, horas_vida, origem, raw_payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (agora, tipo, valor, categoria, descricao, horas_vida, origem, raw_payload))
            conn.commit()
            return cur.lastrowid

    def listar_transacoes(self, limite: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM financas_transacoes ORDER BY id DESC LIMIT ?",
                (limite,)
            ).fetchall()
            return [dict(r) for r in rows]

    def obter_gastos_hoje(self) -> float:
        hoje = date.today().isoformat()
        with self.get_connection() as conn:
            row = conn.execute("""
            SELECT COALESCE(SUM(valor), 0.0) as total
            FROM financas_transacoes
            WHERE tipo = 'despesa' AND data_hora LIKE ?
            """, (f"{hoje}%",)).fetchone()
            return float(row["total"]) if row else 0.0

    def obter_config(self, chave: str, padrao: str = "") -> str:
        with self.get_connection() as conn:
            row = conn.execute("SELECT valor FROM financas_config WHERE chave = ?", (chave,)).fetchone()
            return row["valor"] if row else padrao

    def definir_config(self, chave: str, valor: str) -> None:
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO financas_config (chave, valor) VALUES (?, ?) ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
                (chave, valor)
            )
            conn.commit()

    def obter_todas_configs(self) -> Dict[str, str]:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT chave, valor FROM financas_config").fetchall()
            return {r["chave"]: r["valor"] for r in rows}

    # ==========================================
    # MÉTODOS DE METAS
    # ==========================================

    def criar_meta(self, dados: Dict[str, Any]) -> int:
        agora = datetime.now().isoformat()
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO metas (titulo, pilar, nivel, meta_pai_id, progresso_pct, prazo, status, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dados.get("titulo"),
                dados.get("pilar", "carreira_dev"),
                dados.get("nivel", "macro"),
                dados.get("meta_pai_id"),
                dados.get("progresso_pct", 0.0),
                dados.get("prazo"),
                dados.get("status", "em_andamento"),
                agora
            ))
            conn.commit()
            return cur.lastrowid

    def listar_metas(self, pilar: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM metas WHERE 1=1"
        params = []
        if pilar:
            query += " AND pilar = ?"
            params.append(pilar)
        query += " ORDER BY id ASC"
        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def atualizar_progresso_meta(self, meta_id: int, progresso: float) -> bool:
        with self.get_connection() as conn:
            cur = conn.execute("UPDATE metas SET progresso_pct = ? WHERE id = ?", (progresso, meta_id))
            conn.commit()
            return cur.rowcount > 0

    # ==========================================
    # MÉTODOS DE HÁBITOS
    # ==========================================

    def criar_habito(self, nome: str, pilar: str, frequencia: str = "diario") -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO habitos (nome, pilar, frequencia, streak_atual, melhor_streak)
            VALUES (?, ?, ?, 0, 0)
            """, (nome, pilar, frequencia))
            conn.commit()
            return cur.lastrowid

    def listar_habitos(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM habitos ORDER BY id ASC").fetchall()
            return [dict(r) for r in rows]

    def checkin_habito(self, habito_id: int) -> Optional[Dict[str, Any]]:
        hoje = date.today().isoformat()
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM habitos WHERE id = ?", (habito_id,)).fetchone()
            if not row:
                return None
            habito = dict(row)
            if habito.get("ultimo_checkin") == hoje:
                return habito  # Já fez check-in hoje

            novo_streak = habito.get("streak_atual", 0) + 1
            melhor = max(novo_streak, habito.get("melhor_streak", 0))

            conn.execute("""
            UPDATE habitos SET streak_atual = ?, melhor_streak = ?, ultimo_checkin = ?
            WHERE id = ?
            """, (novo_streak, melhor, hoje, habito_id))
            conn.commit()

            habito["streak_atual"] = novo_streak
            habito["melhor_streak"] = melhor
            habito["ultimo_checkin"] = hoje
            return habito

    # ==========================================
    # TELEMETRIA
    # ==========================================

    def registrar_telemetria(self, tipo_evento: str, detalhes: Dict[str, Any]) -> None:
        agora = datetime.now().isoformat()
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO telemetria (data_hora, tipo_evento, detalhes) VALUES (?, ?, ?)",
                (agora, tipo_evento, json.dumps(detalhes))
            )
            conn.commit()

    # ==========================================
    # AGENDA FIXA (EVENTOS E REUNIÕES)
    # ==========================================

    def criar_evento(self, title: str, start_at: str, end_at: str, is_busy_block: int = 1, external_calendar_id: Optional[str] = None) -> int:
        agora = datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO events (title, start_at, end_at, is_busy_block, external_calendar_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (title, start_at, end_at, is_busy_block, external_calendar_id, agora))
            conn.commit()
            return cursor.lastrowid

    def listar_eventos(self, data: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if data:
                cursor.execute("SELECT * FROM events WHERE start_at LIKE ? ORDER BY start_at ASC", (f"{data}%",))
            else:
                cursor.execute("SELECT * FROM events ORDER BY start_at ASC LIMIT 100")
            return [dict(r) for r in cursor.fetchall()]

    def verificar_usuario_em_reuniao(self, data_hora_iso: Optional[str] = None) -> bool:
        agora = data_hora_iso or datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT COUNT(*) FROM events 
            WHERE is_busy_block = 1 
              AND start_at <= ? 
              AND end_at >= ?
            """, (agora, agora))
            return cursor.fetchone()[0] > 0

    # ==========================================
    # VÍNCULO TAREFA ↔ META (GOAL_ID)
    # ==========================================

    def obter_tarefa_com_impacto_meta(self, tarefa_id: int) -> Optional[Dict[str, Any]]:
        """Retorna tarefa e meta associada para alertar o impacto de atrasos."""
        tarefa = self.obter_tarefa(tarefa_id)
        if not tarefa:
            return None
        meta_id = tarefa.get("meta_id")
        meta_info = None
        if meta_id:
            with self.get_connection() as conn:
                row = conn.execute("SELECT * FROM metas WHERE id = ?", (meta_id,)).fetchone()
                if row:
                    meta_info = dict(row)
        tarefa["meta_associada"] = meta_info
        return tarefa

    # ==========================================
    # GESTÃO DAS 4 CAIXAS FINANCEIRAS & MULTAS
    # ==========================================

    def obter_saldo_caixas(self) -> Dict[str, Any]:
        """Calcula totais consolidados para as 4 Caixas Financeiras."""
        with self.get_connection() as conn:
            # Gastos e receitas por categoria
            rows = conn.execute("""
                SELECT categoria, tipo, COALESCE(SUM(valor), 0.0) as total
                FROM financas_transacoes
                GROUP BY categoria, tipo
            """).fetchall()

            caixas = {
                "custos_fixos": {"despesas": 0.0, "receitas": 0.0, "saldo": 0.0},
                "construcao_futuro": {"despesas": 0.0, "receitas": 0.0, "saldo": 0.0},
                "autoaperfeicoamento": {"despesas": 0.0, "receitas": 0.0, "saldo": 0.0},
                "livre_lazer": {"despesas": 0.0, "receitas": 0.0, "saldo": 0.0}
            }

            multas_total = 0.0

            for r in rows:
                cat = r["categoria"]
                tipo = r["tipo"]
                tot = float(r["total"])
                if tipo == "multa_procrastinacao":
                    multas_total += tot
                    caixas["construcao_futuro"]["receitas"] += tot
                    caixas["livre_lazer"]["despesas"] += tot
                    continue

                if cat not in caixas:
                    cat = "livre_lazer"
                if tipo == "receita":
                    caixas[cat]["receitas"] += tot
                else:
                    caixas[cat]["despesas"] += tot

            for c in caixas:
                caixas[c]["saldo"] = round(caixas[c]["receitas"] - caixas[c]["despesas"], 2)

            teto_diario = float(self.obter_config("teto_diario_livre", "50.0"))
            gastos_hoje = self.obter_gastos_hoje()

            return {
                "caixas": caixas,
                "teto_diario_livre": teto_diario,
                "gastos_hoje": gastos_hoje,
                "saldo_diario_restante": round(teto_diario - gastos_hoje, 2),
                "multas_procrastinacao_total": round(multas_total, 2)
            }

    def aplicar_multa_procrastinacao(self, valor: float, motivo: str, tarefa_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Nível 5: Contrato de Ulisses.
        Transfere o valor da caixa 'livre_lazer' para 'construcao_futuro' como penalidade.
        """
        agora = datetime.now().isoformat()
        valor_hora = float(self.obter_config("valor_hora_trabalho", "25.0"))
        horas_vida = round(valor / valor_hora, 2) if valor_hora > 0 else 0.0

        desc = f"Multa Procrastinação: {motivo}"
        if tarefa_id:
            desc += f" (Tarefa #{tarefa_id})"

        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO financas_transacoes (
                data_hora, tipo, valor, categoria, descricao, horas_vida, origem, raw_payload
            ) VALUES (?, 'multa_procrastinacao', ?, 'construcao_futuro', ?, ?, 'contrato_ulisses', ?)
            """, (agora, valor, desc, horas_vida, json.dumps({"tarefa_id": tarefa_id, "motivo": motivo})))
            tid = cur.lastrowid

            # Acumula na config
            acumulado = float(self.obter_config("multa_procrastinacao_acumulada", "0.0")) + valor
            conn.execute(
                "INSERT INTO financas_config (chave, valor) VALUES ('multa_procrastinacao_acumulada', ?) "
                "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
                (str(acumulado),)
            )
            conn.commit()

        self.registrar_telemetria("multa_procrastinacao_aplicada", {
            "tarefa_id": tarefa_id,
            "valor": valor,
            "motivo": motivo,
            "transacao_id": tid
        })

        return {
            "sucesso": True,
            "transacao_id": tid,
            "valor_multado": valor,
            "origem": "livre_lazer",
            "destino": "construcao_futuro",
            "motivo": motivo,
            "horas_vida_perdidas": horas_vida
        }
