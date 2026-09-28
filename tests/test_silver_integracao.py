import os
from pathlib import Path
from decimal import Decimal
from datetime import date, time

import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values
import pytest

from test_raw_integracao import banco_isolado
from test_transformacao import registro
import silver
from config import ARQUIVOS

pytestmark = pytest.mark.skipif(os.getenv('RUN_SILVER_DB_TESTS') != '1', reason='Requer RUN_SILVER_DB_TESTS=1 e PostgreSQL')


def preparar(conn, dados):
    with conn.cursor() as cur:
        cur.execute((Path(__file__).resolve().parents[1]/'sql/1_criar_raw.sql').read_text(encoding='utf-8'))
        for tabela, linhas in dados.items():
            nomes=ARQUIVOS[tabela]['colunas']
            query=sql.SQL('INSERT INTO {} ({}) VALUES %s').format(sql.Identifier('raw','raw_'+tabela),sql.SQL(',').join(map(sql.Identifier,nomes)))
            execute_values(cur,query,[tuple(r[n] for n in nomes) for r in linhas])
    conn.commit()


def snapshot(conn, schema, tabelas):
    with conn.cursor() as cur:
        resultado={}
        for t in tabelas:
            cur.execute(sql.SQL('SELECT row_to_json(t)::text FROM {} t ORDER BY 1').format(sql.Identifier(schema,t)))
            resultado[t]=cur.fetchall()
    conn.commit()
    return resultado


def test_tipagem_relacoes_rejeicoes_reconciliacao_e_reexecucao(banco_isolado, monkeypatch):
    conn=banco_isolado
    v1=registro('viagem')
    v2=registro('viagem','002'); v2['Período - Data de início']='31/02/2025'
    p=registro('pagamento')
    pi=registro('pagamento'); pi['Valor']='NaN'
    passagem=registro('passagem'); passagem['País - Origem ida']='Estados Unidos'; passagem['UF - Origem ida']='California'
    trechos=[registro('trecho') for _ in range(3)]
    trechos[1]['Sequência Trecho']='2'; trechos[1]['Meio de transporte']='Inválido'
    trechos[2]['Sequência Trecho']='3'; trechos[2]['Destino - Data']='31/12/2024'
    preparar(conn,{'viagem':[v1,v2], 'pagamento':[p,p,registro('pagamento','002'),registro('pagamento','999'),pi],
                   'passagem':[passagem], 'trecho':trechos+[registro('trecho','002')]})
    fonte=snapshot(conn,'raw',['raw_'+t for t in silver.LAYOUT])
    resultado=silver.executar_silver(conn,2)
    assert (resultado['viagem']['aceitos'],resultado['viagem']['rejeitados'])==(1,1)
    assert (resultado['pagamento']['aceitos'],resultado['pagamento']['rejeitados'])==(2,3)
    assert (resultado['trecho']['aceitos'],resultado['trecho']['rejeitados'])==(1,3)
    assert resultado['pagamento']['numericos']['valor']['aceitos']==Decimal('24.68')
    assert resultado['pagamento']['numericos']['valor']['origem_convertivel']==Decimal('49.36')
    assert resultado['pagamento']['numericos']['valor']['invalidos']==1
    tabelas=['silver_'+t for t in silver.LAYOUT]+['rejeitados']
    salvo=snapshot(conn,'silver',tabelas)
    assert silver.executar_silver(conn,1,esperado=resultado)==resultado
    assert snapshot(conn,'silver',tabelas)==salvo
    with pytest.raises(ValueError,match='Reexecução divergente'):
        silver.executar_silver(conn,2,esperado={})
    assert snapshot(conn,'silver',tabelas)==salvo
    assert snapshot(conn,'raw',['raw_'+t for t in silver.LAYOUT])==fonte
    with conn.cursor() as cur:
        cur.execute('SELECT viagem_urgente,data_inicio,valor_diarias FROM silver.silver_viagem')
        b,d,v=cur.fetchone()
        assert b is True and isinstance(d,date) and isinstance(v,Decimal)
        cur.execute('SELECT origem_ida_uf,origem_ida_uf_nome,hora_emissao FROM silver.silver_passagem')
        assert cur.fetchone()==(None,'California',time(0,0))
        cur.execute("SELECT dados_originais->>'Valor' FROM silver.rejeitados WHERE motivos @> '[\"valor:decimal_invalido\"]'")
        assert cur.fetchone()==('NaN',)
    conn.commit()
    with pytest.raises(psycopg2.errors.ForeignKeyViolation):
        with conn.cursor() as cur:
            cur.execute("UPDATE silver.silver_pagamento SET id_viagem='inexistente'")
    conn.rollback()
    with pytest.raises(psycopg2.errors.CheckViolation):
        with conn.cursor() as cur:
            cur.execute('UPDATE silver.silver_trecho SET sequencia=0')
    conn.rollback()
    with pytest.raises(psycopg2.errors.UniqueViolation):
        with conn.cursor() as cur:
            cur.execute('INSERT INTO silver.silver_viagem SELECT * FROM silver.silver_viagem')
    conn.rollback()
    def falhar(*args,**kwargs):
        raise RuntimeError('Falha simulada após inserção')
    monkeypatch.setattr(silver,'verificar',falhar)
    with pytest.raises(RuntimeError,match='simulada'):
        silver.executar_silver(conn,2)
    assert snapshot(conn,'silver',tabelas)==salvo


def test_chaves_ambiguas_sao_rejeitadas_sem_escolher_uma_linha(banco_isolado):
    conn=banco_isolado
    t1=registro('trecho','002'); t2=dict(t1); t2['Sequência Trecho']='01'
    preparar(conn,{'viagem':[registro('viagem'),registro('viagem',' 001 '),registro('viagem','002')],
                   'pagamento':[registro('pagamento')], 'trecho':[t1,t2]})
    r=silver.executar_silver(conn,1)
    assert r['viagem']['motivos']['id_viagem:duplicado_na_origem']==2
    assert r['pagamento']['rejeitados']==1
    assert r['trecho']['motivos']['sequencia:duplicada_na_viagem']==2
    assert r['passagem']['origem']==0
