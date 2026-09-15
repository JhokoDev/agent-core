# Decisões da Fase 0

## Contratos e separação

Servidor Linux (ARM64 pretendido): FastAPI → ModelProvider → Ollama em loopback.
SQLite guarda somente metadados de versão nesta fase. Não há alegação de memória conversacional.
O Bridge Windows será um processo separado, introduzido na Fase 5. Não compartilha o runtime do LLM.

`app/config.py`: configuração validada. `models/base.py`: mensagens, resultados, saúde e protocolo.
`models/registry.py`: seleção de backend. `models/ollama.py`: HTTP e formato específico do Ollama.
`database.py`: inicialização idempotente e versão. `logging.py`: campos fechados de auditoria.
`main.py`: ciclo de vida, autenticação e saúde. `cli.py`: ponto de entrada do operador.

O contrato contém só o que existe: saúde e geração textual não streaming. Tools, visão e streaming
exigirão extensão explícita de capacidades e testes; não há promessa de compatibilidade automática
com qualquer modelo. Trocar embeddings no futuro exigirá versionar/recriar índices, mesmo que trocar
o LLM de conversa não exija isso.

## Ajustes em relação ao planejamento

- Contexto inicial 2048 e saída 128 tokens para o teste; ajustar após medir na VM.
- Nenhum shell liberado por nome de executável. Python/pytest podem executar código arbitrário;
  operações futuras precisarão de schemas fechados, argumentos validados e isolamento real.
- Não criar dezenas de módulos vazios, RAG, Docker ou acesso remoto na preparação.
- Não tratar retorno de ferramenta como comprovação de correção de engenharia.
- Nenhuma suposição sobre disponibilidade/capacidade/gratuidade de uma VM Oracle existente.
- Preparação do Windows limitada a inventário: o serviço do Bridge ainda não existe.

## Limites de segurança

Token não aparece no bootstrap, nos logs da aplicação ou em mensagens de erro do CLI.
`.env`, bancos, logs e ambientes virtuais ficam fora do Git e do pacote de entrega.
O servidor oficial é `personal-agent serve`, que impõe loopback e desabilita access log do Uvicorn.
Executá-lo manualmente com outro comando pode contornar essa configuração; não é isolamento do SO.
O token e loopback não protegem contra um usuário local malicioso com acesso ao mesmo sistema.
Permissões POSIX do arquivo não substituem ACLs do Windows.

Não há CORS amplo, shell, proxy para URL enviada pelo usuário, download automático de modelos,
telemetria de prompts ou chamada a API paga. O cliente HTTP ignora proxies do ambiente e redirects.
Não implementar acesso de rede externo antes de autorização, TLS/túnel, limites e revisão próprios.
Não transportar documentos confidenciais para a VM antes de definir acesso e política dos projetos.

## Fontes técnicas consultadas em 09/09/2026

- [Listagem de modelos Ollama](https://docs.ollama.com/api/tags): diagnóstico por GET /api/tags.
- [Chat Ollama](https://docs.ollama.com/api/chat): geração com stream=false e opções de execução.
- [Ollama Linux](https://docs.ollama.com/linux): instalação e operação no Linux, incluindo ARM64.
- [Qwen 3.5 2B](https://ollama.com/library/qwen3.5:2b): referência inicial do plano, ainda sem benchmark nesta VM.

As tags podem mudar; registre versão do Ollama e digest do modelo no ambiente efetivo.
