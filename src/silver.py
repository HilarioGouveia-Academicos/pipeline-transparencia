"""Conversão e carga transacional Raw -> Silver com rastreabilidade e reconciliação."""
from collections import Counter
from functools import lru_cache
from datetime import date, time
from decimal import Decimal
import hashlib
import io
import json
import logging
import re
import unicodedata

from psycopg2 import sql
from config import ARQUIVOS, PASTA_RAIZ, TAMANHO_BLOCO

LAYOUT = json.loads((PASTA_RAIZ / 'src/silver_layout.json').read_text(encoding='utf-8'))
logger = logging.getLogger(__name__)
LIMITE = Decimal('10000000000000000')
ESTADOS = dict(zip(
    'AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO'.split(),
    ['Acre','Alagoas','Amapá','Amazonas','Bahia','Ceará','Distrito Federal','Espírito Santo','Goiás','Maranhão',
     'Mato Grosso','Mato Grosso do Sul','Minas Gerais','Pará','Paraíba','Paraná','Pernambuco','Piauí',
     'Rio de Janeiro','Rio Grande do Norte','Rio Grande do Sul','Rondônia','Roraima','Santa Catarina','São Paulo','Sergipe','Tocantins']))


def dobrar(texto):
    return ''.join(c for c in unicodedata.normalize('NFKD', texto) if not unicodedata.combining(c)).casefold()


MAPA_UF = {dobrar(nome): sigla for sigla, nome in ESTADOS.items()}
MAPA_UF.update({sigla.lower(): sigla for sigla in ESTADOS})


def texto(valor):
    if valor is None:
        return None
    valor = str(valor).strip()
    return None if not valor or valor.casefold() in ('sem informação', 'sem informacao') else valor


@lru_cache(maxsize=32768)
def decimal_br(valor):
    valor = texto(valor)
    if valor is None:
        return None
    if valor.startswith('R$'):
        valor = valor[2:].strip()
    if not re.fullmatch(r'[+-]?(?:\d+|\d{1,3}(?:\.\d{3})+)(?:,\d{1,2})?', valor):
        raise ValueError('decimal_invalido')
    resultado = Decimal(valor.replace('.', '').replace(',', '.'))
    if abs(resultado) >= LIMITE:
        raise ValueError('decimal_fora_limite')
    return resultado.quantize(Decimal('0.01'))


@lru_cache(maxsize=32768)
def data_estrita(valor):
    valor = texto(valor)
    if valor is None:
        return None
    if re.fullmatch(r'\d{2}/\d{2}/\d{4}', valor):
        dia, mes, ano = map(int, valor.split('/'))
        return date(ano, mes, dia)
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', valor):
        return date.fromisoformat(valor)
    raise ValueError('data_invalida')


@lru_cache(maxsize=32768)
def hora_estrita(valor):
    valor = texto(valor)
    if valor is None:
        return None
    if not re.fullmatch(r'\d{2}:\d{2}(?::\d{2})?', valor):
        raise ValueError('hora_invalida')
    return time.fromisoformat(valor)


@lru_cache(maxsize=32768)
def booleano(valor):
    valor = texto(valor)
    if valor is None:
        return None
    chave = dobrar(valor)
    if chave not in ('sim', 'nao'):
        raise ValueError('booleano_invalido')
    return chave == 'sim'


def inteiro(valor):
    valor = texto(valor)
    if valor is None:
        return None
    if not re.fullmatch(r'\d+', valor) or len(valor) > 10 or int(valor) > 2147483647:
        raise ValueError('inteiro_invalido')
    return int(valor)


def transporte(valor):
    valor = texto(valor)
    if valor is not None and dobrar(valor) == 'invalido':
        raise ValueError('transporte_invalido')
    return valor


@lru_cache(maxsize=32768)
def uf(nome, pais):
    nome = texto(nome)
    if nome is None:
        return None
    # Estados/províncias estrangeiros ficam em *_uf_nome, sem sigla brasileira.
    if pais is not None and dobrar(pais) != 'brasil':
        return None
    resultado = MAPA_UF.get(dobrar(nome))
    if resultado is None:
        raise ValueError('uf_desconhecida')
    return resultado


CONVERSORES = {'texto': texto, 'decimal': decimal_br, 'data': data_estrita, 'hora': hora_estrita,
               'booleano': booleano, 'inteiro': inteiro, 'transporte': transporte}


