# Instalação e primeira execução

## 1. Inventário do servidor

Não foi criada ou acessada uma VM nesta entrega. Em uma VM Linux existente, anote:

```bash
uname -m
python3 --version
free -h
df -h .
```

Requisitos: Python >=3.11 com venv/pip, Git recomendado e espaço para modelo e ambiente.
Para Ubuntu com Python adequado, caso faltem ferramentas, o administrador pode instalar:

```bash
sudo apt-get update
sudo apt-get install python3-venv python3-pip git curl
```

Não substitua o Python do sistema. Se for anterior a 3.11, use um sistema/ambiente compatível.
O servidor foi escrito sem dependências específicas de x86, mas a instalação ARM64 está pendente.

## 2. Preparar projeto

Extraia o pacote na pasta de trabalho da VM e entre em `personal-agent`:

```bash
bash scripts/setup_vm.sh
source .venv/bin/activate
python -m pytest -q
```

O script cria `.venv`, instala dependências e gera `.env`. Não altera `.env` existente,
não usa sudo, não instala Ollama, não inicia serviço nem baixa modelo. Precisa de acesso ao PyPI.
Se faltar rede/dependência, termina com erro; não considere a instalação concluída.
As versões estão limitadas no pyproject, mas ainda não fixadas por um lock testado.
Após teste aprovado, registre o ambiente específico:

```bash
python -m pip freeze --exclude-editable > installed-versions.txt
```

Não trate esse inventário como lock universal para outras plataformas/Python.

## 3. Ollama na VM

Siga a [documentação oficial Linux](https://docs.ollama.com/linux).
Para inspecionar o instalador antes de executá-lo:

```bash
curl -fsSL https://ollama.com/install.sh -o /tmp/personal-agent-ollama-install.sh
less /tmp/personal-agent-ollama-install.sh
sh /tmp/personal-agent-ollama-install.sh
ollama --version
```

O instalador pode solicitar privilégios administrativos. Se usar systemd, configure com
`sudo systemctl edit ollama`:

```ini
[Service]
Environment="OLLAMA_HOST=127.0.0.1:11434"
Environment="OLLAMA_NO_CLOUD=1"
Environment="OLLAMA_NUM_PARALLEL=1"
```

Depois:

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
ollama pull qwen3.5:2b
ollama list
personal-agent doctor
personal-agent smoke-model
```

Não abra portas 11434/8000 na internet. O serviço Ollama executa na VM; o PC Windows não precisa
carregar o modelo. Se não houver systemd, use uma sessão separada para `ollama serve`, com
`OLLAMA_HOST=127.0.0.1:11434` e `OLLAMA_NO_CLOUD=1` no ambiente.

O comando de inferência usa uma pergunta fixa e mostra a resposta. Sem resposta/timeout, ele falha.
Meça tempo e memória antes de testar 4B. A presença em `ollama list` não prova inferência funcional.
O limite de saída curto pode ser insuficiente para modelos com raciocínio; se retornar resposta vazia,
registre o erro e ajuste limites em `.env`, sem presumir qualidade só pela execução.

## 4. API

Na raiz do projeto, com `.venv` ativado:

```bash
personal-agent serve
```

Em outro terminal:

```bash
curl --fail http://127.0.0.1:8000/health
```

Teste readiness sem imprimir o token e sem colocá-lo nos argumentos do curl:

```bash
.venv/bin/python - <<'PYTHON'
import httpx
from app.config import Settings
settings = Settings()
response = httpx.get('http://127.0.0.1:8000/ready',
    headers={'Authorization': 'Bearer ' + settings.api_token.get_secret_value()},
    trust_env=False, timeout=10)
print(response.status_code, response.json())
raise SystemExit(0 if response.status_code == 200 else 1)
PYTHON
```

HTTP 401 = token incorreto/ausente; 503 = banco/modelo indisponível; 200 = dependências detectadas.
Não existe `/chat` nesta fase. Use `smoke-model` somente para validar a inferência.

## 5. Windows

Execute no PowerShell, na pasta extraída, se a política local permitir:

```powershell
.\scripts\preflight_windows.ps1
```

O script somente informa presença de ferramentas. Não mude a política de execução da instituição
para rodá-lo. Se bloqueado, faça manualmente `Get-Command py, git, tailscale, kicad-cli`.
Anote versão instalada do KiCad, Python e Windows para a Fase 5. Nada foi instalado no seu PC.

## 6. Serviço e aceitação

O template `deploy/personal-agent.service` é opcional e ainda não testado em systemd real.
Antes de instalá-lo: criar usuário de serviço sem privilégios, preparar `/opt/personal-agent`,
instalar dependências ali, executar bootstrap como esse usuário e ajustar dono/permissões de
`.env` e `data`. Não copiar o template sem adequar User/WorkingDirectory/ExecStart/ReadWritePaths.
Use inicialmente execução manual até todos os critérios de `FASE_0.md` passarem.

O ZIP não inclui `.git`; setup_vm.sh inicializa um repositório se necessário. Nenhum remote ou
commit é criado automaticamente. Nunca adicione `.env`, bancos ou logs ao repositório.
