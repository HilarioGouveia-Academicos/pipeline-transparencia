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
        x=alt.X('valor:Q', title='Reais (R$)', axis=alt.Axis(format=',.0f'), scale=alt.Scale(zero=True)),
        y=alt.Y('rotulo:N', title='Órgão solicitante', sort='-x', axis=alt.Axis(labelLimit=430)),
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
