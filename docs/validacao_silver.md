# Evidências da Fase 2 — Silver

Validação concluída em **28/09/2026 às 15:54 (America/Sao_Paulo)**, com PostgreSQL 15.

## Carga e reexecução

Comando: `python src/2_transformar.py --repetir`.

O processo terminou com código 0. O relatório local `data/relatorio_silver.json` registrou duas cargas verificadas, com contagens, motivos, totais e assinaturas do conteúdo tipado iguais.

| Entidade | Raw | Aceitos | Rejeitados |
| --- | ---: | ---: | ---: |
| viagem | 341.860 | 341.860 | 0 |
| pagamento | 606.916 | 606.916 | 0 |
| passagem | 167.260 | 167.260 | 0 |
| trecho | 763.349 | 736.690 | 26.659 |

**Total:** 1.879.385 registros de origem, 1.852.726 aceitos e 26.659 rejeitados.

Todos os rejeitados são trechos com motivo `meio_transporte:transporte_invalido`: a fonte informa transporte “Inválido”. Os valores originais e motivos permanecem em `silver.rejeitados`. Essa exclusão deve ser considerada nas análises dos trechos aceitos.

## Reconciliação numérica

Consultas independentes sobre a Raw, com conversão diretamente no PostgreSQL, confirmaram os oito totais abaixo. Origem = aceitos + rejeitados em todos os campos. Não houve números ausentes ou impossíveis de converter nesta fonte. Valores usam ponto decimal nesta tabela; `numero_diarias` representa quantidade e os demais campos representam reais.

| Entidade / campo | Origem | Aceitos | Rejeitados |
| --- | ---: | ---: | ---: |
| viagem / valor_diarias | 834399579.40 | 834399579.40 | 0 |
| viagem / valor_passagens | 355012672.10 | 355012672.10 | 0 |
| viagem / valor_devolucao | 6307679.36 | 6307679.36 | 0 |
| viagem / valor_outros_gastos | 5040158.99 | 5040158.99 | 0 |
| pagamento / valor | 1194365457.37 | 1194365457.37 | 0 |
| passagem / valor_passagem | 317738026.44 | 317738026.44 | 0 |
| passagem / taxa_servico | 1541726.68 | 1541726.68 | 0 |
| trecho / numero_diarias | 1728368.60 | 1687688.10 | 40680.50 |

As entidades têm granularidades diferentes. Seus valores não devem ser somados entre si como se representassem despesas distintas.

As contagens e assinaturas de origem coincidem com o relatório da [Raw da Fase 1](validacao_raw.md). A proveniência inclui registros repetidos e rejeitados.

## Assinaturas do conteúdo Silver

Soma modular dos hashes SHA-256 das linhas tipadas serializadas, igual nas duas cargas:

| Entidade | Assinatura |
| --- | --- |
| viagem | `6c9fabbc487b839120b0f310e3daeb1e1bfe19911bcd9d530aae329951b225f4` |
| pagamento | `4446d8dde95582f7e5f574041db78bb66f0a053b837a0bf5cd8546ebb70dc7fe` |
| passagem | `6797fc628c75c7bd124cc23d6dc54252c0f5031d6e1f2be00b6b208f76f4a690` |
| trecho | `543e1a8adc162b9fda579d94c1af3c2b6f1cb19c33081d3492e69349a476cdc3` |

## Testes

```powershell
$env:RUN_RAW_DB_TESTS="1"
$env:RUN_SILVER_DB_TESTS="1"
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --tb=short tests/
```

**45 testes aprovados em 43,32 segundos.** A suíte cobre conversões, extração, PK, FK, constraints, rejeições, duplicatas, reexecução e rollback. Os testes de falha confirmam a preservação da carga anterior após divergência de reconciliação ou erro ao fim da transação.

## Escopo

Consulte a [modelagem e as regras da Silver](modelagem_silver.md). Gold, gráficos e respostas de negócio são as próximas entregas. O download remoto do ZIP continua pendente de validação: esta execução usou a origem local da Fase 1.
