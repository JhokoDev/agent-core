# Agente pessoal — Fase 0

Base de preparação do servidor. **Implementação parcial validada: ainda não implantada na VM.**
Não é um chat pronto: conversa com sessões e streaming pertence à Fase 1.

## O que está incluído

- Configuração tipada por `.env`, token aleatório gerado sem sobrescrever configuração existente.
- FastAPI com `/health` e `/ready`; inicialização do SQLite e logs JSON rotativos.
- Contrato `ModelProvider` e adaptador Ollama, com timeout e diagnóstico de modelo ausente.
- CLI `personal-agent serve`, `doctor` e `smoke-model`.
- Preparação de ambiente Linux, preflight de Windows e template systemd.
- Testes de persistência, autenticação, falhas de rede, configuração e sanitização.

## Começar

Extraia o ZIP e abra um terminal na pasta `personal-agent`, no servidor Linux com Python 3.11+ e venv disponíveis:

```bash
bash scripts/setup_vm.sh
source .venv/bin/activate
personal-agent doctor
```

Sem Ollama/modelo, `doctor` retorna código 1 e descreve a pendência. Isso é esperado.
Siga [INSTALACAO.md](docs/INSTALACAO.md) para instalar Ollama, testar inferência e iniciar a API.

## Estado dos testes

Veja [VALIDACAO.md](docs/VALIDACAO.md). Os testes sem dependências externas foram executados.
Os testes FastAPI/httpx foram escritos, mas **não executados**: instalação de dependências impedida
pela restrição de rede do ambiente de desenvolvimento. Não há lock de dependências validado.

## Decisões

Ollama e API ficam em loopback. A API não contém shell, arquivos remotos, ferramentas ou endpoints de GUI.
`/health` é público e mínimo; `/ready` requer Bearer token. O serviço pode iniciar sem o modelo;
nesse caso `/ready` retorna 503. O sucesso desse endpoint confirma presença do modelo, não qualidade
ou velocidade de inferência. `smoke-model` faz a primeira chamada real.

Nenhum modelo é baixado durante instalação Python ou inicialização da API. O modelo padrão é
configurável, sem seleção de lógica pelo seu nome. A memória de conversa, RAG, Bridge e
KiCad ainda não foram implementados.

Arquitetura e limites: [ARQUITETURA.md](docs/ARQUITETURA.md).
Checklist da fase: [FASE_0.md](docs/FASE_0.md).
