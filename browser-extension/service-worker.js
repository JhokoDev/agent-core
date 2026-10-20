/**
 * Playwright MCP & Harvey Extension — Service Worker
 * Arquitetura de Alto Desempenho: WebSocket Bidirecional + Snapshots ARIA Numerados
 */

const DEFAULT_SERVER_URL = "http://127.0.0.1:8001";
const DEFAULT_TOKEN = "PqBeTC3OO69SHxZ2RBsb57AIwkXuoUIJbUdsnnpyf-Y";
const DEFAULT_PAIR_CODE = "AGENT-CORE";

// Estado interno
let config = {
  serverUrl: DEFAULT_SERVER_URL,
  token: DEFAULT_TOKEN,
  pairCode: DEFAULT_PAIR_CODE,
  connected: false,
  autoSync: true
};

let ws = null;
let wsReconnectTimer = null;
let isSyncing = false;

/**
 * Carrega configurações do chrome.storage.local
 */
async function loadConfig() {
  try {
    const stored = await chrome.storage.local.get(["serverUrl", "token", "pairCode"]);
    if (stored.serverUrl) config.serverUrl = stored.serverUrl;
    if (stored.token) config.token = stored.token;
    if (stored.pairCode) config.pairCode = stored.pairCode;
  } catch (err) {
    console.warn("Aviso ao ler storage:", err);
  }
}

/**
 * Conecta via WebSocket ao Launcher / Backend para execução em tempo real (<50ms)
 */
function connectWebSocket() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return;
  }

  const wsUrl = config.serverUrl.replace(/^http/, "ws") + "/ws/browser";
  try {
    ws = new WebSocket(wsUrl);

    ws.onopen = async () => {
      console.log("[Playwright MCP] WebSocket conectado com sucesso:", wsUrl);
      config.connected = true;
      const currentTabs = await collectTabs();
      ws.send(JSON.stringify({
        type: "sync",
        token: config.token,
        pair_code: config.pairCode,
        device: {
          id: "chrome-agent-core",
          browser: "Google Chrome (WebSocket MCP Bridge)",
          device: "Windows PC"
        },
        tabs: currentTabs
      }));
    };

    ws.onmessage = async (event) => {
      try {
        const cmd = JSON.parse(event.data);
        if (cmd && cmd.operation) {
          console.log("[Playwright MCP] Comando instantâneo recebido via WS:", cmd.operation, cmd.arguments);
          const resultPayload = await handleCommand(cmd);
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
              type: "result",
              ...resultPayload
            }));
          }
        }
      } catch (err) {
        console.error("[Playwright MCP] Erro ao processar mensagem WS:", err);
      }
    };

    ws.onclose = () => {
      console.log("[Playwright MCP] Conexão WebSocket encerrada. Tentando reconectar em 2s...");
      config.connected = false;
      ws = null;
      clearTimeout(wsReconnectTimer);
      wsReconnectTimer = setTimeout(connectWebSocket, 2000);
    };

    ws.onerror = (err) => {
      console.warn("[Playwright MCP] Erro na conexão WebSocket:", err);
      try { ws.close(); } catch (_) {}
    };
  } catch (e) {
    ws = null;
    clearTimeout(wsReconnectTimer);
    wsReconnectTimer = setTimeout(connectWebSocket, 3000);
  }
}

/**
 * Garante que o alarme de sincronização periódica esteja ativo (fallback)
 */
async function setupAlarm() {
  try {
    await chrome.alarms.clear("sync_alarm");
    chrome.alarms.create("sync_alarm", { periodInMinutes: 0.1 }); // a cada 6s como fallback
  } catch (err) {
    console.warn("Aviso ao criar alarme:", err);
  }
}

/**
 * Inicialização imediata ao carregar o service worker
 */
async function bootstrap() {
  await loadConfig();
  await setupAlarm();
  connectWebSocket();
  await syncWithBackend();
}

bootstrap();

chrome.runtime.onInstalled.addListener(() => { bootstrap(); });
chrome.runtime.onStartup.addListener(() => { bootstrap(); });

chrome.alarms.onAlarm.addListener(alarm => {
  if (alarm.name === "sync_alarm" && config.autoSync) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      connectWebSocket();
      syncWithBackend();
    }
  }
});

// Atualizações reativas de abas
chrome.tabs.onActivated.addListener(async () => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    const tabs = await collectTabs();
    ws.send(JSON.stringify({ type: "tabs_update", tabs }));
  } else {
    syncWithBackend();
  }
});

