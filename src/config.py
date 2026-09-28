"""
config.py
---------
Configurações centrais do projeto: caminhos, credenciais e parâmetros.
"""

import os
import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Caminhos do projeto
# ---------------------------------------------------------------------------
PASTA_RAIZ = Path(__file__).resolve().parent.parent
PASTA_DADOS = PASTA_RAIZ / "data"   # onde ficam os .zip e .csv

# ---------------------------------------------------------------------------
# Leitura simples do arquivo .env (sem biblioteca externa)
# ---------------------------------------------------------------------------
def carregar_env():
    """Lê o arquivo .env (se existir) e joga as variáveis para os.environ."""
    arquivo_env = PASTA_RAIZ / ".env"
    if not arquivo_env.exists():
        return
    for linha in arquivo_env.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip())

carregar_env()

# ---------------------------------------------------------------------------
# Credenciais do PostgreSQL (vem do .env)
# ---------------------------------------------------------------------------
POSTGRES_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "localhost"),
    "port": int(os.environ.get("POSTGRES_PORT", "5432")),
    "user": os.environ.get("POSTGRES_USER", "postgres"),
    "password": os.environ.get("POSTGRES_PASSWORD", ""),
    "dbname": os.environ.get("POSTGRES_DATABASE", "transparencia"),
}

# ---------------------------------------------------------------------------
# Configurações gerais do projeto
# ---------------------------------------------------------------------------
ANO = os.environ.get("ANO", "2025")              # flexível via .env
APP_PORT = int(os.environ.get("APP_PORT", "8501"))
DRIVE_FILE_ID = os.environ.get("DRIVE_FILE_ID", "")
TAMANHO_BLOCO = int(os.environ.get("TAMANHO_BLOCO", "50000"))

# ---------------------------------------------------------------------------
# Mapeamento: cada arquivo CSV dentro do .zip -> tabela RAW correspondente
# ---------------------------------------------------------------------------
ARQUIVOS = json.loads((PASTA_RAIZ / "src" / "raw_layout.json").read_text(encoding="utf-8"))
ZIP_DADOS = Path(os.getenv("ZIP_DADOS", str(PASTA_DADOS / "viagens_2025_6meses.zip")))
if not ZIP_DADOS.is_absolute():
    ZIP_DADOS = PASTA_RAIZ / ZIP_DADOS

# ---------------------------------------------------------------------------
# Características dos arquivos CSV do Portal da Transparência
# ---------------------------------------------------------------------------
CSV_SEPARADOR = ";"
CSV_ENCODING = "latin-1"   # acentuação padrão ISO-8859-1
