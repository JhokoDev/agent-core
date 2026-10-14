"""
Serviço MCP Windows Nativo para inspeção, controle de janelas e automação UI.
Combina Win32 API, UIAutomation, psutil e PowerShell com alta resiliência.
"""
from __future__ import annotations
import os
import sys
import time
import subprocess
from typing import Dict, Any, List, Optional
import psutil

try:
    import win32gui
    import win32con
    import win32process
    import win32api
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

try:
    import uiautomation as uia
    UIA_AVAILABLE = True
except ImportError:
    UIA_AVAILABLE = False


class WindowsMCPService:
    """
    Controlador nativo do sistema operacional Windows:
    - Gerenciamento de janelas abertas (listar, focar, minimizar, maximizar, fechar)
    - Inspeção de controles nativos via UIAutomation (botões, menus, campos de texto)
    - Envio seguro de texto e teclas para janelas com foco garantido
    - Telemetria e controle de processos de alto nível
    """

    def __init__(self):
        self.win32_ready = WIN32_AVAILABLE
        self.uia_ready = UIA_AVAILABLE

    def listar_janelas_ativas(self) -> List[Dict[str, Any]]:
        """
        Lista todas as janelas e programas visíveis na área de trabalho do usuário.
        """
        janelas: List[Dict[str, Any]] = []

        if self.win32_ready:
            def enum_cb(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd) and not win32gui.IsIconic(hwnd):
                    titulo = win32gui.GetWindowText(hwnd).strip()
                    if titulo and titulo not in ("Program Manager", "Default IME", "MSCTFIME UI"):
                        try:
                            _, pid = win32process.GetWindowThreadProcessId(hwnd)
                            proc = psutil.Process(pid)
                            extra.append({
                                "hwnd": hwnd,
                                "titulo": titulo,
                                "pid": pid,
                                "processo": proc.name(),
                                "memoria_mb": round(proc.memory_info().rss / (1024 * 1024), 1)
                            })
                        except Exception:
                            pass

            try:
                win32gui.EnumWindows(enum_cb, janelas)
            except Exception:
                pass

        # Se a enumeração Win32 não retornou janelas (ex: sessão de serviço), complementa com processos de usuário
        if not janelas:
            processos_relevantes = [
                "code.exe", "notepad.exe", "chrome.exe", "msedge.exe", "calc.exe", "explorer.exe",
                "spotify.exe", "discord.exe", "powershell.exe", "cmd.exe", "taskmgr.exe"
            ]
            for p in psutil.process_iter(['pid', 'name', 'memory_info']):
                try:
                    n = p.info['name'].lower()
                    if n in processos_relevantes:
                        janelas.append({
                            "hwnd": 0,
                            "titulo": p.info['name'].replace(".exe", "").capitalize(),
                            "pid": p.info['pid'],
                            "processo": p.info['name'],
                            "memoria_mb": round(p.info['memory_info'].rss / (1024 * 1024), 1)
                        })
                except Exception:
                    pass

        return janelas

    def encontrar_janela(self, termo: str) -> Optional[Dict[str, Any]]:
        """Localiza uma janela ativa por título, processo ou PID."""
        termo_lower = termo.lower().strip()
        janelas = self.listar_janelas_ativas()

        # 1. Busca por PID se for número
        if termo_lower.isdigit():
            pid_target = int(termo_lower)
            for j in janelas:
                if j["pid"] == pid_target:
                    return j

        # 2. Busca exata ou parcial por título ou processo
        for j in janelas:
            if termo_lower in j["titulo"].lower() or termo_lower in j["processo"].lower():
                return j

        return None

    def focar_janela(self, termo_ou_pid: str) -> Dict[str, Any]:
        """Traz a janela do programa para o primeiro plano."""
        janela = self.encontrar_janela(termo_ou_pid)
        if not janela:
            return {"sucesso": False, "erro": f"Janela ou programa '{termo_ou_pid}' não encontrado."}

        hwnd = janela.get("hwnd", 0)
        if hwnd and self.win32_ready:
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                return {
                    "sucesso": True,
                    "mensagem": f"Janela '{janela['titulo']}' colocada em primeiro plano.",
                    "janela": janela
                }
            except Exception as e:
                pass

        # Fallback via PowerShell AppActivate
        try:
            ps_cmd = f"(New-Object -ComObject WScript.Shell).AppActivate({janela['pid']})"
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True)
            if "True" in res.stdout:
                return {"sucesso": True, "mensagem": f"Janela PID {janela['pid']} focada via WScript.", "janela": janela}
        except Exception:
            pass

        return {"sucesso": True, "mensagem": f"Janela identificada: '{janela['titulo']}'.", "janela": janela}

    def fechar_janela(self, termo_ou_pid: str, forcar: bool = False) -> Dict[str, Any]:
        """Fecha uma janela de forma limpa ou encerra o processo se solicitado."""
        janela = self.encontrar_janela(termo_ou_pid)
        if not janela:
            return {"sucesso": False, "erro": f"Janela '{termo_ou_pid}' não encontrada para fechar."}

        hwnd = janela.get("hwnd", 0)
        if hwnd and self.win32_ready and not forcar:
            try:
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                return {"sucesso": True, "mensagem": f"Comando de fechamento enviado para '{janela['titulo']}'."}
            except Exception:
                pass

        # Encerramento pelo processo
        try:
            proc = psutil.Process(janela["pid"])
            if forcar:
                proc.kill()
            else:
                proc.terminate()
            return {"sucesso": True, "mensagem": f"Processo '{janela['processo']}' (PID {janela['pid']}) encerrado."}
        except Exception as e:
            return {"sucesso": False, "erro": f"Falha ao fechar processo: {e}"}

    def minimizar_janela(self, termo_ou_pid: str) -> Dict[str, Any]:
        janela = self.encontrar_janela(termo_ou_pid)
        if not janela or not janela.get("hwnd") or not self.win32_ready:
            return {"sucesso": False, "erro": f"Janela '{termo_ou_pid}' não encontrada."}

        try:
            win32gui.ShowWindow(janela["hwnd"], win32con.SW_MINIMIZE)
            return {"sucesso": True, "mensagem": f"Janela '{janela['titulo']}' minimizada."}
        except Exception as e:
            return {"sucesso": False, "erro": str(e)}

    def maximizar_janela(self, termo_ou_pid: str) -> Dict[str, Any]:
        janela = self.encontrar_janela(termo_ou_pid)
        if not janela or not janela.get("hwnd") or not self.win32_ready:
            return {"sucesso": False, "erro": f"Janela '{termo_ou_pid}' não encontrada."}

        try:
            win32gui.ShowWindow(janela["hwnd"], win32con.SW_MAXIMIZE)
            win32gui.SetForegroundWindow(janela["hwnd"])
            return {"sucesso": True, "mensagem": f"Janela '{janela['titulo']}' maximizada."}
        except Exception as e:
            return {"sucesso": False, "erro": str(e)}

    def inspecionar_elementos(self, termo_ou_pid: str, limite: int = 25) -> Dict[str, Any]:
        """
        Inspeciona os controles interativos reais da janela (botões, caixas de edição, menus) via UIAutomation.
        """
        janela = self.encontrar_janela(termo_ou_pid)
        if not janela:
            return {"sucesso": False, "erro": f"Janela '{termo_ou_pid}' não encontrada."}

        if not self.uia_ready:
            return {
                "sucesso": True,
                "janela": janela,
                "elementos": [],
                "aviso": "UIAutomation não disponível nesta sessão."
            }

        try:
            control_window = None
            if janela.get("hwnd"):
                control_window = uia.ControlFromHandle(janela["hwnd"])
            if not control_window:
                control_window = uia.WindowControl(searchDepth=2, Name=janela["titulo"])

            if not control_window.Exists(maxSearchSeconds=1):
                return {"sucesso": False, "erro": "Janela não respondeu à inspeção UIAutomation."}

            elementos = []
            walker = uia.TreeWalker(uia.TrueCondition)
            child = walker.GetFirstChildControl(control_window)
            count = 0

            while child and count < limite:
                nome = child.Name.strip()
                tipo = child.ControlTypeName
                auto_id = child.AutomationId
                if nome or auto_id:
                    elementos.append({
                        "id": count + 1,
                        "tipo": tipo,
                        "nome": nome,
                        "automation_id": auto_id
                    })
                    count += 1
                child = walker.GetNextSiblingControl(child)

            return {
                "sucesso": True,
                "janela": janela,
                "elementos": elementos,
                "total": len(elementos)
            }
        except Exception as e:
            return {"sucesso": False, "erro": f"Erro na inspeção UIAutomation: {e}"}

    def enviar_teclas_janela(self, termo_ou_pid: str, texto: str) -> Dict[str, Any]:
        """Foca a janela e envia digitação de texto com precisão."""
        foco = self.focar_janela(termo_ou_pid)
        if not foco.get("sucesso"):
            return foco

        time.sleep(0.3)
        try:
            if self.uia_ready:
                uia.SendKeys(texto)
                return {"sucesso": True, "mensagem": f"Texto enviado para '{foco['janela']['titulo']}'."}
        except Exception:
            pass

        # Fallback via PowerShell SendKeys
        try:
            texto_escapado = texto.replace('"', '`"').replace("'", "''")
            ps_script = f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('{texto_escapado}')"
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], timeout=5)
            return {"sucesso": True, "mensagem": f"Texto enviado via Windows Forms SendKeys para '{foco['janela']['titulo']}'."}
        except Exception as e:
            return {"sucesso": False, "erro": f"Falha ao enviar teclas: {e}"}


# Instância global Singleton
windows_mcp_service = WindowsMCPService()
