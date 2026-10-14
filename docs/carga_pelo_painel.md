# Carga pelo painel

Na barra lateral, abra **Carregar dados do projeto**, confira o ID do ZIP do
curso no Google Drive, marque a confirmação e clique em **Carregar dados**.
O ZIP deve estar disponível para download público. O campo recebe o ID do
arquivo, não a URL ou o ID de uma pasta. O ID inicial é o mesmo da configuração
de exemplo do projeto.

O app cria as tabelas usando `sql/0_criar_banco.sql` e executa os scripts
`src/1_extrair.py`, `src/2_transformar.py` e `src/3_analise.py` em sequência.
As credenciais `POSTGRES_*` dos Secrets são usadas também pelos scripts.
Uma execução substitui os dados das camadas Raw, Silver e Gold; cada etapa
mantém sua própria transação e verificação. Uma falha interrompe a sequência,
mas não desfaz as etapas já confirmadas. A Gold anterior permanece disponível
até a conclusão da sua nova carga.

A interface mostra a etapa em andamento e atualiza o painel após o sucesso.
Em caso de falha, oferece os logs das etapas para download. Eles e os relatórios
JSON ficam em `data/`, no servidor do app. Arquivos locais podem desaparecer
quando o Streamlit Cloud recria a máquina; os dados persistem no PostgreSQL.

Um bloqueio no PostgreSQL impede cargas simultâneas iniciadas pelo botão.
Ele não coordena scripts iniciados manualmente fora do app. Mantenha o app
aberto durante a execução. Reiniciar o servidor interrompe a carga; ela também
depende da memória, disco, tempo de execução e espaço disponíveis nos serviços.

A confirmação não autentica o visitante: quem tiver acesso ao app pode usar
essa ação. Para uma operação restrita ao responsável, restrinja o acesso ao app.
