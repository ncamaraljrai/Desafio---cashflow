# Estimativa paramétrica de custos e licenças

**Moeda: USD/mês.** Valores abaixo são hipóteses ilustrativas de orçamento, não preços atuais de Azure, Anthropic ou GitHub e não cotação comercial. Sem região, tier, volume mensal, retenção e contrato não há estimativa fechada defensável. Substituir premissas por orçamento do provedor antes de aprovar produção. Impostos, câmbio, egress, suporte e trabalho da equipe não incluídos.

## Perfil local
Python, FastAPI e SQLite sem contratação de infraestrutura cloud; custo de computador/energia e trabalho não estimado. Modo offline não chama API de LLM. Docker Desktop pode exigir assinatura dependendo da organização; validar termos aplicáveis. Copilot e Anthropic são produtos separados, com cobrança/termos próprios.

## Perfil alvo: dois domínios HA, 730 horas/mês

| Item | Premissa de orçamento (não tarifa) | Fórmula | USD/mês |
|---|---|---|---:|
| Compute APIs/workers | 6 unidades equivalentes, USD0,05/unidade-hora | 6 × 730 × 0,05 | 219 |
| PostgreSQL por domínio com HA | 2 conjuntos, USD250/conjunto | 2 × 250 | 500 |
| Broker gerenciado | envelope reservado | 1 × 80 | 80 |
| Gateway/TLS | envelope reservado | 1 × 60 | 60 |
| Logs/monitoramento | retenção moderada | 1 × 50 | 50 |
| Backup/armazenamento | envelope reservado | 1 × 40 | 40 |
| Secret manager | baixo volume | 1 × 5 | 5 |
| **Subtotal ilustrativo** | | | **1054** |
| Contingência 20% | variabilidade de consumo | 1054 × 0,20 | **210,80** |
| **Total antes de IA/licenças/tributos** | | | **1264,80** |

Essas unidades não são SKUs implantáveis; dimensionamento/HA e limites precisam ser convertidos em serviços e tarifas reais. O objetivo é explicitar a conta e os maiores componentes, não prometer um preço.

50 req/s sustentados por 30 dias = 129.600.000 requisições. Pico por 1 h/dia = 5.400.000 requisições/mês. Não dimensionar apenas pelo pico instantâneo. Logs por request, consultas e tráfego podem dominar custo. Estimar bytes/evento × eventos/s × janela de indisponibilidade, replicação e índices para tamanho do buffer.

## IA variável

`Custo = chamadas × ((tokens_entrada × preço_entrada_por_milhão) + (tokens_saída × preço_saída_por_milhão)) / 1.000.000`

Exemplo **puramente hipotético**, não tarifa Claude: 10.000 chamadas, 3.000 tokens de entrada e 600 de saída, preços assumidos de USD3 e USD15 por milhão → **USD180/mês**. Troque preços pelo modelo exato habilitado na conta. A implementação limita saída a 700 tokens; a conta usa média suposta de 600. Corpus atual usa busca lexical sem custo de embeddings. Evolução híbrida acrescenta ingestão/embeddings, armazenamento e reranking.

Custos por operador Copilot e licenças de ferramentas devem ser adicionados separadamente. Não há gasto Anthropic realizado nesta entrega.

## Otimização
Começar sem Redis/Kubernetes obrigatório. Manter IA opcional e sob quota; restringir logs verbosos e retenção; medir consultas antes de criar réplicas/cache. Se a exigência de HA for relaxada, compute/DB menores podem reduzir custo, mas registrar a perda de resiliência. Não economizar removendo Outbox/Inbox ou backup.
