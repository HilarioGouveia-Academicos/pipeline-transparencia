-- ============================================================
-- Script: 0_criar_banco.sql (Refatorado)
-- Objetivo: Criar schemas, tabelas, constraints e relacionamentos
-- Camadas: RAW, SILVER, GOLD
-- ============================================================

-- 1. Criação dos Schemas
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

-- ============================================================
-- Camada RAW (Área de Staging para Carga Idempotente)
-- ============================================================

-- Raw: cabeçalhos e valores originais do ZIP fornecido pelo curso.

CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.raw_viagem (
    "Identificador do processo de viagem" TEXT NOT NULL,
    "Número da Proposta (PCDP)" TEXT NOT NULL,
    "Situação" TEXT NOT NULL,
    "Viagem Urgente" TEXT NOT NULL,
    "Justificativa Urgência Viagem" TEXT NOT NULL,
    "Código do órgão superior" TEXT NOT NULL,
    "Nome do órgão superior" TEXT NOT NULL,
    "Código órgão solicitante" TEXT NOT NULL,
    "Nome órgão solicitante" TEXT NOT NULL,
    "CPF viajante" TEXT NOT NULL,
    "Nome" TEXT NOT NULL,
    "Cargo" TEXT NOT NULL,
    "Função" TEXT NOT NULL,
    "Descrição Função" TEXT NOT NULL,
    "Período - Data de início" TEXT NOT NULL,
    "Período - Data de fim" TEXT NOT NULL,
    "Destinos" TEXT NOT NULL,
    "Motivo" TEXT NOT NULL,
    "Valor diárias" TEXT NOT NULL,
    "Valor passagens" TEXT NOT NULL,
    "Valor devolução" TEXT NOT NULL,
    "Valor outros gastos" TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.raw_pagamento (
    "Identificador do processo de viagem" TEXT NOT NULL,
    "Número da Proposta (PCDP)" TEXT NOT NULL,
    "Código do órgão superior" TEXT NOT NULL,
    "Nome do órgão superior" TEXT NOT NULL,
    "Codigo do órgão pagador" TEXT NOT NULL,
    "Nome do órgao pagador" TEXT NOT NULL,
    "Código da unidade gestora pagadora" TEXT NOT NULL,
    "Nome da unidade gestora pagadora" TEXT NOT NULL,
    "Tipo de pagamento" TEXT NOT NULL,
    "Valor" TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.raw_passagem (
    "Identificador do processo de viagem" TEXT NOT NULL,
    "Número da Proposta (PCDP)" TEXT NOT NULL,
    "Meio de transporte" TEXT NOT NULL,
    "País - Origem ida" TEXT NOT NULL,
    "UF - Origem ida" TEXT NOT NULL,
    "Cidade - Origem ida" TEXT NOT NULL,
    "País - Destino ida" TEXT NOT NULL,
    "UF - Destino ida" TEXT NOT NULL,
    "Cidade - Destino ida" TEXT NOT NULL,
    "País - Origem volta" TEXT NOT NULL,
    "UF - Origem volta" TEXT NOT NULL,
    "Cidade - Origem volta" TEXT NOT NULL,
    "Pais - Destino volta" TEXT NOT NULL,
    "UF - Destino volta" TEXT NOT NULL,
    "Cidade - Destino volta" TEXT NOT NULL,
    "Valor da passagem" TEXT NOT NULL,
    "Taxa de serviço" TEXT NOT NULL,
    "Data da emissão/compra" TEXT NOT NULL,
    "Hora da emissão/compra" TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.raw_trecho (
    "Identificador do processo de viagem " TEXT NOT NULL,
    "Número da Proposta (PCDP)" TEXT NOT NULL,
    "Sequência Trecho" TEXT NOT NULL,
    "Origem - Data" TEXT NOT NULL,
    "Origem - País" TEXT NOT NULL,
    "Origem - UF" TEXT NOT NULL,
    "Origem - Cidade" TEXT NOT NULL,
    "Destino - Data" TEXT NOT NULL,
    "Destino - País" TEXT NOT NULL,
    "Destino - UF" TEXT NOT NULL,
    "Destino - Cidade" TEXT NOT NULL,
    "Meio de transporte" TEXT NOT NULL,
    "Número Diárias" TEXT NOT NULL,
    "Missao?" TEXT NOT NULL
);
-- ============================================================
-- Camada SILVER (Modelagem Relacional com PK, FK e Constraints)
-- ============================================================

-- Tabela Principal de Viagens/Passagens
CREATE TABLE IF NOT EXISTS silver.silver_passagem (
    id_passagem SERIAL PRIMARY KEY,
    id_viagem_origem INTEGER,
    nome_viajante TEXT NOT NULL,
    nome_orgao_superior TEXT NOT NULL,
    destinos TEXT NOT NULL,
    destino_uf VARCHAR(2) NOT NULL,
    data_inicio DATE NOT NULL,
    data_fim DATE NOT NULL,
    duracao_dias INTEGER NOT NULL,
    valor_total NUMERIC(12,2) NOT NULL,
    CONSTRAINT chk_passagem_datas CHECK (data_fim >= data_inicio),
    CONSTRAINT chk_passagem_duracao CHECK (duracao_dias >= 0),
    CONSTRAINT chk_passagem_valor CHECK (valor_total >= 0)
);

-- Detalhe Financeiro / Pagamentos (Relacionamento 1:N com silver_passagem)
CREATE TABLE IF NOT EXISTS silver.silver_pagamento (
    id_pagamento SERIAL PRIMARY KEY,
    id_passagem INTEGER NOT NULL,
    nome_orgao_pagador TEXT NOT NULL,
    tipo_pagamento TEXT NOT NULL,
    valor NUMERIC(12,2) NOT NULL,
    CONSTRAINT fk_pagamento_passagem FOREIGN KEY (id_passagem)
        REFERENCES silver.silver_passagem (id_passagem)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT chk_pagamento_valor CHECK (valor >= 0)
);

-- Detalhe Logístico / Trechos (Relacionamento 1:N com silver_passagem)
CREATE TABLE IF NOT EXISTS silver.silver_trecho (
    id_trecho SERIAL PRIMARY KEY,
    id_passagem INTEGER NOT NULL,
    meio_transporte TEXT NOT NULL,
    destino_uf VARCHAR(2) NOT NULL,
    CONSTRAINT fk_trecho_passagem FOREIGN KEY (id_passagem)
        REFERENCES silver.silver_passagem (id_passagem)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- ============================================================
-- Camada GOLD (Métricas, Agregações e Visão de Negócio)
-- ============================================================

CREATE TABLE IF NOT EXISTS gold.gold_metricas (
    id SERIAL PRIMARY KEY,
    orgao_superior TEXT NOT NULL,
    custo_total NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    custo_medio_destino NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    viagem_mais_longa TEXT,
    dias_viagem INTEGER,
    tipo_pagamento_caro TEXT,
    meio_transporte_top TEXT,
    uf_frequente VARCHAR(2),
    orgao_pagador_top TEXT,
    atualizado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- Índices para Performance e Otimização de JOINs
-- ============================================================

-- Índices em Chaves Estrangeiras (essenciais para agilizar os JOINs da Gold)
CREATE INDEX IF NOT EXISTS idx_silver_pagamento_id_passagem
    ON silver.silver_pagamento (id_passagem);

CREATE INDEX IF NOT EXISTS idx_silver_trecho_id_passagem
    ON silver.silver_trecho (id_passagem);

-- Índices em colunas de agrupamento e filtro frequente
CREATE INDEX IF NOT EXISTS idx_silver_passagem_orgao
    ON silver.silver_passagem (nome_orgao_superior);

CREATE INDEX IF NOT EXISTS idx_silver_passagem_destino_uf
    ON silver.silver_passagem (destino_uf);

CREATE INDEX IF NOT EXISTS idx_silver_pagamento_orgao
    ON silver.silver_pagamento (nome_orgao_pagador);

CREATE INDEX IF NOT EXISTS idx_silver_trecho_transporte
    ON silver.silver_trecho (meio_transporte);