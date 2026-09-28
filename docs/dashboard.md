# Dashboard — execução e leitura

## Abrir localmente

Com PostgreSQL disponível e as etapas Raw, Silver e Gold concluídas:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app/app.py
```

Acesse `http://localhost:8501`. O painel consulta apenas a tabela
`gold.resumo_orgao_mes`; não executa cargas nem modifica os dados.

Para executar pelo Docker Compose:

```powershell
docker compose up -d --build app
```

O caminho de entrada no Dockerfile e no Compose é `app/app.py`. O serviço recebe
as credenciais pelas variáveis do Compose. O `.env` local não deve ser publicado.

## Filtros e atualização

- O intervalo representa meses completos de início da viagem, conforme o grão da Gold.
- O seletor de órgãos usa código e nome do órgão solicitante. Sem seleção, inclui todos.
- Os filtros de mês e órgão afetam indicadores, gráficos, tabelas e respostas.
- O mínimo de viagens afeta somente o ranking da pergunta 3; não altera os KPIs.
- Dados consultados ficam em cache por até cinco minutos. “Atualizar dados” refaz
  a consulta à Gold; não reexecuta a transformação das camadas anteriores.
- A data exibida é a hora da consulta do painel, não a hora de atualização da fonte.

## Perguntas e visualizações

1. **Quais órgãos concentram o maior valor líquido?** Barras horizontais dos dez
   maiores grupos do recorte, acompanhadas de total, volume e participação do líder.
2. **Como variam volume e valor por mês de início?** Dois gráficos de barras,
   com eixos e unidades próprios, e uma tabela mensal. Meses sem registros para
   a seleção não aparecem como se fossem observações medidas.
3. **Quais órgãos têm maior média por viagem?** Barras horizontais dos dez
   maiores valores médios elegíveis e tabela com a quantidade de viagens.

Cada gráfico tem título, eixos nomeados, unidade, legenda e tooltip. Os rankings
incluem no máximo dez órgãos para manter a leitura; a tabela completa fica ao
final. Nomes longos são abreviados no eixo, com código e nome completo disponíveis
no tooltip e na tabela. As barras têm origem em zero e aceitam valores negativos.

As médias são calculadas por soma do valor líquido dividida pela quantidade de
viagens; médias mensais não recebem pesos iguais. Os cálculos monetários usam
Decimal, e a conversão para float ocorre somente na apresentação gráfica.
Valores completos em reais são exibidos nos indicadores, tabelas e tooltips.

O painel usa o valor líquido da entidade viagem e não adiciona pagamentos nem
passagens novamente. Não disponibiliza filtro por UF, porque a Gold não atribui
os custos de uma viagem a cada destino. Uma divisão desse tipo exigiria uma regra
explícita de alocação para evitar duplicar o custo de viagens com vários destinos.

## Limitações e auditoria

O painel mantém os órgãos sem identificação e sinaliza os trechos rejeitados
vinculados às viagens selecionadas. As viagens continuam presentes nos indicadores
financeiros mesmo quando possuem trechos rejeitados. Todas as situações aceitas
na Silver são incluídas. Valores maiores não demonstram desperdício: duração,
finalidade e destinos precisam ser considerados na interpretação.

Os resultados de referência e sua análise estão em
[validacao_gold.md](validacao_gold.md). As perguntas do protótipo antigo que
exigiam consultas incompatíveis com a Silver foram substituídas pelas três
perguntas documentadas da Gold. O painel não exibe dados pessoais de viajantes.

A implementação usa recursos nativos do Streamlit e gráficos Altair. A documentação
local da skill Streamlit foi consultada como referência de API e práticas; as
consultas, cálculos e interface foram desenvolvidos para o modelo deste projeto,
sem copiar um aplicativo de exemplo.
