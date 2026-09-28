# Validação da Fase 1 — Extração e Raw

Executada em 2026-09-28T14:42:32-03:00.

## Resultado

- Duas cargas completas executadas com `python src/1_extrair.py --repetir`.
- Contagens e assinaturas de conteúdo conferidas com a fonte após cada carga.
- 10 testes de extração/limpeza passaram; o teste de integração também passou.
- O teste de integração verificou reexecução e rollback após falha simulada, em banco temporário isolado.
- PostgreSQL iniciado pelo serviço `db` do Docker Compose.

| Tabela | Registros em cada carga |
| --- | ---: |
| raw.raw_viagem | 341.860 |
| raw.raw_pagamento | 606.916 |
| raw.raw_passagem | 167.260 |
| raw.raw_trecho | 763.349 |

Total por carga: **1.879.385 registros**.

## Rastreabilidade

ZIP local: `viagens_2025_6meses.zip`.

SHA-256: `198855840f73e1570869a05a79144e7469f5249b5a1405c535456fee0d6798b0`.

O relatório detalhado está em `data/relatorio_raw.json` (arquivo local ignorado pelo Git).
As assinaturas somam hashes SHA-256 das linhas, incluindo a multiplicidade de registros iguais e sem depender da ordem da consulta.

## Limites desta validação

- Foi usado o ZIP local existente. O download real do Google Drive e a identidade com o arquivo remoto não foram verificados.
- Silver, Gold e dashboard não foram executados nesta entrega. Eles ainda precisam ser adaptados aos campos originais preservados na Raw.
- Os dados brutos permanecem no diretório local e no volume do PostgreSQL; não foram publicados no GitHub.
