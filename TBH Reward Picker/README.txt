TBH Reward Picker 2.5.6
========================

Um utilitário avançado e completo de automação e rastreamento de loot para TaskbarHero. Esta ferramenta utiliza monitoramento de arquivo de save (save-file) e interceptação de rede para rastrear o seu loot em tempo real, aliado a poderosas tarefas de automação de mouse para permitir um AFK farming 100% seguro.

--------------------------------------------------

1. INSTALAÇÃO E SETUP

Pré-requisitos:
- Python 3.10 ou superior instalado no computador.
- Certifique-se de marcar a opção "Add Python to PATH" durante a instalação.

Passo a Passo:
1. Extraia o conteúdo deste arquivo comprimido em uma pasta.
2. Execute (clique duplo) o arquivo "install_requirements.bat". (Você só precisa fazer isso uma vez para instalar as dependências).
3. Inicie o aplicativo clicando duas vezes em "run_peeker_gui.bat".

--------------------------------------------------

2. CONFIGURAÇÃO INICIAL (Obrigatório na primeira vez)

Ao abrir o aplicativo, você deve configurar duas coisas essenciais para que o utilitário rastreie o seu jogo:

Vincular o seu Arquivo de Save:
1. Vá até a "Save File Section" (Seção de Save File) no painel.
2. Clique no Texto Dourado (o campo do caminho do arquivo).
3. Cole o caminho da pasta de save do seu jogo no campo, ou clique em Browse (Navegar).
4. Selecione o arquivo chamado "SaveFile_Live.es3" e clique em OK.
(Este caminho ficará salvo para sempre).

Iniciando o Proxy (Interceptação de Rede):
- Toda vez que você abrir o Painel, você deve clicar explicitamente no botão verde "START PROXY" na tela principal para ele começar a ouvir as recompensas.

--------------------------------------------------

3. COMO CALIBRAR AS AUTOMAÇÕES (Stage Switcher e Auto-Stash)

Ambas as automações usam o seu Mouse para saber onde devem clicar na tela do jogo.

1. Vá até a aba "Settings" (Configurações).
2. Clique no botão "Calibrate Click 1" para a tarefa de automação que você deseja configurar.
3. Mova o seu mouse sobre o botão desejado na janela do jogo.
4. Dê um CLIQUE ESQUERDO para registrar a coordenada!
(Se quiser cancelar, basta dar um Clique Direito).

As coordenadas são salvas automaticamente. 
Atenção: Se você mover a janela do jogo de lugar no seu monitor, as coordenadas do mouse ficarão erradas e você precisará recalibrar!

--------------------------------------------------

4. DICA AVANÇADA (PRO TIP) PARA AFK (Dormir enquanto joga)

Para permitir que o utilitário rode em loop sem ficar preso em menus, mantenha 3 painéis abertos simultaneamente dentro do jogo:

- Coluna da Esquerda: Stash (Baú)
- Coluna Central: Inventory (Inventário) / Status do Personagem
- Coluna da Direita: Stage Portal (Portal da Fase) / Mapa

Ao fazer isso, a função Auto-Stash clicará no baú na esquerda e o Stage Switcher clicará na fase na direita, sem nunca se sobreporem ou precisarem abrir/fechar menus!
