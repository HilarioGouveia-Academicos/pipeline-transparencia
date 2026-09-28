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

**Escopo:** esta entrega valida a Raw. Os scripts Silver/Gold e o dashboard ainda
precisam ser adaptados ao contrato fiel dos CSVs; não estão validados como fluxo completo.
A documentação de arquitetura abaixo descreve o objetivo das fases seguintes.

---

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_extracao.py tests/test_transformacao.py
```

Os testes de extração cobrem preservação de valores, leitura em blocos,
CSV ausente, linhas com quantidade incorreta de campos, valores NUL,
assinaturas que preservam duplicatas e rejeição de download HTML.
Para verificar transação e rollback em um banco temporário isolado:

```powershell
$env:RUN_RAW_DB_TESTS="1"
.\.venv\Scripts\python.exe -m pytest -q tests/test_raw_integracao.py
Remove-Item Env:RUN_RAW_DB_TESTS
```

Esse teste exige permissão de criar banco no PostgreSQL e remove somente o banco
temporário que ele próprio criou. Verifica duas cargas e restauração do conteúdo
anterior quando a conferência final falha.

Os testes de conexão e de existência de Silver/Gold exigem PostgreSQL e as
fases seguintes preparadas; não são o aceite isolado da Fase 1.

## Próximas fases

- Adaptar a Silver aos cabeçalhos originais e relacionar os quatro arquivos pelo
  identificador do processo de viagem.
- Corrigir as regras das métricas Gold e integrar o dashboard.
- Documentar respostas de negócio com resultados efetivamente executados.
- Versionar os arquivos e registrar a evolução por funcionalidade.
