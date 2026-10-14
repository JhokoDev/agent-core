import os
import re
import json
import shutil
import winreg
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CAMINHO_COMANDOS = BASE_DIR / "comandos_pc.json"

# Catálogo de programas populares que possuem versão web oficial
PROGRAMAS_WEB: Dict[str, str] = {
    "whatsapp": "https://web.whatsapp.com",
    "whatsapp web": "https://web.whatsapp.com",
    "discord": "https://discord.com/app",
    "discord web": "https://discord.com/app",
    "spotify": "https://open.spotify.com",
    "spotify web": "https://open.spotify.com",
    "notion": "https://www.notion.so",
    "figma": "https://www.figma.com",
    "trello": "https://trello.com",
    "canva": "https://www.canva.com",
    "slack": "https://app.slack.com",
    "telegram": "https://web.telegram.org",
    "telegram web": "https://web.telegram.org",
    "chatgpt": "https://chatgpt.com",
    "youtube": "https://youtube.com",
    "google": "https://google.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "google drive": "https://drive.google.com",
    "drive": "https://drive.google.com",
    "google docs": "https://docs.google.com",
    "docs": "https://docs.google.com",
    "google sheets": "https://sheets.google.com",
    "sheets": "https://sheets.google.com",
    "netflix": "https://netflix.com",
    "twitch": "https://twitch.tv",
    "reddit": "https://reddit.com",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "instagram": "https://instagram.com",
    "linkedin": "https://linkedin.com",
    "zoom": "https://zoom.us/join",
    "teams": "https://teams.microsoft.com",
    "onshape": "https://cad.onshape.com",
    "roblox": "https://www.roblox.com",
}


