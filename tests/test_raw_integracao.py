"""Integração opcional: banco temporário isolado para idempotência e rollback.
Execute com RUN_RAW_DB_TESTS=1 quando PostgreSQL estiver disponível.
"""
import importlib.util
import os
from pathlib import Path
import sys
import uuid

import psycopg2
from psycopg2 import sql
import pytest

from test_extracao import etl, criar_zip
from config import POSTGRES_CONFIG

pytestmark = pytest.mark.skipif(os.getenv('RUN_RAW_DB_TESTS') != '1', reason='Requer RUN_RAW_DB_TESTS=1 e PostgreSQL')


@pytest.fixture
def banco_isolado():
    nome = 'teste_raw_' + uuid.uuid4().hex
    admin = psycopg2.connect(**POSTGRES_CONFIG, connect_timeout=10)
    admin.autocommit = True
    conn = None
    criado = False
    try:
        with admin.cursor() as cur:
            cur.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(nome)))
        criado = True
        conn = psycopg2.connect(**{**POSTGRES_CONFIG, 'dbname': nome}, connect_timeout=10)
        yield conn
    finally:
        if conn:
            conn.close()
        if criado:
            with admin.cursor() as cur:
                cur.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(nome)))
        admin.close()


def snapshot(conn):
    resultados = {}
    with conn.cursor() as cur:
        for info in etl.ARQUIVOS.values():
            cur.execute(sql.SQL('SELECT * FROM {}').format(sql.Identifier('raw', info['tabela_raw'])))
            resultados[info['tabela_raw']] = etl.resumir(cur.fetchall())
    conn.commit()
    return resultados


def test_carga_reexecucao_e_rollback(tmp_path, banco_isolado):
    caminho = criar_zip(tmp_path)
    esperado = etl.validar_fonte(caminho, 2)
    etl.carregar_raw(banco_isolado, caminho, 2, esperado)
    assert snapshot(banco_isolado) == esperado
    etl.carregar_raw(banco_isolado, caminho, 1, esperado)
    assert snapshot(banco_isolado) == esperado
    # Falha após inserir todas as tabelas: o rollback precisa restaurar a carga anterior.
    adulterado = {nome: {**dados, 'linhas': dados['linhas'] + 1} for nome, dados in esperado.items()}
    with pytest.raises(ValueError, match='Conteúdo divergente'):
        etl.carregar_raw(banco_isolado, caminho, 2, adulterado)
    assert snapshot(banco_isolado) == esperado
