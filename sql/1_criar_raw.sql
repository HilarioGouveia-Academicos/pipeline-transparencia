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
