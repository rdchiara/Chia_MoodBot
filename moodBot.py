import time
import threading
import schedule
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.apihelper import ApiTelegramException
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
from collections import defaultdict
import config
import json
import os
import logging

# Cria a pasta de logs automaticamente
os.makedirs("logs", exist_ok=True)

# Configura o ficheiro onde os erros serão guardados
logging.basicConfig(
    filename='logs/erros.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ================= ARQUIVOS JSON DINÂMICOS =================
ARQUIVO_PADRAO = 'logs/remedios_padrao.json'
ARQUIVO_MEDS = 'logs/meds_ativos.json'

def obter_remedios_padrao():
    if os.path.exists(ARQUIVO_PADRAO):
        with open(ARQUIVO_PADRAO, 'r') as f:
            return json.load(f)
    # Se não existir, cria a lista inicial
    padrao = ["Ritalina", "Vurtuoso", "Revoc"]
    with open(ARQUIVO_PADRAO, 'w') as f:
        json.dump(padrao, f)
    return padrao

def salvar_remedios_padrao(lista):
    with open(ARQUIVO_PADRAO, 'w') as f:
        json.dump(lista, f)

def obter_meds_ativos():
    if os.path.exists(ARQUIVO_MEDS):
        with open(ARQUIVO_MEDS, 'r') as f:
            return json.load(f)
    return obter_remedios_padrao()

def salvar_meds_ativos(lista):
    with open(ARQUIVO_MEDS, 'w') as f:
        json.dump(lista, f)

# ================= CONFIGURAÇÕES =================
TOKEN = config.TELEGRAM_TOKEN
MEU_CHAT_ID = config.CHAT_ID
bot = telebot.TeleBot(TOKEN)

# Configuração do Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

planilha = client.open('MoodBot')
sheet_humor = planilha.worksheet('Humor')
sheet_meds = planilha.worksheet('Medicamentos')

# ================= ESTRUTURA DE DADOS =================
METRICAS = [
    ("Angústia", "😣"), ("Irritação", "😠"), ("Aperto no peito", "🫀"),
    ("Nó na garganta", "🤐"), ("Inquietação", "🫨"), ("Agitação", "🏃"),
    ("Impulsividade", "⚡"), ("Desatenção", "🫠"), ("Produtividade", "📈"),
    ("Felicidade", "😊"), ("Tristeza", "😢"), ("Ânimo", "🔋")
]
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
    
    markup.add(InlineKeyboardButton("➕ Adicionar Novo Remédio (Apenas hoje)", callback_data="med_novo"))
    markup.add(InlineKeyboardButton("✅ Salvar Remédios e Finalizar", callback_data="med_avancar"))
    return markup

# ================= FLUXO PRINCIPAL =================
def iniciar_fluxo_avaliacao(chat_id):
    user_state[chat_id] = {
        'step': 0,
        'respostas': {nome: 0 for nome, emoji in METRICAS},
        'meds': {med: 0 for med in obter_meds_ativos()},
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


# ================= COMANDOS DE AJUDA, MÉTRICAS E GESTÃO =================
@bot.message_handler(commands=['help'])
def comando_help(message):
    texto = (
        "🧠 **Guia de Utilização - Chia MoodBot**\n\n"
        "Este assistente monitoriza a sua saúde mental diariamente e guarda os registos no Google Sheets (Abas 'Humor' e 'Medicamentos').\n\n"
        "**Como Avaliar (Escala de 0 a 5):**\n"
        "• 0 = Ausência total do sintoma (Nulo).\n"
        "• 5 = Intensidade máxima ou insuportável.\n\n"
        "**Comandos Disponíveis:**\n"
        "/start ou /avaliar - Inicia o check-in manual.\n"
        "/metrica - Calcula a média dos sintomas nos últimos 7 dias.\n"
        "/log - Envia o ficheiro de erros do sistema.\n"
        "/desfazer - Apaga o último registo salvo das planilhas.\n"
        "/ping - Verifica se o bot está ativo e a responder.\n\n"
        "💊 **Gestão de Remédios:**\n"
        "/meds - Mostra o status atual dos seus remédios.\n"
        "/addmed [Nome] - Adiciona um novo remédio contínuo à sua rotina.\n"
        "/pausar [Nome] - Pausa as perguntas diárias sobre um remédio.\n"
        "/retomar [Nome] - Volta a exibir o remédio pausado.\n\n"
        "⏰ **Lembretes Automáticos:** 08:00 e 21:00."
    )
    bot.send_message(message.chat.id, texto, parse_mode="Markdown")

@bot.message_handler(commands=['metrica'])
def comando_metrica(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "⏳ Analisando os últimos 7 dias na planilha de Humor...")
    
    try:
        # Puxa os dados da aba de Humor
        linhas = sheet_humor.get_all_values()[1:] 
        hoje = datetime.now().date()
        limite = hoje - timedelta(days=7)
        
        notas_diarias = defaultdict(lambda: defaultdict(list))
        nomes_metricas = [m[0] for m in METRICAS]
        
        for linha in linhas:
            if not linha or not linha[0]:
                continue
            try:
                data_linha = datetime.strptime(linha[0], "%d/%m/%Y").date()
                if limite < data_linha <= hoje:
                    data_str = linha[0]
                    # As 12 colunas de métricas começam no índice 2
                    for idx, nome in enumerate(nomes_metricas):
                        col_idx = idx + 2
                        if col_idx < len(linha) and linha[col_idx].strip() != "":
                            notas_diarias[data_str][nome].append(int(linha[col_idx]))
            except ValueError:
                continue 
        
        dias_avaliados = len(notas_diarias)
        if dias_avaliados == 0:
            bot.send_message(chat_id, "📉 Nenhum registo encontrado nos últimos 7 dias.")
            return
        
        resposta = f"📊 **Médias dos últimos 7 dias**\n*(Baseado em {dias_avaliados} dia(s) avaliado(s))*\n\n"
        
        for nome, emoji in METRICAS:
            soma_das_medias_diarias = 0
            for data, metricas_dict in notas_diarias.items():
                notas = metricas_dict.get(nome, [])
                if notas:
                    soma_das_medias_diarias += sum(notas) / len(notas)
            
            media_final = soma_das_medias_diarias / dias_avaliados
            resposta += f"{emoji} {nome}: {media_final:.1f}\n"
            
        bot.send_message(chat_id, resposta, parse_mode="Markdown")
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ Erro ao calcular métricas: {e}")

@bot.message_handler(commands=['log'])
def enviar_arquivo_log(message):
    chat_id = message.chat.id
    if chat_id != MEU_CHAT_ID: return
        
    caminho_log = 'logs/erros.log'
    try:
        if os.path.exists(caminho_log) and os.path.getsize(caminho_log) > 0:
            with open(caminho_log, 'rb') as arquivo_log:
                bot.send_document(chat_id, arquivo_log, caption="⚙️ Aqui está o arquivo de erros do sistema.")
        else:
            bot.send_message(chat_id, "✨ O arquivo de logs está limpo e vazio. O bot está rodando perfeitamente!")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Erro ao acessar logs: {e}")

@bot.message_handler(commands=['desfazer'])
def comando_desfazer(message):
    chat_id = message.chat.id
    if chat_id != MEU_CHAT_ID: return
    
    try:
        bot.send_message(chat_id, "⏳ Acessando as planilhas...")
        linhas_humor = sheet_humor.get_all_values()
        total_linhas = len(linhas_humor)
        
        if total_linhas <= 1:
            bot.send_message(chat_id, "⚠️ As planilhas estão vazias. Não há o que desfazer.")
            return
        
        ultima_linha = linhas_humor[-1]
        data_registro = ultima_linha[0]
        hora_registro = ultima_linha[1]
        
        # Apaga de ambas as abas
        sheet_humor.delete_rows(total_linhas)
        sheet_meds.delete_rows(total_linhas)
        
        bot.send_message(chat_id, f"🗑️ **Registro Apagado!**\nA avaliação de {data_registro} às {hora_registro} foi removida das abas Humor e Medicamentos.", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Erro ao tentar desfazer: {e}")
        logging.error(f"Erro no /desfazer: {e}")

@bot.message_handler(commands=['ping'])
def comando_ping(message):
    if message.chat.id != MEU_CHAT_ID: return
    bot.send_message(message.chat.id, "🏓 *Pong!* O sistema está online e a monitorizar a sua rotina.", parse_mode="Markdown")

@bot.message_handler(commands=['meds'])
def gerenciar_meds(message):
    if message.chat.id != MEU_CHAT_ID: return
    padrao = obter_remedios_padrao()
    ativos = obter_meds_ativos()
    
    texto = "💊 *Status dos Remédios Contínuos:*\n\n"
    for med in padrao:
        status = "✅ Ativo" if med in ativos else "⏸️ Pausado"
        texto += f"• {med}: {status}\n"
    
    texto += "\nComandos úteis:\n`/addmed Nome`\n`/pausar Nome`\n`/retomar Nome`"
    bot.send_message(message.chat.id, texto, parse_mode="Markdown")

@bot.message_handler(commands=['addmed'])
def comando_addmed(message):
    if message.chat.id != MEU_CHAT_ID: return
    
    novo_med = message.text.replace("/addmed", "").strip()
    if not novo_med:
        bot.send_message(message.chat.id, "⚠️ Use o formato: `/addmed NomeDoRemedio`", parse_mode="Markdown")
        return
        
    padrao = obter_remedios_padrao()
    ativos = obter_meds_ativos()
    
    if novo_med not in padrao:
        padrao.append(novo_med)
        ativos.append(novo_med)
        salvar_remedios_padrao(padrao)
        salvar_meds_ativos(ativos)
        
        alerta = (
            f"✅ **{novo_med}** adicionado ao tratamento!\n\n"
            f"⚠️ **MUITO IMPORTANTE:** Vá ao Google Sheets na aba *Medicamentos* e adicione uma nova coluna ao final para este remédio (logo antes de 'Outros Remédios')!"
        )
        bot.send_message(message.chat.id, alerta, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "Esse medicamento já está cadastrado.")

@bot.message_handler(commands=['pausar'])
def pausar_med(message):
    if message.chat.id != MEU_CHAT_ID: return
    nome = message.text.replace("/pausar", "").strip()
    ativos = obter_meds_ativos()
    
    if nome in ativos:
        ativos.remove(nome)
        salvar_meds_ativos(ativos)
        bot.send_message(message.chat.id, f"⏸️ O bot não perguntará mais sobre *{nome}*.", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "Nome não encontrado ou já pausado. Veja em /meds.")

@bot.message_handler(commands=['retomar'])
def retomar_med(message):
    if message.chat.id != MEU_CHAT_ID: return
    nome = message.text.replace("/retomar", "").strip()
    padrao = obter_remedios_padrao()
    ativos = obter_meds_ativos()
    
    if nome in padrao and nome not in ativos:
        ativos.append(nome)
        salvar_meds_ativos(ativos)
        bot.send_message(message.chat.id, f"▶️ *{nome}* voltou para a rotina de perguntas!", parse_mode="Markdown")
    elif nome in ativos:
        bot.send_message(message.chat.id, "Esse remédio já está ativo.")
    else:
        bot.send_message(message.chat.id, "Remédio não encontrado. Veja em /meds.")

# ================= CALLBACKS =================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    data = call.data

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
        msg = bot.send_message(chat_id, "Digite o nome e a quantidade do novo remédio esporádico (ex: Dipirona - 1):")
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
    bot.send_message(chat_id, "✅ Adicionado aos remédios extra de hoje!")
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

    # 1. Monta a linha do Humor (Métricas + Obs)
    linha_humor = [data_str, hora_str]
    for nome, emoji in METRICAS:
        linha_humor.append(estado['respostas'].get(nome, 0))
    linha_humor.append(obs)

    # 2. Monta a linha dos Medicamentos Dinâmicos (Remédios Contínuos + Outros)
    linha_meds = [data_str, hora_str]
    for med in obter_remedios_padrao():
        linha_meds.append(estado['meds'].get(med, 0))
    linha_meds.append(outros_meds_str)

    try:
        bot.send_message(chat_id, "⏳ Salvando nas duas planilhas...")
        
        # 3. Envia para as abas correspondentes
        sheet_humor.append_row(linha_humor)
        sheet_meds.append_row(linha_meds)
        
        # Monta o resumo formatado
        resumo = "📋 **Resumo do Registro**\n\n🧠 *Métricas (Apenas > 0):*\n"
        tem_metrica = False
        for nome, emoji in METRICAS:
            nota = estado['respostas'].get(nome, 0)
            if nota > 0:
                resumo += f"{emoji} {nome}: {nota}\n"
                tem_metrica = True
        if not tem_metrica:
            resumo += "Nenhuma métrica registrada.\n"
            
        resumo += "\n💊 *Medicamentos:*\n"
        tem_med = False
        for med in obter_remedios_padrao():
            qtd = estado['meds'].get(med, 0)
            if qtd > 0:
                resumo += f"• {med}: {qtd}\n"
                tem_med = True
        if estado['outros_meds']:
            resumo += f"• Extra: {outros_meds_str}\n"
            tem_med = True
        if not tem_med:
            resumo += "Nenhum medicamento.\n"
            
        resumo += f"\n📝 *Obs:* {obs}"
        
        # Envia o resumo e finaliza
        bot.send_message(chat_id, resumo, parse_mode="Markdown")
        bot.send_message(chat_id, "🎉 **Avaliação salva com sucesso!**", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Erro ao salvar: {e}")
        logging.error(f"Erro ao salvar: {e}")

# ================= EXECUÇÃO =================
print("Bot rodando com agendador de lembretes ativo...")
while True:
    try:
        bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
    except Exception as e:
        logging.error(f"Falha de conexão: {e}")
        time.sleep(5)