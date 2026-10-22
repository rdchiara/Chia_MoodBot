import time
import threading
import schedule
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.apihelper import ApiTelegramException
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import config

# ================= CONFIGURAÇÕES =================
TOKEN = config.TELEGRAM_TOKEN
MEU_CHAT_ID = config.CHAT_ID
bot = telebot.TeleBot(TOKEN)

# Configuração do Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)
sheet = client.open('MoodBot').sheet1

# ================= ESTRUTURA DE DADOS =================
METRICAS = [
    ("Angústia", "😣"), ("Irritação", "😠"), ("Aperto no peito", "🫀"),
    ("Nó na garganta", "🤐"), ("Inquietação", "🫨"), ("Agitação", "🏃"),
    ("Impulsividade", "⚡"), ("Desatenção", "🫠"), ("Produtividade", "📈"),
    ("Felicidade", "😊"), ("Tristeza", "😢"), ("Ânimo", "🔋")
]
REMEDIOS_PADRAO = ["Ritalina", "Vurtuoso", "Revoc"]
user_state = {}

# ================= TECLADOS =================
def gerar_teclado_metricas(chat_id):
    markup = InlineKeyboardMarkup()
    for i, (nome, emoji) in enumerate(METRICAS):
        val_atual = user_state[chat_id]['respostas'][nome]
        markup.add(InlineKeyboardButton(f"{emoji} {nome}", callback_data="ignore"))
        
        botoes_nota = []
        for nota in range(6):
            texto = f"🟢 {nota}" if nota == val_atual else str(nota)
            botoes_nota.append(InlineKeyboardButton(texto, callback_data=f"met_{i}_{nota}"))
        markup.row(*botoes_nota)
    
    markup.add(InlineKeyboardButton("✅ Salvar Métricas e Avançar", callback_data="met_avancar"))
    return markup

def gerar_teclado_remedios(chat_id):
    markup = InlineKeyboardMarkup()
    meds = user_state[chat_id]['meds']
    for med, qtd in meds.items():
        btn_menos = InlineKeyboardButton("-", callback_data=f"med_sub_{med}")
        btn_nome = InlineKeyboardButton(f"{med}: {qtd}", callback_data="ignore")
        btn_mais = InlineKeyboardButton("+", callback_data=f"med_add_{med}")
        markup.row(btn_menos, btn_nome, btn_mais)
    
    markup.add(InlineKeyboardButton("➕ Adicionar Novo Remédio", callback_data="med_novo"))
    markup.add(InlineKeyboardButton("✅ Salvar Remédios e Finalizar", callback_data="med_avancar"))
    return markup

# ================= FLUXO PRINCIPAL =================
def iniciar_fluxo_avaliacao(chat_id):
    user_state[chat_id] = {
        'step': 0,
        'respostas': {nome: 0 for nome, emoji in METRICAS},
        'meds': {med: 0 for med in REMEDIOS_PADRAO},
        'outros_meds': []
    }
    texto = "📊 **Avaliação Diária**\n\nSelecione as notas de 0 a 5 para hoje:\n*(0 = Nulo / 5 = Máximo)*"
    bot.send_message(chat_id, texto, reply_markup=gerar_teclado_metricas(chat_id), parse_mode="Markdown")

@bot.message_handler(commands=['start', 'avaliar'])
def comando_start(message):
    iniciar_fluxo_avaliacao(message.chat.id)

