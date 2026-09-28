# 📄 Software Design Document (SDD)

## Projeto: Pipeline de Dados - Portal da Transparência

---

## 1. Introdução

Este documento descreve a arquitetura, design e componentes do pipeline de dados construído para analisar viagens a serviço do Governo Federal. O objetivo é transformar dados brutos disponibilizados em CSVs em métricas confiáveis e visualizações interativas, seguindo a Arquitetura Medallion (Raw, Silver, Gold).

---

## 2. Objetivos

- Extrair dados brutos de arquivos CSV compactados.
- Transformar e limpar dados para padronização e consistência.
- Carregar dados em camadas estruturadas (Raw, Silver, Gold).
- Disponibilizar métricas e dashboards interativos via Streamlit.
- Garantir replicabilidade com Docker e documentação clara.

---

## 3. Arquitetura do Sistema

### 3.1 Diagrama Medallion

[RAW] → [SILVER] → [GOLD] → [Dashboard Streamlit]

- **RAW**: Dados brutos, sem tratamento.
- **SILVER**: Dados limpos, tipados e integrados.
- **GOLD**: Métricas e KPIs prontos para análise.
- **Dashboard**: Visualização interativa para usuários finais.

### 3.2 Componentes

- **Banco de Dados**: PostgreSQL 15.
- **Scripts ETL**:
  - `1_extrair.py` → ingestão dos CSVs.
  - `2_transformar.py` → limpeza e transformação.
  - `3_analise.py` → geração de métricas.
- **Dashboard**: `app.py` com Streamlit + Plotly.
- **Infraestrutura**: Docker + docker-compose.

---

## 4. Design Detalhado

### 4.1 Banco de Dados

- **Schema RAW**: tabelas correspondentes aos CSVs originais.
- **Schema SILVER**: tabelas com dados tipados e colunas derivadas.
- **Schema GOLD**: tabelas de métricas e agregações.

### 4.2 Scripts

- **banco.py**: abstração de conexão e execução com psycopg2.
- **config.py**: centralização de parâmetros (.env).
- **ETL**:
  - Extração em blocos (`chunksize`) para eficiência.
  - Transformação com pandas (datas, valores, colunas derivadas).
  - Inserção em lote (`executemany`) para performance.

### 4.3 Dashboard

- **Filtros interativos**: órgão, UF, período.
- **Gráficos fixos**: 7 métricas originais (Top órgãos, destinos, viagem mais longa, etc.).
- **Gráficos dinâmicos**: custo por órgão, custo médio por destino, distribuição por UF.

---

## 5. Tecnologias

- **Python 3.11.9** (versão recomendada).
- **PostgreSQL 15**.
- **Streamlit 1.30+**.
- **Pandas 2.0+**.
- **Plotly 5.18+**.
- **Docker Compose 3.9**.

---

## 6. Testes

### 6.1 Testes de Fumaça

- Conexão ao banco.
- Existência das tabelas principais.
- Execução de consultas básicas.
- Inicialização do dashboard.

### 6.2 Execução

- Execute os testes:

  ```bash

  pytest -q tests/

---

## 7. Deploy

### 7.1 Docker Compose

Serviço db: PostgreSQL.

Serviço app: Streamlit + pipeline.

Volume persistente para dados do banco.

### 7.2 Comandos

- Comando:

  ```bash

   docker-compose up --build
   docker-compose down

---

## 8. Futuras Melhorias

Orquestração com Airflow ou Prefect.

Testes unitários e integração contínua (CI/CD).

Filtros avançados no dashboard (multiselect).

Integração com APIs oficiais para dados em tempo real.

---

## 9. Dicionário de Dados

### 9.1 Camada RAW

Dados brutos importados diretamente dos arquivos CSV do Portal da Transparência.

#### Tabela: raw_viagem

| Coluna              | Tipo        | Descrição                                   |
|---------------------|-------------|---------------------------------------------|
| id_viagem           | SERIAL PK   | Identificador único da viagem                |
| nome_viajante       | TEXT        | Nome do servidor que realizou a viagem       |
| orgao_superior      | TEXT        | Órgão superior responsável                   |
| orgao_pagador       | TEXT        | Órgão que realizou o pagamento               |
| destino             | TEXT        | Destino(s) da viagem                         |
| destino_uf          | TEXT        | Unidade Federativa do destino                |
| data_inicio         | TEXT        | Data de início (formato original CSV)        |
| data_fim            | TEXT        | Data de término (formato original CSV)       |
| valor_total         | TEXT        | Valor total da viagem (formato original CSV) |

---

### 9.2 Camada SILVER

Dados limpos, tipados e enriquecidos para análises consistentes.

#### Tabela: silver_passagem

| Coluna              | Tipo        | Descrição                                   |
|---------------------|-------------|---------------------------------------------|
| id_passagem         | SERIAL PK   | Identificador único da passagem              |
| nome_viajante       | TEXT        | Nome do servidor                            |
| nome_orgao_superior | TEXT        | Órgão superior responsável                   |
| destinos            | TEXT        | Destino(s) da viagem                         |
| destino_uf          | TEXT        | Unidade Federativa do destino                |
| data_inicio         | DATE        | Data de início da viagem                     |
| data_fim            | DATE        | Data de término da viagem                    |
| duracao_dias        | INTEGER     | Duração da viagem em dias                    |
| valor_total         | NUMERIC     | Valor total da passagem                      |

#### Tabela: silver_pagamento

| Coluna              | Tipo        | Descrição                                   |
|---------------------|-------------|---------------------------------------------|
| id_pagamento        | SERIAL PK   | Identificador único do pagamento             |
| nome_orgao_pagador  | TEXT        | Órgão que realizou o pagamento               |
| tipo_pagamento      | TEXT        | Forma de pagamento utilizada                 |
| valor               | NUMERIC     | Valor pago                                  |

#### Tabela: silver_trecho

| Coluna              | Tipo        | Descrição                                   |
|---------------------|-------------|---------------------------------------------|
| id_trecho           | SERIAL PK   | Identificador único do trecho                |
| meio_transporte     | TEXT        | Meio de transporte utilizado                 |
| destino_uf          | TEXT        | Unidade Federativa de destino                |

---

### 9.3 Camada GOLD

Métricas e KPIs derivados das tabelas SILVER, prontos para visualização.

#### Tabela: gold_metricas

| Coluna              | Tipo        | Descrição                                   |
|---------------------|-------------|---------------------------------------------|
| orgao_superior      | TEXT        | Órgão superior analisado                     |
| custo_total         | NUMERIC     | Soma dos valores de viagens                  |
| custo_medio_destino | NUMERIC     | Média de custo por destino                   |
| viagem_mais_longa   | TEXT        | Nome do viajante com maior duração           |
| dias_viagem         | INTEGER     | Duração da viagem mais longa                 |
| tipo_pagamento_caro | TEXT        | Tipo de pagamento com maior valor médio      |
| meio_transporte_top | TEXT        | Meio de transporte mais utilizado            |
| uf_frequente        | TEXT        | UF mais frequente como destino               |
| orgao_pagador_top   | TEXT        | Órgão que mais pagou no total                |

---

### Observações

- **RAW**: mantém dados originais para rastreabilidade.
- **SILVER**: garante integridade e consistência (tipagem, datas, valores).
- **GOLD**: agrega e sintetiza informações para análise e dashboards.

---

## 10. Conclusão

O pipeline garante transparência e confiabilidade na análise de viagens a serviço do Governo Federal. A arquitetura modular e containerizada facilita manutenção, replicação e evolução futura.
