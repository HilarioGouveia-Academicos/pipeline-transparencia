"""
tests/conftest.py
Configurações e fixtures partilhadas para os testes com pytest.
"""

import os
import sys
import pytest
import psycopg2
from dotenv import load_dotenv

# Garante que a pasta 'src' ou raiz está no path para importar os módulos
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

@pytest.fixture(scope="session")
def conexao_db():
    """Fixture que estabelece e devolve a ligação à base de dados para os testes."""
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "sua_senha"),
            dbname=os.getenv("POSTGRES_DATABASE", "transparencia")
        )
        yield conn
    finally:
        if 'conn' in locals() and conn:
            conn.close()