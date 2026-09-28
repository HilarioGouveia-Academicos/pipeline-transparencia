# Modelagem e regras da Gold

## Grão e origem

`gold.resumo_orgao_mes` contém uma linha por mês de **início da viagem** e
par (código, nome) do **órgão solicitante**, obtidos de `silver.silver_viagem`.
A PK é `(mes_inicio, orgao_chave)`. A chave do órgão é a representação JSON
do par código/nome: preserva valores nulos sem confundi-los com nomes reais.
Órgãos com nomes iguais e códigos diferentes ficam separados; mudanças de nome
no mesmo código também geram grupos distintos.

As CTEs de `sql/4_carregar_gold.sql` agrupam pagamentos, passagens, trechos e
rejeições por `id_viagem` antes dos LEFT JOINs. Assim, cada viagem participa uma
vez da agregação final com GROUP BY. Viagens sem detalhes continuam na Gold.
Zeros nos indicadores de detalhes significam ausência de registros aceitos.

## Métricas

- `viagens` e `viagens_urgentes`: quantidades de viagens e das marcadas urgentes.
- `duracao_total_dias` e `maior_duracao_dias`: soma e máximo da diferença entre
  fim e início da viagem. Uma viagem no mesmo dia tem duração zero.
- `valor_diarias`, `valor_passagens`, `valor_outros_gastos`, `valor_devolucao`:
  somas dos campos da entidade viagem.
- `valor_total_bruto`: diárias + passagens + outros gastos.
- `valor_total_liquido`: bruto menos devoluções. Pode incluir valores negativos.
- `pagamentos` e `valor_pagamentos`: quantidade e valor dos pagamentos aceitos
  vinculados às viagens do grupo.
- `passagens`, `valor_passagens_detalhe` e `taxa_servico`: quantidade, valor e
  taxa dos registros de passagens. A taxa permanece separada.
- `trechos` e `numero_diarias_trechos`: quantidade de trechos aceitos e soma
  da quantidade de diárias desses trechos.
- `trechos_rejeitados`: trechos auditados vinculados a viagens aceitas do grupo.
  Rejeições sem uma viagem aceita não podem ser atribuídas a órgão/mês.

Os valores monetários usam NUMERIC no banco e Decimal em Python. Uma média por
viagem é `SUM(valor_total_liquido) / SUM(viagens)`; não se deve tirar média das
médias mensais. O indicador não representa custo por destino.

Valores de viagem, pagamentos e passagens são medidas de fontes com grãos
próprios. Não são somados entre si e não se exige igualdade entre eles.
Pagamentos e passagens são atribuídos ao mês de início da viagem: o resultado
não representa fluxo de caixa por mês de pagamento nem emissão de bilhetes.

## Integridade e execução

```powershell
.\.venv\Scripts\python.exe src/3_analise.py --repetir
```

DDL, TRUNCATE, INSERT e conferência ocorrem na mesma transação, com isolamento
REPEATABLE READ. A carga recusa Silver sem viagens. Não aplica filtro adicional
de data ou situação: o escopo é o conjunto aceito pela Silver.

Antes do commit, 17 totais aditivos e a maior duração são comparados diretamente
às tabelas Silver, sem usar o resultado dos JOINs para calcular a referência.
A reexecução compara também o hash SHA-256 das linhas ordenadas da Gold.
Qualquer divergência desfaz a tentativa corrente. O relatório de sucesso fica
em `data/relatorio_gold.json`; um relatório antigo não comprova uma nova execução.

A antiga tabela `gold.gold_metricas`, se existir no banco, não é consumida nem
apagada por esta fase. Sua estrutura foi substituída nos scripts do projeto.
O [dashboard](dashboard.md) consulta a nova tabela desde a Fase 4.

## Perguntas apoiadas por esta entrega

1. Quais órgãos solicitantes concentram o maior valor líquido de viagens?
2. Como variam a quantidade de viagens e o valor líquido por mês de início?
3. Quais órgãos apresentam maior valor médio por viagem, e qual é seu volume?

As consultas estão em `sql/5_perguntas_negocio.sql`. Os resultados devem ser
interpretados junto do volume e da cobertura dos detalhes aceitos. O [dashboard](dashboard.md) apresenta as visualizações e respostas calculadas
para os filtros selecionados.
