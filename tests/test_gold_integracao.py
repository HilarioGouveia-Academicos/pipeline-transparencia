"""Integração Gold: cardinalidade dos JOINs, grupos, reconciliação e rollback."""
import os
from datetime import date
from decimal import Decimal

import pytest

from test_raw_integracao import banco_isolado
from test_silver_integracao import preparar, snapshot
from test_transformacao import registro
import silver
import gold

pytestmark = pytest.mark.skipif(os.getenv('RUN_GOLD_DB_TESTS') != '1', reason='Requer RUN_GOLD_DB_TESTS=1 e PostgreSQL')


def alterar(linha, **campos):
    for campo, valor in campos.items():
        origem = next(f['origem'] for f in silver.LAYOUT['viagem']['campos'] if f['nome'] == campo)
        linha[origem] = valor
    return linha


def carregar(conn):
    viagens = [registro('viagem', str(i)) for i in range(1, 5)]
    alterar(viagens[1], codigo_orgao_solicitante='outro')
    alterar(viagens[2], data_inicio='01/02/2025', data_fim='03/02/2025')
    alterar(viagens[3], codigo_orgao_solicitante='', nome_orgao_solicitante='')
    trechos = [registro('trecho', '1') for _ in range(4)]
    for i, t in enumerate(trechos):
        t['Sequência Trecho'] = str(i + 1)
    trechos[-1]['Meio de transporte'] = 'Inválido'
    preparar(conn, {'viagem': viagens,
                   'pagamento': [registro('pagamento', '1')] * 2,
                   'passagem': [registro('passagem', '1')] * 3,
                   'trecho': trechos})
    silver.executar_silver(conn, 2)


def test_joins_nao_multiplicam_e_preservam_viagens_sem_detalhes(banco_isolado):
    conn = banco_isolado
    carregar(conn)
    fonte = snapshot(conn, 'silver', ['silver_' + t for t in silver.LAYOUT] + ['rejeitados'])
    resultado = gold.executar_gold(conn)
    assert resultado['grupos'] == 4  # nome igual/código diferente, mês diferente e órgão ausente
    assert resultado['totais']['viagens'] == 4
    assert resultado['totais']['valor_total_liquido'] == Decimal('98.72')
    assert resultado['totais']['valor_pagamentos'] == Decimal('24.68')
    assert resultado['totais']['valor_passagens_detalhe'] == Decimal('37.02')
    assert resultado['totais']['trechos'] == 3
    assert resultado['totais']['trechos_rejeitados'] == 1
    assert resultado['maior_duracao_dias'] == 2
    with conn.cursor() as cur:
        cur.execute("SELECT viagens,pagamentos,passagens,trechos,valor_total_liquido FROM gold.resumo_orgao_mes WHERE mes_inicio='2025-01-01' AND codigo_orgao_solicitante='texto'")
        assert cur.fetchone() == (1, 2, 3, 3, Decimal('24.68'))
        cur.execute('SELECT mes_inicio,pagamentos FROM gold.resumo_orgao_mes WHERE codigo_orgao_solicitante IS NULL')
        assert cur.fetchone() == (date(2025, 1, 1), 0)
    conn.commit()
    salvo = snapshot(conn, 'gold', ['resumo_orgao_mes'])
    assert gold.executar_gold(conn, esperado=resultado) == resultado
    assert snapshot(conn, 'gold', ['resumo_orgao_mes']) == salvo
    assert snapshot(conn, 'silver', ['silver_' + t for t in silver.LAYOUT] + ['rejeitados']) == fonte
    with pytest.raises(ValueError, match='Reexecução Gold divergente'):
        gold.executar_gold(conn, esperado={})
    assert snapshot(conn, 'gold', ['resumo_orgao_mes']) == salvo


def test_falha_tardia_e_totais_incorretos(banco_isolado, monkeypatch):
    conn = banco_isolado
    carregar(conn)
    gold.executar_gold(conn)
    salvo = snapshot(conn, 'gold', ['resumo_orgao_mes'])
    original = gold.verificar

    def falhar(conexao):
        with conexao.cursor() as cur:
            cur.execute('UPDATE gold.resumo_orgao_mes SET valor_pagamentos=valor_pagamentos+1')
        return original(conexao)

    monkeypatch.setattr(gold, 'verificar', falhar)
    with pytest.raises(ValueError, match='Total Gold divergente: valor_pagamentos'):
        gold.executar_gold(conn)
    assert snapshot(conn, 'gold', ['resumo_orgao_mes']) == salvo


def test_silver_vazia_nao_produz_sucesso(banco_isolado):
    with banco_isolado.cursor() as cur:
        cur.execute((gold.SQL / '2_criar_silver.sql').read_text(encoding='utf-8-sig'))
    banco_isolado.commit()
    with pytest.raises(ValueError, match='Silver sem viagens'):
        gold.executar_gold(banco_isolado)
