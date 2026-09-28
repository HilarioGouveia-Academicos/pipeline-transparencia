"""Leitura e cálculos do painel. Decimal até a apresentação dos gráficos."""
from datetime import datetime, timezone
from decimal import Decimal
import pandas as pd
from banco import conectar

COLUNAS = ['mes_inicio', 'orgao_chave', 'codigo_orgao_solicitante',
           'nome_orgao_solicitante', 'viagens', 'valor_total_liquido',
           'trechos', 'trechos_rejeitados']


def carregar_gold():
    conn = conectar()
    try:
        with conn, conn.cursor() as cur:
            cur.execute('SELECT ' + ', '.join(COLUNAS) + ' FROM gold.resumo_orgao_mes ORDER BY mes_inicio, orgao_chave')
            dados = pd.DataFrame(cur.fetchall(), columns=COLUNAS)
        return dados, datetime.now(timezone.utc)
    finally:
        conn.close()


def rotulo_orgao(codigo, nome):
    nome = "Órgão sem nome informado" if pd.isna(nome) or nome == "" else nome
    codigo = "sem código" if pd.isna(codigo) or codigo == "" else codigo
    return f"{nome} [{codigo}]"


def preparar(dados):
    dados = dados.copy()
    dados['mes_inicio'] = pd.to_datetime(dados['mes_inicio'])
    dados['orgao'] = [rotulo_orgao(c, n) for c, n in zip(dados['codigo_orgao_solicitante'], dados['nome_orgao_solicitante'])]
    return dados


def filtrar(dados, inicio, fim, orgaos):
    mascara = dados['mes_inicio'].between(pd.Timestamp(inicio), pd.Timestamp(fim))
    if orgaos:
        mascara &= dados['orgao_chave'].isin(orgaos)
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
    if 'mes_inicio' in tabela:
        tabela['mes_inicio'] = tabela['mes_inicio'].dt.strftime('%m/%Y')
    for coluna in ('valor_total_liquido', 'media_por_viagem'):
        if coluna in tabela:
            tabela[coluna] = tabela[coluna].map(lambda v: 'R$ ' + br(v))
    return tabela.rename(columns={'orgao': 'Órgão solicitante', 'mes_inicio': 'Mês de início',
                                 'viagens': 'Viagens', 'valor_total_liquido': 'Valor líquido',
                                 'media_por_viagem': 'Média por viagem'})
