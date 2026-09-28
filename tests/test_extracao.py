"""Testes da preservação e validação dos CSVs antes da carga Raw."""
import csv
import importlib.util
import io
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
spec = importlib.util.spec_from_file_location('extrair', Path(__file__).resolve().parents[1] / 'src/1_extrair.py')
etl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(etl)


def criar_zip(tmp_path, linhas=None, omitir=None):
    caminho = tmp_path / 'dados.zip'
    with zipfile.ZipFile(caminho, 'w') as z:
        for chave, info in etl.ARQUIVOS.items():
            if chave == omitir:
                continue
            stream = io.StringIO(newline='')
            writer = csv.writer(stream, delimiter=';', quoting=csv.QUOTE_ALL)
            writer.writerow(info['colunas'])
            if linhas is None:
                valores = ['', 'NA', 'NULL', '00123', '  espaços  ', '1.234,56', 'texto;com"aspas\ne quebra', '\\N']
                row = [valores[i % len(valores)] for i in range(len(info['colunas']))]
                writer.writerows([row, row, row])
            else:
                writer.writerows(linhas)
            z.writestr(info['csv'], stream.getvalue().encode('latin-1'))
    return caminho


def test_preserva_texto_e_duplicatas_da_fonte(tmp_path):
    caminho = criar_zip(tmp_path)
    etl.validar_zip(caminho)
    for info in etl.ARQUIVOS.values():
        blocos = list(etl.ler_blocos(caminho, info, 2))
        assert [len(b) for b in blocos] == [2, 1]
        assert blocos[0][0][:6] == ['', 'NA', 'NULL', '00123', '  espaços  ', '1.234,56']
        assert blocos[0][0][6] == 'texto;com"aspas\ne quebra'
        assert blocos[0][0][7] == '\\N'
        assert blocos[0][0] == blocos[1][0]


def test_csv_ausente_interrompe(tmp_path):
    with pytest.raises(ValueError, match='ausente'):
        etl.validar_zip(criar_zip(tmp_path, omitir='trecho'))


@pytest.mark.parametrize('quantidade', [1, 40])
def test_linha_incompleta_ou_excedente_nao_e_descartada(tmp_path, quantidade):
    caminho = criar_zip(tmp_path, linhas=[['x'] * quantidade])
    with pytest.raises(ValueError, match='quantidade de campos'):
        etl.validar_fonte(caminho, 2)


def test_nul_interrompe(tmp_path):
    info = etl.ARQUIVOS['viagem']
    caminho = criar_zip(tmp_path, linhas=[['\x00'] * len(info['colunas'])])
    with pytest.raises(ValueError, match='NUL'):
        list(etl.ler_blocos(caminho, info, 2))


def test_assinatura_preserva_multiplicidade_e_ignora_ordem():
    assert etl.resumir([['a'], ['b']]) == etl.resumir([['b'], ['a']])
    assert etl.resumir([['a']]) != etl.resumir([['a'], ['a']])
    assert etl.resumir([['']]) != etl.resumir([[None]])


def test_zip_local_nao_faz_download(tmp_path, monkeypatch):
    caminho = criar_zip(tmp_path)
    def falhar(*args, **kwargs):
        pytest.fail('Download indevido')
    monkeypatch.setattr(etl.urllib.request, 'urlopen', falhar)
    etl.obter_zip(caminho)


def test_download_html_nao_e_aceito_como_zip(tmp_path, monkeypatch):
    monkeypatch.setenv('DRIVE_FILE_ID', 'id_exemplo')
    monkeypatch.setattr(etl.urllib.request, 'urlopen', lambda *a, **k: io.BytesIO(b'<html>confirmar</html>'))
    caminho = tmp_path / 'download.zip'
    with pytest.raises(zipfile.BadZipFile):
        etl.obter_zip(caminho)
    assert not caminho.exists()
    assert not caminho.with_suffix('.zip.part').exists()
