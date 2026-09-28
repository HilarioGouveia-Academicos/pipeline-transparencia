"""Carga Gold transacional, com reconciliação independente e assinatura."""
import hashlib
import json
from pathlib import Path

SQL = Path(__file__).resolve().parents[1] / 'sql'
TOTAIS = {
    'viagens': 'SELECT COUNT(*) FROM silver.silver_viagem',
    'viagens_urgentes': 'SELECT COUNT(*) FROM silver.silver_viagem WHERE viagem_urgente',
    'duracao_total_dias': 'SELECT COALESCE(SUM(duracao_dias),0) FROM silver.silver_viagem',
    **{c: f'SELECT COALESCE(SUM({c}),0) FROM silver.silver_viagem' for c in (
        'valor_diarias', 'valor_passagens', 'valor_outros_gastos', 'valor_devolucao',
        'valor_total_bruto', 'valor_total_liquido')},
    'pagamentos': 'SELECT COUNT(*) FROM silver.silver_pagamento',
    'valor_pagamentos': 'SELECT COALESCE(SUM(valor),0) FROM silver.silver_pagamento',
    'passagens': 'SELECT COUNT(*) FROM silver.silver_passagem',
    'valor_passagens_detalhe': 'SELECT COALESCE(SUM(valor_passagem),0) FROM silver.silver_passagem',
    'taxa_servico': 'SELECT COALESCE(SUM(taxa_servico),0) FROM silver.silver_passagem',
    'trechos': 'SELECT COUNT(*) FROM silver.silver_trecho',
    'numero_diarias_trechos': 'SELECT COALESCE(SUM(numero_diarias),0) FROM silver.silver_trecho',
    'trechos_rejeitados': "SELECT COUNT(*) FROM silver.rejeitados r JOIN silver.silver_viagem v USING(id_viagem) WHERE r.origem='trecho'",
}


def verificar(conn):
    totais = {}
    with conn.cursor() as cur:
        for coluna, consulta in TOTAIS.items():
            cur.execute(consulta)
            esperado = cur.fetchone()[0]
            # Nomes internos fixos; nenhum identificador vem de entrada externa.
            cur.execute(f'SELECT COALESCE(SUM({coluna}),0) FROM gold.resumo_orgao_mes')
            if cur.fetchone()[0] != esperado:
                raise ValueError('Total Gold divergente: ' + coluna)
            totais[coluna] = esperado
        cur.execute('SELECT COALESCE(MAX(duracao_dias),0) FROM silver.silver_viagem')
        maior = cur.fetchone()[0]
        cur.execute('SELECT COALESCE(MAX(maior_duracao_dias),0) FROM gold.resumo_orgao_mes')
        if cur.fetchone()[0] != maior:
            raise ValueError('Duração máxima divergente')
        cur.execute('SELECT * FROM gold.resumo_orgao_mes ORDER BY mes_inicio, orgao_chave')
        linhas = cur.fetchall()
    assinatura = hashlib.sha256(json.dumps(linhas, default=str, ensure_ascii=False).encode()).hexdigest()
    return {'grupos': len(linhas), 'totais': totais, 'maior_duracao_dias': maior, 'assinatura': assinatura}


def executar_gold(conn, esperado=None):
    conn.set_session(isolation_level='REPEATABLE READ')
    with conn:
        with conn.cursor() as cur:
            cur.execute((SQL / '3_criar_gold.sql').read_text(encoding='utf-8-sig'))
            cur.execute('SELECT COUNT(*) FROM silver.silver_viagem')
            if cur.fetchone()[0] == 0:
                raise ValueError('Silver sem viagens: execute e valide a Fase 2 antes da Gold')
            cur.execute('TRUNCATE gold.resumo_orgao_mes')
            cur.execute((SQL / '4_carregar_gold.sql').read_text(encoding='utf-8-sig'))
        resultado = verificar(conn)
        if esperado is not None and resultado != esperado:
            raise ValueError('Reexecução Gold divergente; carga anterior preservada')
    return resultado
