CREATE SCHEMA IF NOT EXISTS gold;

-- Uma linha por mês de início e par (código, nome) do órgão solicitante.
CREATE TABLE IF NOT EXISTS gold.resumo_orgao_mes (
    mes_inicio DATE NOT NULL CHECK (EXTRACT(DAY FROM mes_inicio) = 1),
    orgao_chave TEXT NOT NULL,
    codigo_orgao_solicitante TEXT,
    nome_orgao_solicitante TEXT,
    viagens BIGINT NOT NULL CHECK (viagens > 0),
    viagens_urgentes BIGINT NOT NULL CHECK (viagens_urgentes BETWEEN 0 AND viagens),
    duracao_total_dias BIGINT NOT NULL CHECK (duracao_total_dias >= 0),
    maior_duracao_dias INTEGER NOT NULL CHECK (maior_duracao_dias >= 0),
    valor_diarias NUMERIC NOT NULL,
    valor_passagens NUMERIC NOT NULL,
    valor_outros_gastos NUMERIC NOT NULL,
    valor_devolucao NUMERIC NOT NULL,
    valor_total_bruto NUMERIC NOT NULL,
    valor_total_liquido NUMERIC NOT NULL,
    pagamentos BIGINT NOT NULL CHECK (pagamentos >= 0),
    valor_pagamentos NUMERIC NOT NULL,
    passagens BIGINT NOT NULL CHECK (passagens >= 0),
    valor_passagens_detalhe NUMERIC NOT NULL,
    taxa_servico NUMERIC NOT NULL,
    trechos BIGINT NOT NULL CHECK (trechos >= 0),
    numero_diarias_trechos NUMERIC NOT NULL CHECK (numero_diarias_trechos >= 0),
    trechos_rejeitados BIGINT NOT NULL CHECK (trechos_rejeitados >= 0),
    PRIMARY KEY (mes_inicio, orgao_chave),
    CHECK (orgao_chave = jsonb_build_array(codigo_orgao_solicitante, nome_orgao_solicitante)::text),
    CHECK (valor_total_bruto = valor_diarias + valor_passagens + valor_outros_gastos),
    CHECK (valor_total_liquido = valor_total_bruto - valor_devolucao)
);
