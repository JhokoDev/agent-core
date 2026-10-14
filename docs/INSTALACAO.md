# 🛠️ Guia de Instalação e Configuração — Agent Core

Este guia orienta a configuração completa do ambiente de desenvolvimento e execução do **Agent Core**, cobrindo o sistema operacional Windows (recomendado para automação nativa) e distribuições Linux/WSL.

---

## 1. Requisitos de Sistema

### Ambiente Recomendado:
* **Sistema Operacional:** Windows 10 ou 11 (64-bit) — *necessário para os recursos nativos do Windows MCP (Win32 e UIAutomation)*.
* **Processador:** 4 núcleos ou superior.
* **Memória RAM:** Mínimo de 8 GB (16 GB recomendado para execução simultânea do Ollama e IDEs).
* **Python:** Versão 3.11 ou 3.12 (com `pip` atualizado e marcado para adicionar ao `PATH`).
* **Node.js:** Versão 18.x ou 20.x LTS (com `npm`).
* **Navegador:** Google Chrome atualizado.

---

## 2. Preparação do Ambiente Python

No terminal (PowerShell ou Command Prompt):

1. **Navegue até o diretório do projeto:**
   ```powershell
   cd C:\Projetos\agent-core-main
   ```

2. **Crie e ative um ambiente virtual (Opcional, porém recomendado):**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Instale as dependências principais:**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Instale os pacotes de automação e comunicação nativa:**
   ```powershell
   pip install pywin32 uiautomation pywinauto comtypes pyautogui websockets watchdog
   ```

---

## 3. Preparação do Frontend (`painel-core`)

O painel de controle e chat em tempo real utiliza React 18 com Vite:

1. **Acesse a pasta do frontend:**
   ```powershell
   cd painel-core
   ```

2. **Instale as dependências do Node.js:**
   ```powershell
   npm install
   ```

3. **Retorne à raiz:**
   ```powershell
   cd ..
   ```

---

## 4. Configuração do Modelo Local (Ollama)

O Agent Core é otimizado para executar com inferência local rápida e privada via Ollama:

1. **Instale o Ollama:**
   * Baixe e instale o executável oficial para Windows em [ollama.com](https://ollama.com).
2. **Baixe os modelos recomendados:**
   ```powershell
   # Modelo principal leve e rápido (padrão)
   ollama pull llama3.2:1b

   # Modelo opcional para tarefas de código
   ollama pull qwen2.5-coder:1.5b
   ```
3. O serviço do Ollama roda por padrão em `http://127.0.0.1:11434`.

---

## 5. Configuração das Variáveis de Ambiente (`.env`)

Copie o arquivo de exemplo na raiz do projeto:

```powershell
copy .env.example .env
```

Abra o arquivo `.env` para ajustar conforme sua necessidade:
```ini
AGENT_API_TOKEN=sua_chave_secreta_aqui
AGENT_DATA_DIR=./data
AGENT_HOST=127.0.0.1
AGENT_PORT=8000
AGENT_MODEL_PROVIDER=ollama
AGENT_OLLAMA_URL=http://127.0.0.1:11434
AGENT_MODEL=llama3.2:1b
AGENT_CONTEXT_WINDOW=4096
AGENT_MAX_OUTPUT_TOKENS=1024
```

---

## 6. Configuração da Extensão do Chrome

1. Abra o Google Chrome e digite na barra de navegação:
   ```text
   chrome://extensions/
   ```
2. No canto superior direito, ative a chave **"Modo do desenvolvedor"**.
3. Clique em **"Carregar sem compactação"**.
4. Selecione a pasta:
   ```text
   C:\Projetos\agent-core-main\browser-extension
   ```
5. A extensão se conectará automaticamente ao Launcher do Agent Core via WebSocket.

---

## 7. Inicialização do Sistema

### Opção A: Execução em 1 Clique (Scripts Batch)

* **Iniciar o Backend Principal (Porta 8000):**
  Dê duplo clique em **`ligar.bat`**. O servidor iniciará em background e os logs serão gravados em `server_log.txt`.
* **Iniciar o Launcher (Porta 8001) e o Painel Web (Porta 3000):**
  Dê duplo clique em **`start_services.bat`**.
* **Encerrar Todos os Serviços:**
  Dê duplo clique em **`desligar.bat`**.

---

### Opção B: Execução Manual via Terminal

Abra 3 terminais separados:

* **Terminal 1 — Backend Core:**
  ```powershell
  python -u -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --env-file .env
  ```

* **Terminal 2 — Launcher & WebSocket Relay:**
  ```powershell
  python -m uvicorn launcher:app --host 0.0.0.0 --port 8001
  ```

* **Terminal 3 — Painel Web:**
  ```powershell
  cd painel-core
  npm run dev
  ```

Abra o navegador em: **`http://localhost:3000`**.

---

## 8. Verificação de Saúde (Smoke Tests)

Para confirmar se todos os serviços estão saudáveis, execute no terminal:

```powershell
# 1. Teste de resposta do Backend
Invoke-RestMethod -Uri "http://127.0.0.1:8000/chats" -Headers @{ "Authorization" = "Bearer sua_chave_secreta_aqui" }

# 2. Teste do Launcher
Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/system/status"

# 3. Teste do Registro de Ferramentas
python -c "from app.tools.tool_registry import criar_registry_padrao; r = criar_registry_padrao(); print('Tools ativas:', len(r._ferramentas))"
```
Deve retornar 20 ferramentas ativas sem erros.
