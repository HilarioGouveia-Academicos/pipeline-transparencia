"""
tests/test_transformacao.py
Testes unitários para as funções de limpeza e transformação de dados.
"""

import pandas as pd
from importlib import import_module

limpar_moeda = import_module("src.2_transformar").limpar_moeda

def test_limpar_moeda_padrao_br():
    """Testa a conversão de strings monetárias com pontuação do Brasil."""
    serie_entrada = pd.Series(["R$ 1.250,50", " 3.400,00 ", "R$0,99"])
    serie_esperada = pd.Series(["1250.50", "3400.00", "0.99"])

    resultado = limpar_moeda(serie_entrada)
    pd.testing.assert_series_equal(resultado, serie_esperada)

def test_limpar_moeda_valores_invalidos():
    """Testa o comportamento com dados nulos ou vazios."""
    serie_entrada = pd.Series(["", "NaN", "R$ "])
    # A função original limpa e a conversão do pandas (`to_numeric`) tratará de coerções
    resultado = limpar_moeda(serie_entrada)
    assert resultado.iloc[0] == ""
    assert resultado.iloc[1] == "NaN"
    assert resultado.iloc[2] == ""
