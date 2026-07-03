Pré-requisitos:

- Python 3.10+ (Certifique-se de marcar a opção "Add Python to PATH" durante a instalação)
- Sistema Operacional Windows


Como Instalar e Usar:

1. Crie uma pasta dedicada para os arquivos e extraia o conteúdo do arquivo comprimido (.Zip/.Rar) nela.
2. Execute (clique duplo) o arquivo "install_requirements.bat" para instalar as dependências necessárias (customtkinter, mitmproxy e Pillow).
3. Execute "run_peeker_gui.bat" para abrir a interface gráfica do Painel.


Registrar o Certificado HTTPS (Obrigatório apenas na primeira vez):

Para que o programa possa ler as recompensas do jogo (que trafegam por HTTPS criptografado), você precisa instalar o certificado de segurança:
1. Com a interface gráfica aberta na aba "Dashboard", clique em "Trust CA Certificate" (o painel tentará automatizar a instalação para você).
2. Se aparecer uma tela azul do Windows ou um aviso de segurança perguntando se deseja instalar o certificado de autoridade do "mitmproxy", confirme e aceite (clique em Sim).
3. Uma vez concluído, feche o Painel GUI por completo (isto é necessário para aplicar as alterações).


Como Funciona o Fluxo de Uso (Tudo pela GUI):

1. Abra o painel executando o "run_peeker_gui.bat".
2. Na aba "Dashboard", no painel "Proxy Controller", clique em "Start Peeker Proxy". O status mudará para "Running".
3. Abra o jogo TaskbarHero e mude de fase (ou entre em um estágio) para registrar o peeker.
4. A partir desse momento, os scans começarão a ser detectados e exibidos em tempo real na interface!

Abas Disponíveis e Novidades:

- Dashboard:
  * Alerta de Alvo: Banner no topo que acende com a cor do item encontrado e mostra a sprite (ícone) do item monitorado.
  * Upcoming Important Drops: Cartões com layout fixo que mostram em tempo real os itens de alta raridade (Immortal, Legendary, etc.) da pool atual com seus respectivos ícones de itens e baús.
  * Next Valuable Drop: Exibe o nome, a cor de raridade e o ícone do drop mais valioso do scan atual.
  * Session Telemetry: Estatísticas da sessão (Scans feitos, itens observados, alvos encontrados).
  * Proxy e Relogger: Controles para iniciar o proxy e o Auto-Relogger.

- Targets and Alerts:
  * Permite buscar itens pelo nome ou ID e adicioná-los à lista de monitoramento (Targets).
  * Novo: Agora você pode remover alvos individualmente selecionando-os no menu suspenso de remoção e clicando em "Remove Target", sem precisar limpar toda a lista.
  * Alertas visuais e sonoros serão ativados assim que um desses alvos aparecer nos scans.

- Grade Filters:
  * Filtre quais raridades gerais (ex: RARE, BEYOND, ARCANA) devem disparar o relogger.

- Session Telemetry:
  * Relatório detalhado dos drops observados na sessão com as cores de suas respectivas raridades.


Dica para Envio aos Amigos:
- Certifique-se de enviar a pasta contendo o arquivo "id_to_sprite.json", pois ele já contém o mapeamento de ícones de todos os 5.875 itens do jogo para carregar as imagens instantaneamente.
- A pasta "cache_sprites" também pode ser enviada para que eles não precisem baixar as imagens do site oficial no primeiro uso, mas caso ela não seja enviada, o aplicativo fará o download das sprites automaticamente sob demanda.


Possíveis Erros de Codificação / UTF-8 (Console/Windows):

Se algum dos seus amigos se deparar com erros de codificação ou "UnicodeDecodeError/UnicodeEncodeError" ao rodar os scripts, isso ocorre porque o Windows deles não está com o suporte UTF-8 global ativo. Para resolver:
1. Pressione as teclas "Win + R" no teclado para abrir o menu Executar.
2. Digite "intl.cpl" e pressione Enter (isso abrirá as configurações de Região).
3. Vá na aba "Administrativo".
4. Clique no botão "Alterar local do sistema..." (Change system locale...).
5. Marque a caixinha "Beta: Usar Unicode UTF-8 para suporte de linguagem mundial".
6. Clique em OK e reinicie o computador para aplicar as alterações.
