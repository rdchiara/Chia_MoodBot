# Chia MoodBot 🧠📊

Um bot privado para o Telegram desenvolvido em Python para o monitoramento diário de saúde mental, sintomas de ansiedade, depressão, TDAH e controle de medicação. O bot funciona como um diário interativo que salva todos os registos automaticamente num banco de dados do Google Sheets para acompanhamento clínico e pessoal a longo prazo.

## Funcionalidades

* **Avaliação Interativa (0 a 5):** Interface com botões inline para avaliar 12 métricas diárias de forma rápida e visual (com emojis), sem precisar digitar texto.
* **Métricas Monitoradas:**
  * **Depressão:** Angústia, Irritação, Aperto no peito, Nó na garganta.
  * **Ansiedade:** Inquietação, Agitação, Impulsividade.
  * **TDAH:** Desatenção, Produtividade.
  * **Humor Geral:** Felicidade, Tristeza, Ânimo.
* **Controle de Medicamentos:** Painel dinâmico para registrar a dosagem de medicamentos de uso contínuo (Ritalina, Vurtuoso, Revoc) com botões de `+` e `-`, além de permitir a inserção de medicamentos esporádicos.
* **Lembretes Automáticos:** O bot envia notificações proativas todos os dias às 08:00 e às 21:00 com um atalho para iniciar a avaliação.
* **Análise de Dados (/metrica):** Calcula e exibe a média de cada sintoma com base nos últimos 7 dias registrados na planilha.
* **Integração na Nuvem:** Exportação em tempo real para o Google Sheets, organizando dados por Data, Hora, Sintomas, Medicamentos e Observações Livres.

## Tecnologias e Bibliotecas

* **Python 3**
* **pyTelegramBotAPI (telebot):** Interface de comunicação e criação dos teclados inline.
* **gspread & oauth2client:** Autenticação e manipulação da API do Google Sheets.
* **schedule:** Gerenciamento dos alarmes e lembretes diários.
* **Ambiente de Execução:** Raspberry Pi (24/7).

## Estrutura do Banco de Dados

O bot requer uma planilha no Google Sheets com o nome exato `MoodBot` e o seguinte cabeçalho na primeira linha:
`Data` | `Hora` | `Angústia` | `Irritação` | `Aperto no peito` | `Nó na garganta` | `Inquietação` | `Agitação` | `Impulsividade` | `Desatenção` | `Produtividade` | `Felicidade` | `Tristeza` | `Ânimo` | `Ritalina` | `Vurtuoso` | `Revoc` | `Outros Remédios` | `Observações`

## Instalação e Execução

**1. Clonar o repositório**
```bash
git clone [https://github.com/SEU_USUARIO/Chia_MoodBot.git](https://github.com/SEU_USUARIO/Chia_MoodBot.git)
cd Chia_MoodBot