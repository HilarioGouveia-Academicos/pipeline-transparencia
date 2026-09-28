from pathlib import Path
import logging
import sys
from decimal import Decimal
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import dashboard as dados_painel
from dashboard import agregar, br, filtrar, preparar, tabela_exibicao
from graficos import grafico_meses, grafico_orgaos

st.set_page_config(page_title='Viagens a serviço | Transparência', page_icon=':material/travel_explore:', layout='wide')
st.title('Viagens a serviço')
st.caption('Portal da Transparência · Valores e volume por órgão solicitante e mês de início')


@st.cache_data(ttl=300, max_entries=1, show_spinner='Consultando os dados de viagens…')
def carregar():
    return dados_painel.carregar_gold()


with st.sidebar:
    st.header('Consultar viagens')
    if st.button('Atualizar dados', icon=':material/refresh:', key='atualizar'):
        carregar.clear()

try:
    fonte, consultado_em = carregar()
except Exception:
    logging.exception('Não foi possível carregar o painel')
    st.error('Não foi possível consultar os dados. Verifique a conexão com o banco e a conclusão da etapa Gold.')
    st.stop()

if fonte.empty:
    st.info('Não há dados na Gold. Execute a etapa de análise antes de consultar o painel.')
    st.stop()

dados = preparar(fonte)
meses = sorted(dados['mes_inicio'].unique())
with st.sidebar:
    if len(meses) > 1:
        inicio, fim = st.select_slider('Meses de início', options=meses, value=(meses[0], meses[-1]),
                                       format_func=lambda d: pd.Timestamp(d).strftime('%m/%Y'), key='periodo')
    else:
        inicio = fim = meses[0]
        st.caption('Mês disponível: ' + pd.Timestamp(inicio).strftime('%m/%Y'))
    opcoes = dados[['orgao_chave', 'orgao']].drop_duplicates().sort_values('orgao')
    nomes = dict(zip(opcoes['orgao_chave'], opcoes['orgao']))
    orgaos = st.multiselect('Órgãos solicitantes', options=list(nomes), format_func=nomes.get, key='orgaos')
    st.caption('Sem seleção de órgãos: inclui todos. Os filtros afetam todos os resultados abaixo.')
    st.caption('Dados consultados em ' + consultado_em.astimezone(ZoneInfo('America/Sao_Paulo')).strftime('%d/%m/%Y às %H:%M') + '. Cache de até 5 minutos.')

recorte = filtrar(dados, inicio, fim, orgaos)
if recorte.empty:
    st.info('Nenhuma viagem encontrada para os filtros selecionados. Amplie o período ou a seleção de órgãos.')
    st.stop()

viagens = int(recorte['viagens'].sum())
valor = sum(recorte['valor_total_liquido'], Decimal(0))
media = valor / Decimal(viagens)
rejeitados = int(recorte['trechos_rejeitados'].sum())
trechos = int(recorte['trechos'].sum())
with st.container(horizontal=True):
    st.metric('Viagens', br(viagens, 0), border=True)
    st.metric('Valor líquido', 'R$ ' + br(valor), border=True)
    st.metric('Média por viagem', 'R$ ' + br(media), border=True)

st.caption('Valor líquido = diárias + passagens + outros gastos − devoluções, conforme os valores da viagem. Todos os valores estão em reais nominais.')
if rejeitados:
    percentual = Decimal(rejeitados) * 100 / Decimal(trechos + rejeitados)
    st.warning(f'{br(rejeitados, 0)} trechos auditados como rejeitados ({br(percentual)}% dos trechos vinculados às viagens deste recorte). As viagens continuam incluídas nos indicadores financeiros.')

por_orgao = agregar(recorte, ['orgao_chave', 'orgao']).sort_values(['valor_total_liquido', 'orgao_chave'], ascending=[False, True])
por_mes = agregar(recorte, ['mes_inicio']).sort_values('mes_inicio')