chrome.tabs.onUpdated.addListener(async (_tabId, changeInfo) => {
  if (changeInfo.status === "complete" || changeInfo.url) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      const tabs = await collectTabs();
      ws.send(JSON.stringify({ type: "tabs_update", tabs }));
    } else {
      syncWithBackend();
    }
  }
});

chrome.tabs.onRemoved.addListener(async () => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    const tabs = await collectTabs();
    ws.send(JSON.stringify({ type: "tabs_update", tabs }));
  } else {
    syncWithBackend();
  }
});

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.action === "get_status") {
    sendResponse({ config });
  } else if (msg.action === "save_config") {
    config = { ...config, ...msg.data };
    chrome.storage.local.set(msg.data);
    connectWebSocket();
    syncWithBackend().then(res => sendResponse(res));
    return true;
  } else if (msg.action === "sync_now") {
    connectWebSocket();
    syncWithBackend().then(res => sendResponse(res));
    return true;
  }
});

/**
 * Coleta todas as abas abertas
 */
async function collectTabs() {
  try {
    const tabs = await chrome.tabs.query({});
    return tabs
      .filter(t => t.url && (t.url.startsWith("http://") || t.url.startsWith("https://") || t.url.startsWith("file://")))
      .map(t => ({
        tab_id: t.id,
        window_id: t.windowId,
        title: t.title || "Sem título",
        url: t.url,
        active: Boolean(t.active),
        audible: Boolean(t.audible)
      }));
  } catch (err) {
    console.error("Erro ao listar abas:", err);
    return [];
  }
}

/**
 * Resolve a aba alvo com heurísticas inteligentes
 */
async function resolveTargetTab(preferredTabId, hint) {
  if (preferredTabId) {
    try {
      const tab = await chrome.tabs.get(preferredTabId);
      if (tab) return tab;
    } catch (_) {}
  }

  if (hint === "media" || hint === "pause" || hint === "play") {
    try {
      const audibleTabs = await chrome.tabs.query({ audible: true });
      if (audibleTabs && audibleTabs.length > 0) return audibleTabs[0];
    } catch (_) {}

    try {
      const all = await chrome.tabs.query({});
      const mediaTab = all.find(t => t.url && (t.url.includes("youtube.com/watch") || t.url.includes("spotify.com") || t.url.includes("youtube.com")));
      if (mediaTab) return mediaTab;
    } catch (_) {}
  }

  if (hint === "youtube" || hint === "video") {
    try {
      const all = await chrome.tabs.query({});
      const ytTab = all.find(t => t.url && t.url.includes("youtube.com"));
      if (ytTab) {
        if (ytTab.windowId) await chrome.windows.update(ytTab.windowId, { focused: true });
        await chrome.tabs.update(ytTab.id, { active: true });
        return ytTab;
      }
    } catch (_) {}
  }

  try {
    const [focusedActive] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
    if (focusedActive) return focusedActive;
  } catch (_) {}

  try {
    const [anyActive] = await chrome.tabs.query({ active: true });
    if (anyActive) return anyActive;
  } catch (_) {}

  try {
    const all = await chrome.tabs.query({});
    const httpTab = all.find(t => t.url && (t.url.startsWith("http://") || t.url.startsWith("https://")));
    if (httpTab) return httpTab;
  } catch (_) {}

  return await chrome.tabs.create({ url: "https://www.google.com" });
}

/**
 * Fallback de sincronização HTTP quando WebSocket estiver offline
 */
async function syncWithBackend() {
  if (isSyncing) return { busy: true };
  isSyncing = true;

  try {
    const currentTabs = await collectTabs();
    const payload = {
      token: config.token,
      pair_code: config.pairCode,
      device: {
        id: "chrome-unrestricted-extension",
        browser: "Google Chrome / Microsoft Edge (Acesso Livre)",
        device: "Windows PC"
      },
      tabs: currentTabs
    };

    const res = await fetch(`${config.serverUrl}/api/browser/extension/sync`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      config.connected = false;
      return { success: false, error: `HTTP ${res.status}` };
    }

    const data = await res.json();
    config.connected = Boolean(data.authorized);

    if (data.commands && Array.isArray(data.commands) && data.commands.length > 0) {
      for (const cmd of data.commands) {
        handleCommand(cmd);
      }
    }

    return { success: true, authorized: data.authorized, tabCount: currentTabs.length };
  } catch (err) {
    config.connected = false;
    return { success: false, error: err.message };
  } finally {
    isSyncing = false;
  }
}

