"""Contrato Gold do dashboard: materialização atômica e views de conferência."""
import hashlib
import json
import logging
from pathlib import Path
from psycopg2 import sql

BASE = '''SELECT v.*, date_trunc('month', data_inicio)::date AS mes_inicio,
    jsonb_build_array(codigo_orgao_superior, nome_orgao_superior)::text AS orgao_chave,
    jsonb_build_array(date_trunc('month', data_inicio)::date,
                     codigo_orgao_superior, nome_orgao_superior, situacao)::text AS grupo_chave
    FROM silver.silver_viagem v'''
DIMENSOES = 'b.mes_inicio, b.orgao_chave, b.codigo_orgao_superior, b.nome_orgao_superior, b.situacao, b.grupo_chave'
CONSULTAS = {
    'resumo_viagem_mes': f'''WITH base AS ({BASE}),
      pagamentos AS (SELECT id_viagem, COUNT(*) AS n, SUM(valor) AS valor FROM silver.silver_pagamento GROUP BY 1),
      passagens AS (SELECT id_viagem, COUNT(*) AS n FROM silver.silver_passagem GROUP BY 1),
      trechos AS (SELECT id_viagem, COUNT(*) AS n FROM silver.silver_trecho GROUP BY 1)
      SELECT {DIMENSOES}, COUNT(*) AS viagens,
        SUM(COALESCE(p.n,0))::bigint AS pagamentos, SUM(COALESCE(a.n,0))::bigint AS passagens,
        SUM(COALESCE(t.n,0))::bigint AS trechos, SUM(b.valor_total_liquido) AS valor_total_liquido,
        SUM(COALESCE(p.valor,0)) AS valor_pagamentos, SUM(b.duracao_dias+1)::bigint AS duracao_total_dias
      FROM base b LEFT JOIN pagamentos p USING(id_viagem)
      LEFT JOIN passagens a USING(id_viagem) LEFT JOIN trechos t USING(id_viagem)
      GROUP BY {DIMENSOES}''',
    'resumo_destino_mes': f'''WITH base AS ({BASE}) SELECT {DIMENSOES}, b.destinos AS destino,
      COUNT(*) AS viagens, SUM(b.valor_total_liquido) AS valor_total_liquido
      FROM base b GROUP BY {DIMENSOES}, b.destinos''',
    'gold_pagamento_resumo': f'''WITH base AS ({BASE}) SELECT {DIMENSOES},
      p.nome_orgao_pagador, p.tipo_pagamento, COUNT(*) AS pagamentos, SUM(p.valor) AS total_pago
      FROM base b JOIN silver.silver_pagamento p USING(id_viagem)
      GROUP BY {DIMENSOES}, p.nome_orgao_pagador, p.tipo_pagamento''',
    'gold_trecho_resumo': f'''WITH base AS ({BASE}) SELECT {DIMENSOES},
      t.meio_transporte, t.destino_uf_nome AS destino_uf, COUNT(*) AS trechos
      FROM base b JOIN silver.silver_trecho t USING(id_viagem)
      GROUP BY {DIMENSOES}, t.meio_transporte, t.destino_uf_nome''',
    'viagens_duracao': f'''WITH base AS ({BASE}), candidatas AS (
      SELECT {DIMENSOES}, b.id_viagem, b.data_inicio, b.data_fim,
        b.duracao_dias+1 AS duracao_dias, b.valor_total_liquido,
        ROW_NUMBER() OVER (PARTITION BY b.grupo_chave
          ORDER BY b.duracao_dias DESC, b.valor_total_liquido DESC, b.id_viagem ASC) AS posicao
      FROM base b WHERE b.duracao_dias IS NOT NULL)
      SELECT * FROM candidatas WHERE posicao<=5''',
}


def criar_conjuntos(conn):
    """Define tabelas novas; preserva a Gold anterior e não faz commit próprio."""
    with conn.cursor() as cur:
        for tabela, consulta in CONSULTAS.items():
            view = 'vw_' + tabela
            cur.execute(sql.SQL('CREATE OR REPLACE VIEW {} AS ' + consulta).format(sql.Identifier('gold', view)))
            cur.execute(sql.SQL('CREATE TABLE IF NOT EXISTS {} AS SELECT * FROM {} WITH NO DATA').format(
                sql.Identifier('gold', tabela), sql.Identifier('gold', view)))
            cur.execute(sql.SQL('CREATE INDEX IF NOT EXISTS {} ON {} (mes_inicio, orgao_chave, situacao)').format(
                sql.Identifier('idx_' + tabela + '_filtros'), sql.Identifier('gold', tabela)))
        cur.execute('''CREATE TABLE IF NOT EXISTS gold.carga_dashboard (
            id integer PRIMARY KEY CHECK (id=1), versao integer NOT NULL,
            carregado_em timestamptz NOT NULL, fonte jsonb NOT NULL, conferencia jsonb NOT NULL)''')


