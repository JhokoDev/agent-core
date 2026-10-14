---
id: "interagir_ecra"
nome: "Visão e Controle de Ecrã"
icone: ""
tipo: "tool"
modelo: "qwen2.5:1.5b"
temperatura: 0.1
---
Você tem a capacidade de ver o ecrã do utilizador e controlar o rato e o teclado fisicamente.
Para usar esta ferramenta, você DEVE retornar um JSON com a "acao" que deseja executar.

Ações permitidas:
1. "analisar_tela" -> Tira um print silencioso e o modelo de visão devolve o que está a acontecer no ecrã.
2. "escrever" -> Digita um texto fisicamente no teclado (exige o parâmetro "texto").
3. "tecla" -> Pressiona uma tecla especial, como "enter", "tab", "win", "esc" (exige o parâmetro "texto").
4. "clicar" -> Clica no centro do ecrã (útil para focar a janela após abrir um programa).

Exemplo de uso: Se o utilizador pedir "Abre o Onshape e faz login":
1. Use a tool 'controlar_computador' para 'abrir_onshape'.
2. Use esta tool com acao: 'analisar_tela' para ver se a página carregou.
3. Use esta tool com acao: 'tecla', texto: 'tab' para navegar até ao login.
4. Use esta tool com acao: 'escrever', texto: 'seu_email@email.com'.