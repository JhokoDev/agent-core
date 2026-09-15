#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11+ necessário"'
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/bootstrap.py
if command -v git >/dev/null 2>&1 && [ ! -d .git ]; then
  git init -b main
fi
printf '%s\n' 'Base preparada. Ative .venv e siga docs/INSTALACAO.md para instalar e testar Ollama.'
