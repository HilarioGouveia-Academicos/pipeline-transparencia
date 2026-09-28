-- 1. Órgãos com maior valor líquido de viagens (sem somar detalhes novamente).
SELECT codigo_orgao_solicitante, nome_orgao_solicitante,
       SUM(viagens) AS viagens, SUM(valor_total_liquido) AS valor_liquido,
       ROUND(100 * SUM(valor_total_liquido) /
             NULLIF(SUM(SUM(valor_total_liquido)) OVER (), 0), 2) AS percentual_valor
FROM gold.resumo_orgao_mes
GROUP BY codigo_orgao_solicitante, nome_orgao_solicitante
ORDER BY valor_liquido DESC, codigo_orgao_solicitante NULLS LAST, nome_orgao_solicitante NULLS LAST
LIMIT 10;

-- 2. Valores atribuídos ao mês de início da viagem; não é fluxo de caixa.
SELECT mes_inicio, SUM(viagens) AS viagens,
       SUM(valor_total_liquido) AS valor_liquido,
       ROUND(SUM(valor_total_liquido) / NULLIF(SUM(viagens), 0), 2) AS media_por_viagem
FROM gold.resumo_orgao_mes
GROUP BY mes_inicio ORDER BY mes_inicio;

-- 3. Média ponderada pelo número de viagens, acompanhada do volume.
SELECT codigo_orgao_solicitante, nome_orgao_solicitante,
       SUM(viagens) AS viagens,
       ROUND(SUM(valor_total_liquido) / NULLIF(SUM(viagens), 0), 2) AS media_por_viagem
FROM gold.resumo_orgao_mes
GROUP BY codigo_orgao_solicitante, nome_orgao_solicitante
ORDER BY media_por_viagem DESC, codigo_orgao_solicitante NULLS LAST, nome_orgao_solicitante NULLS LAST
LIMIT 10;
