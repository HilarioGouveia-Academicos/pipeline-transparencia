"""Carga solicitada pelo painel, reutilizando os três scripts do pipeline."""
import os
import subprocess
import sys
from banco import conectar, criar_estrutura
from config import PASTA_RAIZ

ETAPAS = [('Raw', '1_extrair.py'), ('Silver', '2_transformar.py'), ('Gold', '3_analise.py')]
CHAVE_CARGA = 72419031


def carregar_pipeline(drive_file_id, progresso):
    if not drive_file_id or not all(c.isalnum() or c in '_-' for c in drive_file_id):
        raise ValueError('Informe o ID do arquivo ZIP no Google Drive, não o link da pasta.')
    conn = conectar()
    try:
        conn.autocommit = True
        with conn.cursor() as cursor:
            cursor.execute('SELECT pg_try_advisory_lock(%s)', (CHAVE_CARGA,))
            if not cursor.fetchone()[0]:
                raise RuntimeError('Já existe uma carga em andamento. Aguarde sua conclusão.')
        criar_estrutura()
        ambiente = os.environ.copy()
        ambiente.update(DRIVE_FILE_ID=drive_file_id, TAMANHO_BLOCO='5000', PYTHONUNBUFFERED='1')
        pasta = PASTA_RAIZ / 'data'
        pasta.mkdir(parents=True, exist_ok=True)
        for indice, (nome, script) in enumerate(ETAPAS):
            progresso(indice / len(ETAPAS), f'Carregando {nome}…')
            with (pasta / f'carga_{nome.lower()}.log').open('w', encoding='utf-8') as log:
                resultado = subprocess.run(
                    [sys.executable, str(PASTA_RAIZ / 'src' / script)],
                    cwd=PASTA_RAIZ, env=ambiente, stdout=log, stderr=subprocess.STDOUT,
                    timeout=7200, check=False,
                )
            if resultado.returncode:
                raise RuntimeError(f'A carga {nome} falhou. Consulte o log da etapa para identificar a causa.')
        progresso(1.0, 'Raw, Silver e Gold carregadas e verificadas.')
    finally:
        # Fechar a sessão libera o advisory lock também em caso de erro.
        conn.close()
