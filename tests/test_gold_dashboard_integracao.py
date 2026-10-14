"""Contrato Gold: filtros, top cinco, reconciliação, rollback e permissão de leitura."""
import os
import uuid
from decimal import Decimal
from datetime import date
import psycopg2
from psycopg2 import sql
import pytest
from test_raw_integracao import banco_isolado
from test_silver_integracao import preparar, snapshot
from test_transformacao import registro
import silver
import gold
import gold_dashboard
import dashboard
from config import POSTGRES_CONFIG

pytestmark=pytest.mark.skipif(os.getenv('RUN_GOLD_DB_TESTS')!='1',reason='Requer PostgreSQL local')


def carregar(conn):
    viagens=[]
    detalhes={'pagamento':[],'passagem':[],'trecho':[]}
    for i in range(112):
        identificador=f'{i:05d}'
        v=registro('viagem',identificador)
        cancelada=i>=100
        v.update({'Situação':'Cancelada' if cancelada else 'Realizada',
                  'Código do órgão superior':'B' if cancelada else 'A',
                  'Nome do órgão superior':'Órgão B' if cancelada else 'Órgão A',
                  'Destinos':'Destino B' if cancelada else 'Destino A',
                  'Período - Data de início':'01/02/2025' if cancelada else '01/01/2025',
                  'Período - Data de fim':f'{1+i%20:02d}/02/2025' if cancelada else f'{1+i%20:02d}/01/2025'})
        viagens.append(v)
        for entidade in detalhes:
            r=registro(entidade,identificador)
            if entidade=='trecho':
                r['Meio de transporte']='Inválido' if i%2 else 'Rodoviário'
            if entidade=='pagamento':
                r['Nome do órgao pagador']='Pagador B' if cancelada else 'Pagador A'
            detalhes[entidade].append(r)
    preparar(conn,{'viagem':viagens,**detalhes})
    silver.executar_silver(conn,13)
    gold.executar_gold(conn)


def dados(conn):
    import pandas as pd
    resultado={}
    with conn.cursor() as cur:
        for tabela in gold_dashboard.CONSULTAS:
            cur.execute(sql.SQL('SELECT * FROM {}').format(sql.Identifier('gold',tabela)))
            resultado[tabela]=dashboard.preparar(pd.DataFrame(cur.fetchall(),columns=[c.name for c in cur.description]))
    conn.commit()
    return resultado


def test_filtros_top_cinco_e_reconciliacao(banco_isolado):
    conn=banco_isolado
    carregar(conn)
    fontes=dados(conn)
    geral=fontes['resumo_viagem_mes']
    assert int(geral.viagens.sum())==112 and int(geral.trechos.sum())==112
    chave_a=geral.loc[geral.codigo_orgao_superior=='A','orgao_chave'].iloc[0]
    for orgaos,situacoes,inicio,fim in [([],[],date(2025,1,1),date(2025,2,1)),
        ([chave_a],['["Realizada"]'],date(2025,1,1),date(2025,1,1))]:
        recorte={k:dashboard.filtrar(v,inicio,fim,orgaos,situacoes) for k,v in fontes.items()}
        resultados=dashboard.analisar(recorte)
        where='v.data_inicio>=%s AND v.data_inicio<(%s::date+interval \'1 month\')'
        parametros=[inicio,fim]
        if orgaos:
            where+=" AND v.codigo_orgao_superior='A' AND v.situacao='Realizada'"
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*),SUM(valor_total_liquido) FROM silver.silver_viagem v WHERE '+where,parametros)
            quantidade,total=cur.fetchone()
            assert int(recorte['resumo_viagem_mes'].viagens.sum())==quantidade
            assert recorte['resumo_viagem_mes'].valor_total_liquido.sum()==total
            cur.execute('SELECT id_viagem FROM silver.silver_viagem v WHERE '+where+
                        ' ORDER BY duracao_dias DESC,valor_total_liquido DESC,id_viagem LIMIT 5',parametros)
            assert resultados[2].id_viagem.tolist()==[r[0] for r in cur.fetchall()]
            consultas = [
                (0, ['codigo_orgao_superior','valor_total_liquido'],
                 'SELECT codigo_orgao_superior,SUM(valor_total_liquido) FROM silver.silver_viagem v WHERE '+where+
                 ' GROUP BY codigo_orgao_superior ORDER BY SUM(valor_total_liquido) DESC,codigo_orgao_superior LIMIT 5'),
                (1, ['destino','viagens','custo_medio'],
                 'SELECT destinos,COUNT(*),ROUND(SUM(valor_total_liquido)/COUNT(*),2) FROM silver.silver_viagem v WHERE '+where+
                 ' GROUP BY destinos HAVING COUNT(*)>=100 ORDER BY 3 DESC,destinos LIMIT 3'),
                (3, ['tipo_pagamento','pagamentos','valor_medio'],
                 'SELECT tipo_pagamento,COUNT(*),ROUND(SUM(valor)/COUNT(*),2) FROM silver.silver_pagamento p JOIN silver.silver_viagem v USING(id_viagem) WHERE '+where+
                 ' GROUP BY tipo_pagamento ORDER BY 3 DESC,tipo_pagamento'),
                (4, ['meio_transporte','trechos'],
                 'SELECT meio_transporte,COUNT(*) FROM silver.silver_trecho t JOIN silver.silver_viagem v USING(id_viagem) WHERE '+where+
                 ' GROUP BY meio_transporte ORDER BY 2 DESC,meio_transporte'),
                (5, ['destino_uf','trechos'],
                 'SELECT destino_uf_nome,COUNT(*) FROM silver.silver_trecho t JOIN silver.silver_viagem v USING(id_viagem) WHERE '+where+
                 ' GROUP BY destino_uf_nome ORDER BY 2 DESC,destino_uf_nome LIMIT 10'),
                (6, ['nome_orgao_pagador','total_pago'],
                 'SELECT nome_orgao_pagador,SUM(valor) FROM silver.silver_pagamento p JOIN silver.silver_viagem v USING(id_viagem) WHERE '+where+
                 ' GROUP BY nome_orgao_pagador ORDER BY 2 DESC,nome_orgao_pagador LIMIT 5'),
            ]
            for indice,colunas,consulta in consultas:
                cur.execute(consulta,parametros)
                if indice==0:
                    # O código está na identidade JSON usada pelo ranking.
                    import json
                    obtido=[(json.loads(r.orgao_chave)[0],r.valor_total_liquido) for r in resultados[indice].itertuples()]
                else:
                    obtido=list(resultados[indice][colunas].itertuples(index=False,name=None))
                assert obtido==cur.fetchall()
        conn.commit()
        assert resultados[1].iloc[0].destino=='Destino A'
        assert resultados[1].iloc[0].viagens==100
        assert resultados[3].iloc[0].valor_medio==Decimal('12.34')
        assert set(resultados[4].meio_transporte)=={'Inválido','Rodoviário'}
    assert len(fontes['viagens_duracao'])==10
    assert fontes['viagens_duracao'].duracao_dias.max()==20
    assert gold_dashboard.verificar(conn)
    conn.commit()


