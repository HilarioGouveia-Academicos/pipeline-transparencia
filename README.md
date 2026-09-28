# 🚀 Pipeline de Dados - Portal da Transparência

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)
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

## ▶️ Primeira entrega: Extração e Raw

A Fase 1 usa exclusivamente o ZIP de seis meses de 2025 fornecido pelo curso:
[pasta no Google Drive](https://drive.google.com/drive/folders/1J_0kDNI_2p3wHtmgbiwTpGD744beMvdL?usp=sharing).
O arquivo local esperado é `data/viagens_2025_6meses.zip`. A equivalência com o
arquivo remoto deve ser confirmada pelo responsável pela obtenção dos dados.
Não há fallback para o conjunto anual do Portal.

**Validação executada:** duas cargas completas, com 1.879.385 registros em cada uma.
Consulte [a evidência da Fase 1](docs/validacao_raw.md).

### Preparação (PowerShell, na raiz do projeto)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# Apenas se .env ainda não existir:
Copy-Item .env.example .env
```

Preencha as credenciais no `.env`. Os caminhos relativos de `ZIP_DADOS` são
resolvidos a partir da raiz do projeto. Se o ZIP não estiver disponível localmente,
configure `DRIVE_FILE_ID` com o ID do **arquivo ZIP**, não o ID da pasta.
O download exige acesso direto ao arquivo: respostas HTML de login ou confirmação
são rejeitadas. Não se presume que o arquivo baixado seja um ZIP válido.

### Validação sem banco

```powershell
.\.venv\Scripts\python.exe src/1_extrair.py --validar-apenas
.\.venv\Scripts\python.exe -m pytest -q tests/test_extracao.py
```

A validação percorre todos os registros dos quatro CSVs, verifica cabeçalhos,
quantidade de campos e integridade da leitura. Não descarta linhas inválidas.

### Carga e comprovação de reexecução

Com o Docker Desktop iniciado:

```powershell
docker compose up -d db
.\.venv\Scripts\python.exe src/1_extrair.py --repetir
```

Aguarde o PostgreSQL ficar saudável antes da carga. O script cria automaticamente
as quatro tabelas usando `sql/1_criar_raw.sql`. Em bancos com a estrutura antiga,
interrompe antes do TRUNCATE e solicita migração; não apaga tabelas incompatíveis.

`--repetir` executa duas cargas completas. Cada carga faz TRUNCATE e insere os
quatro CSVs em blocos, numa única transação. Qualquer falha desfaz a carga corrente.
Após inserir, compara contagens e assinaturas de todas as linhas com os CSVs,
incluindo a multiplicidade de registros iguais. Duplicatas já existentes na fonte
são preservadas; a reexecução não acrescenta cópias.

O resultado fica em `data/relatorio_raw.json`, com SHA-256 do ZIP, contagens,
assinaturas e número de cargas verificadas. `cargas_verificadas: 0` significa
somente validação da fonte; `2` comprova as duas cargas daquela execução.
Use `--relatorio caminho.json` para manter relatórios separados. Um relatório de
execução anterior não comprova uma tentativa que terminou com erro.

### Contrato da Raw

- `raw.raw_viagem`: 22 colunas originais.
- `raw.raw_pagamento`: 10 colunas originais.
- `raw.raw_passagem`: 19 colunas originais.
- `raw.raw_trecho`: 14 colunas originais.
- Todos os campos são TEXT; nomes originais constam em `src/raw_layout.json`.
- Espaços, zeros à esquerda, campos vazios, acentos e valores monetários textuais
  são preservados. Campos vazios permanecem strings vazias, sem conversão a NULL.
- Cabeçalhos com espaços e acentos devem ser referenciados entre aspas no SQL.
- Não há filtro adicional de datas nem limpeza nesta fase.

**Escopo da Fase 1:** valida a Raw. A transformação relacional está descrita na Fase 2 abaixo.
A Gold está descrita na Fase 3. O dashboard ainda precisa ser adaptado ao modelo atual.

---

## Fase 2 — Silver

A Silver mantém quatro entidades: viagens, pagamentos, passagens e trechos.
Os detalhes se relacionam diretamente ao identificador original da viagem.
Datas, horários, booleanos e números são convertidos explicitamente. Registros
inválidos ficam em `silver.rejeitados`, com valores originais e motivos.

Consulte [a modelagem, regras e dicionário da Silver](docs/modelagem_silver.md).

**Validada em 28/09/2026:** duas cargas completas com resultados iguais e
45 testes aprovados. Foram aceitos 1.852.726 registros e preservados na auditoria
26.659 trechos com transporte inválido. Veja as
[evidências e a reconciliação da Silver](docs/validacao_silver.md).

Com a Raw carregada:

```powershell
.\.venv\Scripts\python.exe src/2_transformar.py --repetir
```

O script cria as tabelas pelo `sql/2_criar_silver.sql`, carrega em blocos, verifica
contagens e valores aceitos/rejeitados e confirma a transação somente após a
reconciliação. A segunda carga também deve apresentar as mesmas assinaturas de
conteúdo. O relatório é salvo em `data/relatorio_silver.json`.

## Fase 3 — Gold

A tabela `gold.resumo_orgao_mes` agrega viagens por mês de início e órgão
solicitante. Pagamentos, passagens e trechos são agrupados por viagem antes dos
JOINs, evitando multiplicar os valores. A carga confere 17 totais e a maior
duração contra a Silver antes do commit.

```powershell
.\.venv\Scripts\python.exe src/3_analise.py --repetir
```

Consulte a [modelagem Gold](docs/modelagem_gold.md) e as
[consultas de negócio](sql/5_perguntas_negocio.sql). O relatório local fica em
`data/relatorio_gold.json`. A tabela antiga `gold.gold_metricas` não é atualizada.

**Validada em 28/09/2026:** duas cargas com 1.232 grupos e 48 testes aprovados.
Veja as [evidências e primeiras respostas de negócio](docs/validacao_gold.md).

## Testes

Testes de conversão e extração sem banco:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_extracao.py tests/test_transformacao.py
```

Com PostgreSQL e as fases Raw e Silver carregadas, execute também os testes de integridade,
idempotência, rejeições, constraints e rollback:

```powershell
$env:RUN_RAW_DB_TESTS="1"
$env:RUN_SILVER_DB_TESTS="1"
$env:RUN_GOLD_DB_TESTS="1"
.\.venv\Scripts\python.exe -m pytest -q tests/
Remove-Item Env:RUN_RAW_DB_TESTS, Env:RUN_SILVER_DB_TESTS, Env:RUN_GOLD_DB_TESTS
```

Os testes de integração criam e removem somente seus próprios bancos temporários.
Os testes de fumaça verificam o banco configurado e as camadas entregues: Raw e Silver.

## Próximas fases

- Adaptar o dashboard e documentar respostas de negócio com resultados e gráficos.
- Validar o download remoto do ZIP; as cargas anteriores usaram o arquivo local.
