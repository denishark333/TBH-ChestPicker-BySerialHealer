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


Novidades da Versão Recente (Integração Steam Market & Cores):

- Integração com a Steam Market (Preços em tempo real):
  * O painel agora busca em tempo real o último valor registrado dos itens na Steam Community Market (convertido para R$, usando a moeda BRL).
  * Exibição elegante em formato pipe (ex: "|  R$ 1,50" ou "|  N/A" para itens indisponíveis/não listados) ao lado do nome do item.
  * O card do "Next Valuable Drop" e todos os 6 cards do "Upcoming Important Drops" exibem preços de forma dinâmica e independente.
  * As fontes foram ampliadas para melhor legibilidade: nomes de itens em tamanho 15, preços em dourado e tamanho 17 (negrito).

- Cache Inteligente e Persistente (market_cache.json):
  * Para evitar bloqueios de IP (Rate Limiting) da Steam por excesso de requisições, as consultas são salvas no arquivo local "market_cache.json".
  * Aplicação de um cooldown incondicional de 12 horas. Se um item for verificado (seja com sucesso, sem valor, ou com erro de conexão), ele não consultará o servidor da Steam novamente pelas próximas 12 horas.

- Paleta de Cores Oficial (tbh.city):
  * Atualização de todas as cores de raridades do painel e do console com as paletas hexadecimais exatas do site oficial "tbh.city".
  * Correção das raridades "BEYOND" (ajustado de verde para rosa-pink) e "COSMIC" (ajustado de rosa para branco puro).


Abas Disponíveis:

- Dashboard:
  * Alerta de Alvo: Banner no topo que acende com a cor do item encontrado e mostra a sprite (ícone) do item monitorado.
  * Upcoming Important Drops: Cartões com layout fixo e preços que mostram em tempo real os itens de alta raridade da pool atual com seus respectivos ícones de itens e baús.
  * Next Valuable Drop: Exibe o nome (sem o sufixo de raridade redundante), a cor oficial de raridade e o ícone do drop mais valioso do scan atual, acompanhado de seu preço de mercado.
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
- Envie também o arquivo "market_cache.json" se quiser compartilhar seu histórico de preços local já salvo.


Possíveis Erros de Codificação / UTF-8 (Console/Windows):

Ao se deparar com erros de codificação ou "UnicodeDecodeError/UnicodeEncodeError" ao rodar os scripts:
Isso ocorre porque o Windows não está com o suporte UTF-8 global ativo. Para resolver:

1. Pressione as teclas "Win + R" no teclado para abrir o menu Executar.
2. Digite "intl.cpl" e pressione Enter (isso abrirá as configurações de Região).
3. Vá na aba "Administrativo".
4. Clique no botão "Alterar local do sistema..." (Change system locale...).
5. Marque a caixinha "Beta: Usar Unicode UTF-8 para suporte de linguagem mundial".
6. Clique em OK e reinicie o computador para aplicar as alterações.