/**
 * Despachador de comandos (executado imediatamente tanto por WS quanto por HTTP)
 */
async function handleCommand(cmd) {
  const { id, operation, arguments: args } = cmd;
  let result = null;
  let error = null;

  try {
    switch (operation) {
      case "navigate":
      case "open_tab":
        result = await execNavigate(args.url);
        break;

      case "snapshot":
        result = await execSnapshot(args.tab_id);
        break;

      case "click":
        result = await execClick(args.selector, args.tab_id);
        break;

      case "type":
        result = await execType(args.selector, args.text, args.enter, args.tab_id);
        break;

      case "media_control":
        result = await execMediaControl(args.action, args.value, args.tab_id);
        break;

      case "tab_control":
        result = await execTabControl(args.action, args.tab_id, args.url);
        break;

      case "block_distractions":
      case "focus_mode":
        result = await execBlockDistractions(args?.redirect_url);
        break;

      default:
        error = `Operação '${operation}' não reconhecida.`;
    }
  } catch (err) {
    error = err.message;
  }

  const resultPayload = {
    id,
    state: error ? "failed" : "completed",
    error,
    result,
    timestamp: Date.now()
  };

  // Se WebSocket ativo, envia de volta imediatamente
  if (ws && ws.readyState === WebSocket.OPEN) {
    try {
      ws.send(JSON.stringify({ type: "result", ...resultPayload }));
    } catch (_) {}
  }

  // Notifica também via HTTP para garantir persistência do histórico
  try {
    await fetch(`${config.serverUrl}/api/browser/extension/result`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(resultPayload)
    });
  } catch (_) {}

  return resultPayload;
}

// -------------------------------------------------------------
// IMPLEMENTAÇÃO DOS COMANDOS
// -------------------------------------------------------------

async function execNavigate(url) {
  if (!url.startsWith("http://") && !url.startsWith("https://")) {
    url = "https://" + url;
  }

  const activeTab = await resolveTargetTab();
  if (activeTab && (activeTab.url === "chrome://newtab/" || activeTab.url === "edge://newtab/" || activeTab.url === "about:blank")) {
    const updated = await chrome.tabs.update(activeTab.id, { url });
    if (updated.windowId) await chrome.windows.update(updated.windowId, { focused: true });
    return { tab_id: updated.id, url, opened: true };
  } else {
    const tab = await chrome.tabs.create({ url });
    if (tab.windowId) await chrome.windows.update(tab.windowId, { focused: true });
    return { tab_id: tab.id, url, opened: true };
  }
}

/**
 * SNAPSHOT SEMÂNTICO (ARIA NUMERADO):
 * Injeta um indexador que varre elementos visíveis e atribui IDs numéricos [1], [2], etc.
 */
async function execSnapshot(tabId) {
  const targetTab = await resolveTargetTab(tabId);
  if (!targetTab?.id) throw new Error("Nenhuma aba ativa para leitura de snapshot.");

  const results = await chrome.scripting.executeScript({
    target: { tabId: targetTab.id },
    func: () => {
      window.__harveyElements = window.__harveyElements || {};
      for (const k in window.__harveyElements) delete window.__harveyElements[k];

      const interactiveSelectors = [
        "a[href]",
        "button",
        "input",
        "textarea",
        "select",
        "[role='button']",
        "[role='link']",
        "[role='tab']",
        "[role='menuitem']",
        "[role='checkbox']",
        "[role='switch']",
        "video",
        "audio",
        "#video-title",
        ".ytp-play-button"
      ];

      const rawElements = Array.from(document.querySelectorAll(interactiveSelectors.join(",")));
      const visibleElements = [];
      let index = 1;

      for (const el of rawElements) {
        const rect = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);
        if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0") continue;
        if (rect.width < 5 || rect.height < 5) continue;
        if (rect.bottom < 0 || rect.top > window.innerHeight * 1.5) continue;

        let name = (
          el.getAttribute("aria-label") ||
          el.title ||
          el.placeholder ||
          el.value ||
          el.innerText ||
          el.getAttribute("alt") ||
          ""
        ).trim().replace(/\s+/g, " ");

        const tag = el.tagName.toLowerCase();
        if (!name && tag === "input") name = el.getAttribute("name") || el.getAttribute("type") || "campo de busca/texto";
        if (!name && tag === "video") name = "Player de vídeo ativo";
        if (!name && tag !== "input" && tag !== "button") continue;

        name = name.slice(0, 100);
        const role = el.getAttribute("role") || tag;

        el.setAttribute("data-agent-id", String(index));
        window.__harveyElements[index] = el;

        visibleElements.push({
          id: index,
          tag: tag,
          role: role,
          name: name
        });

        index++;
        if (index > 40) break;
      }

      const textLines = visibleElements.map(e => `[${e.id}] ${e.role}: "${e.name}"`);

      return {
        title: document.title,
        url: location.href,
        elements_count: visibleElements.length,
        elements: visibleElements,
        text_tree: textLines.join("\n")
      };
    }
  });

  return results?.[0]?.result || { title: targetTab.title, url: targetTab.url, text_tree: "Nenhum elemento interativo visível." };
}

