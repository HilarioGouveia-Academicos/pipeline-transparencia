"""Testes de fumaça das camadas já entregues: Raw e Silver."""
import pytest


def test_existencia_schemas(conexao_db):
    with conexao_db.cursor() as cur:
        cur.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('raw','silver')")
        assert {r[0] for r in cur.fetchall()} == {'raw','silver'}


@pytest.mark.parametrize('schema,tabela',
    [('raw','raw_'+t) for t in ['viagem','pagamento','passagem','trecho']] +
    [('silver','silver_'+t) for t in ['viagem','pagamento','passagem','trecho']] +
    [('silver','rejeitados')])
def test_existencia_tabelas(conexao_db,schema,tabela):
    with conexao_db.cursor() as cur:
        cur.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema=%s AND table_name=%s)",(schema,tabela))
        assert cur.fetchone()[0], f'Tabela ausente: {schema}.{tabela}'
