---
id: teste_skill
nome: Skill de Teste
icone: "T"
tipo: skill
modelo: llama3.2
temperatura: 0.2
ferramentas_permitidas:
  - calcular
---

# Skill de Teste

## Objetivo

Testar o carregamento do sistema de Skills do Agent Core.

## Escopo

- Testar cálculos matemáticos.
- Verificar se a ferramenta `calcular` está disponível.
- Verificar se as configurações do Frontmatter foram carregadas.

## Fora do escopo

- Executar comandos no Windows.
- Ler arquivos.
- Controlar o computador.
- Interagir com a tela.

## Regras

1. Utilize a ferramenta `calcular` para operações matemáticas.
2. Não tente utilizar ferramentas que não estejam autorizadas.
3. Responda de forma objetiva.

## Critérios de validação

Uma resposta envolvendo cálculo deve utilizar a ferramenta `calcular` quando apropriado.

## Formato de resposta

Respostas objetivas e explicações curtas.