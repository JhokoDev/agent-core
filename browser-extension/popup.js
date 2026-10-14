document.addEventListener("DOMContentLoaded", async () => {
  const statusBadge = document.getElementById("statusBadge");
  const statusText = document.getElementById("statusText");
  const serverUrlInput = document.getElementById("serverUrl");
  const tokenInput = document.getElementById("token");
  const pairCodeInput = document.getElementById("pairCode");
  const btnConnect = document.getElementById("btnConnect");
  const btnCheckTabs = document.getElementById("btnCheckTabs");

  // Consulta o estado inicial do service worker
  chrome.runtime.sendMessage({ action: "get_status" }, (res) => {
    if (res && res.config) {
      serverUrlInput.value = res.config.serverUrl || "http://127.0.0.1:8001";
      tokenInput.value = res.config.token || "PqBeTC3OO69SHxZ2RBsb57AIwkXuoUIJbUdsnnpyf-Y";
      pairCodeInput.value = res.config.pairCode || "AGENT-CORE";
      updateStatus(res.config.connected);
    }
  });

  function updateStatus(connected, tabCount) {
    if (connected) {
      statusBadge.className = "badge connected";
      statusText.textContent = tabCount !== undefined ? `Conectado (${tabCount} abas)` : "Conectado";
    } else {
      statusBadge.className = "badge disconnected";
      statusText.textContent = "Desconectado";
    }
  }

  btnConnect.addEventListener("click", () => {
    const data = {
      serverUrl: serverUrlInput.value.trim(),
      token: tokenInput.value.trim(),
      pairCode: pairCodeInput.value.trim()
    };
    btnConnect.textContent = "Sincronizando...";
    chrome.runtime.sendMessage({ action: "save_config", data }, (res) => {
      btnConnect.textContent = "Salvar & Sincronizar";
      if (res && res.success) {
        updateStatus(res.authorized, res.tabCount);
      } else {
        updateStatus(false);
      }
    });
  });

  btnCheckTabs.addEventListener("click", () => {
    btnCheckTabs.textContent = "Consultando...";
    chrome.runtime.sendMessage({ action: "sync_now" }, (res) => {
      btnCheckTabs.textContent = "Atualizar Abas Conectadas";
      if (res && res.success) {
        updateStatus(res.authorized, res.tabCount);
      }
    });
  });
});
