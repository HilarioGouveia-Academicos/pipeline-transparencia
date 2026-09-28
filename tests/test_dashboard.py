import json
import os
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import dashboard
from graficos import grafico_meses, grafico_orgaos

APP = Path(__file__).resolve().parents[1] / 'app/app.py'


@pytest.fixture
def fonte():
    return pd.DataFrame([
        [date(2025,1,1), 'a', '1', 'Órgão A', 1, Decimal('100.00'), 2, 1],
        [date(2025,2,1), 'a', '1', 'Órgão A', 9, Decimal('90.00'), 10, 0],
        [date(2025,1,1), 'b', None, None, 2, Decimal('-10.00'), 0, 0],
    ], columns=dashboard.COLUNAS)


@pytest.fixture(autouse=True)
def limpar_cache():
    st.cache_data.clear()
    yield
    st.cache_data.clear()


def test_media_ponderada_filtros_e_valores_negativos(fonte):
    dados = dashboard.preparar(fonte)
    agregado = dashboard.agregar(dados, ['orgao_chave', 'orgao']).set_index('orgao_chave')
    assert agregado.loc['a', 'media_por_viagem'] == Decimal('19.00')
    assert agregado.loc['b', 'valor_total_liquido'] == Decimal('-10.00')
    assert 'sem nome' in agregado.loc['b', 'orgao']
    filtrado = dashboard.filtrar(dados, date(2025,2,1), date(2025,2,1), ['a'])
    assert len(filtrado) == 1 and filtrado.iloc[0].viagens == 9
    assert dashboard.filtrar(dados, date(2025,2,1), date(2025,2,1), ['b']).empty
    assert dashboard.br(Decimal('1188144731.13')) == '1.188.144.731,13'


def test_graficos_identificam_medidas_e_preservam_valores(fonte):
    dados = dashboard.preparar(fonte)
    orgaos = dashboard.agregar(dados, ['orgao_chave', 'orgao'])
    meses = dashboard.agregar(dados, ['mes_inicio'])
    charts = [grafico_orgaos(orgaos, 'valor_total_liquido', 'Valor por órgão'),
              grafico_orgaos(orgaos, 'media_por_viagem', 'Média por órgão'),
              grafico_meses(meses, 'valor_total_liquido', 'Valor por mês'),
              grafico_meses(meses, 'viagens', 'Volume por mês')]
    for chart in charts:
        spec = chart.to_dict()
        assert spec['title']
        assert spec['encoding']['x']['title'] and spec['encoding']['y']['title']
        assert spec['encoding']['color']['legend']['orient'] == 'top'
        assert spec['encoding']['tooltip']
    assert charts[0].data['valor'].tolist() == [190.0, -10.0]
    assert charts[1].data['valor'].tolist() == [19.0, -5.0]


def test_painel_filtros_sem_resultados_e_minimo(fonte, monkeypatch):
    monkeypatch.setattr(dashboard, 'carregar_gold', lambda: (fonte, datetime.now(timezone.utc)))
    at = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not at.exception and not at.error
    assert [m.value for m in at.metric] == ['12', 'R$ 180,00', 'R$ 15,00']
    assert len(at.get('vega_lite_chart')) == 4
    assert at.warning and '1 trechos' in at.warning[0].value
    at.multiselect(key='orgaos').set_value(['a']).run()
    assert not at.exception and at.metric[2].value == 'R$ 19,00'
    at.select_slider(key='periodo').set_value((pd.Timestamp('2025-02-01'), pd.Timestamp('2025-02-01'))).run()
    assert not at.exception and at.metric[0].value == '9'
    at.number_input(key='minimo').set_value(10).run()
    assert any('mínimo' in i.value for i in at.info)
    assert len(at.get('vega_lite_chart')) == 3
    at.multiselect(key='orgaos').set_value(['b']).run()
    assert not at.exception and len(at.metric) == 0
    assert any('Nenhuma viagem' in i.value for i in at.info)


def test_painel_vazio_e_erro_controlado(fonte, monkeypatch):
    monkeypatch.setattr(dashboard, 'carregar_gold', lambda: (fonte.iloc[:0], datetime.now(timezone.utc)))
    at = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not at.exception and 'Não há dados' in at.info[0].value
    st.cache_data.clear()
    def falhar():
        raise RuntimeError('Detalhe interno de conexão')
    monkeypatch.setattr(dashboard, 'carregar_gold', falhar)
    at = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not at.exception and at.error
    assert 'Detalhe interno' not in at.error[0].value


@pytest.mark.skipif(os.getenv('RUN_DASHBOARD_DB_TESTS') != '1', reason='Requer Gold carregada e RUN_DASHBOARD_DB_TESTS=1')
def test_painel_com_gold_real():
    fonte, _ = dashboard.carregar_gold()
    at = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not at.exception and not at.error
    assert at.metric[0].value == dashboard.br(int(fonte['viagens'].sum()), 0)
    assert at.metric[1].value == 'R$ ' + dashboard.br(sum(fonte['valor_total_liquido'], Decimal(0)))
    assert len(at.get('vega_lite_chart')) == 4
