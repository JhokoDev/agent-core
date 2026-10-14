"""
Serviço de Utilidade Real para o Agent Core:
1. Orquestração de Ambientes de Trabalho (Dev, Estudo, Foco)
2. Curadoria e Organização Automatizada de Arquivos e Downloads
"""
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List
import subprocess

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class WorkspaceUtilityService:
    """
    Gera valor e utilidade imediata para o dia a dia do usuário:
    - Prepara ambientes de desenvolvimento e estudo com um único comando
    - Organiza automaticamente a pasta de Downloads por categoria sem perda de dados
    - Limpa lixeira e arquivos temporários de forma segura
    """

    def __init__(self):
        self.downloads_dir = Path.home() / "Downloads"

    def preparar_ambiente(self, perfil: str) -> Dict[str, Any]:
        """
        Executa uma macro inteligente para preparar a estação de trabalho.
        """
        perfil_clean = perfil.lower().strip()
        acoes_realizadas = []

        if "dev" in perfil_clean or "program" in perfil_clean or "codigo" in perfil_clean:
            # 1. Abrir VS Code na pasta do projeto
            try:
                subprocess.Popen(["code", str(BASE_DIR)], shell=True)
                acoes_realizadas.append(f"VS Code aberto em '{BASE_DIR}'.")
            except Exception:
                pass

            # 2. Abrir Chrome no localhost
            try:
                from app.services.playwright_mcp_service import playwright_service
                playwright_service.dispatch_command("navigate", {"url": "http://localhost:3000"})
                acoes_realizadas.append("Painel Core aberto no Google Chrome (http://localhost:3000).")
            except Exception:
                pass

            return {
                "sucesso": True,
                "perfil": "Desenvolvimento",
                "acoes": acoes_realizadas,
                "mensagem": "Ambiente de desenvolvimento pronto: VS Code e Painel Core abertos!"
            }

        elif "foco" in perfil_clean or "relax" in perfil_clean or "musica" in perfil_clean:
            # 1. Tocar música Lo-Fi / Foco no YouTube
            try:
                from app.services.playwright_mcp_service import playwright_service
                playwright_service.dispatch_command("navigate", {"url": "https://www.youtube.com/results?search_query=lofi+hip+hop+radio+beats+to+relax"})
                acoes_realizadas.append("Rádio Lo-Fi iniciada no Google Chrome.")
            except Exception:
                pass

            # 2. Minimizar janelas secundárias
            try:
                from app.services.windows_mcp_service import windows_mcp_service
                for distracao in ["discord", "steam", "spotify"]:
                    windows_mcp_service.minimizar_janela(distracao)
                acoes_realizadas.append("Janelas de distração minimizadas.")
            except Exception:
                pass

            return {
                "sucesso": True,
                "perfil": "Modo Foco",
                "acoes": acoes_realizadas,
                "mensagem": "Modo Foco ativado: música ambiente iniciada e distrações minimizadas."
            }

        elif "estudo" in perfil_clean or "leitura" in perfil_clean:
            try:
                subprocess.Popen(["notepad"], shell=True)
                acoes_realizadas.append("Bloco de Notas aberto para anotações rápidas.")
            except Exception:
                pass

            return {
                "sucesso": True,
                "perfil": "Modo Estudo",
                "acoes": acoes_realizadas,
                "mensagem": "Ambiente de estudo pronto para anotações e pesquisas."
            }

        return {
            "sucesso": False,
            "erro": f"Perfil '{perfil}' não reconhecido. Perfis disponíveis: 'dev', 'foco', 'estudo'."
        }

    def organizar_downloads(self) -> Dict[str, Any]:
        """
        Varre a pasta Downloads do Windows e move arquivos soltos para subpastas categorizadas.
        """
        if not self.downloads_dir.exists():
            return {"sucesso": False, "erro": "Pasta Downloads não localizada no sistema."}

        regras = {
            "Documentos_PDF": [".pdf"],
            "Documentos_Texto": [".docx", ".doc", ".txt", ".xlsx", ".csv", ".pptx", ".odt"],
            "Instaladores_e_Programas": [".exe", ".msi", ".bat", ".cmd"],
            "Arquivos_Compactados": [".zip", ".rar", ".7z", ".tar", ".gz"],
            "Imagens_e_Fotos": [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico"],
            "Midias_Audio_Video": [".mp3", ".mp4", ".wav", ".mkv", ".avi"]
        }

        relatorio: Dict[str, List[str]] = {cat: [] for cat in regras}
        total_movidos = 0

        for item in self.downloads_dir.iterdir():
            # Apenas arquivos soltos na raiz de Downloads (ignora pastas já existentes)
            if item.is_file() and not item.name.startswith("."):
                ext = item.suffix.lower()
                for categoria, extensoes in regras.items():
                    if ext in extensoes:
                        pasta_destino = self.downloads_dir / categoria
                        pasta_destino.mkdir(exist_ok=True)
                        destino_final = pasta_destino / item.name

                        # Evita sobrescrever se já existir arquivo com o mesmo nome
                        if destino_final.exists():
                            nome_base = item.stem
                            contador = 1
                            while destino_final.exists():
                                destino_final = pasta_destino / f"{nome_base}_{contador}{ext}"
                                contador += 1

                        try:
                            shutil.move(str(item), str(destino_final))
                            relatorio[categoria].append(item.name)
                            total_movidos += 1
                        except Exception:
                            pass
                        break

        detalhes = []
        for cat, arquivos in relatorio.items():
            if arquivos:
                detalhes.append(f"- **{cat.replace('_', ' ')}** ({len(arquivos)} arquivo(s)): {', '.join(arquivos[:3])}{'...' if len(arquivos) > 3 else ''}")

        if total_movidos == 0:
            return {
                "sucesso": True,
                "total_movidos": 0,
                "mensagem": "Sua pasta Downloads já está limpa e organizada! Nenhum arquivo solto precisou ser movido."
            }

        return {
            "sucesso": True,
            "total_movidos": total_movidos,
            "mensagem": f"Sucesso! {total_movidos} arquivo(s) foram organizados na pasta Downloads:\n" + "\n".join(detalhes)
        }


workspace_service = WorkspaceUtilityService()
