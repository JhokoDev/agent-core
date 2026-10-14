"""Painel local para administrar conversas, Skills e arquivos do Agent Core."""
from __future__ import annotations
import json
import psutil
import httpx
import pandas as pd
import yaml
from pathlib import Path
from typing import Any
import streamlit as st
import dash_utils as utils

st.set_page_config(page_title="Agent Core", page_icon="🤖", layout="wide", initial_sidebar_state="expanded")

def aplicar_estilo() -> None:
    st.markdown(
        """
        <style>
            #MainMenu, header, footer, .stAppDeployButton {visibility: hidden; display: none;}
            .block-container { max-width: 1400px; padding-top: 1rem; padding-bottom: 2.5rem; }
            [data-testid="stSidebar"] { border-right: 1px solid rgba(255, 255, 255, 0.05); background-color: #0D1117; }
            [data-testid="stMetric"] {
                background: linear-gradient(145deg, #161B22, #0D1117);
                border: 1px solid rgba(255, 255, 255, 0.08); border-left: 4px solid #00D2FF;
                border-radius: 6px; padding: 1rem 1.2rem; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }
            [data-testid="stMetric"]:hover { transform: translateY(-2px); box-shadow: 0 6px 12px rgba(0, 210, 255, 0.15); border-left: 4px solid #00E676; }
            .agent-core-subtitle { color: #8B949E; font-size: 1.05rem; margin-top: -1.2rem; margin-bottom: 2rem; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 1rem;}
        </style>
        """, unsafe_allow_html=True
    )

def mensagem_de_sessao(message: str) -> None:
    st.session_state["mensagem_sucesso"] = message

def mostrar_mensagem_de_sessao() -> None:
    message = st.session_state.pop("mensagem_sucesso", None)
    if message: st.success(message)

def renderizar_sidebar(chats, skills, tools) -> str:
    with st.sidebar:
        st.title("🤖 Agent Core")
        st.caption("Centro de Comando")
        st.divider()
        page = st.radio("Navegação", ("Visão geral", "Playground", "Sandbox (Projetos)", "Analytics", "Histórico de chats", "Skills", "Monitoramento", "Sistema"), label_visibility="collapsed")
        st.divider()
        if st.button("↻ Atualizar dados", use_container_width=True): st.rerun()
    return page

