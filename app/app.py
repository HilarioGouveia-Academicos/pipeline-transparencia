"""Dashboard com leitura exclusiva de tabelas Gold."""
from pathlib import Path
import logging
import sys
from decimal import Decimal
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from psycopg2 import OperationalError
from psycopg2.errors import InvalidCatalogName, UndefinedTable, InvalidSchemaName
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import dashboard as dados_painel
from dashboard import agregar, analisar, br, filtrar, tabela_exibicao
from graficos import grafico_meses, grafico_orgaos, grafico_ranking
from config import POSTGRES_CONFIG

st.set_page_config(page_title='Viagens a serviço | Transparência', page_icon=':material/travel_explore:', layout='wide')
st.title('Viagens a serviço')
st.caption('Portal da Transparência · Indicadores e sete perguntas de negócio')

@st.cache_data(ttl=300, max_entries=1, show_spinner='Consultando a Gold…')
def carregar():
    return dados_painel.carregar_gold()

with st.sidebar:
    st.header('Dados do painel')
    if st.button('Atualizar dados', icon=':material/refresh:', key='atualizar'):
        carregar.clear()
try:
    conjuntos, metadados = carregar()
except Exception as erro:
    causa = erro.__cause__ or erro.__context__ or erro
    banco_ausente = isinstance(causa,InvalidCatalogName) or (
        isinstance(causa,OperationalError) and f'database "{POSTGRES_CONFIG["dbname"]}" does not exist' in str(causa))
    if banco_ausente or isinstance(erro,(UndefinedTable,InvalidSchemaName)):
        st.warning('A estrutura Gold do painel ainda não está disponível.')
        st.info('Execute a carga pelo terminal e depois atualize os dados do painel.')
    else:
        logging.exception('Não foi possível consultar a Gold')
        st.error('Não foi possível consultar os dados. Verifique a conexão e as permissões de leitura da Gold.')
    st.stop()

fonte = conjuntos['resumo_viagem_mes']
if fonte.empty or metadados['carregado_em'] is None:
    st.info('Não há uma carga Gold validada. O responsável deve executar a carga antes de consultar o painel.')
    st.stop()
meses = sorted(fonte['mes_inicio'].unique())
opcoes = fonte[['orgao_chave','orgao']].drop_duplicates().sort_values('orgao')
nomes = dict(zip(opcoes['orgao_chave'],opcoes['orgao']))
situacoes = dict(zip(fonte['situacao_chave'],fonte['situacao'].fillna('Situação não informada')))
padrao = [chave for chave,nome in situacoes.items() if nome=='Realizada']
with st.sidebar:
    st.header('Filtros')
    if len(meses)>1:
        inicio,fim = st.select_slider('Período de início da viagem',options=meses,value=(meses[0],meses[-1]),format_func=lambda d: pd.Timestamp(d).strftime('%m/%Y'),key='periodo')
    else:
        inicio=fim=meses[0]
        st.caption('Período: '+pd.Timestamp(inicio).strftime('%m/%Y'))
    orgaos = st.multiselect('Órgãos superiores',options=list(nomes),format_func=nomes.get,key='orgaos')
    selecionadas = st.multiselect('Situação da viagem',options=sorted(situacoes),default=padrao,format_func=situacoes.get,key='situacoes')
    st.caption('Sem seleção de órgãos ou situações: inclui todos. Os filtros afetam todos os indicadores e análises.')
escopo = ', '.join(situacoes[s] for s in selecionadas) if selecionadas else 'Todas as situações'
rotulo_orgaos = 'Todos os órgãos' if not orgaos else ', '.join(nomes[o] for o in orgaos)
st.caption(f'{pd.Timestamp(inicio):%m/%Y} a {pd.Timestamp(fim):%m/%Y} · {rotulo_orgaos} · {escopo}')
carregado = metadados['carregado_em'].astimezone(ZoneInfo('America/Sao_Paulo'))
st.caption(f'Gold carregada em {carregado:%d/%m/%Y às %H:%M}. Cache de leitura de até 5 minutos.')
recortes = {nome: filtrar(dados,inicio,fim,orgaos,selecionadas) for nome,dados in conjuntos.items()}
geral = recortes['resumo_viagem_mes']
if geral.empty:
    st.info('Nenhuma viagem encontrada para os filtros selecionados.')
    st.stop()
st.subheader('Volume do recorte')
with st.container(horizontal=True):
    for coluna,rotulo in [('viagens','Viagens'),('pagamentos','Pagamentos'),('passagens','Passagens'),('trechos','Trechos')]:
        st.metric(rotulo,br(int(geral[coluna].sum()),0),border=True)