def transformar(tabela, original):
    dados, erros = {}, []
    for campo in LAYOUT[tabela]['campos']:
        nome = campo['nome']
        try:
            valor = CONVERSORES[campo['tipo']](original[campo['origem']])
            if valor is None and campo['obrigatorio']:
                raise ValueError('obrigatorio_ausente')
            dados[nome] = valor
        except (ValueError, ArithmeticError) as exc:
            dados[nome] = None
            motivo = str(exc)
            conhecidos = {'decimal_invalido','decimal_fora_limite','data_invalida','hora_invalida','booleano_invalido','inteiro_invalido','transporte_invalido','obrigatorio_ausente'}
            if motivo not in conhecidos:
                motivo = campo['tipo'] + '_invalido'
            erros.append(nome + ':' + motivo)
    if tabela == 'viagem':
        inicio, fim = dados['data_inicio'], dados['data_fim']
        dados['duracao_dias'] = (fim - inicio).days if inicio and fim else None
        if dados['duracao_dias'] is not None and dados['duracao_dias'] < 0:
            erros.append('datas:ordem_invalida')
        valores = [dados[n] for n in ['valor_diarias','valor_passagens','valor_outros_gastos','valor_devolucao']]
        dados['valor_total_bruto'] = sum(valores[:3], Decimal(0)) if all(v is not None for v in valores[:3]) else None
        dados['valor_total_liquido'] = dados['valor_total_bruto'] - valores[3] if all(v is not None for v in valores) else None
        if any(v is not None and abs(v) >= LIMITE for v in [dados['valor_total_bruto'], dados['valor_total_liquido']]):
            erros.append('totais:fora_limite')
    if tabela == 'trecho':
        if dados['sequencia'] is not None and dados['sequencia'] <= 0:
            erros.append('sequencia:nao_positiva')
        if dados['numero_diarias'] is not None and dados['numero_diarias'] < 0:
            erros.append('numero_diarias:negativo')
        if dados['origem_data'] and dados['destino_data'] and dados['destino_data'] < dados['origem_data']:
            erros.append('datas:ordem_invalida')
    for nome in LAYOUT[tabela]['extras']:
        if nome.endswith('_uf'):
            prefixo = nome[:-3]
            try:
                dados[nome] = uf(dados[prefixo+'_uf_nome'], dados[prefixo+'_pais'])
            except ValueError:
                dados[nome] = None
                erros.append(nome + ':uf_desconhecida')
    return dados, erros


def colunas(tabela):
    return ([] if tabela == 'viagem' else ['id_'+tabela]) + [f['nome'] for f in LAYOUT[tabela]['campos']] + LAYOUT[tabela]['extras'] + ['registro_hash','ocorrencia']


def copy_linhas(conn, tabela, nomes, linhas):
    if not linhas:
        return
    def formatar(v):
        if v is None:
            return ''  # NULL do COPY CSV; uma string vazia seria enviada entre aspas.
        if isinstance(v, bool):
            v = 'true' if v else 'false'
        elif isinstance(v, (date, time)):
            v = v.isoformat()
        return '"' + str(v).replace('"', '""') + '"'
    buffer = io.StringIO(newline='')
    for linha in linhas:
        buffer.write(','.join(formatar(v) for v in linha) + '\n')
    buffer.seek(0)
    comando = sql.SQL('COPY {} ({}) FROM STDIN WITH (FORMAT CSV)').format(
        sql.Identifier('silver', tabela), sql.SQL(', ').join(map(sql.Identifier, nomes)))
    with conn.cursor() as cur:
        cur.copy_expert(comando.as_string(conn), buffer)


def duplicadas(conn, tabela):
    id_origem = ARQUIVOS[tabela]['colunas'][0]
    with conn.cursor() as cur:
        if tabela == 'viagem':
            cur.execute(sql.SQL('SELECT btrim({}) FROM {} GROUP BY 1 HAVING count(*) > 1').format(
                sql.Identifier(id_origem), sql.Identifier('raw', 'raw_viagem')))
            return {r[0] for r in cur}
        if tabela == 'trecho':
            cur.execute(sql.SQL("""SELECT btrim({}), CASE WHEN btrim("Sequência Trecho") ~ '^[0-9]{{1,10}}$'
                      THEN btrim("Sequência Trecho")::bigint END
                      FROM raw.raw_trecho GROUP BY 1,2 HAVING count(*) > 1""").format(sql.Identifier(id_origem)))
            return set(cur.fetchall())
    return set()