def test_falha_na_gold_preserva_todos_os_conjuntos(banco_isolado,monkeypatch):
    conn=banco_isolado
    carregar(conn)
    tabelas=list(gold_dashboard.CONSULTAS)+['carga_dashboard','resumo_orgao_mes']
    anterior=snapshot(conn,'gold',tabelas)
    original=gold_dashboard.verificar
    def falhar(conexao):
        with conexao.cursor() as cur:
            cur.execute('UPDATE gold.gold_trecho_resumo SET trechos=trechos+1')
        return original(conexao)
    monkeypatch.setattr(gold_dashboard,'verificar',falhar)
    with pytest.raises(ValueError,match='Conteúdo Gold divergente'):
        gold.executar_gold(conn)
    assert snapshot(conn,'gold',tabelas)==anterior


def test_painel_le_somente_gold_com_permissao_restrita(banco_isolado,monkeypatch):
    conn=banco_isolado
    carregar(conn)
    role='teste_gold_'+uuid.uuid4().hex
    admin=psycopg2.connect(**POSTGRES_CONFIG)
    admin.autocommit=True
    restrita=None
    try:
        with admin.cursor() as cur:
            cur.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD %s').format(sql.Identifier(role)),('teste-isolado',))
        with conn.cursor() as cur:
            cur.execute(sql.SQL('GRANT USAGE ON SCHEMA gold TO {}').format(sql.Identifier(role)))
            for tabela in list(gold_dashboard.CONSULTAS)+['carga_dashboard']:
                cur.execute(sql.SQL('GRANT SELECT ON {} TO {}').format(sql.Identifier('gold',tabela),sql.Identifier(role)))
        conn.commit()
        restrita=psycopg2.connect(**{**POSTGRES_CONFIG,'dbname':conn.info.dbname,'user':role,'password':'teste-isolado'})
        monkeypatch.setattr(dashboard,'conectar',lambda **kw:restrita)
        conjuntos,meta=dashboard.carregar_gold()
        assert len(conjuntos)==5 and meta['carregado_em']
        # A função fecha sua conexão; abrir outra prova que a Silver é inacessível.
        restrita=psycopg2.connect(**{**POSTGRES_CONFIG,'dbname':conn.info.dbname,'user':role,'password':'teste-isolado'})
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            with restrita.cursor() as cur:cur.execute('SELECT * FROM silver.silver_viagem')
        restrita.rollback()
    finally:
        if restrita:restrita.close()
        with conn.cursor() as cur:
            cur.execute(sql.SQL('DROP OWNED BY {}').format(sql.Identifier(role)))
        conn.commit()
        with admin.cursor() as cur:cur.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role)))
        admin.close()


def test_migracao_remove_apenas_regra_antiga_de_transporte(banco_isolado):
    conn=banco_isolado
    carregar(conn)
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE silver.silver_trecho ADD CONSTRAINT antiga_transporte CHECK (lower(btrim(meio_transporte)) <> 'inválido') NOT VALID")
    conn.commit()
    resumo=silver.executar_silver(conn,13)
    assert resumo['trecho']['aceitos']==112 and resumo['trecho']['rejeitados']==0
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM pg_constraint WHERE conrelid='silver.silver_trecho'::regclass AND conname='antiga_transporte'")
        assert cur.fetchone()[0]==0
        cur.execute("SELECT COUNT(*) FROM silver.silver_trecho WHERE meio_transporte='Inválido'")
        assert cur.fetchone()[0]==56
    conn.commit()
