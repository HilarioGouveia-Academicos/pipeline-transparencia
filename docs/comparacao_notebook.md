# Comparação com 3_analise.ipynb

Conferência em 30/09/2026, no PostgreSQL local do Docker. Foram executadas
somente consultas de leitura. O pipeline, suas tabelas e o dashboard não foram
alterados. O notebook de referência está em Downloads/3_analise.ipynb.

## Critérios aplicados

- Somente viagens com `situacao = 'Realizada'`.
- Custo líquido = diárias + passagens + outros gastos − devolução.
- Pergunta 1 agrupada por órgão superior, não órgão solicitante.
- Destinos considerados pelo texto completo, com pelo menos 100 viagens.
- Duração inclusiva: data final − inicial + 1.
- Categoria de transporte `Inválido` mantida para reproduzir a referência.
- Média de pagamentos = soma dos valores / quantidade de pagamentos.
- Pagadores e trechos associados à viagem pelo identificador original.

## Resultados

As listas completas retornadas coincidem com as saídas gravadas no notebook:
5 órgãos, 3 destinos, 5 viagens mais longas, 4 tipos de pagamento, 8 meios de
transporte, 10 UFs e 5 órgãos pagadores, usando os ajustes de leitura abaixo.

| Pergunta | Resultado principal reproduzido |
|---|---|
| 1. Maior custo por órgão superior | Ministério da Justiça e Segurança Pública: R$ 485.748.241,43 |
| 2. Maior média por destino | Brasília/DF, Brasília/DF: 283 viagens, R$ 27.401,80 |
| 3. Maior duração | Viagem 0000000000020699856: 384 dias, R$ 0,00 |
| 4. Maior média por tipo de pagamento | DIÁRIAS: 400.364 pagamentos, R$ 2.078,79 |
| 5. Transporte mais usado | Veículo Oficial: 385.734 de 755.885 trechos |
| 6. UF mais frequente | São Paulo: 81.727 trechos |
| 7. Maior órgão pagador | Fundo Nacional de Segurança Pública: R$ 278.288.685,42 |

## Ajustes usados somente nas consultas da conferência

A Silver atual calcula duração como data final − inicial. A consulta da pergunta
3 acrescentou um dia; nenhuma duração gravada foi modificada.

A Silver atual rejeita transporte `Inválido`. Para as perguntas 5 e 6, os trechos
originais foram lidos da Raw e relacionados às viagens realizadas da Silver.
Isso recuperou 26.523 trechos `Inválido` de viagens realizadas. O total de 26.659
rejeitados da carga inclui também outras situações de viagem.

Sem essa recuperação, a Silver atual tem 729.362 trechos de viagens realizadas.
Veículo Oficial continua com 385.734 trechos, mas sua participação muda porque
o denominador é menor. São Paulo tem 80.255 trechos na Silver atual, contra
81.727 na referência. As dez UFs permanecem na mesma ordem.

## Conferências adicionais

- Datas de emissão NULL na Silver: 664.
- Soma dos pagamentos Raw: R$ 1.194.365.457,37.
- Soma dos pagamentos Silver: R$ 1.194.365.457,37.
- Agrupamento esperado de pagamentos: 655 linhas.
- Agrupamento esperado de trechos, incluindo `Inválido`: 201 linhas.

As contagens 655 e 201 foram reproduzidas com consultas de agrupamento; as duas
tabelas e suas views da referência não foram criadas. A Gold atual continua
sendo `gold.resumo_orgao_mes`. Portanto, a conferência demonstra equivalência
dos resultados sob os mesmos critérios, não equivalência da implementação
atual ou do dashboard com o notebook.

Resultados completos: `data/comparacao_notebook.json`.
Consultas reproduzíveis: `data/conferir_notebook.py`.