def conferir_estrutura(conn):
    with conn.cursor() as cur:
        for tabela in LAYOUT:
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='silver' AND table_name=%s ORDER BY ordinal_position", ('silver_'+tabela,))
            if [r[0] for r in cur] != colunas(tabela):
                raise ValueError('Estrutura Silver incompatível. Migre o banco antigo antes de executar a Fase 2.')


def serializar(objeto):
    return json.dumps(objeto, ensure_ascii=False, sort_keys=True, default=str)


def verificar(conn, tabela, resumo):
    nomes_numericos = list(resumo['numericos'])
    with conn.cursor() as cur:
        cur.execute(sql.SQL('SELECT count(*){} FROM {}').format(
            sql.SQL(''.join(', COALESCE(SUM("'+n+'"),0)' for n in nomes_numericos)),
            sql.Identifier('silver', 'silver_'+tabela)))
        dados = cur.fetchone()
        if dados[0] != resumo['aceitos']:
            raise ValueError('Contagem Silver divergente: '+tabela)
        for nome, total in zip(nomes_numericos, dados[1:]):
            if total != resumo['numericos'][nome]['aceitos']:
                raise ValueError('Total Silver divergente: '+tabela+'.'+nome)
        cur.execute('SELECT count(*) FROM silver.rejeitados WHERE origem=%s', (tabela,))
        if cur.fetchone()[0] != resumo['rejeitados']:
            raise ValueError('Contagem de rejeitados divergente: '+tabela)
        for nome in nomes_numericos:
            cur.execute('SELECT COALESCE(SUM((valores_convertidos ->> %s)::numeric),0) FROM silver.rejeitados WHERE origem=%s', (nome,tabela))
            if cur.fetchone()[0] != resumo['numericos'][nome]['rejeitados']:
                raise ValueError('Total rejeitado divergente: '+tabela+'.'+nome)
            valores = resumo['numericos'][nome]
            if valores['origem_convertivel'] != valores['aceitos'] + valores['rejeitados']:
                raise ValueError('Reconciliação numérica divergente: '+tabela+'.'+nome)
        if resumo['origem'] != resumo['aceitos'] + resumo['rejeitados']:
            raise ValueError('Reconciliação de registros divergente: '+tabela)
    soma, quantidade = 0, 0
    with conn.cursor(name='proveniencia_silver') as cur:
        cur.itersize = TAMANHO_BLOCO
        cur.execute(sql.SQL('SELECT registro_hash FROM {} UNION ALL SELECT registro_hash FROM silver.rejeitados WHERE origem=%s').format(sql.Identifier('silver','silver_'+tabela)), (tabela,))
        for (hash_linha,) in cur:
            quantidade += 1
            soma = (soma + int(hash_linha,16)) % (1 << 256)
    if quantidade != resumo['origem'] or f'{soma:064x}' != resumo['assinatura_origem']:
        raise ValueError('Proveniência divergente: '+tabela)
    # Assinatura do conteúdo efetivamente persistido, além dos hashes de origem.
    assinatura = 0
    with conn.cursor(name='conteudo_silver') as cur:
        cur.itersize = TAMANHO_BLOCO
        cur.execute(sql.SQL('SELECT * FROM {}').format(sql.Identifier('silver', 'silver_'+tabela)))
        for linha in cur:
            assinatura = (assinatura + int.from_bytes(hashlib.sha256(serializar(linha).encode('utf-8')).digest(),'big')) % (1 << 256)
    resumo['assinatura_silver'] = f'{assinatura:064x}'