def renderizar_visao_geral(chats, skills, tools) -> None:
    st.title("Visão geral")
    st.markdown('<p class="agent-core-subtitle">Acompanhe o conteúdo local do Agent Core.</p>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Conversas", len(chats))
    c2.metric("Skills", len(skills))
    c3.metric("Tools", len(tools))
    c4.metric("Projetos (Sandbox)", len(utils.listar_projetos()))

def renderizar_playground(skills, tools):
    st.title("Playground de Testes")
    st.markdown('<p class="agent-core-subtitle">Simule o aplicativo Android diretamente pelo navegador via Server-Sent Events.</p>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    skill_selecionada = c1.selectbox("Skill Ativa", ["default"] + [s.stem for s in skills])
    tool_selecionada = c2.selectbox("Tool Ativa", ["Nenhuma"] + [t.stem for t in tools])
    tool_id = None if tool_selecionada == "Nenhuma" else tool_selecionada

    if "pg_mensagens" not in st.session_state: st.session_state["pg_mensagens"] = []
    
    for msg in st.session_state["pg_mensagens"]:
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Digite sua mensagem para a IA..."):
        st.session_state["pg_mensagens"].append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"): st.markdown(prompt)

        with st.chat_message("assistant", avatar="🤖"):
            placeholder = st.empty()
            texto_completo, token = "", ""
            
            # Lê o token nativamente sem precisar de bibliotecas extras
            env_path = utils.BASE_DIR / ".env"
            if env_path.exists():
                for linha in env_path.read_text(encoding="utf-8").splitlines():
                    if linha.startswith("AGENT_API_TOKEN="): token = linha.split("=", 1)[1].strip()

            payload = {"texto": prompt, "skill_id": skill_selecionada, "tool_id": tool_id}
            headers = {"Authorization": f"Bearer {token}"}
            
            try:
                with httpx.stream("POST", "http://127.0.0.1:8000/chat", json=payload, headers=headers, timeout=120.0) as r:
                    r.raise_for_status()
                    for linha in r.iter_lines():
                        if linha.startswith("data: "):
                            try:
                                dados = json.loads(linha[6:])
                                if "chunk" in dados:
                                    texto_completo += dados["chunk"]
                                    placeholder.markdown(texto_completo + "▌")
                            except: pass
                placeholder.markdown(texto_completo)
                st.session_state["pg_mensagens"].append({"role": "assistant", "content": texto_completo})
            except Exception as e:
                st.error(f"O backend está desligado ou o token é inválido: {e}")

def renderizar_sandbox():
    st.title("Sandbox (Projetos)")
    st.markdown('<p class="agent-core-subtitle">Gerencie os códigos-fonte que a IA pode acessar via ferramentas.</p>', unsafe_allow_html=True)
    projetos = utils.listar_projetos()
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("Upload de Código")
        uploaded = st.file_uploader("Fazer upload (.cs, .php, .py)", label_visibility="collapsed")
        if uploaded:
            (utils.PROJETOS_DIR / uploaded.name).write_bytes(uploaded.read())
            st.success(f"{uploaded.name} salvo na sandbox!")
            st.rerun()
            
        selecionado = None
        if projetos:
            st.divider()
            selecionado = st.selectbox("Selecione um arquivo para editar", projetos, format_func=lambda p: p.name)
            if st.button("Excluir Arquivo", type="secondary", use_container_width=True):
                selecionado.unlink()
                st.rerun()
                
    with c2:
        if selecionado:
            st.subheader(f"Editando: {selecionado.name}")
            conteudo_atual = selecionado.read_text(encoding="utf-8", errors="replace")
            novo_conteudo = st.text_area("Código", value=conteudo_atual, height=500, label_visibility="collapsed")
            if st.button("Salvar Alterações", type="primary"):
                selecionado.write_text(novo_conteudo, encoding="utf-8")
                mensagem_de_sessao("Arquivo atualizado com sucesso!")
                st.rerun()
        else:
            st.info("Faça o upload ou selecione um arquivo na coluna ao lado.")

def renderizar_analytics():
    st.title("Analytics de Consumo")
    st.markdown('<p class="agent-core-subtitle">Acompanhe o peso computacional e financeiro (Tokens) do seu Agente.</p>', unsafe_allow_html=True)
    dados = utils.obter_analytics()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Tokens de Prompt (Leitura)", f'{dados["total_prompt"]:,}')
    c2.metric("Tokens de Resposta (Geração)", f'{dados["total_resposta"]:,}')
    c3.metric("Total Processado", f'{dados["total_prompt"] + dados["total_resposta"]:,}')
    
    st.divider()
    if dados["dados"]:
        df = pd.DataFrame(dados["dados"]).set_index("Chat")
        st.subheader("Uso de Tokens por Conversa")
        st.bar_chart(df[["Tokens Prompt", "Tokens Resposta"]])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Envie mensagens para a IA para começar a gerar o gráfico de Tokens.")

def renderizar_historico(chats: list[Path]) -> None:
    st.title("Histórico de chats")
    st.markdown('<p class="agent-core-subtitle">Pesquise, consulte e exporte as conversas armazenadas localmente.</p>', unsafe_allow_html=True)
    if not chats:
        st.info("Nenhuma conversa encontrada."); return

    search = st.text_input("Pesquisar", placeholder="Título ou conteúdo da conversa").strip().casefold()
    valid_chats = []
    for path in chats:
        chat = utils.carregar_json(path)
        if chat is None: continue
        if not search or search in json.dumps(chat, ensure_ascii=False).casefold():
            valid_chats.append((path, chat))

    if not valid_chats: st.warning("Nenhuma correspondência."); return

    labels = {path: utils.rotulo_chat(path, chat) for path, chat in valid_chats}
    selected_path = st.selectbox("Conversa", [p for p, _ in valid_chats], format_func=lambda p: labels[p])
    selected_chat = next(chat for p, chat in valid_chats if p == selected_path)
    messages = selected_chat.get("mensagens") if isinstance(selected_chat.get("mensagens"), list) else []

    l, m, r = st.columns(3)
    l.caption(f"**ID:** {selected_chat.get('id') or 'Não informado'}")
    m.caption(f"**Mensagens:** {len(messages)}")
    r.caption(f"**Arquivo:** {selected_path.name}")
    st.download_button("Baixar sessão JSON", data=json.dumps(selected_chat, ensure_ascii=False, indent=2), file_name=selected_path.name, mime="application/json")
    st.divider()

    for index, message in enumerate(messages, start=1):
        if not isinstance(message, dict): continue
        role = str(message.get("role") or "unknown")
        content = utils.renderizar_conteudo(message.get("content", ""))
        
        if role in {"user", "assistant"}:
            with st.chat_message(role, avatar="🤖" if role == "assistant" else "👤"):
                st.markdown(content)
                if "meta" in message:
                    st.caption(f"⚡ Tokens: {message['meta'].get('total_tokens', 0)}")
        else:
            with st.expander(f"{role.title()} · mensagem {index}"):
                st.code(content, language="text")

def ler_frontmatter_skill(path: Path) -> tuple[dict[str, Any], str]:
    """Lê o Frontmatter YAML e o corpo de uma Skill."""
    try:
        conteudo = path.read_text(encoding="utf-8")
    except OSError:
        return {}, ""

    conteudo = conteudo.strip()

    if not conteudo.startswith("---"):
        return {}, conteudo

    partes = conteudo.split("---", 2)

    if len(partes) != 3:
        return {}, conteudo

    try:
        configuracao = yaml.safe_load(partes[1]) or {}
        if not isinstance(configuracao, dict):
            configuracao = {}
        return configuracao, partes[2].strip()
    except yaml.YAMLError:
        return {}, conteudo


def normalizar_lista_skill(valor: Any) -> list[str]:
    """Normaliza listas do Frontmatter para uso no Dashboard."""
    if valor is None:
        return []

    if isinstance(valor, str):
        valor = valor.strip()
        return [valor] if valor else []

    if not isinstance(valor, list):
        return []

    resultado = []
    for item in valor:
        if isinstance(item, str):
            item = item.strip()
            if item and item not in resultado:
                resultado.append(item)

    return resultado


def montar_skill_markdown(configuracao: dict[str, Any], corpo: str) -> str:
    """Reconstrói uma Skill preservando Frontmatter + corpo."""
    frontmatter = yaml.safe_dump(
        configuracao,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    ).strip()

    corpo = corpo.strip()

    if corpo:
        return f"---\n{frontmatter}\n---\n\n{corpo}\n"

    return f"---\n{frontmatter}\n---\n"


def dados_da_skill(path: Path) -> dict[str, Any]:
    """Retorna metadados úteis para exibição."""
    configuracao, corpo = ler_frontmatter_skill(path)

    skill_id = str(
        configuracao.get("id") or path.stem
    ).strip()

    nome = str(
        configuracao.get("nome") or skill_id.replace("_", " ").title()
    ).strip()

    icone = str(configuracao.get("icone") or "").strip()
    tipo = str(configuracao.get("tipo") or "skill").strip()
    modelo = str(configuracao.get("modelo") or "não definido").strip()

    try:
        temperatura = float(configuracao.get("temperatura", 0.5))
    except (TypeError, ValueError):
        temperatura = 0.5

    ferramentas = normalizar_lista_skill(
        configuracao.get("ferramentas_permitidas", [])
    )

    return {
        "id": skill_id,
        "nome": nome,
        "icone": icone,
        "tipo": tipo,
        "modelo": modelo,
        "temperatura": temperatura,
        "ferramentas": ferramentas,
        "corpo": corpo,
        "configuracao": configuracao,
    }


def renderizar_skills(skills: list[Path]) -> None:
    st.title("Skills")
    st.markdown(
        '<p class="agent-core-subtitle">'
        'Gerencie Skills, metadados, modelo, temperatura e permissões de ferramentas.'
        '</p>',
        unsafe_allow_html=True,
    )

    dados_skills = [dados_da_skill(path) for path in skills]

    # ==========================================
    # VISÃO GERAL
    # ==========================================

    total = len(dados_skills)
    com_frontmatter = sum(
        bool(dado["configuracao"]) for dado in dados_skills
    )
    com_tools = sum(
        bool(dado["ferramentas"]) for dado in dados_skills
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Skills carregadas", total)
    c2.metric("Com Frontmatter", com_frontmatter)
    c3.metric("Com Tools autorizadas", com_tools)

    st.divider()

    if dados_skills:
        tabela = []

        for dado in dados_skills:
            ferramentas = ", ".join(dado["ferramentas"]) or "Nenhuma"

            tabela.append({
                "": dado["icone"],
                "Nome": dado["nome"],
                "ID": dado["id"],
                "Tipo": dado["tipo"],
                "Modelo": dado["modelo"],
                "Temperatura": dado["temperatura"],
                "Tools autorizadas": ferramentas,
            })

        st.dataframe(
            pd.DataFrame(tabela),
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    tab_create, tab_edit, tab_delete = st.tabs(
        ("Criar", "Editar", "Excluir")
    )

    tool_ids = sorted(
        {
            path.stem
            for path in utils.listar_tools()
            if path.is_file()
        },
        key=str.casefold,
    )

    # ==========================================
    # CRIAR
    # ==========================================

    with tab_create:
        st.subheader("Nova Skill")
        st.caption(
            "Novas Skills são criadas com Frontmatter YAML compatível "
            "com o Skill Loader."
        )

        with st.form("criar_skill", clear_on_submit=True):
            c1, c2 = st.columns(2)

            with c1:
                nome = st.text_input(
                    "Nome",
                    placeholder="Desenvolvedor Sênior",
                )
                skill_id = st.text_input(
                    "ID",
                    placeholder="dev_senior",
                    help="3 a 50 caracteres: minúsculas, números, _ e -.",
                )
                icone = st.text_input(
                    "Ícone",
                    placeholder="💻",
                )
                tipo = st.text_input(
                    "Tipo",
                    value="skill",
                )

            with c2:
                modelo = st.text_input(
                    "Modelo",
                    value="qwen2.5:1.5b",
                )
                temperatura = st.number_input(
                    "Temperatura",
                    min_value=0.0,
                    max_value=2.0,
                    value=0.2,
                    step=0.1,
                )
                ferramentas = st.multiselect(
                    "Ferramentas permitidas",
                    options=tool_ids,
                )

            prompt = st.text_area(
                "Prompt da Skill",
                height=280,
                placeholder="# Nome da Skill\n\n## Objetivo\n...",
            )

            if st.form_submit_button("Criar Skill", type="primary"):
                skill_id = skill_id.strip().lower()
                nome_limpo = nome.strip()

                target = utils.SKILLS_DIR / f"{skill_id}.md"

                if not nome_limpo or not prompt.strip():
                    st.error("Nome e prompt são obrigatórios.")
                elif not utils.validar_id_skill(skill_id):
                    st.error("ID inválido.")
                elif target.exists():
                    st.error(f"Skill {skill_id} já existe.")
                else:
                    configuracao = {
                        "id": skill_id,
                        "nome": nome_limpo,
                        "icone": icone.strip(),
                        "tipo": tipo.strip() or "skill",
                        "modelo": modelo.strip() or "qwen2.5:1.5b",
                        "temperatura": float(temperatura),
                        "ferramentas_permitidas": ferramentas,
                    }

                    target.write_text(
                        montar_skill_markdown(
                            configuracao,
                            prompt,
                        ),
                        encoding="utf-8",
                    )

                    mensagem_de_sessao(
                        f"Skill {nome_limpo} criada com Frontmatter."
                    )
                    st.rerun()

    # ==========================================
    # EDITAR
    # ==========================================

    with tab_edit:
        if not skills:
            st.info("Nenhuma Skill para edição.")
        else:
            selected = st.selectbox(
                "Editar",
                skills,
                format_func=lambda path: (
                    f"{dados_da_skill(path)['icone']} "
                    f"{dados_da_skill(path)['nome']} "
                    f"({dados_da_skill(path)['id']})"
                ),
            )

            configuracao, corpo = ler_frontmatter_skill(selected)

            if not configuracao:
                st.warning(
                    "Esta Skill não possui um Frontmatter YAML válido. "
                    "Preencha os campos abaixo para migrá-la."
                )

            dado = dados_da_skill(selected)

            with st.form(f"editar_skill_{selected}"):
                c1, c2 = st.columns(2)

                with c1:
                    edit_nome = st.text_input(
                        "Nome",
                        value=dado["nome"],
                    )
                    edit_id = st.text_input(
                        "ID",
                        value=dado["id"],
                    )
                    edit_icone = st.text_input(
                        "Ícone",
                        value=dado["icone"],
                    )
                    edit_tipo = st.text_input(
                        "Tipo",
                        value=dado["tipo"],
                    )

                with c2:
                    edit_modelo = st.text_input(
                        "Modelo",
                        value=dado["modelo"]
                        if dado["modelo"] != "não definido"
                        else "qwen2.5:1.5b",
                    )
                    edit_temperatura = st.number_input(
                        "Temperatura",
                        min_value=0.0,
                        max_value=2.0,
                        value=float(dado["temperatura"]),
                        step=0.1,
                    )
                    edit_ferramentas = st.multiselect(
                        "Ferramentas permitidas",
                        options=tool_ids,
                        default=[
                            ferramenta
                            for ferramenta in dado["ferramentas"]
                            if ferramenta in tool_ids
                        ],
                    )

                edit_corpo = st.text_area(
                    "Conteúdo da Skill",
                    value=corpo,
                    height=400,
                )

                salvar = st.form_submit_button(
                    "Salvar alterações",
                    type="primary",
                )

            if salvar:
                edit_id = edit_id.strip().lower()

                if not edit_nome.strip() or not edit_corpo.strip():
                    st.error("Nome e conteúdo são obrigatórios.")
                elif not utils.validar_id_skill(edit_id):
                    st.error("ID inválido.")
                else:
                    configuracao_atualizada = {
                        "id": edit_id,
                        "nome": edit_nome.strip(),
                        "icone": edit_icone.strip(),
                        "tipo": edit_tipo.strip() or "skill",
                        "modelo": edit_modelo.strip() or "qwen2.5:1.5b",
                        "temperatura": float(edit_temperatura),
                        "ferramentas_permitidas": edit_ferramentas,
                    }

                    if edit_id != selected.stem:
                        novo_caminho = selected.with_name(
                            f"{edit_id}.md"
                        )

                        if novo_caminho.exists():
                            st.error(
                                f"Já existe uma Skill com o ID {edit_id}."
                            )
                        else:
                            selected.unlink()
                            novo_caminho.write_text(
                                montar_skill_markdown(
                                    configuracao_atualizada,
                                    edit_corpo,
                                ),
                                encoding="utf-8",
                            )
                            mensagem_de_sessao(
                                f"Skill {edit_id} atualizada."
                            )
                            st.rerun()
                    else:
                        selected.write_text(
                            montar_skill_markdown(
                                configuracao_atualizada,
                                edit_corpo,
                            ),
                            encoding="utf-8",
                        )
                        mensagem_de_sessao(
                            f"Skill {edit_id} atualizada."
                        )
                        st.rerun()

    # ==========================================
    # EXCLUIR
    # ==========================================

    with tab_delete:
        if not skills:
            st.info("Nenhuma Skill para excluir.")
        else:
            selected = st.selectbox(
                "Excluir",
                skills,
                format_func=lambda path: (
                    f"{dados_da_skill(path)['icone']} "
                    f"{dados_da_skill(path)['nome']} "
                    f"({dados_da_skill(path)['id']})"
                ),
            )

            dado = dados_da_skill(selected)

            st.warning(
                f"Você está prestes a excluir a Skill "
                f"`{dado['id']}`."
            )

            st.code(
                selected.read_text(
                    encoding="utf-8",
                    errors="replace",
                ),
                language="markdown",
            )

            confirmar = st.checkbox(
                f"Confirmar exclusão de {dado['id']}"
            )

            if st.button(
                "Excluir Skill",
                type="primary",
                disabled=not confirmar,
            ):
                selected.unlink()

                mensagem_de_sessao(
                    f"Skill {dado['id']} excluída."
                )
                st.rerun()

def renderizar_monitoramento() -> None:
    st.title("Monitoramento e Logs")
    st.markdown('<p class="agent-core-subtitle">Acompanhe a saúde do hardware e os logs do servidor em tempo real.</p>', unsafe_allow_html=True)
    cpu_percent = psutil.cpu_percent(interval=0.2)
    ram = psutil.virtual_memory()
    
    ollama_ram_mb = 0
    for proc in psutil.process_iter(['name', 'memory_info']):
        try:
            if proc.info['name'] and 'ollama' in proc.info['name'].lower():
                ollama_ram_mb += proc.info['memory_info'].rss / (1024 * 1024)
        except (psutil.NoSuchProcess, psutil.AccessDenied): continue

    st.subheader("Hardware (Servidor Local)")
    c1, c2, c3 = st.columns(3)
    c1.metric("Uso de CPU", f"{cpu_percent}%")
    c2.metric("Uso de RAM Total", f"{ram.percent}%", f"{ram.used / (1024**3):.1f} GB / {ram.total / (1024**3):.1f} GB", delta_color="off")
    c3.metric("RAM Isolada (Ollama)", f"{ollama_ram_mb:.1f} MB", "Consumo do Motor LLM", delta_color="off")

    st.divider()
    st.subheader("Logs do Backend (Ao Vivo)")
    log_path = utils.BASE_DIR / "server_log.txt"
    if log_path.exists():
        texto_log = "".join(log_path.read_text(encoding="utf-8", errors="replace").splitlines(True)[-40:])
        st.code(texto_log, language="bash")
        if st.button("↻ Atualizar Logs"): st.rerun()
    else:
        st.info("Arquivo 'server_log.txt' não encontrado.")

def renderizar_sistema() -> None:
    st.title("Sistema")
    st.markdown('<p class="agent-core-subtitle">Referência dos diretórios do Agent Core.</p>', unsafe_allow_html=True)
    rows = [{"Diretório": "data/", "Caminho": str(utils.DATA_DIR)},
            {"Diretório": "skills/", "Caminho": str(utils.SKILLS_DIR)},
            {"Diretório": "tools/", "Caminho": str(utils.TOOLS_DIR)},
            {"Diretório": "projetos/", "Caminho": str(utils.PROJETOS_DIR)}]
    st.dataframe(rows, use_container_width=True, hide_index=True)

aplicar_estilo()
chats, skills, tools = utils.listar_chats(), utils.listar_skills(), utils.listar_tools()
page = renderizar_sidebar(chats, skills, tools)
mostrar_mensagem_de_sessao()

if page == "Visão geral": renderizar_visao_geral(chats, skills, tools)
elif page == "Playground": renderizar_playground(skills, tools)
elif page == "Sandbox (Projetos)": renderizar_sandbox()
elif page == "Analytics": renderizar_analytics()
elif page == "Histórico de chats": renderizar_historico(chats)
elif page == "Skills": renderizar_skills(skills)
elif page == "Monitoramento": renderizar_monitoramento()
else: renderizar_sistema()