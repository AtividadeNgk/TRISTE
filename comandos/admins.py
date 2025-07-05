import modules.manager as manager
import json, re, requests


from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters, Updater, CallbackContext, ChatJoinRequestHandler
from telegram.error import BadRequest, Conflict

from modules.utils import process_command, is_admin, cancel, error_callback, error_message

ADMIN_ESCOLHA, ADMIN_REMOVER, ADMIN_RECEBER, ADMIN_CONFIRMAR = range(4)

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command_check = await process_command(update, context)
    if not command_check:
        return ConversationHandler.END
    if not await is_admin(context, update.message.from_user.id):
        
        return ConversationHandler.END
    context.user_data['conv_state'] = "admin"

    keyboard = False
    
    admin_list = manager.get_bot_admin(context.bot_data['id'])
    if len(admin_list) > 0:
        keyboard = [
            [InlineKeyboardButton("➕ ADICIONAR", callback_data="adicionar"), InlineKeyboardButton("➖ REMOVER", callback_data="remover")],
            [InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]]
    else:
        keyboard = [
            [InlineKeyboardButton("➕ ADICIONAR", callback_data="adicionar")],
            [InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🛡️ Qual ação deseja fazer com os admins:", reply_markup=reply_markup)
    return ADMIN_ESCOLHA


async def admin_escolha(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    if query.data == 'cancelar':
        await cancel(update, context)
        return ConversationHandler.END

    elif query.data == 'adicionar':
        keyboard = [[InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("🛡️ Envie o id do admin que deseja adicionar\:\n> Adicione pessoas de confiança apenas, não nos responsabilizamos por problemas com admins", reply_markup=reply_markup, parse_mode='MarkdownV2')
        return ADMIN_RECEBER
    elif query.data == 'remover':
        admins = manager.get_bot_admin(context.bot_data['id'])
        keyboard = []
        
        for i in admins:
            admin = await context.bot.get_chat(i)
            keyboard.append([InlineKeyboardButton(admin['username'], callback_data=i)])
        keyboard.append([InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("🛡️ Qual admin deseja remover:", reply_markup=reply_markup)
        return ADMIN_REMOVER


async def recebe_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    
    if not update.message.text:
        await update.message.reply_text(text=f"⛔ ID Invalido, por favor envie um valido")
        return ADMIN_RECEBER
    
    id_recebido = update.message.text.strip()
    admin_list = manager.get_bot_admin(context.bot_data['id'])
    
    if id_recebido in admin_list:
        await update.message.reply_text(text=f"⛔ Esse usuario ja possui privilegios admin")
        context.user_data['conv_state'] = False
        return ConversationHandler.END
    admin_chat = False
    try:
        admin_chat = await context.bot.get_chat(id_recebido)
    except:
        await update.message.reply_text(text=f"⛔ ID Invalido, por favor envie um valido")
        return ADMIN_RECEBER
    
    if admin_chat:
        keyboard = [
            [InlineKeyboardButton("✅ CONFIRMAR", callback_data="confirmar")],
            [InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]]

        reply_markup = InlineKeyboardMarkup(keyboard)
        context.user_data['admin_payload'] = id_recebido
        await update.message.reply_text(text=f"🛡️ Tem certeza que quer adicionar *{admin_chat['username']}*\n\n>Não nos responsabilizamos por ações tomadas por administradores, irregularidades por parte de adminstradores causam punição para o dono do bot",reply_markup=reply_markup, parse_mode='MarkdownV2')
        return ADMIN_CONFIRMAR
    else:
        keyboard = [[InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text=f"⛔ ID Invalido, por favor envie um valido")
        return ADMIN_RECEBER



async def admin_remover(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancelar':
        await cancel(update, context)
        return ConversationHandler.END
    admin_list = manager.get_bot_admin(context.bot_data['id'])

    if query.data in admin_list:
        admin_list.remove(query.data)
        manager.update_bot_admin(context.bot_data['id'], admin_list)
        await query.message.edit_text("✅ Admin removido com sucesso")
    else:
        await query.message.edit_text("⛔ Admin não encontrado")

    context.user_data['conv_state'] = False
    return ConversationHandler.END

async def admin_confirmar(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    if query.data == 'cancelar':
        await cancel(update, context)
        return ConversationHandler.END

    elif query.data == 'confirmar':
        admin_list = manager.get_bot_admin(context.bot_data['id'])
        admin_list.append(context.user_data['admin_payload'])
        manager.update_bot_admin(context.bot_data['id'], admin_list)
        await query.message.edit_text("✅ Admin adicionado com sucesso")
        
        context.user_data['conv_state'] = False
        return ConversationHandler.END




conv_handler_admin = ConversationHandler(
    entry_points=[CommandHandler("admin", admin)],
    states={
        ADMIN_ESCOLHA: [CallbackQueryHandler(admin_escolha)],
        ADMIN_REMOVER: [CallbackQueryHandler(admin_remover)],
        ADMIN_RECEBER: [MessageHandler(~filters.COMMAND, recebe_admin), CallbackQueryHandler(cancel)],
        ADMIN_CONFIRMAR: [CallbackQueryHandler(admin_confirmar)]

    },
    fallbacks=[CallbackQueryHandler(error_callback)]
    )