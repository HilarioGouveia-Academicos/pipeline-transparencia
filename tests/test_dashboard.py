from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
import json
import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import dashboard
from gold_dashboard import CONSULTAS
from graficos import grafico_ranking
APP=Path(__file__).resolve().parents[1]/'app/app.py'


@pytest.fixture
def pacote():
    comuns = ['mes_inicio','orgao_chave','codigo_orgao_superior','nome_orgao_superior','situacao','grupo_chave']
    a=[date(2025,1,1),'a','1','Órgão A','Realizada','a-realizada']
    b=[date(2025,2,1),'b','2','Órgão B','Cancelada','b-cancelada']
    frames={
      'resumo_viagem_mes': pd.DataFrame([a+[100,120,40,180,Decimal('1000'),Decimal('1200'),100],
                                       b+[2,3,1,4,Decimal('500'),Decimal('600'),4]],columns=comuns+['viagens','pagamentos','passagens','trechos','valor_total_liquido','valor_pagamentos','duracao_total_dias']),
      'resumo_destino_mes':pd.DataFrame([a+['Destino A',100,Decimal('1000')],b+['Destino B',2,Decimal('500')]],columns=comuns+['destino','viagens','valor_total_liquido']),
      'gold_pagamento_resumo':pd.DataFrame([a+['Pagador A','DIÁRIAS',120,Decimal('1200')],b+['Pagador B','PASSAGEM',3,Decimal('600')]],columns=comuns+['nome_orgao_pagador','tipo_pagamento','pagamentos','total_pago']),
      'gold_trecho_resumo':pd.DataFrame([a+['Inválido','São Paulo',180],b+['Aéreo','Distrito Federal',4]],columns=comuns+['meio_transporte','destino_uf','trechos']),
      'viagens_duracao':pd.DataFrame([a+['001',date(2025,1,1),date(2025,1,1),1,Decimal('1000'),1],b+['002',date(2025,2,1),date(2025,2,4),4,Decimal('500'),1]],columns=comuns+['id_viagem','data_inicio','data_fim','duracao_dias','valor_total_liquido','posicao'])
    }
    return {k:dashboard.preparar(v) for k,v in frames.items()}, {'carregado_em':datetime.now(timezone.utc),'consultado_em':datetime.now(timezone.utc),'fonte':{},'conferencia':{}}


@pytest.fixture(autouse=True)
def limpar(monkeypatch):
    st.cache_data.clear()
    yield
    st.cache_data.clear()


def test_painel_situacao_padrao_todas_orgao_periodo_e_vazio(pacote,monkeypatch):
    monkeypatch.setattr(dashboard,'carregar_gold',lambda:pacote)
    at=AppTest.from_file(str(APP),default_timeout=30).run()
    assert not at.exception and not at.error
    assert [m.value for m in at.metric][:4]==['100','120','40','180']
    assert at.metric[5].value=='R$ 10,00'
    assert len(at.get('vega_lite_chart'))==10
    assert not any(b.label=='Carregar dados' for b in at.button)
    at.multiselect(key='situacoes').set_value([]).run()
    assert not at.exception and at.metric[0].value=='102'
    at.multiselect(key='orgaos').set_value(['b']).run()
    assert at.metric[0].value=='2' and any('elegíveis' in i.value for i in at.info)
    at.select_slider(key='periodo').set_value((pd.Timestamp('2025-01-01'),pd.Timestamp('2025-01-01'))).run()
    assert not at.exception and not at.metric
    assert any('Nenhuma viagem' in i.value for i in at.info)


def test_medias_ponderadas_minimo_e_categoria_invalido(pacote):
    frames,_=pacote
    q=dashboard.analisar(frames)
    assert q[1].iloc[0].destino=='Destino A'
    assert q[3].iloc[0].tipo_pagamento=='PASSAGEM' and q[3].iloc[0].valor_medio==Decimal('200')
    assert q[4].iloc[0].meio_transporte=='Inválido'
    assert q[2].iloc[0].id_viagem=='002'
    chart=grafico_ranking(q[3],'tipo_pagamento','valor_medio','Média',True).to_dict()
    assert chart['encoding']['x']['title']=='Reais (R$)' and chart['encoding']['tooltip']


def test_painel_vazio_e_erro_sem_detalhes(pacote,monkeypatch):
    frames,meta=pacote
    monkeypatch.setattr(dashboard,'carregar_gold',lambda:({k:v.iloc[:0] for k,v in frames.items()},meta))
    at=AppTest.from_file(str(APP),default_timeout=30).run()
    assert not at.exception and any('carga Gold' in i.value for i in at.info)
    st.cache_data.clear()
    def falhar():raise RuntimeError('senha e detalhe interno')
    monkeypatch.setattr(dashboard,'carregar_gold',falhar)
    at=AppTest.from_file(str(APP),default_timeout=30).run()
    assert at.error and 'senha' not in at.error[0].value


@pytest.mark.parametrize('banco_ausente',[False,True])
def test_estrutura_ausente_nao_cria_banco(monkeypatch,banco_ausente):
    from psycopg2.errors import InvalidCatalogName,UndefinedTable
    def fonte():
        if banco_ausente:
            raise RuntimeError('ausente') from InvalidCatalogName('ausente')
        raise UndefinedTable('ausente')
    monkeypatch.setattr(dashboard,'carregar_gold',fonte)
    at=AppTest.from_file(str(APP),default_timeout=30).run()
    assert not at.exception and at.warning
    assert not any(b.label.startswith('Criar') or b.label=='Carregar dados' for b in at.button)


def test_identidade_situacao_nula_nao_colide_com_rotulo(pacote):
    frames,_=pacote
    dados=frames['resumo_viagem_mes'].copy()
    dados['situacao']=[None,'Situação não informada']
    dados=dashboard.preparar(dados)
    assert dados.situacao_chave.nunique()==2
