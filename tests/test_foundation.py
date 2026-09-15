import json
import logging
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from app.database import Database
from app.logging import configure_logging

ROOT = Path(__file__).resolve().parents[1]


class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def test_database_survives_reinitialization(self):
        path = self.root / "data" / "memory.db"
        db = Database(path)
        db.initialize()
        with sqlite3.connect(path) as connection:
            connection.execute("INSERT INTO app_metadata VALUES ('sentinel', 'preserved')")
        Database(path).initialize()
        with sqlite3.connect(path) as connection:
            self.assertEqual(connection.execute("SELECT value FROM app_metadata WHERE key='sentinel'").fetchone(), ('preserved',))
        self.assertTrue(Database(path).ready())

    def test_missing_database_is_not_created_by_health(self):
        db = Database(self.root / "absent.db")
        self.assertFalse(db.ready())
        self.assertFalse(db.path.exists())

    def test_corrupt_database_is_unavailable(self):
        path = self.root / "corrupt.db"
        path.write_text("not a database")
        self.assertFalse(Database(path).ready())

    def test_unknown_schema_is_rejected(self):
        path = self.root / "newer.db"
        with sqlite3.connect(path) as connection:
            connection.execute("PRAGMA user_version=99")
        with self.assertRaises(RuntimeError):
            Database(path).initialize()

    def test_logs_exclude_sensitive_fields(self):
        logger = configure_logging(self.root)
        logger.info("SECRET_BODY", extra={"event": "http_request", "request_id": "abc", "status": 200,
                                           "authorization": "SECRET_TOKEN", "body": "PRIVATE_TEXT"})
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
        text = (self.root / "logs" / "agent.jsonl").read_text()
        self.assertEqual(json.loads(text)["status"], 200)
        for value in ("SECRET_BODY", "SECRET_TOKEN", "PRIVATE_TEXT"):
            self.assertNotIn(value, text)

    def test_log_configuration_does_not_duplicate_handlers(self):
        first = configure_logging(self.root)
        second = configure_logging(self.root)
        self.assertIs(first, second)
        self.assertEqual(len(first.handlers), 1)
        for handler in first.handlers[:]:
            handler.close()
            first.removeHandler(handler)

    def test_bootstrap_preserves_existing_secret_and_hides_it(self):
        (self.root / "scripts").mkdir()
        shutil.copyfile(ROOT / "scripts" / "bootstrap.py", self.root / "scripts" / "bootstrap.py")
        shutil.copyfile(ROOT / ".env.example", self.root / ".env.example")
        command = [sys.executable, str(self.root / "scripts" / "bootstrap.py")]
        first = subprocess.run(command, check=True, capture_output=True, text=True)
        content = (self.root / ".env").read_bytes()
        token = next(line.split("=", 1)[1] for line in content.decode().splitlines() if line.startswith("AGENT_API_TOKEN="))
        self.assertGreaterEqual(len(token), 32)
        second = subprocess.run(command, check=True, capture_output=True, text=True)
        self.assertEqual((self.root / ".env").read_bytes(), content)
        self.assertNotIn(token, first.stdout + first.stderr + second.stdout + second.stderr)


if __name__ == "__main__":
    unittest.main()
