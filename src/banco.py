"""
banco.py
--------
Camada de acesso ao PostgreSQL: conexão, execução e inserções.
"""

import psycopg2
from psycopg2 import Error
from psycopg2 import sql as pg_sql
from config import POSTGRES_CONFIG
from pathlib import Path
import logging

# Configuração básica de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def criar_estrutura(criar_database=False):
    """Executa o mesmo SQL da instalação manual, somente após confirmação na UI."""
    script = (Path(__file__).resolve().parents[1] / 'sql/0_criar_banco.sql').read_text(encoding='utf-8-sig')
    if criar_database:
        configuracao = {**POSTGRES_CONFIG, 'dbname': 'postgres'}
        manutencao = psycopg2.connect(**configuracao)
        try:
            manutencao.autocommit = True
            with manutencao.cursor() as cursor:
                cursor.execute('SELECT 1 FROM pg_database WHERE datname = %s', (POSTGRES_CONFIG['dbname'],))
                if cursor.fetchone() is None:
                    cursor.execute(pg_sql.SQL('CREATE DATABASE {}').format(pg_sql.Identifier(POSTGRES_CONFIG['dbname'])))
        finally:
            manutencao.close()
    conexao = conectar()
    try:
        with conexao:
            with conexao.cursor() as cursor:
                cursor.execute(script)
    finally:
        conexao.close()

def conectar():
    """
    Abre uma conexão com o PostgreSQL (no database configurado no .env).
    Retorna a conexão ativa ou lança RuntimeError em caso de falha.
    """
    try:
        conexao = psycopg2.connect(**POSTGRES_CONFIG)
        logging.info(f"Conectado ao PostgreSQL em {POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['dbname']}")
        return conexao
    except Error as erro:
        raise RuntimeError(
            f"Não foi possível conectar ao PostgreSQL em "
            f"{POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']} / database "
            f"'{POSTGRES_CONFIG['dbname']}'. Verifique o .env e se você já rodou "
            f"o script '0_criar_banco.sql'. Detalhe: {erro}"
        )

def executar(conexao, sql, params=None):
    """
    Executa um comando SQL simples (DDL ou DML).
    Aceita parâmetros opcionais para evitar SQL injection.
    """
    try:
        with conexao.cursor() as cursor:
            cursor.execute(sql, params)
            conexao.commit()
            logging.info("Comando SQL executado com sucesso.")
    except Error as erro:
        conexao.rollback()
        logging.error(f"Erro ao executar SQL: {erro}")
        raise

def inserir_em_lote(conexao, sql_insert, linhas):
    """
    Insere várias linhas de uma vez (mais rápido que uma a uma).
    'linhas' é uma lista de tuplas; 'sql_insert' usa %s nos valores.
    """
    if not linhas:
        logging.warning("Nenhuma linha para inserir.")
        return
    try:
        with conexao.cursor() as cursor:
            cursor.executemany(sql_insert, linhas)
            conexao.commit()
            logging.info(f"{cursor.rowcount} linhas inseridas com sucesso.")
    except Error as erro:
        conexao.rollback()
        logging.error(f"Erro ao inserir em lote: {erro}")
        raise

def consultar(conexao, sql, params=None):
    """
    Executa um SELECT e retorna os resultados como lista de tuplas.
    """
    try:
        with conexao.cursor() as cursor:
            cursor.execute(sql, params)
            resultados = cursor.fetchall()
            logging.info(f"Consulta retornou {len(resultados)} registros.")
            return resultados
    except Error as erro:
        logging.error(f"Erro ao consultar: {erro}")
        raise
