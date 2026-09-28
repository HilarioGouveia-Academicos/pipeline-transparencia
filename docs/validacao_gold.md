# Evidências da Fase 3 — Gold

Execução concluída em **28/09/2026 às 16:06 (America/Sao_Paulo)**.

## Validação técnica

- Comando: `python src/3_analise.py --repetir`, encerrado com código 0.
- Duas cargas verificadas, com **1.232 grupos** por mês de início e órgão solicitante.
- 17 totais aditivos e a maior duração conferidos diretamente contra a Silver.
- As duas cargas apresentaram a mesma assinatura SHA-256 do conteúdo ordenado:
  `f94c853e6648a30a4d245bc90efe6d5241b5d2ff665d80d7e1abeb2c9d9fff23`.
- **48 testes aprovados em 11,71 segundos**, com os três conjuntos de integração habilitados.
- Testes incluem múltiplos detalhes por viagem, ausência de detalhes, agrupamento por mês/código/nome, órgão ausente, reexecução e rollback após adulteração de totais.

Para repetir a suíte:

```powershell
$env:RUN_RAW_DB_TESTS="1"
$env:RUN_SILVER_DB_TESTS="1"
$env:RUN_GOLD_DB_TESTS="1"
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --tb=short tests/
```

## Totais conciliados

| Indicador | Total |
| --- | ---: |
| `viagens` | 341.860 |
| `viagens_urgentes` | 203.949 |
| `duracao_total_dias` | 2.414.119 |
| `valor_diarias` | 834.399.579,40 |
| `valor_passagens` | 355.012.672,10 |
| `valor_outros_gastos` | 5.040.158,99 |
| `valor_devolucao` | 6.307.679,36 |
| `valor_total_bruto` | 1.194.452.410,49 |
| `valor_total_liquido` | 1.188.144.731,13 |
| `pagamentos` | 606.916 |
| `valor_pagamentos` | 1.194.365.457,37 |
| `passagens` | 167.260 |
| `valor_passagens_detalhe` | 317.738.026,44 |
| `taxa_servico` | 1.541.726,68 |
| `trechos` | 736.690 |
| `numero_diarias_trechos` | 1.687.688,10 |
| `trechos_rejeitados` | 26.659 |

Maior duração: **383 dias**. O recorte é pelo início das viagens, que podem terminar depois de junho de 2025. A duração é a diferença entre datas; não foi limitada artificialmente ao semestre.

## Primeiras respostas de negócio

Resultados das consultas em [sql/5_perguntas_negocio.sql](../sql/5_perguntas_negocio.sql). Todas as referências a órgão nesta análise significam órgão solicitante. Valores líquidos seguem a definição da [modelagem](modelagem_gold.md).

### 1. Quais órgãos concentram o maior valor líquido?

| Órgão | Viagens | Valor líquido (R$) | Participação (%) |
| --- | ---: | ---: | ---: |
| Ministério da Justiça e Segurança Pública - Unidades com vínculo direto | 26.807 | 319.251.830,28 | 26,87 |
| Polícia Federal | 31.694 | 118.269.425,67 | 9,95 |
| Comando da Aeronáutica | 32.777 | 81.481.682,65 | 6,86 |
| Comando do Exército | 22.036 | 48.686.328,89 | 4,10 |
| Polícia Rodoviária Federal | 17.100 | 48.258.424,30 | 4,06 |

As unidades com vínculo direto do Ministério da Justiça e Segurança Pública concentram 26,87% do valor líquido, embora não liderem o número de viagens entre os órgãos apresentados. O total isolado não permite concluir eficiência ou irregularidade: finalidade, duração e destinos precisam ser analisados antes dessa interpretação.

### 2. Como o valor e o volume variam por mês de início?

| Mês | Viagens | Valor líquido (R$) | Média por viagem (R$) |
| --- | ---: | ---: | ---: |
| 2025-01 | 26.866 | 287.809.341,26 | 10.712,77 |
| 2025-02 | 44.808 | 118.565.376,52 | 2.646,08 |
| 2025-03 | 63.949 | 203.417.919,31 | 3.180,94 |
| 2025-04 | 61.391 | 168.147.181,21 | 2.738,95 |
| 2025-05 | 73.372 | 207.534.951,42 | 2.828,53 |
| 2025-06 | 71.474 | 202.669.961,41 | 2.835,58 |

Maio tem o maior volume (73.372 viagens), enquanto janeiro concentra o maior valor líquido (R$ 287.809.341,26) e a maior média (R$ 10.712,77). Essa diferença merece investigação por duração, órgão e destino. Não demonstra crescimento dos pagamentos em janeiro: os valores foram atribuídos ao mês em que a viagem começou.

### 3. Quais órgãos têm maior média por viagem?

| Órgão | Viagens | Média líquida por viagem (R$) |
| --- | ---: | ---: |
| Ministério das Relações Exteriores - Unidades com vínculo direto | 1.996 | 12.732,76 |
| Ministério da Justiça e Segurança Pública - Unidades com vínculo direto | 26.807 | 11.909,27 |
| Agência Nacional de Vigilância Sanitária | 1.425 | 11.027,45 |

As unidades com vínculo direto do Ministério das Relações Exteriores lideram a média, com 1.996 viagens. A média é ponderada pelo número de viagens, incluindo valores negativos e todas as situações aceitas na Silver. Diferenças de perfil das viagens não foram controladas; uma média maior não estabelece desperdício.

## Cobertura e limites

- A Gold representa 341.860 viagens iniciadas entre janeiro e junho de 2025.
- Os 26.659 trechos rejeitados continuam na auditoria e são contados separadamente. Não entram nos totais de trechos aceitos ou em suas diárias.
- Há 14.768 viagens com código de órgão `-1` e nome ausente, somando R$ 21.900.462,73 (1,84% do valor líquido). Esse grupo foi preservado.
- Pagamentos, valores da entidade viagem e detalhes de passagens não são somados entre si: têm definições e granularidades próprias.
- O arquivo local é a origem validada. A obtenção remota do ZIP continua pendente.
- Estas respostas ainda precisam ser acompanhadas de visualizações no dashboard para completar os critérios de dataviz da avaliação.
