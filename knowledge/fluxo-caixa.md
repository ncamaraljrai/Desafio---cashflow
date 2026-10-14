# Regras do fluxo de caixa
Crédito representa entrada; débito representa saída. Valores são inteiros em centavos de BRL. Saldo inicial é a soma líquida dos dias anteriores. Movimento líquido diário é créditos menos débitos. Saldo final é saldo inicial mais movimento líquido. O saldo pode ser negativo. Uma data sem lançamentos tem movimento zero e carrega o saldo anterior. Estes dados são demonstrativos de um único comerciante.

# Datas e consolidação
business_date é a data comercial informada explicitamente em YYYY-MM-DD, no calendário America/Sao_Paulo. created_at registra recebimento em UTC. Lançamentos retroativos são permitidos e alteram os saldos posteriores. O consolidado tem consistência eventual. Um relatório pode estar defasado enquanto há eventos pendentes; o último evento recebido não prova que todas as mensagens chegaram.
