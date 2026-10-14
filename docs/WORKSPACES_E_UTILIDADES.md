# 🚀 Workspaces & Curadoria de Arquivos (Utilidade Real)

Este documento descreve o módulo de utilidade do **Agent Core**, desenvolvido para transformar o agente em um assistente de produtividade prático e indispensável no dia a dia.

---

## 1. Visão Geral

Assistentes de IA tradicionais falham em entregar utilidade real quando se limitam a responder perguntas teóricas ou executar comandos atômicos isolados (como simplesmente abrir a calculadora).

O módulo de utilidade (`app/services/workspace_service.py`) entrega:
1. **Composições de Ambientes de Trabalho (Macros Inteligentes):** Configuração completa da estação de trabalho com um único comando.
2. **Curadoria e Organização de Arquivos:** Manutenção preventiva e higienização da pasta de Downloads do usuário sem perda ou corrupção de dados.

---

## 2. Perfis de Trabalho (`preparar_ambiente_trabalho`)

O agente possui perfis predefinidos que realizam múltiplos passos coordenados:

### 1. Perfil `dev` (Desenvolvimento)
* **Objetivo:** Preparar instantaneamente o ambiente para codificação.
* **Ações Executadas:**
  1. Abre o **Visual Studio Code** apontando diretamente para o diretório raiz do projeto.
  2. Abre o **Google Chrome** apontando para o painel de desenvolvimento local (`http://localhost:3000`).
* **Comandos Naturais Reconhecidos:**
  * *"modo dev"*, *"preparar ambiente de desenvolvimento"*, *"workspace dev"*, *"ativar modo programador"*.

### 2. Perfil `foco` (Concentração & Deep Work)
* **Objetivo:** Eliminar distrações visuais e sonoras para trabalho focado.
* **Ações Executadas:**
  1. Abre e inicia uma rádio **Lo-Fi Beats / Estudo** no YouTube no navegador.
  2. Identifica e minimiza automaticamente janelas de distração (como Discord, Steam, Spotify).
* **Comandos Naturais Reconhecidos:**
  * *"modo foco"*, *"modo concentração"*, *"ambiente de foco"*, *"preciso focar"*.

### 3. Perfil `estudo` (Leitura & Notas)
* **Objetivo:** Configuração rápida para leituras e apontamentos.
* **Ações Executadas:**
  1. Abre o Bloco de Notas para anotações rápidas.
  2. Prepara o navegador para pesquisas acadêmicas ou documentações.
* **Comandos Naturais Reconhecidos:**
  * *"modo estudo"*, *"ambiente de estudos"*, *"modo anotações"*.

---

## 3. Curadoria Automática de Downloads (`organizar_downloads`)

A pasta `Downloads` do Windows frequentemente se torna um repositório caótico de arquivos de diversos tipos misturados. A ferramenta `organizar_downloads` executa uma varredura segura e organiza os arquivos soltos em categorias estruturadas.

### Categorias e Extensões Suportadas:

| Pasta de Destino | Extensões Agrupadas |
| :--- | :--- |
| **`Documentos_PDF`** | `.pdf` |
| **`Documentos_Texto`** | `.docx`, `.doc`, `.txt`, `.xlsx`, `.csv`, `.pptx`, `.odt` |
| **`Instaladores_e_Programas`** | `.exe`, `.msi`, `.bat`, `.cmd` |
| **`Arquivos_Compactados`** | `.zip`, `.rar`, `.7z`, `.tar`, `.gz` |
| **`Imagens_e_Fotos`** | `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.webp`, `.ico` |
| **`Midias_Audio_Video`** | `.mp3`, `.mp4`, `.wav`, `.mkv`, `.avi` |

### Garantias de Segurança:
* **Sem Sobrescrita:** Se um arquivo chamado `relatorio.pdf` já existir dentro de `Documentos_PDF`, o novo arquivo é salvo automaticamente como `relatorio_1.pdf`, `relatorio_2.pdf`, etc.
* **Preservação de Pastas:** Pastas já existentes na raiz de Downloads não são tocadas nem movidas.
* **Arquivos Ocultos:** Arquivos iniciados por `.` (como `.tmp` ou arquivos de sistema) são ignorados para evitar quebras de downloads em andamento.

### Relatório Detalhado:
Ao concluir a organização, o agente retorna um resumo quantitativo:
```text
Sucesso! 14 arquivo(s) foram organizados na pasta Downloads:
- Documentos PDF (3 arquivo(s)): edital.pdf, fatura.pdf, contrato.pdf
- Instaladores e Programas (2 arquivo(s)): vscode_setup.exe, nodejs.msi
- Imagens e Fotos (9 arquivo(s)): screenshot1.png, foto.jpg, banner.png...
```

---

## 4. Contratos das Ferramentas no Orquestrador

```python
# Preparar Ambiente de Trabalho
ToolContract(
    id="preparar_ambiente_trabalho",
    nome="Preparar Ambiente de Trabalho",
    descricao="Prepara a estação de trabalho para modos específicos: 'dev', 'foco', 'estudo'.",
    categoria="computador",
    argumentos={"perfil": {"tipo": "string", "obrigatorio": True}}
)

# Organizar Pasta Downloads
ToolContract(
    id="organizar_downloads",
    nome="Organizar Pasta Downloads",
    descricao="Varre a pasta Downloads e move arquivos soltos para subpastas categorizadas com segurança.",
    categoria="arquivos",
    argumentos={}
)
```
