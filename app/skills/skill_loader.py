from pathlib import Path
from dataclasses import dataclass


@dataclass
class SkillArquivo:
    id: str
    caminho: Path
    conteudo: str


IGNORAR_DIRETORIOS = {
    "assets",
    "images",
    "docs",
    "__pycache__",
}


class SkillLoader:
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir

    def descobrir_arquivos(self) -> list[Path]:
        if not self.skills_dir.exists():
            return []

        arquivos = []

        for caminho in self.skills_dir.rglob("*"):
            if not caminho.is_file():
                continue

            if caminho.suffix.lower() not in {".md", ".txt"}:
                continue

            if any(
                parte.lower() in IGNORAR_DIRETORIOS
                for parte in caminho.relative_to(self.skills_dir).parts[:-1]
            ):
                continue

            arquivos.append(caminho)

        return sorted(
            arquivos,
            key=lambda caminho: str(caminho).casefold()
        )

    def identificar_id(self, caminho: Path) -> str:
        # Futuramente:
        # skills/minha_skill/SKILL.md -> minha_skill
        if caminho.name.lower() == "skill.md":
            return caminho.parent.name

        # Compatibilidade atual:
        # skills/minha_skill.md -> minha_skill
        return caminho.stem

    def carregar_arquivo(self, caminho: Path) -> SkillArquivo:
        conteudo = caminho.read_text(
            encoding="utf-8"
        )

        return SkillArquivo(
            id=self.identificar_id(caminho),
            caminho=caminho,
            conteudo=conteudo,
        )

    def carregar_todas(self) -> list[SkillArquivo]:
        skills = []

        for caminho in self.descobrir_arquivos():
            try:
                skills.append(
                    self.carregar_arquivo(caminho)
                )
            except (OSError, UnicodeError):
                continue

        return skills