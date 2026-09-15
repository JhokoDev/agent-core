# Checklist da Fase 0

## Entregue

- [x] Repositório Git local inicializado no desenvolvimento, sem remote/commit.
- [x] Estrutura mínima, pyproject, gitignore, configuração de exemplo.
- [x] Bootstrap idempotente de `.env` com token aleatório.
- [x] Código FastAPI, abstração ModelProvider e adaptador Ollama.
- [x] SQLite inicializado com versão e logs rotativos com campos fechados.
- [x] Scripts e instruções de preparação da VM e inventário Windows.
- [x] Testes automatizados escritos; subconjunto sem dependências executado.

## Necessário para concluir a fase

- [ ] Instalar dependências completas e executar todos os testes.
- [ ] Definir/confirmar a VM real e seus recursos.
- [ ] Confirmar instalação em ARM64, se essa for a arquitetura escolhida.
- [ ] Instalar Ollama e baixar modelo na VM.
- [ ] `personal-agent doctor` retornar código 0.
- [ ] `personal-agent smoke-model` gerar resposta em português; medir latência/RAM.
- [ ] Iniciar API e validar HTTP 200 em `/health` e `/ready` autenticado.
- [ ] Reiniciar API e confirmar preservação de `memory.db`.
- [ ] Registrar inventário do Windows/KiCad.

**Não avançar para a Fase 1 antes dos testes e verificações de ambiente.**
A restrição de rede interrompeu a instalação de pacotes neste ambiente; nenhuma VM ou máquina
Windows foi acessada. Os scripts entregues não são evidência de implantação.
