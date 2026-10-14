from dataclasses import dataclass
from typing import Any

import yaml


@dataclass
class SkillFrontmatter:
    id: str | None = None
    nome: str | None = None
    icone: str = ""
    tipo: str = "skill"
    modelo: str | None = None
    temperatura: float = 0.5
    ferramentas_permitidas: list[str] | None = None


def ler_frontmatter(conteudo: str) -> tuple[dict[str, Any], str]:
    """
    Extrai o Frontmatter YAML de uma Skill Markdown.

    Retorna:
        (configuracoes, corpo)
    """

    conteudo = conteudo.strip()

    if not conteudo.startswith("---"):
        return {}, conteudo

    partes = conteudo.split("---", 2)

    if len(partes) != 3:
        return {}, conteudo

    try:
        configuracoes = yaml.safe_load(partes[1]) or {}

        if not isinstance(configuracoes, dict):
            configuracoes = {}

        corpo = partes[2].strip()

        return configuracoes, corpo

    except yaml.YAMLError as erro:
        print(
            f"Erro ao interpretar Frontmatter YAML: {erro}"
        )
        return {}, conteudo


def normalizar_ferramentas(valor: Any) -> list[str]:
    """
    Garante que ferramentas_permitidas seja uma lista
    limpa de strings únicas.
    """

    if valor is None:
        return []

    if isinstance(valor, str):
        valor = valor.strip()

        return [valor] if valor else []

    if not isinstance(valor, list):
        return []

    resultado = []

    for item in valor:
        if not isinstance(item, str):
            continue

        item = item.strip()

        if item and item not in resultado:
            resultado.append(item)

    return resultado


def criar_configuracao(
    configuracoes: dict[str, Any]
) -> SkillFrontmatter:

    ferramentas = normalizar_ferramentas(
        configuracoes.get(
            "ferramentas_permitidas",
            []
        )
    )

    temperatura = configuracoes.get(
        "temperatura",
        0.5
    )

    try:
        temperatura = float(temperatura)
    except (TypeError, ValueError):
        temperatura = 0.5

    return SkillFrontmatter(
        id=(
            str(configuracoes["id"]).strip()
            if configuracoes.get("id") is not None
            else None
        ),
        nome=(
            str(configuracoes["nome"]).strip()
            if configuracoes.get("nome") is not None
            else None
        ),
        icone=str(
            configuracoes.get("icone", "")
        ),
        tipo=str(
            configuracoes.get("tipo", "skill")
        ),
        modelo=(
            str(configuracoes["modelo"]).strip()
            if configuracoes.get("modelo") is not None
            else None
        ),
        temperatura=temperatura,
        ferramentas_permitidas=ferramentas,
    )