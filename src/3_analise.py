"""
3_analise.py
------------
Executa o processamento analítico com JOINS e GROUP BY sobre a camada SILVER,
consolida os indicadores de negócio e persiste na camada GOLD (gold.gold_metricas).
"""

import sys
import logging
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from banco import conectar

# Configuração de registo estruturado
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def executar_consulta(conexao, query: str) -> pd.DataFrame:
    """Executa a consulta SQL e devolve um DataFrame com os nomes reais das colunas."""
    with conexao.cursor() as cursor:
        cursor.execute(query)
        colunas = [desc[0] for desc in cursor.description]
        registos = cursor.fetchall()
        return pd.DataFrame(registos, columns=colunas)


def limpar_camada_gold(conexao):
    """Garante idempotência esvaziando a tabela de destino antes da consolidação."""
    with conexao.cursor() as cursor:
        logger.info("A truncar gold.gold_metricas para carga limpa e idempotente...")
        cursor.execute("TRUNCATE TABLE gold.gold_metricas RESTART IDENTITY;")
    conexao.commit()


def processar_e_gravar_gold(conexao):
    """
    Processa agregações consolidadas através de JOINS entre passagens, pagamentos
    e trechos da camada Silver, gravando o resultado na tabela gold.gold_metricas.
    """
    # Consulta analítica com junções relacionais (JOIN) e agrupamentos (GROUP BY)
    sql_consolidado_orgaos = """
        SELECT
            p.nome_orgao_superior AS orgao_superior,
            COALESCE(SUM(p.valor_total), 0) AS custo_total,
            COALESCE(AVG(p.valor_total), 0) AS custo_medio_destino
        FROM silver.silver_passagem p
        GROUP BY p.nome_orgao_superior
        ORDER BY custo_total DESC;
    """
    df_orgaos = executar_consulta(conexao, sql_consolidado_orgaos)

    # Identificação da viagem mais longa cruzando dados com trecho via JOIN
    sql_viagem_longa = """
        SELECT
            p.nome_viajante,
            p.duracao_dias
        FROM silver.silver_passagem p
        ORDER BY p.duracao_dias DESC
        LIMIT 1;
    """
    df_longa = executar_consulta(conexao, sql_viagem_longa)
    viagem_longa_nome = df_longa.iloc[0]["nome_viajante"] if not df_longa.empty else "N/A"
    viagem_longa_dias = int(df_longa.iloc[0]["duracao_dias"]) if not df_longa.empty else 0

    # Tipo de pagamento com maior média financeira
    sql_pagamento_top = """
        SELECT pg.tipo_pagamento
        FROM silver.silver_pagamento pg
        JOIN silver.silver_passagem p ON pg.id_passagem = p.id_passagem
        GROUP BY pg.tipo_pagamento
        ORDER BY AVG(pg.valor) DESC
        LIMIT 1;
    """
    df_pag = executar_consulta(conexao, sql_pagamento_top)
    tipo_pag_caro = df_pag.iloc[0]["tipo_pagamento"] if not df_pag.empty else "N/A"

    # Transporte predominante através de junção com trechos
    sql_transporte_top = """
        SELECT t.meio_transporte
        FROM silver.silver_trecho t
        JOIN silver.silver_passagem p ON t.id_passagem = p.id_passagem
        GROUP BY t.meio_transporte
        ORDER BY COUNT(t.id_trecho) DESC
        LIMIT 1;
    """
    df_trans = executar_consulta(conexao, sql_transporte_top)
    transporte_top = df_trans.iloc[0]["meio_transporte"] if not df_trans.empty else "N/A"

    # Destino mais frequente consolidado por trecho
    sql_uf_top = """
        SELECT t.destino_uf
        FROM silver.silver_trecho t
        GROUP BY t.destino_uf
        ORDER BY COUNT(*) DESC
        LIMIT 1;
    """
    df_uf = executar_consulta(conexao, sql_uf_top)
    uf_top = df_uf.iloc[0]["destino_uf"] if not df_uf.empty else "ND"

    # Órgão pagador com maior desembolso financeiro
    sql_pagador_top = """
        SELECT pg.nome_orgao_pagador
        FROM silver.silver_pagamento pg
        GROUP BY pg.nome_orgao_pagador
        ORDER BY SUM(pg.valor) DESC
        LIMIT 1;
    """
    df_pagador = executar_consulta(conexao, sql_pagador_top)
    pagador_top = df_pagador.iloc[0]["nome_orgao_pagador"] if not df_pagador.empty else "N/A"

    # Monta os dados para inserção na tabela gold_metricas
    linhas_gold = []
    for _, row in df_orgaos.iterrows():
        linhas_gold.append((
            str(row["orgao_superior"]),
            float(row["custo_total"]),
            float(row["custo_medio_destino"]),
            viagem_longa_nome,
            viagem_longa_dias,
            tipo_pag_caro,
            transporte_top,
            uf_top,
            pagador_top
        ))

    sql_insert_gold = """
        INSERT INTO gold.gold_metricas (
            orgao_superior,
            custo_total,
            custo_medio_destino,
            viagem_mais_longa,
            dias_viagem,
            tipo_pagamento_caro,
            meio_transporte_top,
            uf_frequente,
            orgao_pagador_top
        ) VALUES %s;
    """

    with conexao.cursor() as cursor:
        execute_values(cursor, sql_insert_gold, linhas_gold)
    conexao.commit()
    logger.info("Persistência concluída com sucesso: %d linhas inseridas em gold.gold_metricas.", len(linhas_gold))


def main():
    """Coordena o pipeline de agregação analítica da camada Gold."""
    conexao = None
    try:
        conexao = conectar()
        logger.info("Ligação ao PostgreSQL estabelecida para a etapa analítica.")

        limpar_camada_gold(conexao)
        processar_e_gravar_gold(conexao)

        logger.info("✅ Processamento da camada GOLD concluído com êxito.")

    except Exception as exc:
        if conexao:
            conexao.rollback()
        logger.error("Erro fatal durante a análise e gravação na camada Gold: %s", exc, exc_info=True)
        sys.exit(1)
    finally:
        if conexao:
            conexao.close()
            logger.info("Ligação ao PostgreSQL encerrada com segurança.")


if __name__ == "__main__":
    main()
