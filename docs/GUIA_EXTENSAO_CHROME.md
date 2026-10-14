# 🌐 Guia de Integração com o Google Chrome (Playwright MCP)

Este guia explica como instalar, configurar e utilizar a extensão oficial do **Agent Core** no Google Chrome para permitir controle web em tempo real, snapshots interativos e automação resiliente.

---

## 1. O que é a Extensão do Agent Core?

A extensão (`browser-extension/`) é um componente **Manifest V3** que atua como uma ponte (Bridge) entre o navegador Google Chrome e o motor do **Agent Core**.

Ela permite que o agente:
1. **Conheça o Estado do Navegador:** Abas abertas, títulos, URLs ativas e abas reproduzindo áudio/vídeo.
2. **Leia a Tela com Alta Precisão:** Em vez de capturar imagens pesadas ou ler o HTML inteiro bruto, a extensão extrai uma árvore de acessibilidade (ARIA Snapshot) compacta com elementos numerados: `[1]`, `[2]`, `[3]`.
3. **Execute Ações Cirúrgicas:** Clica e digita em elementos específicos usando os identificadores numéricos, sem depender de coordenadas físicas ou OCR.
4. **Controle Multimídia:** Encontra players de vídeo/música em qualquer aba ativa e envia sinais de play, pause, mute e busca de reprodução.
5. **Utilize Playbooks Inteligentes:** Aplica automações pré-configuradas para pular anúncios, fechar popups de consentimento de cookies e ir direto ao conteúdo.

---

## 2. Passo a Passo de Instalação no Chrome

### Pré-requisito
Certifique-se de que o **Launcher** do Agent Core está em execução na porta `8001`:
```bash
python -m uvicorn launcher:app --host 0.0.0.0 --port 8001
# OU simplesmente execute o arquivo start_services.bat
```

### Instalação da Extensão
1. Abra o Google Chrome.
2. Na barra de endereços, digite e acesse:
   ```text
   chrome://extensions/
   ```
3. No canto superior direito da página, ative o botão deslizante **"Modo do desenvolvedor"** (Developer mode).
4. No canto superior esquerdo, clique no botão **"Carregar sem compactação"** (Load unpacked).
5. Na janela de seleção de pastas, navegue até a pasta do projeto e selecione:
   ```text
   C:\Projetos\agent-core-main\browser-extension
   ```
6. Clique em **"Selecionar pasta"**.
7. Pronto! A extensão **"Playwright MCP & Harvey Extension"** aparecerá na sua lista de extensões ativas.

---

## 3. Verificando o Status da Conexão

1. Na barra de ferramentas do Chrome, clique no ícone do quebra-cabeça (Extensões) e fixe o ícone da extensão.
2. Clique no ícone da extensão para abrir o popup de status.
3. Você deverá ver:
   * **Status da Conexão:** `Conectado via WebSocket` (ícone verde).
   * **URL do Servidor:** `ws://127.0.0.1:8001/ws/browser`.
   * **Abas Sincronizadas:** O número de abas ativas monitoradas.

> [!NOTE]
> Se o Launcher não estiver rodando no momento em que o Chrome for aberto, a extensão tentará reconectar automaticamente a cada 2 segundos e entrará em modo de fallback HTTP até que o WebSocket volte a responder.

---

## 4. Como Funciona a Leitura de Tela (ARIA Snapshots)

Quando o usuário solicita ao agente uma ação como *"clique no primeiro vídeo"* ou *"leia a página"*, o orquestrador dispara a ferramenta `pw_snapshot`.

A extensão varre os nós interativos da aba ativa e formata o resultado:

```text
Visão da Tela (Elementos Interativos):
[1] link 'YouTube Home'
[2] input 'Pesquisar'
[3] button 'Pesquisar'
[4] link 'Luan Santana - Melhores Músicas'
[5] link 'Henrique e Juliano - Ao Vivo'
```

Ao receber este resumo enxuto, o agente ou o orquestrador invoca `pw_clicar(seletor="4")`. O comando viaja pelo canal WebSocket e é executado em menos de 50ms diretamente no elemento do DOM.

---

## 5. Playbooks de Navegação (`browser_playbooks.json`)

Para evitar alucinações de URLs e cliques redundantes em sites populares, o sistema armazena heurísticas no arquivo [`data/browser_playbooks.json`](file:///c:/Projetos/agent-core-main/data/browser_playbooks.json).

### Exemplo de Playbook para o YouTube:
```json
{
  "domain": "youtube.com",
  "name": "YouTube",
  "search_url_template": "https://www.youtube.com/results?search_query={query}",
  "ad_skip_selectors": [
    ".ytp-ad-skip-button-modern",
    ".ytp-ad-skip-button",
    ".ytp-ad-overlay-close-button"
  ],
  "video_item_selector": "ytd-video-renderer #video-title",
  "cookie_banner_selectors": [
    "button[aria-label*='Aceitar']",
    "button[aria-label*='Accept']"
  ]
}
```

### Como Adicionar Novos Sites:
Basta editar `data/browser_playbooks.json` e incluir o novo domínio com suas respectivas regras de busca e remoção de modais/anúncios. O serviço `playwright_mcp_service.py` recarrega as regras dinamicamente.

---

## 6. Solução de Problemas Comuns

| Sintoma | Causa Mais Provável | Solução |
| :--- | :--- | :--- |
| **Popup exibe "Desconectado"** | O serviço do Launcher (porta 8001) não está em execução. | Execute `start_services.bat` ou `python -m uvicorn launcher:app --port 8001`. |
| **Clique não surte efeito na página** | A aba foi recarregada ou o elemento mudou de posição. | Peça ao agente para "ler a tela novamente" para obter um novo snapshot ARIA atualizado. |
| **Vídeo não pausa com comando de voz** | O título da aba não contém palavras-chave de mídia. | A extensão monitora abas com atributo `audible`. Certifique-se de que a aba esteja de fato reproduzindo som. |
