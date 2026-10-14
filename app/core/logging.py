import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Lista fechada: nunca serializa mensagem, exceção, URL, corpo ou cabeçalhos.
        output = {"timestamp": datetime.now(timezone.utc).isoformat(), "level": record.levelname}
        for key in ("event", "request_id", "status", "duration_ms"):
            if hasattr(record, key):
                output[key] = getattr(record, key)
        return json.dumps(output)


def configure_logging(data_dir: Path) -> logging.Logger:
    directory = data_dir / "logs"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    logger = logging.getLogger("personal_agent." + str(directory.resolve()))
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        file = directory / "agent.jsonl"
        handler = RotatingFileHandler(file, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        file.chmod(0o600)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    return logger
