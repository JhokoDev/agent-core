import sqlite3
from pathlib import Path


class Database:
    def __init__(self, path: Path):
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with sqlite3.connect(self.path, timeout=5) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise RuntimeError("Versão de banco incompatível")
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("CREATE TABLE IF NOT EXISTS app_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            connection.execute("INSERT OR IGNORE INTO app_metadata VALUES ('schema_version', '1')")
            connection.execute("PRAGMA user_version=1")
        self.path.chmod(0o600)

    def ready(self) -> bool:
        try:
            uri = self.path.resolve().as_uri() + "?mode=rw"
            with sqlite3.connect(uri, uri=True, timeout=2) as connection:
                return connection.execute("SELECT value FROM app_metadata WHERE key='schema_version'").fetchone() == ('1',)
        except sqlite3.Error:
            return False
