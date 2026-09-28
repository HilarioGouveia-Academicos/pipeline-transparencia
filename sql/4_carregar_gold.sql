-- Cada detalhe vira uma linha por viagem ANTES dos JOINs: evita produto cartesiano.
WITH pagamentos AS (
    SELECT id_viagem, COUNT(*) AS quantidade, SUM(valor) AS valor
    FROM silver.silver_pagamento GROUP BY id_viagem
), passagens AS (
    SELECT id_viagem, COUNT(*) AS quantidade, SUM(valor_passagem) AS valor,
           SUM(taxa_servico) AS taxa
    FROM silver.silver_passagem GROUP BY id_viagem
), trechos AS (
    SELECT id_viagem, COUNT(*) AS quantidade, SUM(numero_diarias) AS diarias
    FROM silver.silver_trecho GROUP BY id_viagem
), rejeitados AS (
    SELECT id_viagem, COUNT(*) AS quantidade
    FROM silver.rejeitados WHERE origem = 'trecho' GROUP BY id_viagem
)
INSERT INTO gold.resumo_orgao_mes
SELECT date_trunc('month', v.data_inicio)::date,
       jsonb_build_array(v.codigo_orgao_solicitante, v.nome_orgao_solicitante)::text,
       v.codigo_orgao_solicitante, v.nome_orgao_solicitante,
       COUNT(*), COUNT(*) FILTER (WHERE v.viagem_urgente),
       SUM(v.duracao_dias), MAX(v.duracao_dias),
       SUM(v.valor_diarias), SUM(v.valor_passagens), SUM(v.valor_outros_gastos),
       SUM(v.valor_devolucao), SUM(v.valor_total_bruto), SUM(v.valor_total_liquido),
       SUM(COALESCE(p.quantidade, 0)), SUM(COALESCE(p.valor, 0)),
       SUM(COALESCE(a.quantidade, 0)), SUM(COALESCE(a.valor, 0)), SUM(COALESCE(a.taxa, 0)),
       SUM(COALESCE(t.quantidade, 0)), SUM(COALESCE(t.diarias, 0)),
       SUM(COALESCE(r.quantidade, 0))
FROM silver.silver_viagem v
LEFT JOIN pagamentos p ON p.id_viagem = v.id_viagem
LEFT JOIN passagens a ON a.id_viagem = v.id_viagem
LEFT JOIN trechos t ON t.id_viagem = v.id_viagem
LEFT JOIN rejeitados r ON r.id_viagem = v.id_viagem
GROUP BY date_trunc('month', v.data_inicio)::date,
         v.codigo_orgao_solicitante, v.nome_orgao_solicitante;
