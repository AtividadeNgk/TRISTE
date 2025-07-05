import modules.manager as manager
import json, re, requests


from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters, Updater, CallbackContext, ChatJoinRequestHandler
from telegram.error import BadRequest, Conflict

async def is_admin(context, user_id, show_plans_if_not_admin=True):
    if (str(user_id) in manager.get_bot_admin(context.bot_data['id']) or is_owner(context, user_id)):
        return True
    else:
        # Só mostra planos se for explicitamente solicitado
        if show_plans_if_not_admin:
            planos = manager.get_bot_plans(context.bot_data['id'])
            keyboard_plans = []
            for plan_index in range(len(planos)):
                keyboard_plans.append([InlineKeyboardButton(f'{planos[plan_index]['name']} - R$ {planos[plan_index]['value']}', callback_data=f"plano_{plan_index}")])
            reply_markup = InlineKeyboardMarkup(keyboard_plans)
            await context.bot.send_message(user_id, 'Escolha uma oferta abaixo:', reply_markup=reply_markup)
        return False
    
    
def is_owner(context, user_id):
    return (str(user_id) == manager.get_bot_owner(context.bot_data['id']))
        


async def process_command(update: Update, context):
    conv_state = context.user_data.get('conv_state', False)
    if conv_state != False:

        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton('Cancelar', callback_data='cancelar')]])
        await update.message.reply_text(f'O comando {conv_state} está em execução no momento\n\n> Caso deseja cancelar clique no botão abaixo', reply_markup=keyboard, parse_mode='MarkdownV2')    
        return False
    return True

async def error_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass

async def error_callback(update: Update, context: CallbackContext):
    pass

def escape_markdown_v2(text):
    # Função para escapar caracteres especiais no MarkdownV2
    return re.sub(r'([_\*\[\]\(\)~`>#+\-=|{}\.!])', r'\\\1', str(text))


def check_link(url:str):
    # Expressão regular para verificar o formato da URL
    url = url.lower()
    if url.startswith('t.me'):
        return True
    regex_url = re.compile(
        r'^(https?://)?'  # Protocolo opcional (http ou https)
        r'(www\.)?'       # Subdomínio opcional (www)
        r'[a-zA-Z0-9-]+'  # Nome do domínio
        r'(\.[a-zA-Z]{2,})'  # TLD (top-level domain)
        r'(:\d+)?'        # Porta opcional
        r'(\/[^\s]*)?$'   # Caminho opcional
    )

    # Verifica o formato da URL
    if not re.match(regex_url, url):
        return False

    # Tenta acessar a URL para validar a acessibilidade
    try:
        response = requests.head(url, timeout=5)
        return response.status_code < 400
    except requests.RequestException:
        return False




async def cancel(update: Update, context: CallbackContext):
    query = update.callback_query
    command = context.user_data.get('conv_state', False)
    await query.answer()
    context.user_data.clear()
    if command:
        await query.message.edit_text(f'✅ Comando {command} cancelado com sucesso')
    else:
        await query.message.edit_text(f'❌ Nenhum comando em execução foi encontrado')
    return ConversationHandler.END
