# Operação do dashboard Gold

Implementação da [especificação aprovada](especificacao_dashboard_gold.md).
Resultados da base completa em [Validação do dashboard Gold](validacao_dashboard_gold.md).
PostgreSQL permanece como banco. O painel lê apenas tabelas Gold e a informação
da última carga. As views de conferência leem Silver somente durante a validação.

## Atualizar a carga existente

Execute a transformação antes da nova Gold, para manter os trechos Inválido:

```powershell
.\.venv\Scripts\python.exe src/2_transformar.py
.\.venv\Scripts\python.exe src/3_analise.py
```

Se a Raw ainda não existir ou a fonte tiver mudado, execute primeiro
`src/1_extrair.py`. Todas as etapas usam o PostgreSQL configurado em `POSTGRES_*`.
A Gold antiga `resumo_orgao_mes` continua disponível; a nova materialização
não a exclui. A carga dos cinco novos conjuntos e seu relatório de conferência
é atômica, junto à atualização da Gold anterior. A ausência dos conjuntos ou
da carga validada é informada pelo app, sem apresentar resultados incompletos.

O módulo `src/gold_dashboard.py` define as consultas das views de referência e
cria as tabelas correspondentes durante a carga Python. Executar somente o SQL
antigo não materializa os conjuntos novos.

## Filtros e indicadores

Os três filtros ficam na barra lateral. O resumo do recorte aparece no painel.

- Período seleciona meses completos de início da viagem.
- Órgão seleciona órgão superior, inclusive valores ausentes.
- Situação começa em Realizada; limpar a seleção inclui todas as situações.
- Todos os indicadores, rankings, gráficos e exportações seguem os três filtros.
- O ranking adicional de média por viagem usa órgão superior.
- Duração da Gold inclui início e fim. A Silver mantém seu campo original
  de diferença de datas para compatibilidade.
- Trechos Inválido são mantidos. Outros erros de integridade ainda são auditados.

## Conexão de leitura

O painel aceita `DASHBOARD_POSTGRES_HOST`, `DASHBOARD_POSTGRES_PORT`,
`DASHBOARD_POSTGRES_USER`, `DASHBOARD_POSTGRES_PASSWORD` e
`DASHBOARD_POSTGRES_DATABASE`. Cada valor ausente usa seu correspondente
`POSTGRES_*`. As operações administrativas continuam usando `POSTGRES_*`.

O leitor precisa de USAGE no schema Gold e SELECT somente nestas tabelas:

```sql
GRANT USAGE ON SCHEMA gold TO leitor_gold;
GRANT SELECT ON gold.resumo_viagem_mes, gold.resumo_destino_mes,
    gold.gold_pagamento_resumo, gold.gold_trecho_resumo,
    gold.viagens_duracao, gold.carga_dashboard TO leitor_gold;
```

O responsável cria o usuário `leitor_gold` e sua senha fora desse exemplo.
Não conceder acesso às views de referência ao leitor. Os testes demonstram
que o dashboard consegue ler sem permissão para acessar Silver.

## Carga somente pelo terminal

Durante a implementação, o usuário escolheu **Somente carga pelo terminal,
sem login no app**. O dashboard não oferece botões de criação ou carga e não
executa operações administrativas. Não é necessário configurar OIDC.

O responsável executa os três scripts no ambiente de processamento. No app
publicado, configura as credenciais de leitura nos Secrets e usa Atualizar
dados após disponibilizar a nova Gold. As variáveis PostgreSQL ficam na raiz
do TOML, sem uma seção que impeça sua promoção a variáveis de ambiente.

## Armazenamento e publicação

A nova interface não resolve a falta de espaço da carga completa no Render de
1 GB. Raw e Silver continuam necessárias no ambiente de processamento. O
ambiente do dashboard pode receber somente as cinco tabelas materializadas e
`carga_dashboard`, sem suas views e sem Raw/Silver, e usar a conexão de leitura.
Isso exige uma transferência explícita dos resultados PostgreSQL e sua validação.
A implementação não apaga camadas no Render nem faz essa transferência automaticamente.

Se leitura e processamento usarem bancos distintos, os scripts de carga atuam
somente no banco `POSTGRES_*`; o responsável precisa transferir a Gold validada
ao banco de leitura antes de atualizar o painel. Não apontar as credenciais de
processamento para um banco com espaço insuficiente.

## Publicação no Render em 14/10/2026

As cinco tabelas materializadas e `carga_dashboard` foram importadas no Render
em uma transação. O conteúdo de cada tabela foi comparado com o banco local
antes do commit, incluindo contagens, assinaturas SHA-256 e totais financeiros.
O teste do dashboard consultando o Render passou com Realizada e Todas.

O banco do Render ocupa aproximadamente 589 MiB, incluindo a Raw que já existia.
A Silver local ocupa 1.188 MiB com índices e não cabe no limite informado de 1 GB.
O processamento permanece local; o painel pode funcionar somente com a Gold.

No Streamlit Cloud, selecionar a branch que contém esta implementação e o
arquivo principal `app/app.py`. Configurar os cinco valores `POSTGRES_*` do
Render na raiz dos Secrets, usando o host externo. As credenciais não pertencem
ao GitHub. Para atualizações posteriores, transferir a nova Gold de forma
atômica e validar o conteúdo antes de disponibilizá-la ao painel.