def resolver_caminho_chrome() -> Optional[str]:
    """Localiza o executável do Google Chrome no Windows."""
    c = shutil.which("chrome") or shutil.which("chrome.exe")
    if c:
        return c

    locais = [
        Path(os.environ.get("PROGRAMFILES", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
    ]
    for loc in locais:
        if loc.exists():
            return str(loc)
    return None


def buscar_no_registro_windows(nome_programa: str) -> Optional[str]:
    """
    Busca o executável no Registro do Windows (App Paths).
    Essa é a forma oficial que o Windows usa para encontrar programas no 'Executar' (Win+R).
    """
    nome_alvo = nome_programa.lower().replace(" ", "")
    for root in [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]:
        try:
            with winreg.OpenKey(root, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths") as key:
                num_subkeys = winreg.QueryInfoKey(key)[0]
                for i in range(num_subkeys):
                    subkey_name = winreg.EnumKey(key, i)
                    subkey_clean = subkey_name.lower().replace(".exe", "").replace(" ", "")
                    if nome_alvo == subkey_clean or (len(nome_alvo) >= 4 and nome_alvo in subkey_clean):
                        try:
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                val, _ = winreg.QueryValueEx(subkey, "")
                                val_limpo = val.strip().strip('"')
                                if val_limpo and Path(val_limpo).exists():
                                    return val_limpo
                        except Exception:
                            continue
        except Exception:
            continue
    return None


def buscar_no_menu_iniciar(nome_programa: str) -> Optional[str]:
    """Vasculha atalhos (.lnk) no Menu Iniciar do Windows."""
    nome_alvo = nome_programa.lower().strip()
    pastas_iniciar = [
        Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    ]

    candidatos = []
    for pasta in pastas_iniciar:
        if not pasta.exists():
            continue
        try:
            for atalho in pasta.rglob("*.lnk"):
                nome_base = atalho.stem.lower()
                if nome_alvo == nome_base or nome_alvo in nome_base:
                    if nome_alvo == nome_base:
                        return str(atalho)
                    candidatos.append(str(atalho))
        except Exception:
            continue

    if candidatos:
        return candidatos[0]
    return None


def buscar_em_pastas_instalacao(nome_programa: str) -> Optional[str]:
    """
    Procura executáveis em diretórios comuns de programas e AppData:
    %LOCALAPPDATA%, %APPDATA%, %PROGRAMFILES%, %PROGRAMFILES(X86)%.
    Suporta instaladores modernos Squirrel (Discord, Spotify, etc.).
    """
    nome_alvo = nome_programa.lower().strip().replace(" ", "")
    pastas_base = [
        Path(os.environ.get("LOCALAPPDATA", "")),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs",
        Path(os.environ.get("APPDATA", "")),
        Path(os.environ.get("PROGRAMFILES", "")),
        Path(os.environ.get("ProgramFiles(x86)", ""))
    ]

    for p_base in pastas_base:
        if not p_base.exists():
            continue
        try:
            for sub in p_base.iterdir():
                if not sub.is_dir():
                    continue
                sub_clean = sub.name.lower().replace(" ", "")
                if nome_alvo == sub_clean or (len(nome_alvo) >= 4 and nome_alvo in sub_clean):
                    # 1. Checa executável direto na pasta
                    exe_direto = sub / f"{sub.name}.exe"
                    if exe_direto.exists():
                        return str(exe_direto)

                    exe_alvo = sub / f"{nome_alvo}.exe"
                    if exe_alvo.exists():
                        return str(exe_alvo)

                    # 2. Checa em subpastas com versão (ex: app-1.0.9251/Discord.exe)
                    exes_sub = sorted(sub.glob("**/*.exe"), reverse=True)
                    for exe in exes_sub:
                        if exe.stem.lower() == nome_alvo:
                            return str(exe)
        except Exception:
            continue
    return None


def buscar_instalacao_local(nome_programa: str) -> Optional[Tuple[str, str]]:
    """Procura se o programa está instalado localmente no computador."""
    # 1. Registro (App Paths)
    reg_exe = buscar_no_registro_windows(nome_programa)
    if reg_exe:
        return reg_exe, "nativo_registro"

    # 2. Pastas de Instalação (AppData, Program Files)
    pasta_exe = buscar_em_pastas_instalacao(nome_programa)
    if pasta_exe:
        return pasta_exe, "nativo_pasta"

    # 3. Menu Iniciar (.lnk)
    lnk = buscar_no_menu_iniciar(nome_programa)
    if lnk:
        return lnk, "nativo_menu_iniciar"

    # 4. PATH do sistema
    which_p = shutil.which(nome_programa) or shutil.which(f"{nome_programa}.exe")
    if which_p:
        return which_p, "nativo_path"

    return None


def descobrir_comando(nome_programa: str) -> Optional[Tuple[str, str, str]]:
    """
    Descobre como executar um programa requisitado.
    Estratégia híbrida inteligente:
    1. Se o usuário pedir expressamente versão web (ex: 'discord web', 'whatsapp web'):
       -> Abre diretamente no Chrome.
    2. Se o programa ESTÁ instalado localmente no computador:
       -> Abre o aplicativo nativo da máquina!
    3. Se NÃO estiver instalado localmente, mas tiver versão web conhecida (ou for ferramenta web):
       -> Abre a versão web no Google Chrome!
    4. Fallback de URL/Domínio: abre no Chrome.
    """
    termo = nome_programa.lower().strip()
    for prefixo in ["abrir_", "abrir ", "abrir", "abra_", "abra ", "abra", "iniciar_", "iniciar ", "iniciar", "inicie ", "execute_", "execute ", "execute", "executar "]:
        if termo.startswith(prefixo) and len(termo) > len(prefixo):
            termo = termo[len(prefixo):].strip(" _-")
            break

    chave_sugerida = f"abrir_{termo.replace(' ', '_').replace('-', '_')}"

    # Caso 1: Usuário pediu explicitamente versão Web (ex: "discord web", "whatsapp web")
    quer_web_explicito = "web" in termo or any(s in termo for s in [".com", ".org", "http://", "https://"])
    if quer_web_explicito:
        nome_sem_web = termo.replace("web", "").strip()
        url = PROGRAMAS_WEB.get(termo) or PROGRAMAS_WEB.get(nome_sem_web)
        if not url and any(s in termo for s in [".com", ".org", "http"]):
            url = termo if termo.startswith("http") else f"https://{termo}"

        if url:
            return chave_sugerida, url, "web_playwright_mcp"

    # Caso 2: Procura se o programa existe localmente no computador
    local = buscar_instalacao_local(termo)
    if local:
        caminho_local, tipo_local = local
        return chave_sugerida, caminho_local, tipo_local

    # Caso 3: Não encontrado localmente, mas possui versão Web oficial conhecida
    if termo in PROGRAMAS_WEB:
        url = PROGRAMAS_WEB[termo]
        return chave_sugerida, url, "web_playwright_mcp"

    # Caso 4: Fallback se for um domínio/site direto
    if any(sufixo in termo for sufixo in [".com", ".org", ".net", ".io", "http://", "https://"]):
        url = termo if termo.startswith("http") else f"https://{termo}"
        return chave_sugerida, url, "web_playwright_mcp"

    return None


def aprender_e_registrar_comando(nome_programa: str) -> Dict[str, Any]:
    """
    Executa o ciclo de auto-aprendizado:
    1. Descobre como abrir o programa.
    2. Se for aplicativo nativo local, persiste em comandos_pc.json.
    3. Se for serviço web, sinaliza para navegação via Playwright MCP Bridge.
    4. Retorna o resultado detalhado.
    """
    descoberta = descobrir_comando(nome_programa)
    if not descoberta:
        return {
            "sucesso": False,
            "chave": None,
            "comando": None,
            "tipo": None,
            "mensagem": f"Não foi possível encontrar o programa '{nome_programa}' no sistema nem em serviços web conhecidos."
        }

    chave, comando, tipo = descoberta

    # Se for nativo, persiste no comandos_pc.json
    if tipo != "web_playwright_mcp":
        comandos = {}
        if CAMINHO_COMANDOS.exists():
            try:
                with open(CAMINHO_COMANDOS, "r", encoding="utf-8") as f:
                    comandos = json.load(f)
            except Exception:
                comandos = {}

        comandos[chave] = comando

        try:
            with open(CAMINHO_COMANDOS, "w", encoding="utf-8") as f:
                json.dump(comandos, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Discovery Error] Não foi possível salvar comandos_pc.json: {e}")
            return {
                "sucesso": False,
                "chave": chave,
                "comando": comando,
                "tipo": tipo,
                "mensagem": f"Comando descoberto, mas falhou ao gravar no comandos_pc.json: {e}"
            }


    try:
        from launcher import registrar_log
        registrar_log(f"[PC-LEARN] Novo comando aprendido: {chave} -> {comando} ({tipo})")
    except Exception:
        pass

    return {
        "sucesso": True,
        "chave": chave,
        "comando": comando,
        "tipo": tipo,
        "mensagem": f"Comando '{chave}' aprendido com sucesso ({tipo})."
    }
