# Validação do dashboard

## Ambiente e execução

Em 28/09/2026, o painel foi executado com Streamlit 1.64.0, Altair 6.3.0 e
PostgreSQL 15, usando `streamlit.testing.v1.AppTest`. Esse mecanismo executa o
script e simula os widgets sem iniciar um servidor web.

A suíte completa terminou com **53 testes aprovados em 32,54 segundos**, com
`RUN_RAW_DB_TESTS`, `RUN_SILVER_DB_TESTS`, `RUN_GOLD_DB_TESTS` e
`RUN_DASHBOARD_DB_TESTS` definidos como `1`.

## Verificações

- O painel consulta a Gold real sem exceções e produz quatro elementos de gráfico.
- Indicadores do recorte completo: **341.860 viagens**, **R$ 1.188.144.731,13**
  de valor líquido e **R$ 3.475,53** de média por viagem.
- Alterar órgão e período atualiza os indicadores; combinações sem dados mostram
  mensagem informativa, sem manter os valores do recorte anterior.
- O mínimo de viagens remove órgãos apenas do ranking de médias.
- Órgãos sem nome/código são identificados, sem exibir `NaN` como nome.
- Valores negativos são preservados e as médias são ponderadas pelo volume.
- As especificações dos quatro gráficos possuem título, eixos, legendas e tooltips.
- O banco indisponível e a Gold vazia apresentam mensagens controladas.
- `docker compose config --quiet` terminou com código 0.

O AppTest verifica a execução, os elementos e as interações dos widgets; não
verifica pixels, cortes de texto ou responsividade em um navegador. A inspeção
visual em navegador e o build da imagem Docker foram concluídos posteriormente
na [validação final](validacao_final.md), com correções de instalação e gráficos.

## Critérios de avaliação apoiados

- **Perguntas de negócio:** três perguntas, respostas calculadas conforme os filtros,
  valores de referência e interpretação em [validacao_gold.md](validacao_gold.md).
- **Gráficos/dataviz:** quatro gráficos com elementos identificados, barras ordenadas
  nos rankings, unidades explícitas e volume acompanhado do valor médio.
- **Organização/documentação:** entrada `app/app.py`, módulos de consulta e gráficos,
  testes e [guia de execução](dashboard.md). Docker e Compose usam o mesmo caminho.

O download remoto do ZIP foi comprovado posteriormente na [validação final](validacao_final.md). A execução do pipeline
utilizou o arquivo local, conforme registrado nas entregas anteriores. Esta
validação não atribui nota nem comprova ausência de plágio por comparação externa.