def verificar(conn):
    conferencia = {}
    with conn.cursor() as cur:
        for tabela in CONSULTAS:
            # EXCEPT ALL detecta divergência de valores e multiplicidade, além das contagens.
            cur.execute(sql.SQL('''SELECT EXISTS(
                (SELECT * FROM {} EXCEPT ALL SELECT * FROM {}) UNION ALL
                (SELECT * FROM {} EXCEPT ALL SELECT * FROM {}))''').format(
                sql.Identifier('gold', tabela), sql.Identifier('gold', 'vw_'+tabela),
                sql.Identifier('gold', 'vw_'+tabela), sql.Identifier('gold', tabela)))
            if cur.fetchone()[0]:
                raise ValueError('Conteúdo Gold divergente: ' + tabela)
            cur.execute(sql.SQL('SELECT row_to_json(t)::text FROM {} t ORDER BY 1').format(sql.Identifier('gold', tabela)))
            digest = hashlib.sha256()
            quantidade = 0
            for (linha,) in cur:
                digest.update(linha.encode('utf-8'))
                digest.update(b'\n')
                quantidade += 1
            conferencia[tabela] = {'linhas': quantidade, 'sha256': digest.hexdigest()}
            logging.info('Gold %s: %d linhas e conteúdo conferidos com a view', tabela, quantidade)
        medidas = {'viagens': 'SELECT COUNT(*) FROM silver.silver_viagem',
                   'pagamentos': 'SELECT COUNT(*) FROM silver.silver_pagamento',
                   'passagens': 'SELECT COUNT(*) FROM silver.silver_passagem',
                   'trechos': 'SELECT COUNT(*) FROM silver.silver_trecho',
                   'valor_total_liquido': 'SELECT COALESCE(SUM(valor_total_liquido),0) FROM silver.silver_viagem',
                   'valor_pagamentos': 'SELECT COALESCE(SUM(valor),0) FROM silver.silver_pagamento'}
        for coluna, consulta in medidas.items():
            cur.execute(consulta)
            esperado = cur.fetchone()[0]
            cur.execute(sql.SQL('SELECT COALESCE(SUM({}),0) FROM gold.resumo_viagem_mes').format(sql.Identifier(coluna)))
            if cur.fetchone()[0] != esperado:
                raise ValueError('Total Gold divergente: ' + coluna)
    return conferencia


def materializar(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM silver.rejeitados WHERE origem='trecho' AND motivos @> '[\"meio_transporte:transporte_invalido\"]'")
        if cur.fetchone()[0]:
            raise ValueError('Silver com regra antiga de transporte: execute novamente 2_transformar.py antes da Gold.')
    criar_conjuntos(conn)
    with conn.cursor() as cur:
        for tabela in CONSULTAS:
            cur.execute(sql.SQL('TRUNCATE {}').format(sql.Identifier('gold', tabela)))
            cur.execute(sql.SQL('INSERT INTO {} SELECT * FROM {}').format(
                sql.Identifier('gold', tabela), sql.Identifier('gold', 'vw_'+tabela)))
            logging.info('Gold %s: %d linhas materializadas', tabela, cur.rowcount)
    conferencia = verificar(conn)
    fonte = {}
    arquivo = Path(__file__).resolve().parents[1] / 'data/relatorio_raw.json'
    if arquivo.exists():
        relatorio = json.loads(arquivo.read_text(encoding='utf-8'))
        fonte = {k: relatorio[k] for k in ('zip', 'sha256_zip') if k in relatorio}
    with conn.cursor() as cur:
        cur.execute('''INSERT INTO gold.carga_dashboard VALUES (1,1,CURRENT_TIMESTAMP,%s::jsonb,%s::jsonb)
            ON CONFLICT (id) DO UPDATE SET versao=EXCLUDED.versao, carregado_em=EXCLUDED.carregado_em,
            fonte=EXCLUDED.fonte, conferencia=EXCLUDED.conferencia''',
            (json.dumps(fonte), json.dumps(conferencia)))
    return conferencia
