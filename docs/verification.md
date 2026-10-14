# Evidências de validação

Executadas em 13/10/2026 no ambiente de desenvolvimento, Python 3.12. Os arquivos JSON e TXT nesta pasta registram os resultados originais. Não representam validação de uma implantação cloud.

## Resultado

| Verificação | Resultado |
|---|---|
| pytest | 20 testes aprovados |
| ruff check / format | Aprovados |
| Ledger com Summary desligado | 30 créditos confirmados por HTTP |
| Recuperação do backlog | Saldo reconciliado em 3000 centavos |
| Queda/reinício de Summary e débito durante falha | Débito confirmado; saldo recuperado de 2500 centavos |
| Consultas: 50 req/s por 30 s | 1500/1500 concluídas; 0 erros; p95 5,36 ms |
| Ingestão: 50 req/s por 30 s | 1500/1500 concluídas; 0 erros; p95 5,22 ms |
| Reconciliação após ingestão | Aprovada |
| RAG offline e abstenção | Testes aprovados |
| Anthropic HTTP contract | Teste com transporte simulado aprovado |
| Docker/Compose | Não executado localmente; job CI preparado |
| Anthropic live | Não executado; requer chave/modelo e consumo externo |
| HA, TLS/OIDC, PostgreSQL, Service Bus | Arquitetura proposta, não implantada |
| GitHub público / Actions remoto | Pendente de publicação e execução |

O p95 do benchmark mede desde o horário agendado até a resposta, incluindo atraso de agendamento, para não ocultar atraso do gerador. É carga aberta de loopback, serviço único e base pequena. Consultas e ingestão foram exercitadas separadamente; sem base histórica grande, ruído de rede externa, carga mista ou soak de horas. O SLO de produção exige repetir no ambiente alvo. Logs dos serviços foram descartados apenas no benchmark para não poluir a saída; aplicação normal emite logs.

pytest emitiu um aviso de depreciação da combinação Starlette TestClient/httpx nas versões instaladas. Os testes passaram; migrar o transporte de testes quando exigido pelas dependências. O cliente HTTP da aplicação segue usando httpx. Não silenciamos o aviso.

## Cenários cobertos

Saldo inicial/final e movimento; datas retroativas; valores inválidos e float/bool; duplicação concorrente de evento e chave HTTP; conflito de payload; rollback de lançamento quando Outbox falha; perda de ACK depois do commit; retry e recuperação; quarentena sem bloquear próximo evento; persistência depois de reabrir banco; autenticação e credenciais separadas para evento; contrato Anthropic; citações inválidas; pergunta sem evidência; dependências da Clean Architecture.

## Próximos gates antes de produção

Carga mista e longa duração; cardinalidade histórica; falha do disco e backup/restore; HA e failover real; migrations versionadas; reconciliação/rebuild automatizados; segurança JWT e isolamento por comerciante; scan CVE e secrets; avaliação semântica RAG e prompt injection; teste de Anthropic em conta autorizada; aprovação de orçamento e limites.
