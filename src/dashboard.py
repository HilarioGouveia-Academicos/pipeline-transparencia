"""Leitura e cálculos do painel. Decimal até a apresentação dos gráficos."""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import pandas as pd
import json
from banco import conectar
from gold_dashboard import CONSULTAS

COLUNAS = ['mes_inicio', 'orgao_chave', 'codigo_orgao_solicitante',
           'nome_orgao_solicitante', 'viagens', 'valor_total_liquido',
           'trechos', 'trechos_rejeitados']


def carregar_gold():
    conn = conectar(leitura=True)
    try:
        conn.set_session(readonly=True, isolation_level='REPEATABLE READ')
        with conn, conn.cursor() as cur:
            # Somente tabelas Gold: as views de validação leem Silver e não são usadas aqui.
            from psycopg2 import sql
            dados = {}
            for tabela in CONSULTAS:
                cur.execute(sql.SQL('SELECT * FROM {}').format(sql.Identifier('gold', tabela)))
                dados[tabela] = preparar(pd.DataFrame(cur.fetchall(), columns=[c.name for c in cur.description]))
            cur.execute('SELECT carregado_em,fonte,conferencia FROM gold.carga_dashboard WHERE id=1 AND versao=1')
            carga = cur.fetchone()
        return dados, {'consultado_em': datetime.now(timezone.utc),
                       'carregado_em': carga[0] if carga else None,
                       'fonte': carga[1] if carga else {}, 'conferencia': carga[2] if carga else {}}
    finally:
        conn.close()


def rotulo_orgao(codigo, nome):
    nome = "Órgão sem nome informado" if pd.isna(nome) or nome == "" else nome
    codigo = "sem código" if pd.isna(codigo) or codigo == "" else codigo
    return f"{nome} [{codigo}]"


def preparar(dados):
    dados = dados.copy()
    dados['mes_inicio'] = pd.to_datetime(dados['mes_inicio'])
    codigo = 'codigo_orgao_superior' if 'codigo_orgao_superior' in dados else 'codigo_orgao_solicitante'
    nome = 'nome_orgao_superior' if 'nome_orgao_superior' in dados else 'nome_orgao_solicitante'
    dados['orgao'] = [rotulo_orgao(c, n) for c, n in zip(dados[codigo], dados[nome])]
    if 'situacao' in dados:
        dados['situacao_chave'] = dados['situacao'].map(lambda v: json.dumps([None if pd.isna(v) else v], ensure_ascii=False))
    return dados


def filtrar(dados, inicio, fim, orgaos, situacoes=None):
    mascara = dados['mes_inicio'].between(pd.Timestamp(inicio), pd.Timestamp(fim))
    if orgaos:
        mascara &= dados['orgao_chave'].isin(orgaos)
    if situacoes:
        mascara &= dados['situacao_chave'].isin(situacoes)
    return dados.loc[mascara].copy()


def agregar(dados, chaves):
    resultado = dados.groupby(chaves, as_index=False, dropna=False).agg(
        viagens=('viagens', 'sum'), valor_total_liquido=('valor_total_liquido', 'sum'))
    resultado['media_por_viagem'] = [v / Decimal(int(n)) for v, n in zip(resultado['valor_total_liquido'], resultado['viagens'])]
    return resultado


def br(valor, casas=2):
    return f'{valor:,.{casas}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def tabela_exibicao(dados):
    tabela = dados.copy()
    for coluna in ('destino', 'destino_uf', 'meio_transporte', 'tipo_pagamento', 'nome_orgao_pagador'):
        if coluna in tabela:
            tabela[coluna] = tabela[coluna].fillna('Não informado')
    if 'mes_inicio' in tabela:
        tabela['mes_inicio'] = tabela['mes_inicio'].dt.strftime('%m/%Y')
    for coluna in ('valor_total_liquido', 'media_por_viagem', 'valor_pagamentos', 'custo_medio', 'valor_medio', 'total_pago'):
        if coluna in tabela:
            tabela[coluna] = tabela[coluna].map(lambda v: 'R$ ' + br(v))
    return tabela.rename(columns={'orgao': 'Órgão superior', 'mes_inicio': 'Mês de início',
                                 'viagens': 'Viagens', 'valor_total_liquido': 'Valor líquido',
                                 'media_por_viagem': 'Média por viagem'})


def ranking(dados, chaves, medidas, ordenar, limite=None, minimo=0, denominador=None, media=None):
    """Reagrupar totais após filtros; conservar grupos nulos e desempates estáveis."""
    resultado = dados.groupby(chaves, as_index=False, dropna=False)[medidas].sum()
    if denominador:
        resultado = resultado[resultado[denominador] >= max(1, minimo)].copy()
    if media:
        numerador, divisor, destino = media
        resultado[destino] = [(v / Decimal(int(n))).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
                              for v, n in zip(resultado[numerador], resultado[divisor])]
    resultado = resultado.sort_values([ordenar] + chaves, ascending=[False] + [True]*len(chaves), na_position='last')
    return resultado.head(limite) if limite else resultado


def analisar(conjuntos):
    geral = conjuntos['resumo_viagem_mes']
    financeiro = ranking(geral, ['orgao_chave','orgao'], ['viagens','valor_total_liquido'], 'valor_total_liquido', 5)
    destinos = ranking(conjuntos['resumo_destino_mes'], ['destino'], ['viagens','valor_total_liquido'],
                       'custo_medio', 3, 100, 'viagens', ('valor_total_liquido','viagens','custo_medio'))
    duracao = conjuntos['viagens_duracao'].sort_values(['duracao_dias','valor_total_liquido','id_viagem'],
                                                     ascending=[False,False,True]).head(5)
    pagamentos = ranking(conjuntos['gold_pagamento_resumo'], ['tipo_pagamento'], ['pagamentos','total_pago'],
                         'valor_medio', denominador='pagamentos', media=('total_pago','pagamentos','valor_medio'))
    transportes = ranking(conjuntos['gold_trecho_resumo'], ['meio_transporte'], ['trechos'], 'trechos')
    total = int(transportes['trechos'].sum())
    transportes['participacao'] = [Decimal(int(n))*100/Decimal(total) if total else Decimal(0) for n in transportes['trechos']]
    ufs = ranking(conjuntos['gold_trecho_resumo'], ['destino_uf'], ['trechos'], 'trechos', 10)
    pagadores = ranking(conjuntos['gold_pagamento_resumo'], ['nome_orgao_pagador'], ['pagamentos','total_pago'], 'total_pago', 5)
    return [financeiro, destinos, duracao, pagamentos, transportes, ufs, pagadores]
