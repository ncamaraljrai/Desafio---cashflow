# Registro de decisões arquiteturais

## ADR-001 — Serviços independentes com Clean Architecture
**Status:** aceito para o desafio. **Contexto:** indisponibilidade do consolidado não pode impedir registro. **Decisão:** Ledger, Summary e relay em processos independentes, com ports/adapters. **Alternativas:** monólito modular simplifica operação, mas compartilha falhas; serverless facilita elasticidade, porém acrescenta runtime/observabilidade específicos. **Consequência:** mais componentes, consistência eventual explícita e testes de integração necessários.

## ADR-002 — Outbox transacional e Inbox idempotente
**Status:** implementado. **Decisão:** entry+outbox em um commit, inbox+daily em outro. **Alternativas:** gravar e depois enviar sem Outbox perde mensagens na janela de falha; transação distribuída aumenta acoplamento e coordenação. **Consequência:** reenvio esperado, persistência adicional e reconciliação operacional. Não prometer exactly-once de rede.

## ADR-003 — Python/FastAPI e persistência local SQLite
**Status:** implementado localmente. **Decisão:** Python favorece clareza, testes e integração IA; FastAPI fornece contratos; SQLite evita dependência de infraestrutura para avaliar regras. **Alternativas:** .NET/Java seriam igualmente adequados; PostgreSQL desde o início acrescenta setup, mas é o adapter indicado para produção. **Consequência:** host único, um escritor de cada vez e limite operacional explícito. A escolha local não demonstra horizontal scaling.

## ADR-004 — PostgreSQL HA e Service Bus no alvo
**Status:** proposto, não implementado. **Decisão:** isolamento de dados por domínio e broker durável gerenciado. **Alternativas:** RabbitMQ requer mais operação; Kafka é valioso para streams/replay em grande escala, mas excessivo para 50 req/s. **Consequência:** custo, políticas de retenção/DLQ, identidades e configuração de infraestrutura. Confirmar tier/região e restrições na implantação.

## ADR-005 — Centavos inteiros e diário derivado
**Status:** implementado. **Decisão:** money em inteiro, eventos imutáveis, opening calculado a partir dos dias anteriores. **Alternativas:** decimal exato funciona, mas exige serialização cuidadosa; float inadequado. **Consequência:** limitar valores, considerar overflow acumulado e múltiplas moedas em evolução. Não oferecer edit/delete.

## ADR-006 — RAG lexical primeiro; Claude atrás de porta
**Status:** implementado opcionalmente. **Decisão:** FTS5/BM25 sobre corpus pequeno, chunks de 900 caracteres com passo de 700, top-4; adapter Anthropic Messages API; offline extrativo. **Alternativas:** embeddings/híbrido melhora sinônimos e corpus maior, mas exige avaliação, infraestrutura e custo. Anthropic não é tratado como fornecedor de embeddings. **Consequência:** lexical pode falhar em paráfrases; abstenção e conjunto de avaliação são necessários. Evoluir para PostgreSQL/pgvector + embeddings de provedor escolhido, mantendo geração Anthropic.

## ADR-007 — IA fora da decisão financeira
**Status:** implementado. **Decisão:** nenhum cálculo nem lançamento delegado ao LLM; endpoint recebe data explícita e busca facts por GET. Sem tools de escrita, sem text-to-SQL. **Consequência:** menor flexibilidade conversacional, melhor contenção de risco. Citações verificam identidade, não veracidade semântica. Revisão humana segue necessária para explicações.
