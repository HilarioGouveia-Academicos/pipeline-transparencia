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

-- Silver: uma tabela por entidade da fonte. Não altera a Raw.

CREATE SCHEMA IF NOT EXISTS silver;

CREATE TABLE IF NOT EXISTS silver.silver_viagem (
    id_viagem TEXT NOT NULL PRIMARY KEY,
    CHECK (btrim(id_viagem) <> ''),
    numero_proposta TEXT,
    situacao TEXT,
    viagem_urgente BOOLEAN NOT NULL,
    justificativa_urgencia TEXT,
    codigo_orgao_superior TEXT,
    nome_orgao_superior TEXT,
    codigo_orgao_solicitante TEXT,
    nome_orgao_solicitante TEXT,
    cpf_viajante TEXT,
    nome_viajante TEXT,
    cargo TEXT,
    funcao TEXT,
    descricao_funcao TEXT,
    data_inicio DATE NOT NULL,
    data_fim DATE NOT NULL,
    destinos TEXT,
    motivo TEXT,
    valor_diarias NUMERIC(18,2) NOT NULL,
    CHECK (valor_diarias > -10000000000000000 AND valor_diarias < 10000000000000000),
    valor_passagens NUMERIC(18,2) NOT NULL,
    CHECK (valor_passagens > -10000000000000000 AND valor_passagens < 10000000000000000),
    valor_devolucao NUMERIC(18,2) NOT NULL,
    CHECK (valor_devolucao > -10000000000000000 AND valor_devolucao < 10000000000000000),
    valor_outros_gastos NUMERIC(18,2) NOT NULL,
    CHECK (valor_outros_gastos > -10000000000000000 AND valor_outros_gastos < 10000000000000000),
    duracao_dias INTEGER NOT NULL,
    valor_total_bruto NUMERIC(18,2) NOT NULL,
    valor_total_liquido NUMERIC(18,2) NOT NULL,
    registro_hash CHAR(64) NOT NULL CHECK (registro_hash ~ '^[0-9a-f]{64}$'),
    ocorrencia INTEGER NOT NULL CHECK (ocorrencia > 0),
    UNIQUE (registro_hash, ocorrencia),
    CHECK (data_fim >= data_inicio),
    CHECK (duracao_dias = data_fim - data_inicio),
    CHECK (valor_total_bruto = valor_diarias + valor_passagens + valor_outros_gastos),
    CHECK (valor_total_liquido = valor_total_bruto - valor_devolucao)
);

CREATE TABLE IF NOT EXISTS silver.silver_pagamento (
    id_pagamento TEXT PRIMARY KEY,
    id_viagem TEXT NOT NULL REFERENCES silver.silver_viagem(id_viagem) ON DELETE RESTRICT,
    CHECK (btrim(id_viagem) <> ''),
    numero_proposta TEXT,
    codigo_orgao_superior TEXT,
    nome_orgao_superior TEXT,
    codigo_orgao_pagador TEXT,
    nome_orgao_pagador TEXT,
    codigo_unidade_gestora TEXT,
    nome_unidade_gestora TEXT,
    tipo_pagamento TEXT NOT NULL,
    CHECK (btrim(tipo_pagamento) <> ''),
    valor NUMERIC(18,2) NOT NULL,
    CHECK (valor > -10000000000000000 AND valor < 10000000000000000),
    registro_hash CHAR(64) NOT NULL CHECK (registro_hash ~ '^[0-9a-f]{64}$'),
    ocorrencia INTEGER NOT NULL CHECK (ocorrencia > 0),
    UNIQUE (registro_hash, ocorrencia),
    CHECK (id_pagamento = registro_hash || ':' || ocorrencia::text)
);

CREATE INDEX IF NOT EXISTS idx_silver_pagamento_viagem ON silver.silver_pagamento(id_viagem);

