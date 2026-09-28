from datetime import date, time
from decimal import Decimal
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from silver import decimal_br, data_estrita, hora_estrita, booleano, uf, transformar, LAYOUT


@pytest.mark.parametrize('entrada,esperado', [('R$ 1.250,50','1250.50'),(' 3.400,00 ','3400.00'),('0,99','0.99'),('-10,50','-10.50'),('1.000','1000.00'),('0','0.00')])
def test_moeda_exata(entrada,esperado):
    assert decimal_br(entrada) == Decimal(esperado)


@pytest.mark.parametrize('entrada', ['NaN','Infinity','12.50','1.25,00','1,234','10000000000000000,00'])
def test_moeda_invalida_nao_vira_zero(entrada):
    with pytest.raises(ValueError):
        decimal_br(entrada)


def test_ausencia_permanece_nula():
    assert decimal_br('') is None
    assert decimal_br('Sem informação') is None
    assert booleano('') is None
    r = registro('viagem')
    r['Valor diárias'] = ''
    dados, erros = transformar('viagem', r)
    assert dados['valor_diarias'] is None
    assert 'valor_diarias:obrigatorio_ausente' in erros


@pytest.mark.parametrize('entrada', ['31/02/2025','2025-02-29','05/13/2025','01/02/25'])
def test_data_invalida(entrada):
    with pytest.raises(ValueError):
        data_estrita(entrada)


def test_datas_sem_ambiguidade_e_hora():
    assert data_estrita('01/02/2025') == date(2025,2,1)
    assert data_estrita('2025-02-01') == date(2025,2,1)
    assert data_estrita('29/02/2024') == date(2024,2,29)
    assert hora_estrita('00:00') == time(0,0)
    with pytest.raises(ValueError):
        hora_estrita('25:00')


def test_booleanos():
    assert booleano('SIM') is True
    assert booleano('NÃO') is False
    with pytest.raises(ValueError):
        booleano('talvez')


def test_uf_sem_truncamento():
    assert uf('São Paulo','Brasil') == 'SP'
    assert uf('Rio Grande do Norte','Brasil') == 'RN'
    assert uf('df','Brasil') == 'DF'
    assert uf('Sem informação','Brasil') is None
    assert uf('California','Estados Unidos') is None
    with pytest.raises(ValueError):
        uf('XY','Brasil')


def registro(tabela, id_viagem='001'):
    resultado = {}
    for f in LAYOUT[tabela]['campos']:
        valor = {'texto':'texto','data':'01/01/2025','hora':'00:00','decimal':'12,34','inteiro':'1','booleano':'Sim','transporte':'Rodoviário'}[f['tipo']]
        if f['nome']=='id_viagem': valor=id_viagem
        if f['nome'].endswith('_uf_nome'): valor='São Paulo'
        if f['nome'].endswith('_pais'): valor='Brasil'
        if f['nome']=='data_fim': valor='02/01/2025'
        resultado[f['origem']] = valor
    return resultado


def test_totais_e_identificador_nominal():
    dados,erros=transformar('viagem',registro('viagem'))
    assert erros == []
    assert dados['id_viagem']=='001'
    assert dados['duracao_dias']==1
    assert dados['valor_total_bruto']==Decimal('37.02')
    assert dados['valor_total_liquido']==Decimal('24.68')


def test_transporte_invalido_e_datas_invertidas_sao_identificados():
    r=registro('trecho')
    r['Meio de transporte']='Inválido'
    r['Destino - Data']='31/12/2024'
    r['Número Diárias']='-0,50'
    _,erros=transformar('trecho',r)
    assert 'meio_transporte:transporte_invalido' in erros
    assert 'datas:ordem_invalida' in erros
    assert 'numero_diarias:negativo' in erros
