"""
tests/test_conexao_banco.py
Valida a conetividade básica com o PostgreSQL.
"""

def test_conexao_ativa(conexao_db):
    """Testa se a ligação à base de dados é bem-sucedida e responde."""
    assert conexao_db is not None
    assert conexao_db.closed == 0

def test_query_simples(conexao_db):
    """Executa uma query básica (SELECT 1) para confirmar execução."""
    with conexao_db.cursor() as cur:
        cur.execute("SELECT 1;")
        resultado = cur.fetchone()
        assert resultado[0] == 1