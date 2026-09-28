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