st.header('1. Quais órgãos concentram o maior valor líquido?')
lider = por_orgao.iloc[0]
participacao = f' ({br(lider.valor_total_liquido * 100 / valor)}% do total selecionado)' if valor > 0 else ''
st.markdown(f'**{lider.orgao}** lidera o recorte com **R$ {br(lider.valor_total_liquido)}**{participacao}, em **{br(int(lider.viagens), 0)} viagens**.')
st.altair_chart(grafico_orgaos(por_orgao, 'valor_total_liquido', 'Até 10 órgãos com maior valor líquido'), width='stretch', height=460, theme=None)
st.caption('A ordem considera o valor líquido. Nomes abreviados no eixo podem ser consultados por inteiro ao passar o cursor ou na tabela de resultados.')

st.header('2. Como variam o volume e o valor por mês de início?')
mes_valor = por_mes.loc[por_mes['valor_total_liquido'].idxmax()]
mes_volume = por_mes.loc[por_mes['viagens'].idxmax()]
st.markdown(f'**{mes_valor.mes_inicio:%m/%Y}** apresenta o maior valor líquido (**R$ {br(mes_valor.valor_total_liquido)}**). O maior volume ocorre em **{mes_volume.mes_inicio:%m/%Y}**, com **{br(int(mes_volume.viagens), 0)} viagens**. Em caso de empate, é exibido o primeiro mês.')
st.altair_chart(grafico_meses(por_mes, 'valor_total_liquido', 'Valor líquido por mês de início'), width='stretch', height=360, theme=None)
st.altair_chart(grafico_meses(por_mes, 'viagens', 'Viagens por mês de início'), width='stretch', height=360, theme=None)
st.caption('Os valores são atribuídos ao início da viagem. Esta série não representa pagamentos efetuados em cada mês. Meses sem viagens para a seleção não são exibidos.')
st.dataframe(tabela_exibicao(por_mes), hide_index=True)

st.header('3. Quais órgãos têm maior média por viagem?')
minimo = st.number_input('Mínimo de viagens para este ranking', min_value=1, value=1, step=1, key='minimo', help='Afeta apenas a pergunta 3. Ajuda a comparar órgãos com volumes suficientes para a análise.')
ranking = por_orgao[por_orgao['viagens'] >= minimo].sort_values(['media_por_viagem', 'orgao_chave'], ascending=[False, True])
if ranking.empty:
    st.info('Nenhum órgão atinge o mínimo de viagens informado.')
else:
    maior = ranking.iloc[0]
    st.markdown(f'**{maior.orgao}** tem a maior média elegível: **R$ {br(maior.media_por_viagem)} por viagem**, considerando **{br(int(maior.viagens), 0)} viagens**.')
    st.altair_chart(grafico_orgaos(ranking, 'media_por_viagem', 'Até 10 órgãos com maior média líquida por viagem'), width='stretch', height=460, theme=None)
    st.dataframe(tabela_exibicao(ranking[['orgao', 'viagens', 'valor_total_liquido', 'media_por_viagem']].head(10)), hide_index=True)
st.caption('Média = soma do valor líquido ÷ quantidade de viagens. Uma média maior não demonstra desperdício: duração, finalidade e destinos precisam ser considerados.')

with st.expander('Resultados completos e critérios de leitura'):
    st.dataframe(tabela_exibicao(por_orgao[['orgao', 'viagens', 'valor_total_liquido', 'media_por_viagem']]), hide_index=True)
    st.markdown('''- Inclui todas as situações de viagem aceitas na Silver, sem filtros adicionais de data ou situação além da seleção acima.
- Órgãos sem nome ou código são mantidos e identificados na tabela.
- Despesas da viagem, pagamentos e bilhetes têm definições próprias; seus valores não são somados entre si.
- O recorte original contém viagens iniciadas de janeiro a junho de 2025; elas podem terminar depois desse período.
- A comparação não controla diferenças de duração, finalidade ou destino e não estabelece causalidade.''')
