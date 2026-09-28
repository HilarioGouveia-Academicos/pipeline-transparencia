# Documento de arquitetura — Pipeline de viagens

## Objetivo e estado das entregas

Organizar o conjunto de viagens fornecido pelo curso, referente a um recorte de
seis meses de 2025, preservando a fonte e produzindo dados relacionais auditáveis.

| Camada | Responsabilidade | Implementação |
| --- | --- | --- |
| Raw | Preservar os quatro CSVs integralmente | `src/1_extrair.py`, `sql/1_criar_raw.sql` |
| Silver | Converter, relacionar e registrar rejeições | `src/2_transformar.py`, `src/silver.py`, `sql/2_criar_silver.sql` |
| Gold | Agregar métricas de negócio | Próxima etapa; o script legado ainda precisa ser adaptado |
| Dashboard | Exibir resultados e gráficos | Próxima etapa; a versão inicial ainda precisa ser adaptada |

## Fluxo

ZIP do curso → quatro tabelas Raw → quatro entidades Silver + rejeições → Gold → dashboard.

A Raw mantém todos os campos em texto. O cabeçalho original está em `src/raw_layout.json`.
A Silver preserva o vínculo com cada linha de origem por hash e ocorrência, convertendo
campos pelo mapeamento explícito em `src/silver_layout.json`.

Viagens são a entidade principal. Pagamentos, passagens e trechos referenciam a PK
original da viagem por FKs obrigatórias. Não há preenchimento fixo de transporte ou
categoria de pagamento. Registros rejeitados preservam os valores brutos em JSONB.

A modelagem vigente, os critérios de rejeição e o dicionário completo estão em
[modelagem_silver.md](docs/modelagem_silver.md). O arquivo `sql/0_criar_banco.sql`
reúne as estruturas atuais e a tabela Gold inicial; não é uma migração automática
para instalações com versões anteriores das tabelas.

## Integridade e reexecução

Cada fase usa TRUNCATE e recarga numa transação. Falhas desfazem a tentativa corrente.
A Silver lê uma visão consistente da Raw em REPEATABLE READ e reconcilia contagens,
valores numéricos e proveniência antes do commit. Datas inválidas e valores não
conversíveis são identificados; não são substituídos silenciosamente por zero.

Os relatórios locais em `data/` registram contagens, assinaturas e cargas verificadas.
A documentação de validação em `docs/` registra as evidências das entregas.

## Ambiente

Python 3.11+, PostgreSQL 15 e Docker Compose. O serviço `db` pode ser iniciado
independentemente do dashboard. Credenciais ficam no `.env` local; `.env.example`
contém somente exemplos. ZIPs, CSVs e dados de auditoria não são enviados ao Git.

As instruções de execução e testes estão no [README](README.md).
