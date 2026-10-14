# 🪟 Windows MCP & Automação Nativa de Sistema

Este documento descreve o funcionamento do subsistema **Windows MCP** do Agent Core, responsável pela integração e controle de aplicativos desktop sem depender de coordenadas físicas de tela.

---

## 1. Por que Automação Nativa e não `pyautogui`?

Tradicionalmente, muitos agentes de IA tentam controlar o computador movendo o cursor do mouse e clicando em coordenadas `(x, y)` calculadas por visão computacional ou estimativas.

### Problemas dos Cliques por Coordenadas:
* **Frágil a Redimensionamentos:** Se a janela mudar de tamanho, posição ou monitor, o clique erra o alvo.
* **Invasivo:** O cursor físico do usuário é sequestrado enquanto o agente trabalha.
* **Cego a Estados:** Não há como saber se o botão estava desabilitado, se a janela estava em segundo plano ou se outra janela cobriu o botão.

### Vantagens do Windows MCP:
* **Zero Sequestro de Mouse:** Ações como focar, minimizar, maximizar e fechar operam via chamadas diretas de API do kernel do Windows.
* **Consciência de Processos:** O agente sabe exatamente qual processo (`chrome.exe`, `Code.exe`, `notepad.exe`) pertence à janela.
* **Inspeção de Controles (Acessibilidade Nativa):** Através do Microsoft UIAutomation, o agente lê a hierarquia de controles (botões, campos de texto, menus) de qualquer janela Win32, WPF ou UWP.

---

## 2. Bibliotecas e Componentes Utilizados

O Windows MCP utiliza as seguintes bibliotecas Python no ambiente local:
* **`pywin32` (`win32gui`, `win32con`, `win32process`):** Comunicação direta com a API Win32 do Windows para manipulação de identificadores de janela (HWND), z-order e estados.
* **`uiautomation`:** Biblioteca de interface para o framework de automação de interface de usuário da Microsoft (UI Automation).
* **`psutil`:** Leitura de métricas de processos, PIDs e consumo de memória RAM.

---

## 3. Principais Métodos do Serviço (`windows_mcp_service.py`)

### 1. `listar_janelas_ativas(apenas_com_titulo=True)`
Enumera todas as janelas principais no desktop:
```python
from app.services.windows_mcp_service import windows_mcp_service

janelas = windows_mcp_service.listar_janelas_ativas()
# Retorna lista de dicts:
# [
#   {"hwnd": 123456, "titulo": "Visual Studio Code", "pid": 4568, "processo": "Code.exe", "memoria_mb": 145.2},
#   {"hwnd": 654321, "titulo": "Google Chrome", "pid": 7890, "processo": "chrome.exe", "memoria_mb": 210.8}
# ]
```

### 2. `focar_janela(alvo)`
Traz a janela desejada para o primeiro plano imediatamente:
* O parâmetro `alvo` aceita o título parcial (ex: `"vscode"`, `"chrome"`), nome do executável ou PID numérico.
* Restaura a janela se estiver minimizada (`win32con.SW_RESTORE`) e a torna a janela ativa em foco (`win32gui.SetForegroundWindow`).

### 3. `minimizar_janela(alvo)` / `maximizar_janela(alvo)` / `fechar_janela(alvo)`
Altera o estado da janela pelo seu HWND sem intervenção do usuário.

### 4. `inspecionar_elementos(alvo, max_elementos=30)`
Gera uma árvore textual dos botões, menus e controles internos da janela através do `uiautomation.ControlFromHandle(hwnd)`:
```text
Controles da Janela 'Bloco de Notas':
[1] Documento: 'Área de Texto' (EditControl)
[2] Menu: 'Arquivo' (MenuItemControl)
[3] Menu: 'Editar' (MenuItemControl)
[4] Botão: 'Fechar' (ButtonControl)
```

### 5. `enviar_teclas_janela(alvo, texto)`
Foca na janela do aplicativo e digita o texto solicitado diretamente nos controles em foco.

---

## 4. Contrato da Ferramenta (`gerenciar_janelas_windows`)

Esta capacidade está exposta ao orquestrador cognitivo e ao modelo LLM sob o contrato:

* **ID da Tool:** `gerenciar_janelas_windows`
* **Categoria:** `computador`
* **Risco:** `medio`
* **Argumentos:**
  * `acao` (obrigatório, string): `'listar'`, `'focar'`, `'fechar'`, `'minimizar'`, `'maximizar'`, `'digitar'`, `'inspecionar'`.
  * `alvo` (opcional, string): Nome da janela, processo ou PID.
  * `texto` (opcional, string): Texto a ser enviado se a ação for `'digitar'`.

---

## 5. Exemplos de Uso em Linguagem Natural

O usuário pode interagir com o agente usando termos cotidianos:

* *"Quais programas estão abertos agora?"*
  $\rightarrow$ Invoca `gerenciar_janelas_windows(acao="listar")`.
* *"Traga o VS Code para a frente"*
  $\rightarrow$ Invoca `gerenciar_janelas_windows(acao="focar", alvo="code")`.
* *"Minimize a janela do Spotify"*
  $\rightarrow$ Invoca `gerenciar_janelas_windows(acao="minimizar", alvo="spotify")`.
* *"Feche a calculadora"*
  $\rightarrow$ Invoca `gerenciar_janelas_windows(acao="fechar", alvo="calc")`.
