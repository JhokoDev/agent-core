"""Gera configuração sem sobrescrever segredos existentes. Python >=3.11."""
import os
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
example = (root / ".env.example").read_text(encoding="utf-8")
target = root / ".env"
try:
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    print(".env existente preservado.")
else:
    with os.fdopen(descriptor, "w", encoding="utf-8") as file:
        file.write(example.replace("CHANGE_ME", secrets.token_urlsafe(48)))
    print(".env criado com token aleatório; token não exibido.")
(root / "data").mkdir(exist_ok=True, mode=0o700)
