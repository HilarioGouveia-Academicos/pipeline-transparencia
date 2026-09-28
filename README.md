# 🚀 Pipeline de Dados - Portal da Transparência

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red?logo=streamlit)
![Status](https://img.shields.io/badge/Status-MVP-green)

---

## 📌 Problema que resolve

Os dados de viagens a serviço do Governo Federal são disponibilizados em formato bruto (CSVs), sem limpeza ou organização. Isso dificulta análises confiáveis e a tomada de decisão.  
Este projeto resolve esse problema construindo um **pipeline de dados completo** que transforma dados brutos em métricas e gráficos claros, seguindo a **Arquitetura Medallion (Raw, Silver, Gold)**.

---

## 🛠️ Técnicas e Tecnologias Utilizadas

- **Python (pandas, psycopg2, plotly)** → extração, transformação e análise.
- **PostgreSQL** → armazenamento estruturado com integridade referencial.
- **Streamlit** → visualização interativa dos resultados.
- **Docker + docker-compose** → ambiente containerizado e replicável.
- **Arquitetura Medallion** → organização em camadas (Raw, Silver, Gold).

---

## 🧩 Arquitetura Medallion

A arquitetura Medallion organiza o pipeline em três camadas principais, garantindo rastreabilidade e qualidade dos dados:

![Arquitetura Medallion Pipeline](https://copilot.microsoft.com/th/id/BCO.54b33819-3ece-48f8-a0cb-8e0e4cda7a70.png)

**Fluxo resumido:**

1. **RAW** → Área de *staging* com dados brutos, sem tratamento.
2. **SILVER** → Dados limpos, tipados e integrados.
3. **GOLD** → Métricas, KPIs e dashboards para análise.

---

## ▶️ Como Executar

1. Clone o repositório:

   ```bash
   git clone https://github.com/seu-repo/pipeline-transparencia.git
   cd pipeline-transparencia

2. Configure o arquivo .env com suas credenciais:

   ```bash
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=sua_senha
   POSTGRES_DATABASE=transparencia
   ANO=2025
   APP_PORT=8501

3. Suba os containers:

   ```bash
   docker-compose up --build

4. Execute o pipeline:

   ```bash
   python 1_extrair.py → carrega CSVs na camada Raw.

   python 2_transformar.py → limpa e tipa dados na Silver.

   python 3_analise.py → gera métricas e gráficos na Gold.

5. Acesse o dashboard:

   👉 http://localhost:8501 (localhost in Bing)

---

## 🧪 Testes de Fumaça

Este projeto inclui testes de fumaça para garantir que os componentes principais estão funcionando:

- Conexão ao banco de dados PostgreSQL
- Existência das tabelas RAW e SILVER
- Execução de consultas básicas
- Inicialização do dashboard Streamlit

### ▶️ Como rodar os testes

- Execute os testes:

  ```bash
  pytest -q tests/

---

## 🔧 Possíveis Melhorias

- Automatizar o pipeline com Airflow ou Prefect.

- Criar agendamento para atualização contínua dos dados.

- Adicionar testes unitários para funções de transformação.

- Expandir o dashboard com filtros interativos (órgão, UF, período).

- Integrar com APIs oficiais para dados em tempo real.

---

## 📊 Conclusões e Insights

A partir dos gráficos e análises, é possível observar:

- Órgãos com maior custo total → ajudam a identificar onde estão os maiores gastos.

- Destinos com maior custo médio → revelam padrões de viagens mais caras.

- Viagem mais longa e seu custo → útil para auditoria e planejamento.

- Tipo de pagamento mais caro → mostra práticas financeiras que podem ser otimizadas.

- Meio de transporte mais usado → indica tendências logísticas.

- UF mais frequente → revela destinos prioritários.

- Órgão que mais pagou no total → evidencia concentração de despesas.

Esses insights tornam os dados acessíveis e confiáveis para gestores e cidadãos, promovendo transparência e eficiência.