# ================= LEMBRETES AUTOMÁTICOS =================
def enviar_lembrete():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📝 Responder Agora", callback_data="iniciar_lembrete"))
    try:
        bot.send_message(MEU_CHAT_ID, "⏰ **Hora do Check-in!**\nComo estão os seus níveis agora?", reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        print(f"Erro ao enviar lembrete: {e}")

def rodar_agendador():
    schedule.every().day.at("08:00").do(enviar_lembrete)
    schedule.every().day.at("21:00").do(enviar_lembrete)
    while True:
        schedule.run_pending()
        time.sleep(1)

# Inicia a thread dos lembretes em segundo plano
threading.Thread(target=rodar_agendador, daemon=True).start()

# ================= CALLBACKS =================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    data = call.data

    # Handler especial para o botão do lembrete
    if data == "iniciar_lembrete":
        bot.answer_callback_query(call.id)
        iniciar_fluxo_avaliacao(chat_id)
        return

    if chat_id not in user_state:
        bot.answer_callback_query(call.id, "Sessão expirada. Digite /avaliar novamente.")
        return

    # --- MÉTRICAS ---
    if data.startswith("met_") and data != "met_avancar":
        _, idx, nota = data.split("_")
        nome_metrica = METRICAS[int(idx)][0]
        nota = int(nota)
        
        if user_state[chat_id]['respostas'][nome_metrica] != nota:
            user_state[chat_id]['respostas'][nome_metrica] = nota
            try:
                bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=gerar_teclado_metricas(chat_id))
            except ApiTelegramException:
                pass
        bot.answer_callback_query(call.id)

    elif data == "met_avancar":
        try:
            bot.edit_message_text("✅ Métricas registradas!", chat_id, call.message.message_id)
        except ApiTelegramException:
            pass
        bot.send_message(chat_id, "💊 **Medicamentos**\nQuantidade de comprimidos tomados hoje:", reply_markup=gerar_teclado_remedios(chat_id), parse_mode="Markdown")
        bot.answer_callback_query(call.id)

    # --- REMÉDIOS ---
    elif data.startswith("med_add_"):
        med = data.split("med_add_")[1]
        user_state[chat_id]['meds'][med] += 1
        try:
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=gerar_teclado_remedios(chat_id))
        except ApiTelegramException:
            pass
        bot.answer_callback_query(call.id)
    
    elif data.startswith("med_sub_"):
        med = data.split("med_sub_")[1]
        if user_state[chat_id]['meds'][med] > 0:
            user_state[chat_id]['meds'][med] -= 1
            try:
                bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=gerar_teclado_remedios(chat_id))
            except ApiTelegramException:
                pass
        bot.answer_callback_query(call.id)
        
    elif data == "med_novo":
        msg = bot.send_message(chat_id, "Digite o nome e a quantidade do novo remédio (ex: Dipirona - 1):")
        bot.register_next_step_handler(msg, adicionar_novo_remedio, call.message.message_id)
        bot.answer_callback_query(call.id)

    elif data == "med_avancar":
        try:
            bot.edit_message_text("✅ Remédios registrados!", chat_id, call.message.message_id)
        except ApiTelegramException:
            pass
        msg = bot.send_message(chat_id, "📝 **Observações do dia**\nEscreva o que julgar importante (ou digite 'Nada'):", parse_mode="Markdown")
        bot.register_next_step_handler(msg, finalizar_avaliacao)
        bot.answer_callback_query(call.id)

    elif data == "ignore":
        bot.answer_callback_query(call.id)

def adicionar_novo_remedio(message, painel_msg_id):
    chat_id = message.chat.id
    user_state[chat_id]['outros_meds'].append(message.text)
    bot.send_message(chat_id, "✅ Adicionado!")
    bot.send_message(chat_id, "💊 **Medicamentos**\nQuantidade de comprimidos tomados hoje:", reply_markup=gerar_teclado_remedios(chat_id), parse_mode="Markdown")

# ================= FINALIZAÇÃO =================
def finalizar_avaliacao(message):
    chat_id = message.chat.id
    obs = message.text
    estado = user_state[chat_id]
    
    agora = datetime.now()
    data_str = agora.strftime("%d/%m/%Y")
    hora_str = agora.strftime("%H:%M:%S")
    outros_meds_str = " | ".join(estado['outros_meds']) if estado['outros_meds'] else "Nenhum"

    linha = [
        data_str, hora_str,
        estado['respostas'].get("Angústia", 0), estado['respostas'].get("Irritação", 0),
        estado['respostas'].get("Aperto no peito", 0), estado['respostas'].get("Nó na garganta", 0),
        estado['respostas'].get("Inquietação", 0), estado['respostas'].get("Agitação", 0),
        estado['respostas'].get("Impulsividade", 0), estado['respostas'].get("Desatenção", 0),
        estado['respostas'].get("Produtividade", 0), estado['respostas'].get("Felicidade", 0),
        estado['respostas'].get("Tristeza", 0), estado['respostas'].get("Ânimo", 0),
        estado['meds'].get("Ritalina", 0), estado['meds'].get("Vurtuoso", 0),
        estado['meds'].get("Revoc", 0), outros_meds_str, obs
    ]

    try:
        bot.send_message(chat_id, "⏳ Salvando no banco de dados...")
        sheet.append_row(linha)
        bot.send_message(chat_id, "🎉 **Avaliação salva com sucesso!**", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Erro ao salvar: {e}")

# ================= EXECUÇÃO =================
print("Bot rodando com agendador de lembretes ativo...")
while True:
    try:
        bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"Erro de conexão. Reconectando em 5 segundos... Erro: {e}")
        time.sleep(5)