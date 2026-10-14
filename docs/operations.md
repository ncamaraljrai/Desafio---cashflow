# Operação, observabilidade e segurança

## Implementado versus alvo

| Área | Implementado localmente | Produção proposta |
|---|---|---|
| Identidade | Bearer tokens aleatórios, API/evento distintos, comparação constante | OIDC/JWT validando assinatura, issuer, audience, exp; scopes ledger:write/balances:read; identidade de serviço |
| Rede | Localhost no Compose, separação de portas | TLS, rede privada, mTLS/identidade, gateway, egress restrito |
| Entrada | Tipos estritos, valores/datas, campos extras proibidos, SQL parametrizado | WAF, body limit, quotas por identidade, rate limiting distribuído |
| Logs | JSON por request: ID, método, path, status, duração; relay loga ID/tentativa | Coletor central, traces OTel, correlation/causation ID em eventos, alertas |
| Saúde | Live/ready por banco próprio | Readiness sem dependência transitiva; liveness sem banco; probes e múltiplas zonas |
| Persistência | WAL + synchronous FULL, volumes, transações | PostgreSQL HA/PITR, backups criptografados, restore testado |
| Segredos | .env ignorado no Git, sem valores reais no pacote | Secret manager, rotação, credencial por papel, scanner no CI |
| Supply chain | Versões diretas/transitivas travadas, Dependabot | SBOM, scan CVE/imagem, assinaturas, actions por SHA aprovado |

O lock registra versões usadas, mas não é atestado de ausência de vulnerabilidades. Imagem base e actions usam tags, não digest/SHA imutável; endurecer conforme política da organização. A implantação local é uma demonstração, não fronteira segura de internet. Não expor Uvicorn diretamente em produção.

## Métricas e alertas

Hoje: logs de duração/status e `GET /ops/outbox` com pending, quarantined e idade da pendência mais antiga. Logs não incluem token, pergunta IA ou descrição financeira. Este endpoint é protegido pelo token demo; alvo exige papel ops dedicado. Não existe exporter Prometheus nem tracing distribuído instalado.

Configurar na produção:

| Sinal | Alerta proposto | Ação |
|---|---|---|
| Erros de consulta | >5% em 5 min sob 50 req/s | Inspecionar API/DB, escalar, rollback |
| p95 consultas | >300 ms por 5 min | Locks, plano SQL, CPU, pool |
| Outbox mais antiga | >60 s por 5 min | Verificar relay/broker/destino |
| Quarentena/DLQ | Qualquer evento | Investigar contrato; nunca descartar sem auditoria |
| Disco ledger | >70% warning; >85% crítico | Aumentar capacidade, restaurar entrega, retenção segura |
| Frescor | evento→commit p95 >5 s | Aumentar consumidores após medir contenção |
| IA | 429/5xx, tokens e custo | Quota, reduzir contexto, desabilitar assistente |

Falha de armazenamento pode impedir escritas; nenhuma arquitetura com recursos finitos garante buffering ilimitado. Dimensionar retenção para falha plausível e responder 503 sem confirmação falsa quando a transação não puder ser persistida.

## Falha e recuperação local

1. `docker compose stop summary`: lançamentos continuam respondendo; pending cresce.
2. Consulte `/ops/outbox` com API_TOKEN; nunca publique o token.
3. `docker compose start summary`: retries drenam backlog. Backoff exponencial com jitter até cerca de 61 s; sem expiração automática para falhas transitórias.
4. Compare saldo com créditos menos débitos aceitos e contagem de eventos. Teste automatizado: `scripts/verify_runtime.py`.
5. Timeout após commit do consumidor resulta em replay idempotente. Commit do ledger que ocorreu sem resposta ao cliente também exige replay com mesma Idempotency-Key.

400/409/413/422 na entrega são erros de contrato permanentes e ficam em quarentena. 401, 429 e 5xx geram retry e exigem alerta operacional. Corrija credencial/contrato antes de reprocessar. No demo, reprocessamento de quarentena é intervenção administrativa controlada no banco, com backup e registro do incidente; não existe endpoint público de replay. Nunca altere payload com mesmo event_id para “corrigir” conflito.

## Retenção, reconciliação e desastre

Entries, idempotency keys, Inbox e Outbox entregue não são purgadas automaticamente no demo. Definir retenção de acordo com negócio; não remover deduplicação antes do horizonte máximo de replay. Crescimento de dados precisa de monitoramento. Evolução: particionar histórico e compactar Outbox entregue, mantendo auditoria e capacidade de reconciliação.

Runbook alvo: restaurar banco Ledger a partir de backup/PITR; validar integridade e totais; recriar Summary e sua Inbox juntos; reproduzir eventos derivados do Ledger imutável; reconciliar contagem e soma por dia; liberar leitura quando consistente. Não zerar Inbox mantendo daily, pois isso duplicaria efeitos. Esse rebuild deve ser implementado e ensaiado antes de produção; a entrega não fornece automação de desastre.

Backup local SQLite deve usar a API de backup ou processo consistente, não copiar apenas o arquivo principal enquanto WAL está ativo. Restaurar em ambiente separado e testar antes de substituir dados ativos. RPO/RTO propostos estão em requirements.md.

## Ameaças consideradas

Replay financeiro → chave única e fingerprint. Injeção SQL → parâmetros. Alteração do evento → Inbox compara digest. Roubo de token → secrets/rotação/TLS no alvo; token local não tem revogação granular. DoS → limite de concorrência no servidor e bulkhead IA; gateway de produção ainda necessário. Exfiltração por prompt → corpus aprovado, sem tools, egress fixo, redução de dados. Falha simultânea do host → persistência/replicação em produção; Compose não protege.
