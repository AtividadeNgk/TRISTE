import modules.manager as manager
import json, re, requests


from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters, Updater, CallbackContext, ChatJoinRequestHandler
from telegram.error import BadRequest, Conflict

from modules.utils import process_command, is_admin, error_callback, error_message, cancel

EXPIRACAO_RECEBER, EXPIRACAO_ESCOLHA = range(2)

#comando adeus
async def adeus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command_check = await process_command(update, context)
    planos = manager.get_bot_plans(context.bot_data['id'])
    if not command_check:
        return ConversationHandler.END
    if not await is_admin(context, update.message.from_user.id):
        
        return ConversationHandler.END
    context.user_data['conv_state'] = "adeus"

    keyboard = [
            [InlineKeyboardButton("➕ ADICIONAR", callback_data="adicionar"), InlineKeyboardButton("➖ REMOVER", callback_data="remover")],
            [InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("⏳ Qual ação deseja fazer com a mensagem de expiração:", reply_markup=reply_markup)
    return EXPIRACAO_ESCOLHA

async def adeus_escolha(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    if query.data == 'cancelar':
        await cancel(update, context)
        return ConversationHandler.END
    elif query.data == 'adicionar':
        keyboard = [[InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text("⏳ Envie como deseja a mensagem de expiração\:\n> Pode conter midia", reply_markup=reply_markup, parse_mode='MarkdownV2')
        return EXPIRACAO_RECEBER
    elif query.data == 'remover':
        manager.update_bot_expiration(context.bot_data['id'], {}) 
        await query.message.edit_text("✅ Expiração deletado com sucesso")
        context.user_data['conv_state'] = False
        return ConversationHandler.END

async def adeus_receber_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        print(update.message)
        save = {
            'media':False,
            'text':False
            }
        if update.message.photo:
            photo_file = await update.message.photo[-1].get_file()
            save['media'] = {
                'file':photo_file.file_id,
                'type':'photo'
            }

        elif update.message.video:
            video_file = await update.message.video.get_file()
            save['media'] = {
                'file':video_file.file_id,
                'type':'video'
            }
        elif update.message.text:
            save['text'] = update.message.text
        else: 
            await update.message.reply_text("⛔ Somente texto ou midia:")
            return EXPIRACAO_RECEBER
        if update.message.caption:
            save['text'] = update.message.caption

        
        manager.update_bot_expiration(context.bot_data['id'], save)
        await update.message.reply_text(text="✅ Expiração salva com sucesso", parse_mode='MarkdownV2')
    except Exception as e:
        await update.message.reply_text(text=f"⛔ Erro ao salvar expiração {str(e)}")
        context.user_data['conv_state'] = False
        return ConversationHandler.END


conv_handler_adeus = ConversationHandler(
    entry_points=[CommandHandler("adeus", adeus)],
    states={
        EXPIRACAO_ESCOLHA: [CallbackQueryHandler(adeus_escolha)],
        EXPIRACAO_RECEBER:[MessageHandler(~filters.COMMAND, adeus_receber_mensagem), CallbackQueryHandler(cancel)]
    },
    fallbacks=[CallbackQueryHandler(error_callback)]
    )

#Expiração
#{
#"text":"",
#"media"{"type", "file"}
#}