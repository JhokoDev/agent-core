import os
import json
from pathlib import Path
from typing import Dict

from app.api.schemas import AgenteInfo
from app.skills.skill_loader import SkillLoader
from app.skills.skill_frontmatter import (
    ler_frontmatter,
    criar_configuracao,
)


agentes_db: Dict[str, AgenteInfo] = {}


# ==========================================
# CARREGAMENTO PRINCIPAL
# ==========================================

def carregar_arquivos():

    modelo_padrao = os.getenv(
        "AGENT_MODEL",
        "qwen2.5:1.5b"
    )

    # Limpa o estado anterior antes de recarregar
    agentes_db.clear()

    # ==========================================
    # SKILL DEFAULT
    # ==========================================

    agentes_db["default"] = AgenteInfo(
        id="default",
        nome="Assistente PadrÃ£o",
        icone="",
        tipo="padrao",
        modelo="llama3.2",
        temperatura=0.2,
        prompt_sistema=(
            "VocÃª Ã© um assistente pessoal Ãºtil e direto."
        ),
        ferramentas_permitidas=[]
    )

    # ==========================================
    # GARANTIR DIRETÃ“RIOS
    # ==========================================

    for pasta in [
        "skills",
        "tools",
        "data",
        "projetos"
    ]:
        os.makedirs(
            pasta,
            exist_ok=True
        )

    # ==========================================
    # CARREGAMENTO DE SKILLS
    # ==========================================

    loader = SkillLoader(
        Path("skills")
    )

    for skill_arquivo in loader.carregar_todas():

        try:

            conteudo = skill_arquivo.conteudo.strip()

            if not conteudo:
                continue

            skill_id_padrao = skill_arquivo.id

            if skill_id_padrao.lower() in [
                "assets",
                "images",
                "docs",
                "readme",
            ]:
                continue

            # ==========================================
            # FRONTMATTER
            # ==========================================

            configuracoes, prompt_final = ler_frontmatter(
                conteudo
            )

            config = criar_configuracao(
                configuracoes
            )

            # ==========================================
            # IDENTIDADE DA SKILL
            # ==========================================

            skill_id = (
                config.id
                or skill_id_padrao
            )

            nome = (
                config.nome
                or skill_id.replace(
                    "_",
                    " "
                ).replace(
                    "-",
                    " "
                ).title()
            )

            icone = config.icone

            tipo = config.tipo

            # ==========================================
            # CONFIGURAÃ‡ÃƒO DO MODELO
            # ==========================================

            modelo_final = (
                config.modelo
                or modelo_padrao
            )

            temperatura_final = (
                config.temperatura
            )

            # ==========================================
            # FERRAMENTAS PERMITIDAS
            # ==========================================

            ferramentas_permitidas = (
                config.ferramentas_permitidas
                or []
            )

            # ==========================================
            # REGISTRAR SKILL
            # ==========================================

            agentes_db[skill_id] = AgenteInfo(
                id=skill_id,
                nome=nome,
                icone=icone,
                tipo=tipo,
                modelo=modelo_final,
                temperatura=temperatura_final,
                prompt_sistema=prompt_final,
                ferramentas_permitidas=(
                    ferramentas_permitidas
                )
            )

        except Exception as erro:

            print(
                f"Erro ao carregar Skill "
                f"{skill_arquivo.caminho}: {erro}"
            )

    # ==========================================
    # CARREGAMENTO DE TOOLS
    # ==========================================

    for arquivo in os.listdir("tools"):

        if not arquivo.endswith(".md"):
            continue

        caminho = os.path.join(
            "tools",
            arquivo
        )

        try:

            with open(
                caminho,
                "r",
                encoding="utf-8"
            ) as f:

                conteudo = f.read().strip()

            configuracoes, prompt_tool = (
                ler_frontmatter(
                    conteudo
                )
            )

            if not configuracoes:
                continue

            tool_id = configuracoes.get(
                "id",
                arquivo.rsplit(
                    ".",
                    1
                )[0]
            )

            try:

                temperatura_tool = float(
                    configuracoes.get(
                        "temperatura",
                        0.7
                    )
                )

            except (
                TypeError,
                ValueError
            ):

                temperatura_tool = 0.7

            agentes_db[tool_id] = AgenteInfo(
                id=str(tool_id),

                nome=str(
                    configuracoes.get(
                        "nome",
                        "Tool"
                    )
                ),

                icone=str(
                    configuracoes.get(
                        "icone",
                        ""
                    )
                ),

                tipo="tool",

                modelo=str(
                    configuracoes.get(
                        "modelo",
                        modelo_padrao
                    )
                ),

                temperatura=temperatura_tool,

                prompt_sistema=prompt_tool,

                ferramentas_permitidas=[]
            )

        except Exception as erro:

            print(
                f"Erro ao carregar Tool "
                f"{caminho}: {erro}"
            )


# ==========================================
# INICIALIZAÃ‡ÃƒO
# ==========================================

carregar_arquivos()


# ==========================================
# CONSULTAS
# ==========================================

def listar_todos_agentes():

    return [
        {
            "id": agente.id,
            "nome": agente.nome,
            "icone": agente.icone,
            "tipo": agente.tipo
        }
        for agente in agentes_db.values()
    ]


def obter_agente(agente_id: str):

    agente = agentes_db.get(
        agente_id
    )

    if agente is None:
        return None

    return agente.model_dump()


# ==========================================
# HISTÃ“RICO
# ==========================================

def listar_historico_chats():

    chats = []

    if not os.path.exists("data"):
        return chats

    for arquivo in os.listdir("data"):

        if not arquivo.endswith(".json"):
            continue

        caminho = os.path.join(
            "data",
            arquivo
        )

        try:

            with open(
                caminho,
                "r",
                encoding="utf-8"
            ) as f:

                dados = json.load(f)

            chats.append(
                {
                    "id": dados.get("id"),

                    "titulo": dados.get(
                        "titulo",
                        "Novo Chat"
                    ),

                    "atualizado_em": os.path.getmtime(
                        caminho
                    )
                }
            )

        except Exception:
            continue

    chats.sort(
        key=lambda x: x["atualizado_em"],
        reverse=True
    )

    return chats


def obter_chat(chat_id: str):

    caminho = os.path.join(
        "data",
        f"{chat_id}.json"
    )

    if not os.path.exists(caminho):
        return None

    with open(
        caminho,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ==========================================
# PERSISTÃŠNCIA DE CHAT
# ==========================================

def salvar_chat(
    chat_id: str,
    chat_data: dict
):

    os.makedirs(
        "data",
        exist_ok=True
    )

    caminho = os.path.join(
        "data",
        f"{chat_id}.json"
    )

    with open(
        caminho,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            chat_data,
            f,
            ensure_ascii=False,
            indent=2
        )
