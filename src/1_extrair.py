"""Carga fiel do ZIP do curso na Raw, em blocos e em uma única transação."""
import argparse
import csv
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import shutil
import sys
import urllib.request
import zipfile

from psycopg2 import sql
from banco import conectar
from config import ARQUIVOS, CSV_ENCODING, CSV_SEPARADOR, PASTA_RAIZ, TAMANHO_BLOCO, ZIP_DADOS

logger = logging.getLogger(__name__)
# Campos de justificativa podem ser maiores que o limite padrão do csv.
csv.field_size_limit(16 * 1024 * 1024)


def validar_zip(caminho):
    """Confere os quatro membros e os cabeçalhos, antes de modificar o banco."""
    with zipfile.ZipFile(caminho) as arquivo:
        for info in ARQUIVOS.values():
            if arquivo.namelist().count(info['csv']) != 1:
                raise ValueError(f"CSV ausente ou repetido no ZIP: {info['csv']}")
            with arquivo.open(info['csv']) as origem:
                leitor = csv.reader(io.TextIOWrapper(origem, encoding=CSV_ENCODING, newline=''),
                                    delimiter=CSV_SEPARADOR, strict=True)
                if next(leitor, None) != info['colunas']:
                    raise ValueError(f"Cabeçalho incompatível: {info['csv']}")


def obter_zip(caminho):
    if caminho.exists():
        validar_zip(caminho)
        return
    file_id = os.getenv('DRIVE_FILE_ID', '').strip()
    if not file_id or file_id == 'COLE_AQUI_O_ID_DO_ARQUIVO_NO_DRIVE':
        raise ValueError('ZIP local ausente. Configure DRIVE_FILE_ID com o ID do arquivo ZIP do curso (não da pasta).')
    if not all(c.isalnum() or c in '_-' for c in file_id):
        raise ValueError('DRIVE_FILE_ID deve conter apenas o ID do arquivo, não uma URL.')
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_suffix('.zip.part')
    try:
        req = urllib.request.Request(
            f'https://drive.google.com/uc?export=download&id={file_id}',
            headers={'User-Agent': 'pipeline-transparencia/1.0'})
        with urllib.request.urlopen(req, timeout=120) as resposta, temporario.open('wb') as destino:
            shutil.copyfileobj(resposta, destino, length=1024 * 1024)
        validar_zip(temporario)
        temporario.replace(caminho)
    except Exception:
        temporario.unlink(missing_ok=True)
        logger.exception('Download inválido ou indisponível. Verifique o ID e o acesso ao ZIP do curso.')
        raise


def ler_blocos(caminho, info, tamanho):
    if tamanho <= 0:
        raise ValueError('O tamanho do bloco deve ser positivo.')
    with zipfile.ZipFile(caminho) as arquivo, arquivo.open(info['csv']) as origem:
        leitor = csv.reader(io.TextIOWrapper(origem, encoding=CSV_ENCODING, newline=''),
                            delimiter=CSV_SEPARADOR, strict=True)
        if next(leitor, None) != info['colunas']:
            raise ValueError(f"Cabeçalho incompatível: {info['csv']}")
        bloco = []
        for linha in leitor:
            if len(linha) != len(info['colunas']):
                raise ValueError(f"{info['csv']}, linha física {leitor.line_num}: quantidade de campos inválida")
            if any('\x00' in valor for valor in linha):
                raise ValueError(f"{info['csv']}, linha {leitor.line_num}: NUL não suportado por PostgreSQL TEXT")
            bloco.append(linha)
            if len(bloco) == tamanho:
                yield bloco
                bloco = []
        if bloco:
            yield bloco


