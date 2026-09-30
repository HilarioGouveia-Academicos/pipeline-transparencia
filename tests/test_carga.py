import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import carga


@pytest.mark.parametrize('falha', [False, True])
def test_etapas_e_interrupcao_na_falha(tmp_path, monkeypatch, falha):
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (True,)
    monkeypatch.setattr(carga, 'conectar', lambda: conn)
    monkeypatch.setattr(carga, 'criar_estrutura', MagicMock())
    monkeypatch.setattr(carga, 'PASTA_RAIZ', tmp_path)
    executar = MagicMock(return_value=MagicMock(returncode=1 if falha else 0))
    monkeypatch.setattr(carga.subprocess, 'run', executar)
    progresso = MagicMock()
    if falha:
        with pytest.raises(RuntimeError, match='Raw'):
            carga.carregar_pipeline('arquivo_zip', progresso)
        assert executar.call_count == 1
    else:
        carga.carregar_pipeline('arquivo_zip', progresso)
        assert [Path(c.args[0][1]).name for c in executar.call_args_list] == [s for _, s in carga.ETAPAS]
        assert progresso.call_args.args[0] == 1.0
    conn.close.assert_called_once()


def test_carga_concorrente_nao_executa_pipeline(monkeypatch):
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (False,)
    monkeypatch.setattr(carga, 'conectar', lambda: conn)
    criar = MagicMock()
    monkeypatch.setattr(carga, 'criar_estrutura', criar)
    with pytest.raises(RuntimeError, match='andamento'):
        carga.carregar_pipeline('arquivo_zip', MagicMock())
    criar.assert_not_called()
    conn.close.assert_called_once()