/**
 * CLIQUE INTELIGENTE POR ID NUMÉRICO OU TEXTO
 */
async function execClick(selector, tabId) {
  let cleanSel = String(selector || "").trim();
  if (cleanSel.startsWith("text=")) cleanSel = cleanSel.slice(5).trim();
  cleanSel = cleanSel.replace(/^["']|["']$/g, "").trim();

  // Verifica se o seletor é um ID numérico da árvore ARIA (ex: "3" ou "[3]")
  const numMatch = cleanSel.match(/^\[?(\d+)\]?$/);
  const targetId = numMatch ? parseInt(numMatch[1], 10) : null;

  const isVideoHint = cleanSel.toLowerCase().includes("video") || cleanSel.toLowerCase().includes("musica") || cleanSel.toLowerCase().includes("luan santana");
  const targetTab = await resolveTargetTab(tabId, isVideoHint ? "youtube" : null);
  if (!targetTab?.id) throw new Error("Nenhuma aba ativa para clique.");

  const results = await chrome.scripting.executeScript({
    target: { tabId: targetTab.id },
    args: [cleanSel, targetId],
    func: (sel, id) => {
      let targetEl = null;

      // 1. Busca prioritária por ID numérico indexado
      if (id !== null) {
        if (window.__harveyElements && window.__harveyElements[id]) {
          targetEl = window.__harveyElements[id];
        } else {
          targetEl = document.querySelector(`[data-agent-id='${id}']`);
        }
      }

      // 2. Se não achou por ID ou foi passado seletor CSS tradicional
      if (!targetEl) {
        if (sel.startsWith("#") || sel.startsWith(".") || sel.startsWith("[") || sel.includes(">")) {
          try { targetEl = document.querySelector(sel); } catch (_) {}
        }
      }

      // 3. Busca por texto/rótulo nos elementos interativos
      if (!targetEl) {
        const selNorm = sel.toLowerCase();
        const allCandidates = Array.from(document.querySelectorAll(
          "a, button, [role='button'], [role='link'], #video-title, ytd-video-renderer, ytd-rich-item-renderer, input, textarea, [title], [aria-label]"
        ));
        targetEl = allCandidates.find(el => {
          const t = (el.innerText || el.getAttribute("aria-label") || el.title || el.value || "").toLowerCase().trim();
          return t && t.includes(selNorm);
        });
      }

      if (!targetEl) {
        return { clicked: false, error: `Elemento '${sel}' não foi encontrado na página.` };
      }

      targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      targetEl.focus();
      targetEl.click();
      targetEl.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window }));
      targetEl.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window }));
      targetEl.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));

      const anchor = targetEl.tagName.toLowerCase() === 'a' ? targetEl : targetEl.closest('a');
      if (anchor && anchor.href && !anchor.href.includes('#')) {
        try { anchor.click(); } catch (_) {}
        if (location.host.includes("youtube.com") && (anchor.href.includes("/watch") || anchor.href.includes("/playlist"))) {
          setTimeout(() => {
            if (location.href !== anchor.href) {
              window.location.href = anchor.href;
            }
          }, 200);
        }
      }

      const label = (targetEl.innerText || targetEl.getAttribute("aria-label") || targetEl.title || "").trim().slice(0, 80);
      return { clicked: true, tag: targetEl.tagName, text: label, id: id || targetEl.getAttribute("data-agent-id") };
    }
  });

  return results?.[0]?.result || { clicked: true };
}

/**
 * DIGITAÇÃO INTELIGENTE POR ID NUMÉRICO OU SELETOR
 */