def assinatura(linha):
    # Soma dos hashes preserva multiplicidade e independe da ordem de leitura.
    payload = json.dumps(list(linha), ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return int.from_bytes(hashlib.sha256(payload).digest(), 'big')


def resumir(linhas):
    total, soma = 0, 0
    for linha in linhas:
        total += 1
        soma = (soma + assinatura(linha)) % (1 << 256)
    return {'linhas': total, 'assinatura': f'{soma:064x}'}


def validar_fonte(caminho, tamanho):
    validar_zip(caminho)
    resultados = {}
    for info in ARQUIVOS.values():
        resultados[info['tabela_raw']] = resumir(
            linha for bloco in ler_blocos(caminho, info, tamanho) for linha in bloco)
        logger.info('%s: %d registros validados', info['csv'], resultados[info['tabela_raw']]['linhas'])
    return resultados


def conferir_estrutura(conn):
    with conn.cursor() as cur:
        for info in ARQUIVOS.values():
            cur.execute('''SELECT column_name, data_type FROM information_schema.columns
                           WHERE table_schema = 'raw' AND table_name = %s ORDER BY ordinal_position''',
                        (info['tabela_raw'],))
            if cur.fetchall() != [(nome, 'text') for nome in info['colunas']]:
                raise ValueError(f"Estrutura incompatível em raw.{info['tabela_raw']}. Nenhuma tabela será truncada. Use sql/1_criar_raw.sql em um banco novo ou migre a estrutura antiga.")


def carregar_raw(conn, caminho, tamanho, esperado):
    """DDL, TRUNCATE, COPY e conferência compartilham o mesmo commit/rollback."""
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute((PASTA_RAIZ / 'sql/1_criar_raw.sql').read_text(encoding='utf-8'))
            conferir_estrutura(conn)
            with conn.cursor() as cur:
                tabelas = sql.SQL(', ').join(sql.Identifier('raw', i['tabela_raw']) for i in ARQUIVOS.values())
                # Sem CASCADE: não apaga dependências fora da Raw.
                cur.execute(sql.SQL('TRUNCATE TABLE {} RESTART IDENTITY').format(tabelas))
                for info in ARQUIVOS.values():
                    comando = sql.SQL('COPY {} ({}) FROM STDIN WITH (FORMAT CSV)').format(
                        sql.Identifier('raw', info['tabela_raw']),
                        sql.SQL(', ').join(map(sql.Identifier, info['colunas'])))
                    for bloco in ler_blocos(caminho, info, tamanho):
                        buffer = io.StringIO(newline='')
                        # Todos os valores entre aspas: vazio, NA e barra-N continuam texto.
                        csv.writer(buffer, quoting=csv.QUOTE_ALL, lineterminator='\n').writerows(bloco)
                        buffer.seek(0)
                        cur.copy_expert(comando.as_string(conn), buffer)
                    logger.info('Carga concluída: raw.%s', info['tabela_raw'])
            for info in ARQUIVOS.values():
                with conn.cursor(name='conferencia_raw') as cur:
                    cur.itersize = tamanho
                    cur.execute(sql.SQL('SELECT {} FROM {}').format(
                        sql.SQL(', ').join(map(sql.Identifier, info['colunas'])),
                        sql.Identifier('raw', info['tabela_raw'])))
                    obtido = resumir(cur)
                if obtido != esperado[info['tabela_raw']]:
                    raise ValueError(f"Conteúdo divergente em {info['tabela_raw']}; carga desfeita")
    except Exception:
        logger.exception('Carga Raw desfeita; transação não confirmada.')
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip', type=Path, default=ZIP_DADOS)
    parser.add_argument('--validar-apenas', action='store_true', help='Valida todos os CSVs sem acessar o banco')
    parser.add_argument('--repetir', action='store_true', help='Executa duas cargas e confere conteúdo após cada uma')
    parser.add_argument('--relatorio', type=Path, default=PASTA_RAIZ / 'data/relatorio_raw.json')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    try:
        if TAMANHO_BLOCO <= 0:
            raise ValueError('TAMANHO_BLOCO deve ser positivo')
        obter_zip(args.zip)
        esperado = validar_fonte(args.zip, TAMANHO_BLOCO)
        with args.zip.open('rb') as arquivo:
            zip_hash = hashlib.file_digest(arquivo, 'sha256').hexdigest()
        execucoes = 0
        if not args.validar_apenas:
            conn = conectar()
            try:
                for _ in range(2 if args.repetir else 1):
                    carregar_raw(conn, args.zip, TAMANHO_BLOCO, esperado)
                    execucoes += 1
            finally:
                conn.close()
        relatorio = {'zip': args.zip.name, 'sha256_zip': zip_hash,
                     'cargas_verificadas': execucoes, 'tabelas': esperado}
        args.relatorio.parent.mkdir(parents=True, exist_ok=True)
        args.relatorio.write_text(json.dumps(relatorio, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        logger.info('Concluído. Relatório: %s', args.relatorio)
        return 0
    except Exception:
        logger.exception('Falha na Fase 1')
        return 1


if __name__ == '__main__':
    sys.exit(main())
