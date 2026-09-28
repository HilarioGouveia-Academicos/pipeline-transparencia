"""
Módulo de Transformação (Camada Raw -> Camada Silver)
Realiza a limpeza, conversão de tipos, enriquecimento e carga relacional.
"""

import os
import sys
import logging
from typing import Iterator
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Configuração de logging estruturado
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Parâmetros de infraestrutura e performance
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", 5432))
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "sua_senha")
POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE", "transparencia")
TAMANHO_BLOCO = int(os.getenv("TAMANHO_BLOCO", 50000))


def obter_conexao():
    """Gera uma conexão ativa com o banco PostgreSQL."""
    return psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        dbname=POSTGRES_DATABASE
    )


def limpar_moeda(serie: pd.Series) -> pd.Series:
    """Converte valores monetários em formato texto para numérico decimal."""
    return (
        serie.astype(str)
        .str.replace("R$", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.strip()
    )


def carregar_dados_raw(conn, tamanho_bloco: int) -> Iterator[pd.DataFrame]:
    """Lê os dados da camada Raw em lotes para otimização de memória."""
    query = """
        SELECT
            id_viagem,
            nome_viajante,
            orgao_superior,
            orgao_pagador,
            destino,
            destino_uf,
            data_inicio,
            data_fim,
            valor_total
        FROM raw.raw_viagem
        ORDER BY id_viagem;
    """
    for chunk in pd.read_sql_query(query, conn, chunksize=tamanho_bloco):
        yield chunk


def transformar_dados(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Aplica tipagem, sanitização e cálculo de campos derivados."""
    df = df_raw.copy()

    # Sanitização de textos
    colunas_texto = ["nome_viajante", "orgao_superior", "orgao_pagador", "destino", "destino_uf"]
    for col in colunas_texto:
        df[col] = df[col].astype(str).str.strip()

    # Normalização de UF para 2 dígitos
    df["destino_uf"] = df["destino_uf"].str.upper().str.slice(0, 2)
    df["destino_uf"] = df["destino_uf"].replace({"": "ND", "NA": "ND", "NAN": "ND"})

    # Conversão rigorosa de datas (DD/MM/AAAA ou ISO)
    df["data_inicio_dt"] = pd.to_datetime(df["data_inicio"], dayfirst=True, errors="coerce")
    df["data_fim_dt"] = pd.to_datetime(df["data_fim"], dayfirst=True, errors="coerce")

    # Tratamento de datas inconsistentes ou nulas
    df = df.dropna(subset=["data_inicio_dt", "data_fim_dt"])
    df = df[df["data_fim_dt"] >= df["data_inicio_dt"]]

    # Campo derivado: duração em dias
    df["duracao_dias"] = (df["data_fim_dt"] - df["data_inicio_dt"]).dt.days

    # Conversão e saneamento de valores monetários
    df["valor_total_num"] = pd.to_numeric(limpar_moeda(df["valor_total"]), errors="coerce").fillna(0.0)
    df = df[df["valor_total_num"] >= 0]

    return df


def carregar_camada_silver(conn, df_limpo: pd.DataFrame):
    """
    Persiste os dados limpos nas tabelas Silver mantendo a integridade referencial.
    """
    with conn.cursor() as cur:
        # 1. Inserção na tabela-mãe (silver_passagem) retornando os IDs gerados
        sql_passagem = """
            INSERT INTO silver.silver_passagem (
                id_viagem_origem,
                nome_viajante,
                nome_orgao_superior,
                destinos,
                destino_uf,
                data_inicio,
                data_fim,
                duracao_dias,
                valor_total
            ) VALUES %s
            RETURNING id_passagem, id_viagem_origem;
        """

        valores_passagem = [
            (
                int(row["id_viagem"]),
                row["nome_viajante"],
                row["orgao_superior"],
                row["destino"],
                row["destino_uf"],
                row["data_inicio_dt"].date(),
                row["data_fim_dt"].date(),
                int(row["duracao_dias"]),
                float(row["valor_total_num"])
            )
            for _, row in df_limpo.iterrows()
        ]

        ids_criados = execute_values(cur, sql_passagem, valores_passagem, fetch=True)
        mapa_ids = {id_origem: id_passagem for id_passagem, id_origem in ids_criados}

        # 2. Inserção com Chave Estrangeira em silver_pagamento
        sql_pagamento = """
            INSERT INTO silver.silver_pagamento (
                id_passagem,
                nome_orgao_pagador,
                tipo_pagamento,
                valor
            ) VALUES %s;
        """

        valores_pagamento = [
            (
                mapa_ids[row["id_viagem"]],
                row["orgao_pagador"],
                "Boleto/Ordem Bancária",  # Classificação padrão caso venha consolidado
                float(row["valor_total_num"])
            )
            for _, row in df_limpo.iterrows()
            if row["id_viagem"] in mapa_ids
        ]

        if valores_pagamento:
            execute_values(cur, sql_pagamento, valores_pagamento)

        # 3. Inserção com Chave Estrangeira em silver_trecho
        sql_trecho = """
            INSERT INTO silver.silver_trecho (
                id_passagem,
                meio_transporte,
                destino_uf
            ) VALUES %s;
        """

        valores_trecho = [
            (
                mapa_ids[row["id_viagem"]],
                "Aéreo",  # Meio padrão deduzido dos metadados de viagens a serviço
                row["destino_uf"]
            )
            for _, row in df_limpo.iterrows()
            if row["id_viagem"] in mapa_ids
        ]

        if valores_trecho:
            execute_values(cur, sql_trecho, valores_trecho)

    conn.commit()


def limpar_camada_silver(conn):
    """Garante a idempotência do pipeline truncando as tabelas com CASCADE."""
    with conn.cursor() as cur:
        logger.info("A limpar tabelas da camada Silver para reexecução idempotente...")
        cur.execute("TRUNCATE TABLE silver.silver_passagem RESTART IDENTITY CASCADE;")
    conn.commit()


def main():
    """Fluxo principal do processo de transformação e carga Silver."""
    logger.info("Iniciando o processamento da Camada Silver...")

    try:
        conn = obter_conexao()
        limpar_camada_silver(conn)

        total_processado = 0
        for bloco_idx, chunk in enumerate(carregar_dados_raw(conn, TAMANHO_BLOCO), start=1):
            if chunk.empty:
                continue

            logger.info("Processando bloco %d com %d registos...", bloco_idx, len(chunk))
            df_limpo = transformar_dados(chunk)

            if not df_limpo.empty:
                carregar_camada_silver(conn, df_limpo)
                total_processado += len(df_limpo)

        logger.info("Processamento concluído com sucesso. Total de registos transformados: %d", total_processado)

    except Exception as exc:
        logger.error("Erro fatal durante a transformação para a Silver: %s", exc, exc_info=True)
        sys.exit(1)
    finally:
        if "conn" in locals() and conn:
            conn.close()
            logger.info("Conexão ao PostgreSQL encerrada.")


if __name__ == "__main__":
    main()