async function execType(selector, text, sendEnter, tabId) {
  let cleanSel = String(selector || "").trim();
  const numMatch = cleanSel.match(/^\[?(\d+)\]?$/);
  const targetId = numMatch ? parseInt(numMatch[1], 10) : null;

  const targetTab = await resolveTargetTab(tabId);
  if (!targetTab?.id) throw new Error("Nenhuma aba ativa para digitação.");

  const results = await chrome.scripting.executeScript({
    target: { tabId: targetTab.id },
    args: [cleanSel, targetId, text, Boolean(sendEnter)],
    func: (sel, id, val, enter) => {
      let input = null;
      if (id !== null) {
        if (window.__harveyElements && window.__harveyElements[id]) {
          input = window.__harveyElements[id];
        } else {
          input = document.querySelector(`[data-agent-id='${id}']`);
        }
      }

      if (!input) {
        if (sel.startsWith("#") || sel.startsWith(".") || sel.startsWith("[")) {
          try { input = document.querySelector(sel); } catch (_) {}
        }
      }

      if (!input) {
        input = document.querySelector("input[type='text'], input[type='search'], textarea, input:not([type='hidden'])");
      }

      if (!input) {
        return { typed: false, error: "Campo de texto não localizado: " + sel };
      }

      input.scrollIntoView({ behavior: 'smooth', block: 'center' });
      input.focus();
      input.value = val;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));

      if (enter) {
        input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", keyCode: 13, bubbles: true }));
        input.dispatchEvent(new KeyboardEvent("keypress", { key: "Enter", keyCode: 13, bubbles: true }));
        input.dispatchEvent(new KeyboardEvent("keyup", { key: "Enter", keyCode: 13, bubbles: true }));
        if (input.form) {
          try { input.form.submit(); } catch (_) {}
        }
      }

      return { typed: true, value: val, enterSent: enter, tag: input.tagName };
    }
  });

  return results?.[0]?.result || { typed: true };
}

/**
 * CONTROLE DE MÍDIA DIRETO (HTML5 + YOUTUBE PLAYER)
 */
async function execMediaControl(action, value, tabId) {
  const targetTab = await resolveTargetTab(tabId, "media");
  if (!targetTab?.id) throw new Error("Nenhuma aba ativa com mídia encontrada.");

  const results = await chrome.scripting.executeScript({
    target: { tabId: targetTab.id },
    args: [action, value],
    func: (act, val) => {
      let changed = false;

      const medias = Array.from(document.querySelectorAll("video, audio"));
      medias.forEach(m => {
        if (act === "pause") { m.pause(); changed = true; }
        else if (act === "play") { m.play(); changed = true; }
        else if (act === "volume" && val !== null && val !== undefined) { m.volume = Math.max(0, Math.min(1, val)); changed = true; }
        else if (act === "seek" && val !== null && val !== undefined) { m.currentTime = val; changed = true; }
      });

      try {
        const ytPlayer = document.getElementById("movie_player");
        if (ytPlayer) {
          if (act === "pause" && ytPlayer.pauseVideo) { ytPlayer.pauseVideo(); changed = true; }
          else if (act === "play" && ytPlayer.playVideo) { ytPlayer.playVideo(); changed = true; }
        }
      } catch (_) {}

      try {
        const playBtn = document.querySelector(".ytp-play-button");
        if (playBtn) {
          const title = (playBtn.getAttribute("data-title-no-tooltip") || playBtn.title || "").toLowerCase();
          const isCurrentlyPlaying = title.includes("paus") || title.includes("pause");
          if ((act === "pause" && isCurrentlyPlaying) || (act === "play" && !isCurrentlyPlaying)) {
            playBtn.click();
            changed = true;
          }
        }
      } catch (_) {}

      if (changed || medias.length > 0) {
        return { found: true, action: act, title: document.title, url: location.href };
      }

      return { found: false, error: "Nenhum elemento de mídia encontrado na aba '" + document.title + "'." };
    }
  });

  return results?.[0]?.result || { found: true };
}

async function execTabControl(action, tabId, url) {
  if (action === "open" && url) {
    const tab = await chrome.tabs.create({ url });
    if (tab.windowId) await chrome.windows.update(tab.windowId, { focused: true });
    return { opened: true, tab_id: tab.id };
  } else if (action === "activate" && tabId) {
    const updated = await chrome.tabs.update(tabId, { active: true });
    if (updated.windowId) await chrome.windows.update(updated.windowId, { focused: true });
    return { activated: true, tab_id: tabId };
  } else if (action === "close" && tabId) {
    await chrome.tabs.remove(tabId);
    return { closed: true, tab_id: tabId };
  } else if (action === "list") {
    const tabs = await collectTabs();
    return { tabs };
  }
  return { status: "invalid_action" };
}
