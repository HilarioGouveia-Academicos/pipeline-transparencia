"""
tests/test_camadas_tabelas.py
Verifica a existência dos schemas e tabelas das camadas Raw, Silver e Gold.
"""

import pytest

def test_existencia_schemas(conexao_db):
    """Verifica se os schemas raw, silver e gold foram criados."""
    with conexao_db.cursor() as cur:
        cur.execute("""
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name IN ('raw', 'silver', 'gold');
        """)
        schemas = [row[0] for row in cur.fetchall()]
        assert "raw" in schemas
        assert "silver" in schemas
        assert "gold" in schemas

@pytest.mark.parametrize("schema, tabela", [
    ("raw", "raw_viagem"),
    ("silver", "silver_passagem"),
    ("silver", "silver_pagamento"),
    ("silver", "silver_trecho"),
    ("gold", "gold_metricas"),
])
def test_existencia_tabelas(conexao_db, schema, tabela):
    """Verifica se as tabelas estruturais existem nos respetivos schemas."""
    with conexao_db.cursor() as cur:
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = %s AND table_name = %s
            );
        """, (schema, tabela))
        existe = cur.fetchone()[0]
        assert existe is True, f"A tabela {schema}.{tabela} não foi encontrada."