def executar_silver(conn, tamanho=TAMANHO_BLOCO, esperado=None):
    if tamanho <= 0:
        raise ValueError('Tamanho do bloco deve ser positivo')
    conn.set_session(isolation_level='REPEATABLE READ')
    relatorio, ids_aceitos = {}, set()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute((PASTA_RAIZ / 'sql/2_criar_silver.sql').read_text(encoding='utf-8'))
            conferir_estrutura(conn)
            with conn.cursor() as cur:
                cur.execute('TRUNCATE silver.silver_pagamento, silver.silver_passagem, silver.silver_trecho, silver.silver_viagem, silver.rejeitados')
            for tabela, layout in LAYOUT.items():
                repetidas = duplicadas(conn, tabela)
                ocorrencias = Counter()
                campos_numericos = [f for f in layout['campos'] if f['tipo']=='decimal']
                numericos = [f['nome'] for f in campos_numericos]
                nomes_destino = colunas(tabela)
                resumo = {'origem':0, 'aceitos':0, 'rejeitados':0, 'motivos':Counter(),
                          'numericos':{n:{'origem_convertivel':Decimal(0),'aceitos':Decimal(0),'rejeitados':Decimal(0),'invalidos':0,'ausentes':0} for n in numericos}}
                soma = 0
                with conn.cursor(name='leitura_raw_silver') as leitura:
                    leitura.itersize = tamanho
                    leitura.execute(sql.SQL('SELECT {} FROM {}').format(
                        sql.SQL(', ').join(map(sql.Identifier,ARQUIVOS[tabela]['colunas'])), sql.Identifier('raw','raw_'+tabela)))
                    for bloco in iter(lambda: leitura.fetchmany(tamanho), []):
                        aceitos, rejeitados = [], []
                        for linha in bloco:
                            original = dict(zip(ARQUIVOS[tabela]['colunas'], linha))
                            registro_hash = hashlib.sha256(json.dumps(list(linha),ensure_ascii=False,separators=(',',':')).encode('utf-8')).hexdigest()
                            ocorrencias[registro_hash] += 1
                            ocorrencia = ocorrencias[registro_hash]
                            soma = (soma + int(registro_hash,16)) % (1 << 256)
                            dados, erros = transformar(tabela, original)
                            id_viagem = dados['id_viagem']
                            if tabela=='viagem' and id_viagem in repetidas:
                                erros.append('id_viagem:duplicado_na_origem')
                            if tabela!='viagem' and id_viagem not in ids_aceitos:
                                erros.append('id_viagem:sem_viagem_aceita')
                            if tabela=='trecho' and (id_viagem,dados['sequencia']) in repetidas:
                                erros.append('sequencia:duplicada_na_viagem')
                            resumo['origem'] += 1
                            destino = 'rejeitados' if erros else 'aceitos'
                            resumo[destino] += 1
                            for campo in campos_numericos:
                                nome = campo['nome']
                                valor = dados[nome]
                                if valor is None:
                                    chave = 'ausentes' if texto(original[campo['origem']]) is None else 'invalidos'
                                    resumo['numericos'][nome][chave] += 1
                                else:
                                    resumo['numericos'][nome]['origem_convertivel'] += valor
                                    resumo['numericos'][nome][destino] += valor
                            if erros:
                                resumo['motivos'].update(erros)
                                rejeitados.append((tabela,registro_hash,ocorrencia,id_viagem,serializar(erros),serializar(original),serializar({n:dados[n] for n in numericos})))
                            else:
                                if tabela=='viagem':
                                    ids_aceitos.add(id_viagem)
                                else:
                                    dados['id_'+tabela] = registro_hash+':'+str(ocorrencia)
                                dados.update(registro_hash=registro_hash, ocorrencia=ocorrencia)
                                aceitos.append(tuple(dados[n] for n in nomes_destino))
                        copy_linhas(conn, 'silver_'+tabela, nomes_destino, aceitos)
                        copy_linhas(conn, 'rejeitados', ['origem','registro_hash','ocorrencia','id_viagem','motivos','dados_originais','valores_convertidos'], rejeitados)
                        logger.info('%s: %d registros tratados', tabela, resumo['origem'])
                resumo['assinatura_origem'] = f'{soma:064x}'
                resumo['motivos'] = dict(resumo['motivos'])
                verificar(conn,tabela,resumo)
                relatorio[tabela] = resumo
                logger.info('%s: %d aceitos, %d rejeitados; reconciliação conferida', tabela,resumo['aceitos'],resumo['rejeitados'])
            if esperado is not None and relatorio != esperado:
                raise ValueError('Reexecução divergente; a carga anterior foi preservada')
    except Exception:
        logger.exception('Falha na Silver: transação desfeita, carga anterior preservada')
        raise
    return relatorio
