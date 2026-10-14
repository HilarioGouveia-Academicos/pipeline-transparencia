"""Gráficos com títulos, unidades, legendas e valores completos no tooltip."""
import altair as alt
from dashboard import br


def grafico_orgaos(dados, campo, titulo):
    dados = dados.head(10).copy()
    dados['rotulo'] = dados['orgao'].map(lambda s: s if len(s) <= 65 else s[:48] + '… ' + s[s.rfind('['):])
    dados['rotulo'] = [f'{i}. {rotulo}' for i, rotulo in enumerate(dados['rotulo'], 1)]
    dados['valor'] = dados[campo].map(float)
    dados['valor_formatado'] = dados[campo].map(lambda x: 'R$ ' + br(x))
    dados['indicador'] = 'Valor líquido' if campo == 'valor_total_liquido' else 'Média por viagem'
    chart = alt.Chart(dados[['rotulo', 'orgao', 'valor', 'valor_formatado', 'viagens', 'indicador']]).mark_bar().encode(
        x=alt.X('valor:Q', title='Reais (R$)', axis=alt.Axis(format='.3s', tickCount=5), scale=alt.Scale(zero=True)),
        y=alt.Y('rotulo:N', title='Órgão superior', sort='-x', axis=alt.Axis(labelLimit=310, labelOverlap=False, titleAngle=0, titleAlign='right', titleX=-12, titleY=-12)),
        color=alt.Color('indicador:N', title='Indicador', scale=alt.Scale(range=['#156b87']), legend=alt.Legend(orient='top')),
        tooltip=[alt.Tooltip('orgao:N', title='Órgão'), alt.Tooltip('valor_formatado:N', title='Valor'), alt.Tooltip('viagens:Q', title='Viagens', format=',')],
    ).properties(title=titulo, height=max(170, len(dados) * 34))
    return chart


def grafico_meses(dados, campo, titulo):
    dados = dados.copy()
    monetario = campo == 'valor_total_liquido'
    dados['valor'] = dados[campo].map(float)
    dados['valor_formatado'] = dados[campo].map(lambda x: ('R$ ' if monetario else '') + br(x, 2 if monetario else 0))
    dados['mes'] = dados['mes_inicio'].dt.strftime('%m/%Y')
    dados['indicador'] = 'Valor líquido' if monetario else 'Viagens'
    return alt.Chart(dados[['mes', 'mes_inicio', 'valor', 'valor_formatado', 'indicador']]).mark_bar().encode(
        x=alt.X('mes:N', title='Mês de início da viagem', sort=dados['mes'].tolist(), axis=alt.Axis(labelAngle=0)),
        y=alt.Y('valor:Q', title='Reais (R$)' if monetario else 'Quantidade de viagens', axis=alt.Axis(format=',.0f'), scale=alt.Scale(zero=True)),
        color=alt.Color('indicador:N', title='Indicador', scale=alt.Scale(range=['#156b87' if monetario else '#b05a23']), legend=alt.Legend(orient='top')),
        tooltip=[alt.Tooltip('mes:N', title='Mês'), alt.Tooltip('valor_formatado:N', title='Total')],
    ).properties(title=titulo, height=280)


def grafico_ranking(dados, categoria, campo, titulo, monetario=False):
    dados = dados.copy()
    dados['categoria'] = dados[categoria].fillna('Não informado').map(str)
    dados['rotulo'] = [f'{i}. {v}' for i,v in enumerate(dados['categoria'],1)]
    dados['valor'] = dados[campo].map(float)
    dados['formatado'] = dados[campo].map(lambda v: ('R$ ' if monetario else '') + br(v, 2 if monetario else 0))
    return alt.Chart(dados[['categoria','rotulo','valor','formatado']]).mark_bar().encode(
        x=alt.X('valor:Q', title='Reais (R$)' if monetario else ('Dias' if campo=='duracao_dias' else 'Quantidade'), scale=alt.Scale(zero=True)),
        y=alt.Y('rotulo:N', title=categoria.replace('_',' ').capitalize(), sort=None, axis=alt.Axis(labelLimit=280)),
        tooltip=[alt.Tooltip('categoria:N',title='Categoria'),alt.Tooltip('formatado:N',title='Resultado')],
    ).properties(title=titulo,height=max(160,len(dados)*35))
