
import modules.manager as manager
import json, re, requests


from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters, Updater, CallbackContext, ChatJoinRequestHandler
from telegram.error import BadRequest, Conflict

from modules.utils import process_command, is_admin, error_callback, escape_markdown_v2, cancel
GRUPO_RECEBER = 0


# Comando para receber id do grupo
# /grupo função
async def grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command_check = await process_command(update, context)
    # Verifica permissões e status de comandos
    
    if not command_check:
        return ConversationHandler.END
    
    if not await is_admin(context, update.message.from_user.id):
        
        return ConversationHandler.END
    
    context.user_data['conv_state'] = "grupo"

    keyboard = [[InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔗 Por favor, forneça o ID do grupo:", reply_markup=reply_markup)
    return GRUPO_RECEBER


async def recebe_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    id_recebido = update.message.text.strip()
    keyboard = [[InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    id_grupo = ''
    if not id_recebido.lstrip('-').isdigit():
        await update.message.reply_text("❌ Insira um ID valido:", reply_markup=reply_markup)
        return GRUPO_RECEBER
    invite_link = ''
    try:
        invite_link = await context.bot.create_chat_invite_link(chat_id=id_recebido, member_limit=1, creates_join_request=False)
        id_grupo = id_recebido
    except:
        try:
            id_grupo = id_recebido.replace('-', '-100')
            invite_link = await context.bot.create_chat_invite_link(chat_id=id_recebido.replace('-', '-100'), member_limit=1, creates_join_request=False)
        except:
            await update.message.reply_text("❌ Insira um ID valido\:\n>Lembre\-se o bot tem que ter permissão de admin no grupo", reply_markup=reply_markup, parse_mode='MarkdownV2')
            return GRUPO_RECEBER
    manager.update_bot_group(context.bot_data['id'], id_grupo)
    await update.message.reply_text(text=f"✅ ID do grupo modificado com sucesso\n\nNovo grupo\:\n> {escape_markdown_v2(invite_link.invite_link)}", parse_mode='MarkdownV2')
    context.user_data['conv_state'] = False
    return ConversationHandler.END





conv_handler_grupo = ConversationHandler(
    entry_points=[CommandHandler("vip", grupo)],
    states={
        GRUPO_RECEBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, recebe_grupo), CallbackQueryHandler(cancel)]
    },
    fallbacks=[CallbackQueryHandler(error_callback)]
    )