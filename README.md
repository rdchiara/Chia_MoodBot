# 🧠 Chia MoodBot

Um assistente pessoal no Telegram para monitorização diária de saúde mental e gestão de medicação. O bot realiza check-ins interativos, envia lembretes automáticos e estrutura todos os dados de forma normalizada num banco de dados do Google Sheets.

Desenvolvido em Python e projetado para rodar de forma contínua num Raspberry Pi via `systemd`.

---

## ✨ Funcionalidades Principais

* 📊 **Avaliação Interativa:** Teclados inline no Telegram para registar níveis (0 a 5) de humor, ansiedade, depressão e TDAH.
* 💊 **Gestão Dinâmica de Medicamentos:** Adicione novos tratamentos contínuos diretamente pelo chat (comando `/addmed`). O bot ajusta automaticamente a infraestrutura do Google Sheets, realocando colunas sem quebrar o histórico de dados.
* 📂 **Arquitetura de Dados Normalizada:** Separação inteligente em duas abas (`Humor` e `Medicamentos`) para evitar o desalinhamento de dados caso os tratamentos mudem ao longo do tempo.
* ⏰ **Lembretes Automáticos:** Tarefas agendadas (`schedule`) proativas às 08:00 e 21:00.
* 📈 **Métricas e Relatórios:** Cálculo automático das médias de sintomas dos últimos 7 dias.
* 🛡️ **Segurança e Isolamento:** Acesso restrito ao ID do utilizador (`MEU_CHAT_ID`).

---

## 🛠️ Tecnologias Utilizadas

* **Linguagem:** Python 3
* **Bibliotecas:** `pyTelegramBotAPI` (telebot), `gspread`, `oauth2client`, `schedule`
* **Infraestrutura:** Raspberry Pi (Raspberry Pi OS)
* **Gerenciamento de Processos:** `systemd` (Daemon rodando 24/7)
* **Banco de Dados:** Google Sheets API
* **Acesso Remoto:** Tailscale

---

## 🚀 Como Configurar e Instalar

### 1. Pré-requisitos
* Um bot criado no [BotFather](https://t.me/BotFather) do Telegram (para obter o Token).
* Uma conta no Google Cloud com a **Google Sheets API** e **Google Drive API** ativadas.
* Um ficheiro `credentials.json` (chave de serviço do Google Cloud) na raiz do projeto.
* O ID do seu chat no Telegram (para restringir o acesso).

### 2. Estrutura do Google Sheets
Crie uma planilha no Google Sheets chamada **MoodBot** e partilhe-a (como Editor) com o e-mail do seu bot de serviço do Google Cloud. 
A planilha **deve** conter exatamente estas duas abas e cabeçalhos:

**Aba 1: Humor**
`Data | Hora | Angústia | Irritação | Aperto no peito | Nó na garganta | Inquietação | Agitação | Impulsividade | Desatenção | Produtividade | Felicidade | Tristeza | Ânimo | Observações`

**Aba 2: Medicamentos**
`Data | Hora | Ritalina | Vurtuoso | Revoc | Outros Remédios`
*(Nota: O bot adicionará novas colunas antes de "Outros Remédios" automaticamente ao usar o comando `/addmed`).*

### 3. Instalação do Ambiente
Clone o repositório e instale as dependências:
```bash
git clone [https://github.com/SEU_USUARIO/Chia_MoodBot.git](https://github.com/SEU_USUARIO/Chia_MoodBot.git)
cd Chia_MoodBot
python3 -m venv venv
source venv/bin/activate
pip install pyTelegramBotAPI gspread oauth2client schedule