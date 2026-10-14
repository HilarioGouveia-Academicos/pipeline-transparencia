# Validação do dashboard Gold

Validação concluída no PostgreSQL local, com o ZIP `viagens_2025_6meses.zip`.
SHA-256 da fonte: `198855840f73e1570869a05a79144e7469f5249b5a1405c535456fee0d6798b0`.
A carga Silver completa foi confirmada em 30/09/2026 às 20:56 e a Gold
às 21:07, horário de Brasília.

## Base completa

| Conferência | Resultado |
|---|---:|
| Viagens | 341.860 |
| Pagamentos | 606.916 |
| Passagens | 167.260 |
| Trechos, incluindo Inválido | 763.349 |
| Registros rejeitados na Silver | 0 |
| Datas de emissão convertidas para NULL | 664 |
| Soma dos pagamentos | R$ 1.194.365.457,37 |

## Comparação com o notebook

Com todos os meses e órgãos, situação Realizada, as sete listas do notebook
foram conferidas: custos por órgão superior; médias por destino; identificadores
e durações das viagens; médias por tipo de pagamento; quantidades por transporte;
quantidades por UF; e totais por órgão pagador.

A maior duração é 384 dias. Realizada possui 755.885 trechos, dos quais
26.523 têm transporte Inválido. Os agrupamentos no formato do notebook têm
655 grupos de pagamento e 201 grupos de trecho.

## Materialização

| Tabela Gold | Linhas |
|---|---:|
| resumo_viagem_mes | 403 |
| resumo_destino_mes | 58.262 |
| gold_pagamento_resumo | 4.619 |
| gold_trecho_resumo | 15.867 |
| viagens_duracao | 1.874 |

Todos os conteúdos foram comparados com as respectivas views usando EXCEPT ALL
nos dois sentidos. As contagens e somas do resumo foram reconciliadas com Silver.
Os cinco conjuntos e `carga_dashboard` ocupam 22.126.592 bytes (21,1 MiB),
incluindo índices. Essa medida não inclui Raw, Silver ou a Gold anterior.

## Testes

Passaram testes de filtros combinados nas sete perguntas, médias ponderadas,
destinos com mínimo de 100 viagens, categorias ausentes, transporte Inválido,
desempate de duração, reexecução sem duplicatas, migração da regra antiga,
preservação da Gold em caso de falha e leitura com usuário sem acesso à Silver.
Os testes Streamlit verificam o padrão Realizada, Todas, órgão, período vazio,
exportações e ausência de controles administrativos.

Relatórios locais: `data/relatorio_silver_dashboard.json`,
`data/relatorio_gold_dashboard.json` e `data/validacao_dashboard_gold.json`.
A [documentação operacional](dashboard_gold_operacao.md) descreve os comandos.
Disponibilizar os novos conjuntos no banco do painel é uma etapa de publicação.

## Revalidação e publicação em 14/10/2026

Raw, Silver e Gold foram recriadas no banco local e as contagens completas,
as sete análises e o teste Streamlit passaram novamente. Em seguida, os cinco
conjuntos Gold e `carga_dashboard` foram importados no Render. A comparação de
conteúdo entre origem e destino passou antes do commit. O teste Streamlit com
leitura do Render confirmou os mesmos indicadores em Realizada e Todas.

O relatório local da transferência está em `data/validacao_gold_render.json`.
