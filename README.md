# Fluxo de Caixa — Clean Architecture + Anthropic RAG

Dois serviços independentes para registrar débitos/créditos e consultar o saldo diário. Assistente GenAI opcional, somente leitura, com recuperação documental e adapter Anthropic/Claude.

**Decisão central:** confirmar o lançamento somente depois de gravar lançamento + Outbox na mesma transação. A indisponibilidade do consolidado não entra no caminho síncrono dos lançamentos. O relay entrega eventos com repetição segura; Inbox e atualização do consolidado são atômicos.

## Comece aqui

- [Arquitetura local e alvo, C4 e fluxo](docs/architecture.md)
- [Requisitos, premissas, metas e rastreabilidade](docs/requirements.md)
- [Decisões arquiteturais](docs/adr/decisions.md)
- [Anthropic, LLM, RAG e GenAI](docs/ai.md)
- [Segurança, operação, observabilidade e recuperação](docs/operations.md)
- [Transição de legado](docs/transition.md)
- [Modelo de custos e licenças](docs/costs.md)
- [Evidências e limites da validação](docs/verification.md)
- [Copilot e autoria](docs/copilot.md)
- [Publicação GitHub](docs/github.md)

## Executar sem Docker

Python 3.12+, com SQLite FTS5 para o assistente opcional. Execute na raiz do projeto:

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.lock
python scripts/configure.py
python scripts/dev.py --ai
```

O configurador cria `.env` com tokens aleatórios e recusa sobrescrever arquivo existente. O launcher lê esse arquivo. Portas: lançamentos **8000**, consolidado **8001**, assistente **8002**. Omita `--ai` para executar apenas o núcleo. Ctrl+C encerra os processos; os dados ficam em `data/`.

Cada serviço oferece `/health/live`, `/health/ready`, `/docs` e `/openapi.json`. No Swagger, clique em **Authorize** e informe o `API_TOKEN` do `.env`; a rota de eventos requer `EVENT_TOKEN` separado. Os schemas exportados estão em `docs/contracts/`.

## Executar com Docker Compose

```bash
python scripts/configure.py  # somente se ainda não existir .env
# núcleo
docker compose up --build -d
# núcleo + IA offline
docker compose --profile ai up --build -d
# acompanhar
docker compose logs -f
# parar sem apagar dados
docker compose --profile ai down
```

Volumes persistem dados por serviço. Portas publicadas somente em localhost. `down -v` apaga os dados: use apenas em ambiente descartável. Docker Compose foi preparado, mas não executado no ambiente desta entrega; há job CI para validá-lo.

## Exemplo completo

Em outro terminal Linux/macOS na raiz, carregue os tokens locais:

```bash
set -a
source .env
set +a
curl -i http://localhost:8000/entries \
  -H "Authorization: Bearer $API_TOKEN" \
  -H 'Idempotency-Key: venda-001' \
  -H 'Content-Type: application/json' \
  -d '{"kind":"credit","amount_cents":10000,"business_date":"2026-10-13","description":"Venda"}'
curl -i http://localhost:8000/entries \
  -H "Authorization: Bearer $API_TOKEN" \
  -H 'Idempotency-Key: despesa-001' \
  -H 'Content-Type: application/json' \
  -d '{"kind":"debit","amount_cents":2500,"business_date":"2026-10-13","description":"Despesa"}'
curl http://localhost:8001/balances/2026-10-13 \
  -H "Authorization: Bearer $API_TOKEN"
```

Em banco vazio, depois da entrega dos eventos: créditos **10000**, débitos **2500**, movimento **7500**, saldo final **7500** centavos (R$75,00). Se consultar antes, o resultado pode estar defasado: aguarde e consulte novamente. O primeiro POST retorna 201; replay idêntico retorna 200; mesma chave e outro conteúdo retorna 409.

```bash
curl http://localhost:8002/assistant/ask \
  -H "Authorization: Bearer $API_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"question":"Como funciona o saldo diário?","business_date":"2026-10-13"}'
```

Por padrão, `provider=offline` retorna trechos com citações, sem chamar LLM e sem custo de API. Para Claude, defina `AI_PROVIDER=anthropic`, `ANTHROPIC_API_KEY` e `ANTHROPIC_MODEL` no `.env`, usando um ID exato habilitado na sua conta, e reinicie o assistente. Isso envia pergunta, trechos e totais agregados à Anthropic e pode gerar cobrança. Nunca coloque dados pessoais ou segredos no corpus. A integração real não foi acionada nesta entrega.

## Testes e qualidade

```bash
python -m pytest -q
ruff check .
ruff format --check .
# teste real de indisponibilidade, recuperação, carga aberta e reconciliação
PYTHONPATH=. python scripts/verify_runtime.py --seconds 30
# PowerShell: $env:PYTHONPATH='.'; python scripts/verify_runtime.py --seconds 30
```

O teste de runtime sobe serviços em portas livres, usa bancos temporários, mantém o consolidado fora do ar, registra lançamentos, recupera e reinicia o consolidado. Depois executa 50 req/s de consultas e 50 req/s de eventos, em cenários separados. O processo falha se a taxa de erro exceder 5% ou a reconciliação divergir. A evidência JSON contém duração, volume, p95 e ambiente; não é certificação de capacidade de produção.

## Estrutura e limites

| Pasta | Responsabilidade |
|---|---|
| `cashflow/domain` | Invariantes financeiras e contrato de evento |
| `cashflow/application` | Casos de uso e portas; sem framework ou banco |
| `cashflow/infrastructure` | SQLite, transporte HTTP, FTS5 e Anthropic |
| `cashflow/presentation` | APIs, validação e autenticação |
| `cashflow/main.py`, `ai_main.py` | Composição e ciclo de vida |
| `tests`, `scripts` | Testes, carga, falhas, execução local |
| `docs`, `.github` | Arquitetura, decisões, contratos, CI e Copilot |

**Implementado:** um comerciante, BRL, lançamentos imutáveis, datas retroativas, Outbox/Inbox, entrega HTTP assíncrona, autenticação por tokens locais, RAG lexical, adapter Anthropic e CI.

**Arquitetura alvo, ainda não implantada:** PostgreSQL HA, Service Bus, OIDC/JWT, TLS/gateway, réplicas horizontais, OpenTelemetry, recuperação regional e busca híbrida. Não escalar SQLite para múltiplos hosts. A API de lançamentos independe do consolidado, mas continua dependente do próprio banco/disco.

**GitHub:** projeto pronto para repositório público, porém ainda não publicado. O requisito obrigatório de hospedagem permanece pendente até existir URL pública. Não há licença de redistribuição escolhida; o autor deve decidir antes de licenciar o projeto.
