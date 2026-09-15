# Relatório de validação — 09/09/2026

## Executado neste ambiente

Ambiente: Linux de desenvolvimento, Python 3.12.14. Não é a VM nem o Windows do usuário.

| Verificação | Resultado |
|---|---|
| `python3 -m unittest discover -s tests -p test_foundation.py -v` | 7 testes aprovados |
| Persistência SQLite após reinicialização | Aprovado |
| Banco ausente/corrompido e schema futuro | Aprovado |
| Logs sem conteúdo/token e sem handlers duplicados | Aprovado |
| Bootstrap preserva segredo existente e não o imprime | Aprovado |
| `python3 -m compileall -q app scripts tests` | Aprovado |
| `bash -n scripts/setup_vm.sh` | Aprovado |
| Bootstrap real da pasta de desenvolvimento | Executado; `.env` gerado e excluído da entrega |
| Git ignora `.env` e `data/memory.db` | Aprovado |

## Não executado

A instalação de FastAPI, pydantic-settings, httpx, Uvicorn e pytest não foi concluída.
O processo de download foi interrompido por restrição de rede/aprovação de rede cancelada no ambiente.
Não foi usado acesso alternativo para contornar essa restrição.

- `tests/test_api_provider.py`: testes escritos, não executados.
- Inicialização real FastAPI e requisições HTTP.
- Download/execução Ollama e inferência do modelo.
- Instalação ARM64 e resolução completa das dependências.
- Preflight PowerShell e integração Windows/KiCad.
- Serviço systemd e reinicialização da VM.

## Retomada

No ambiente com acesso às dependências, executar `bash scripts/setup_vm.sh`, ativar `.venv`
e rodar `python -m pytest -q`. Corrigir qualquer falha antes de seguir para Ollama.
Depois seguir `docs/INSTALACAO.md` e registrar resultados de `doctor`, `smoke-model`,
HTTP readiness, memória e latência. Somente então concluir os itens de `docs/FASE_0.md`.
