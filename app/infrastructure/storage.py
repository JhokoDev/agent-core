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

        nome="Assistente Geral",

        icone="🤖",
        tipo="padrao",

        modelo="llama3.2",

        temperatura=0.2,

        prompt_sistema=(
            "Você é um assistente pessoal útil e direto."

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

# ==========================================

# HISTÓRICO DE CHATS

# ==========================================

def listar_historico_chats():

    chats = []

    if not os.path.exists("data"):

        return chats

    for arquivo in os.listdir("data"):

        if not arquivo.endswith(".json"):

            continue

        caminho = os.path.join("data", arquivo)

        try:

            with open(caminho, "r", encoding="utf-8") as f:

                dados = json.load(f)

            if not isinstance(dados, dict):

                continue

            # Filtra apenas arquivos de chat reais (ignora config, relay_state, notas, etc)

            chat_id = dados.get("id")

            if not chat_id and arquivo.startswith("chat_"):

                chat_id = arquivo.replace(".json", "")

            if not chat_id or "messages" not in dados:

                continue

            messages = dados.get("messages", [])

            # Extrai ou gera título inteligente a partir da primeira mensagem de usuário

            titulo = dados.get("titulo")

            if not titulo or titulo == "Novo Chat":

                for msg in messages:

                    if msg.get("role") == "user" and msg.get("content"):

                        raw = msg["content"].strip().replace("\n", " ")

                        titulo = (raw[:38] + "...") if len(raw) > 38 else raw

                        break

            if not titulo:

                titulo = "Conversa sem título"

            # Preview da última mensagem

            ultima_msg = ""

            if messages:

                last_content = messages[-1].get("content", "")

                if isinstance(last_content, str):

                    last_content = last_content.strip().replace("\n", " ")

                    ultima_msg = (last_content[:60] + "...") if len(last_content) > 60 else last_content

            chats.append({

                "id": str(chat_id),

                "titulo": titulo,

                "atualizado_em": os.path.getmtime(caminho),

                "mensagem_count": len(messages),

                "preview": ultima_msg

            })

        except Exception:

            continue

    chats.sort(key=lambda x: x["atualizado_em"], reverse=True)

    return chats

def obter_chat(chat_id: str):

    caminho = os.path.join("data", f"{chat_id}.json")

    if not os.path.exists(caminho):

        return None

    with open(caminho, "r", encoding="utf-8") as f:

        dados = json.load(f)

    if isinstance(dados, dict):

        if not dados.get("titulo") or dados.get("titulo") == "Novo Chat":

            for msg in dados.get("messages", []):

                if msg.get("role") == "user" and msg.get("content"):

                    raw = msg["content"].strip().replace("\n", " ")

                    dados["titulo"] = (raw[:38] + "...") if len(raw) > 38 else raw

                    break

    return dados

def deletar_chat(chat_id: str) -> bool:

    caminho = os.path.join("data", f"{chat_id}.json")

    if os.path.exists(caminho):

        try:

            os.remove(caminho)

            return True

        except Exception:

            return False

    return False

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