valor = sum(geral['valor_total_liquido'],Decimal(0))
viagens = int(geral['viagens'].sum())
with st.container(horizontal=True):
    st.metric('Valor líquido','R$ '+br(valor),border=True)
    st.metric('Média por viagem','R$ '+br(valor/Decimal(viagens)),border=True)
    st.metric('Total pago','R$ '+br(sum(geral['valor_pagamentos'],Decimal(0))),border=True)
st.caption('Valor líquido = diárias + passagens + outros gastos − devoluções. Total pago é uma medida distinta. Trechos incluem a categoria Inválido.')

def mostrar(tabela,categoria,campo,titulo,monetario=False):
    if tabela.empty:
        st.info('Não há dados elegíveis para esta análise no recorte.')
        return
    st.altair_chart(grafico_ranking(tabela,categoria,campo,titulo,monetario),width='stretch',theme=None)
    st.dataframe(tabela_exibicao(tabela),hide_index=True)

visao,perguntas = st.tabs(['Visão geral','Sete perguntas de negócio'])
with visao:
    por_mes = agregar(geral,['mes_inicio']).sort_values('mes_inicio')
    st.subheader('Evolução por mês de início')
    st.altair_chart(grafico_meses(por_mes,'valor_total_liquido','Valor líquido por mês'),width='stretch',theme=None)
    st.altair_chart(grafico_meses(por_mes,'viagens','Viagens por mês'),width='stretch',theme=None)
    st.caption('Os valores são atribuídos ao início da viagem; não representam fluxo de caixa mensal.')
    st.dataframe(tabela_exibicao(por_mes),hide_index=True)
    st.subheader('Órgãos superiores com maior média por viagem')
    minimo = st.number_input('Mínimo de viagens para este ranking',min_value=1,value=1,step=1,key='minimo')
    medias = agregar(geral,['orgao_chave','orgao'])
    medias = medias[medias['viagens']>=minimo].sort_values(['media_por_viagem','orgao_chave'],ascending=[False,True]).head(10)
    if medias.empty:
        st.info('Nenhum órgão atinge o mínimo de viagens informado.')
    else:
        st.altair_chart(grafico_orgaos(medias,'media_por_viagem','Até dez órgãos com maior média'),width='stretch',theme=None)
        st.dataframe(tabela_exibicao(medias[['orgao','viagens','valor_total_liquido','media_por_viagem']]),hide_index=True)

with perguntas:
    resultados = analisar(recortes)
    configuracoes = [
        ('Quais são os cinco órgãos com maior custo total?','orgao','valor_total_liquido',True),
        ('Quais são os três destinos com maior custo médio?','destino','custo_medio',True),
        ('Qual é a viagem de maior duração e seu custo?','id_viagem','duracao_dias',False),
        ('Qual tipo de pagamento tem maior valor médio?','tipo_pagamento','valor_medio',True),
        ('Qual meio de transporte é mais usado?','meio_transporte','trechos',False),
        ('Qual UF de destino é mais frequente?','destino_uf','trechos',False),
        ('Qual órgão pagou mais no total?','nome_orgao_pagador','total_pago',True),
    ]
    for i,(q,(pergunta,categoria,campo,monetario)) in enumerate(zip(resultados,configuracoes),1):
        st.subheader(f'{i}. {pergunta}')
        if i==2:
            st.caption('Destino é o texto completo da fonte. Mínimo de 100 viagens por destino no recorte.')
        if i==3:
            st.caption('A duração inclui os dias de início e fim.')
            exibicao = q[['id_viagem','orgao','data_inicio','data_fim','duracao_dias','valor_total_liquido']]
        elif i==1:
            exibicao = q[['orgao','viagens','valor_total_liquido']]
        else:
            exibicao = q
        mostrar(exibicao,categoria,campo,pergunta,monetario)
        if not q.empty:
            lider=q.iloc[0]
            nome = str(lider[categoria]) if pd.notna(lider[categoria]) else 'Não informado'
            if i==3:
                st.write(f'A viagem {nome} dura {int(lider.duracao_dias)} dias e custa R$ {br(lider.valor_total_liquido)}.')
            elif i==5:
                st.write(f'{nome} lidera com {br(int(lider.trechos),0)} trechos ({br(lider.participacao)}% do total).')
            else:
                st.write(f'{nome} lidera: '+('R$ '+br(lider[campo]) if monetario else br(int(lider[campo]),0)+' trechos')+'.')
        if i==7:
            st.caption('Órgão pagador pode diferir do órgão superior selecionado no filtro.')

with st.expander('Exportar resultados do recorte'):
    for i,tabela in enumerate(resultados,1):
        st.download_button(f'Exportar pergunta {i}',tabela.to_csv(index=False).encode('utf-8-sig'),file_name=f'pergunta_{i}.csv',mime='text/csv',key=f'exportar_{i}')
