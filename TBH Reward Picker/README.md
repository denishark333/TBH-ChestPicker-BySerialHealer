# TBH Reward Picker 2.5.6

Um utilitário avançado e completo de automação e rastreamento de loot para **TaskbarHero**. Esta ferramenta utiliza monitoramento de arquivo de save (save-file) e interceptação de rede para rastrear o seu loot em tempo real, aliado a poderosas tarefas de automação de mouse para permitir um *AFK farming* 100% seguro.

---

## 🚀 Principais Funcionalidades

### 📦 Rastreamento de Loot e Sistema de Alvos (Targets)
*   **Monitoramento de Save em Tempo Real:** Fica de olho no seu arquivo de save local para detectar sempre que um baú é aberto ou um item é adquirido.
*   **Banco de Dados de Itens Alvo:** Adicione IDs de itens específicos à sua lista de "Targets". Se um item alvo cair (dropar), o utilitário interrompe imediatamente todas as automações e dispara um alarme para proteger o seu loot.
*   **Interceptação de Rede (Mitmproxy):** Analisa os pacotes de rede do jogo para prever e registrar as tabelas de loot instantaneamente.

### 🤖 Suíte de Automação de Mouse
*   **Auto-Relogger:** Reinicia o jogo e faz o login automaticamente caso um travamento seja detectado ou se alguma tarefa de automação ficar presa. Inclui um **Atraso de Segurança Anti-Rollback** que aguarda o save computar antes de forçar o fechamento do jogo quando um Target cai.
*   **Stage Switcher:** Um loop personalizável que clica periodicamente em 2 coordenadas da sua tela para alternar entre fases ou reentrar em portais automaticamente.
*   **Auto-Stash / Inventory Cleaner:** Um loop personalizável que clica periodicamente em até 3 coordenadas para mover seus itens do inventário para o Baú (Stash) ou Sintetizá-los automaticamente.
    *   *Cooldown Inteligente:* Se um Item Alvo (Target) cair, o Auto-Stash aplica automaticamente um tempo de espera (cooldown) de 15 minutos para garantir que o seu item alvo seja salvo com segurança antes de interagir com o baú.

### 🔔 Integrações com Discord
*   **Notificações via Webhook:** Envia um aviso para o seu servidor do Discord sempre que um Baú Raro for encontrado ou quando um Item Alvo for adquirido.

---

## 🛠️ Instalação e Setup

Você não precisa instalar dependências manualmente se usar o script `.bat` fornecido.

1.  Clone ou baixe este repositório.
2.  Execute o arquivo **`install_requirements.bat`**. *(Você só precisa fazer isso uma vez, ou sempre que uma nova atualização exigir uma nova biblioteca)*.
3.  Inicie o aplicativo clicando duas vezes em **`run_peeker_gui.bat`**.

> **Nota:** É necessário ter o Python 3.10 ou mais recente instalado no seu sistema e adicionado ao seu `PATH`.

---

## 🛠️ Configuração Inicial (Crucial para a Primeira Vez)

Ao abrir o aplicativo, você deve configurar duas coisas essenciais para que o utilitário rastreie o seu jogo:

### 1. Vinculando o seu Arquivo de Save (Save File)
Para permitir que o utilitário leia o seu loot, você precisa apontá-lo para o seu arquivo de save:
1. Vá até a **Save File Section** (Seção de Save File) no painel.
2. Clique no **Texto Dourado** (o campo do caminho do arquivo).
3. Cole o caminho da pasta de save do seu jogo no campo.
4. Clique em **Browse** (Navegar).
5. Selecione o arquivo chamado **`SaveFile_Live.es3`**.
6. Clique em **OK**.
*(Este caminho ficará salvo, então você só precisará fazer isso uma vez!)*

### 2. Iniciando o Proxy
A Interceptação de Rede (Mitmproxy) não inicia automaticamente para evitar conflitos de rede no seu computador.
* **Toda vez que você abrir o Painel**, você deve clicar explicitamente em **"START PROXY"** na tela principal para começar a rastrear as tabelas de loot pela rede.

---

## 🖱️ Como Calibrar as Tarefas de Automação

Tanto o **Stage Switcher** quanto o **Auto-Stash** usam um simples Ouvinte de Mouse (Mouse Listener) para calibração.

1.  Vá até a aba **Settings** (Configurações).
2.  Clique no botão "Calibrate Click" para a tarefa de automação que você deseja configurar.
3.  Mova o seu mouse sobre o botão desejado na janela do jogo.
4.  Dê um **Clique Esquerdo** para registrar a coordenada.
    *   *(Você pode dar um Clique Direito a qualquer momento para cancelar a calibração).*
5.  *As coordenadas são salvas automaticamente no seu `config.json`. Nota: Se você mover a janela do jogo de lugar, precisará recalibrar!*

---

## ⚙️ Configuração "Pro Tip" para AFK (Longe do Teclado)

Para o enquadramento perfeito (permitindo que o utilitário rode em loop sem ficar preso em menus), mantenha **3 painéis abertos simultaneamente** dentro do jogo:
1.  **Coluna da Esquerda:** Stash (Baú)
2.  **Coluna Central:** Inventory (Inventário) / Status do Personagem
3.  **Coluna da Direita:** Stage Portal (Portal da Fase) / Mapa

*Ao fazer isso, o **Auto-Stash** clicará na esquerda e o **Stage Switcher** clicará na direita, sem nunca se sobreporem ou precisarem abrir/fechar menus!*