CREATE TABLE IF NOT EXISTS silver.silver_passagem (
    id_passagem TEXT PRIMARY KEY,
    id_viagem TEXT NOT NULL REFERENCES silver.silver_viagem(id_viagem) ON DELETE RESTRICT,
    CHECK (btrim(id_viagem) <> ''),
    numero_proposta TEXT,
    meio_transporte TEXT NOT NULL,
    CHECK (btrim(meio_transporte) <> ''),
    origem_ida_pais TEXT,
    origem_ida_uf_nome TEXT,
    origem_ida_cidade TEXT,
    destino_ida_pais TEXT,
    destino_ida_uf_nome TEXT,
    destino_ida_cidade TEXT,
    origem_volta_pais TEXT,
    origem_volta_uf_nome TEXT,
    origem_volta_cidade TEXT,
    destino_volta_pais TEXT,
    destino_volta_uf_nome TEXT,
    destino_volta_cidade TEXT,
    valor_passagem NUMERIC(18,2) NOT NULL,
    CHECK (valor_passagem > -10000000000000000 AND valor_passagem < 10000000000000000),
    taxa_servico NUMERIC(18,2) NOT NULL,
    CHECK (taxa_servico > -10000000000000000 AND taxa_servico < 10000000000000000),
    data_emissao DATE,
    hora_emissao TIME WITHOUT TIME ZONE,
    origem_ida_uf VARCHAR(2),
    destino_ida_uf VARCHAR(2),
    origem_volta_uf VARCHAR(2),
    destino_volta_uf VARCHAR(2),
    registro_hash CHAR(64) NOT NULL CHECK (registro_hash ~ '^[0-9a-f]{64}$'),
    ocorrencia INTEGER NOT NULL CHECK (ocorrencia > 0),
    UNIQUE (registro_hash, ocorrencia),
    CHECK (id_passagem = registro_hash || ':' || ocorrencia::text),
    CHECK (lower(btrim(meio_transporte)) <> 'inválido'),
    CHECK (origem_ida_uf IN ('AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO')),
    CHECK (destino_ida_uf IN ('AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO')),
    CHECK (origem_volta_uf IN ('AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO')),
    CHECK (destino_volta_uf IN ('AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO'))
);

CREATE INDEX IF NOT EXISTS idx_silver_passagem_viagem ON silver.silver_passagem(id_viagem);

CREATE TABLE IF NOT EXISTS silver.silver_trecho (
    id_trecho TEXT PRIMARY KEY,
    id_viagem TEXT NOT NULL REFERENCES silver.silver_viagem(id_viagem) ON DELETE RESTRICT,
    CHECK (btrim(id_viagem) <> ''),
    numero_proposta TEXT,
    sequencia INTEGER NOT NULL,
    origem_data DATE NOT NULL,
    origem_pais TEXT,
    origem_uf_nome TEXT,
    origem_cidade TEXT,
    destino_data DATE NOT NULL,
    destino_pais TEXT,
    destino_uf_nome TEXT,
    destino_cidade TEXT,
    meio_transporte TEXT NOT NULL,
    CHECK (btrim(meio_transporte) <> ''),
    numero_diarias NUMERIC(18,2) NOT NULL,
    CHECK (numero_diarias > -10000000000000000 AND numero_diarias < 10000000000000000),
    missao BOOLEAN NOT NULL,
    origem_uf VARCHAR(2),
    destino_uf VARCHAR(2),
    registro_hash CHAR(64) NOT NULL CHECK (registro_hash ~ '^[0-9a-f]{64}$'),
    ocorrencia INTEGER NOT NULL CHECK (ocorrencia > 0),
    UNIQUE (registro_hash, ocorrencia),
    CHECK (id_trecho = registro_hash || ':' || ocorrencia::text),
    CHECK (sequencia > 0),
    UNIQUE (id_viagem, sequencia),
    CHECK (destino_data >= origem_data),
    CHECK (numero_diarias >= 0),
    CHECK (lower(btrim(meio_transporte)) <> 'inválido'),
    CHECK (origem_uf IN ('AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO')),
    CHECK (destino_uf IN ('AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO'))
);

CREATE INDEX IF NOT EXISTS idx_silver_trecho_viagem ON silver.silver_trecho(id_viagem);

CREATE TABLE IF NOT EXISTS silver.rejeitados (
    origem TEXT NOT NULL CHECK (origem IN ('viagem','pagamento','passagem','trecho')),
    registro_hash CHAR(64) NOT NULL CHECK (registro_hash ~ '^[0-9a-f]{64}$'),
    ocorrencia INTEGER NOT NULL CHECK (ocorrencia > 0),
    id_viagem TEXT,
    motivos JSONB NOT NULL CHECK (jsonb_typeof(motivos) = 'array' AND jsonb_array_length(motivos) > 0),
    dados_originais JSONB NOT NULL CHECK (jsonb_typeof(dados_originais) = 'object'),
    valores_convertidos JSONB NOT NULL CHECK (jsonb_typeof(valores_convertidos) = 'object'),
    PRIMARY KEY (origem, registro_hash, ocorrencia)
);

CREATE INDEX IF NOT EXISTS idx_rejeitados_viagem ON silver.rejeitados(id_viagem);

-- ============================================================
-- Camada GOLD (Métricas, Agregações e Visão de Negócio)
-- ============================================================

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
