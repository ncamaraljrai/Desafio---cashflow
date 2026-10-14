# Indisponibilidade do consolidado
Lançamentos e Outbox são gravados na mesma transação. A API de lançamentos não chama o consolidado. Se o consolidado cair, os eventos permanecem pendentes e o relay tenta novamente com backoff. Ao retornar, o consolidado processa os eventos. Eventos duplicados não duplicam o saldo. Erros permanentes de contrato ficam em quarentena para investigação.

# Segurança e IA
O assistente só consulta documentos aprovados e o relatório consolidado. Não cria, altera nem exclui lançamentos. O modo offline retorna trechos; o modo anthropic usa um LLM Claude. A resposta gerada não é a fonte oficial de valores. Os campos facts vêm do cálculo determinístico. Citações válidas não garantem, sozinhas, a veracidade de cada frase.
