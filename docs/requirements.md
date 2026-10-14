# Requisitos refinados e rastreabilidade

Fonte: desafio fornecido pelo candidato, páginas 2–3. Texto pede controle de lançamentos, consolidado diário, independência de disponibilidade e 50 req/s com no máximo 5% de perda. Não exige linguagem ou nuvem específica.

## Premissas a confirmar com negócio

1. Um comerciante e uma moeda BRL por instalação. Multitenancy requer identidade derivada do token, particionamento e testes de isolamento; não basta aceitar merchant_id do cliente.
2. Valor positivo em centavos; tipo determina sinal. Saldo negativo permitido. Limite de valor por lançamento: 10^12 centavos, escolhido para validação técnica; ajustar à política real.
3. Data comercial explícita no calendário America/Sao_Paulo; timestamp técnico em UTC. A API não infere data a partir de timezone do servidor.
4. Saldo diário significa saldo inicial, créditos, débitos, movimento e saldo final. Saldo inicial zero antes do primeiro lançamento; saldo legado precisa ser importado de forma auditável.
5. Retroativos permitidos; não há fechamento contábil, estorno referenciado ou exclusão. Correções formais/estornos são evolução a modelar com negócio; não editar silenciosamente histórico.
6. A consulta pode estar atrasada por consistência eventual. `last_event_received_at_epoch` indica última recepção, não completude do dia. Não rotular relatório como fechado.
7. Perda no teste significa timeout, erro HTTP ou requisição agendada não concluída. Máximo 5% é limite de indisponibilidade de solicitações sob carga, **não permissão para perder 5% dos lançamentos confirmados**.
8. Testamos 50 req/s de leitura e 50 req/s de ingestão separadamente por ambiguidade do enunciado. Carga mista, longa duração e base histórica de produção ainda precisam de validação.

## Funcionais e evidências

| ID | Aceitação | Implementação / evidência |
|---|---|---|
| F1 | Criar crédito/débito válido | POST /entries; teste de contrato |
| F2 | Não duplicar retry do cliente | Chave única + fingerprint; testes concorrentes |
| F3 | Consolidar por dia e saldo acumulado | SummaryStore.report; exemplo 10000+5000−2500=12500 |
| F4 | Não duplicar evento | Inbox + daily atômicos; replay e lost ACK |
| F5 | Rejeitar mesma identidade alterada | 409 em chave/evento conflitante |
| F6 | Retroativos e dias vazios corretos | opening calculado a partir de daily |
| F7 | Recuperar após indisponibilidade | Relay durável, teste HTTP com parada/reinício |
| F8 | Documentação e execução claras | README + contratos + scripts + Compose |
| F9 | Repositório público GitHub | **Pendente de publicação**; docs/github.md |
| D1 | GenAI/RAG com fontes | Serviço opcional, corpus versionado, citations e facts |
| D2 | Transição, custos, observabilidade, segurança | Documentos específicos, distinguindo local e alvo |

## Não funcionais: requisitos versus metas propostas

| Item | Critério | Situação |
|---|---|---|
| Obrigatório | Ledger aceita lançamentos quando Summary cai | Testado via HTTP real |
| Obrigatório | 50 req/s, erros ≤5% | Carga local aberta; evidência JSON; produção não certificada |
| Integridade proposta | Zero perda de lançamento confirmado por falha do Summary | Atomicidade e recuperação testadas; depende de retenção e integridade do disco Ledger |
| Latência proposta | Consulta p95 <300 ms; escrita p95 <500 ms | Consulta medida; escrita SLO ainda precisa benchmark dedicado |
| Frescor proposto | p95 evento→projeção <5 s em operação normal | Meta, sem medição contínua implementada |
| Disponibilidade proposta | 99,9% mensal por API | Meta de produção; Compose não é HA |
| Recuperação proposta | RPO ≤5 min e RTO ≤30 min em desastre regional | Exige backup/PITR e ensaio; não demonstrado |
| Segurança local | Tokens distintos, validação, queries parametrizadas | Testado parcialmente; TLS/OIDC no alvo |
| Manutenibilidade | Núcleo sem frameworks, dependências travadas, CI | Testes AST, locks, workflows |

99,9% mensal admite cerca de 43 minutos em um mês de 30 dias. Isso não é promessa contratual. O RPO regional não deve ser confundido com ausência de perda por falha de Summary: são cenários distintos.
