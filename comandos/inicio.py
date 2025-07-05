import modules.manager as manager
import json, re, requests


from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters, Updater, CallbackContext, ChatJoinRequestHandler
from telegram.error import BadRequest, Conflict

from modules.utils import process_command, is_admin, cancel, error_callback, error_message

keyboardc = [
            [InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]
        ]
cancel_markup = InlineKeyboardMarkup(keyboardc)


INICIO_ESCOLHA, INICIO_ADICIONAR_OU_DELETAR, INICIO_RECEBER = range(3)


# Comando definir inicio
# /Inicio
async def inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command_check = await process_command(update, context)
    if not command_check:
        return ConversationHandler.END

    if not await is_admin(context, update.message.from_user.id):
        
        return ConversationHandler.END
    context.user_data['inicio_context'] = manager.get_bot_config(context.bot_data['id'])
    context.user_data['conv_state'] = "inicio"

    keyboard = [
        [InlineKeyboardButton("Midia Inicial", callback_data="midia"), InlineKeyboardButton("Texto 1", callback_data="texto1")],
        [InlineKeyboardButton("Texto 2", callback_data="texto2"), InlineKeyboardButton("Botão", callback_data="botao")],
        [InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("🛠️ O que deseja modificar no inicio?", reply_markup=reply_markup)
    return INICIO_ESCOLHA

async def inicio_escolha(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == 'cancelar':
        await cancel(update, context)
        return ConversationHandler.END

    context.user_data['inicio_acao'] = query.data

    keyboard = [
        [InlineKeyboardButton("➕ Adicionar", callback_data="adicionar"), InlineKeyboardButton("➖ Deletar", callback_data="deletar")],
        [InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.edit_text(f"🛠️ Deseja adicionar ou deletar o valor para {query.data}?", reply_markup=reply_markup)
    return INICIO_ADICIONAR_OU_DELETAR

async def inicio_adicionar_ou_deletar(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    acao = context.user_data.get('inicio_acao')
    if query.data == 'cancelar':
        await cancel(update, context)
        return ConversationHandler.END

    if query.data == 'deletar':

        if acao == 'texto2':
            await query.message.edit_text(f"⛔ Não e possivel deletar o texto 2.")
            context.user_data['conv_state'] = False
            return ConversationHandler.END
        if acao == 'botao':
            await query.message.edit_text(f"⛔ Não e possivel deletar o botão.")
            context.user_data['conv_state'] = False
            return ConversationHandler.END




        context.user_data['inicio_context'][acao] = False
        await query.message.edit_text(f"✅ {acao.capitalize()} foi deletado com sucesso.")
        manager.update_bot_config(context.bot_data['id'], context.user_data['inicio_context'])
        
        context.user_data['conv_state'] = False
        return ConversationHandler.END

    elif query.data == 'adicionar':
        keyboard = [[InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if acao == "midia":
            await query.message.edit_text("🎥 Envie a mídia inicial.", reply_markup=reply_markup)
        elif acao in ["texto1", "texto2"]:
            await query.message.edit_text(f"📝 Envie o novo valor para {acao.capitalize()}.", reply_markup=reply_markup)
        elif acao == "botao":
            await query.message.edit_text("🔘 Envie o novo texto para o botão.", reply_markup=reply_markup)
        return INICIO_RECEBER

async def inicio_receber(update: Update, context: ContextTypes.DEFAULT_TYPE):
    acao = context.user_data.get('inicio_acao')
    for i in range(10):
        print('receber')
    mensagem = update.message.text if update.message else None
    try:
        if acao == "midia":
            if update.message.photo or update.message.video:
                media_file = await (update.message.photo[-1] if update.message.photo else update.message.video).get_file()
                context.user_data['inicio_context']['midia'] = {
                    'file': media_file.file_id,
                    'type': 'photo' if update.message.photo else 'video'
                }
                await update.message.reply_text("✅ Mídia inicial atualizada com sucesso.")
                manager.update_bot_config(context.bot_data['id'], context.user_data['inicio_context'])
            else:
                for i in range(10):
                    print('erro')
                await update.message.reply_text("⛔ Envie uma mídia válida (foto ou vídeo).", reply_markup=cancel_markup)
                return INICIO_RECEBER

        elif acao in ["texto1", "texto2"]:
            if update.message.photo or update.message.video:
                await update.message.reply_text(f"⛔ Envie apenas texto, midia não suportada", reply_markup=cancel_markup)
                return INICIO_RECEBER
            context.user_data['inicio_context'][acao] = mensagem
            await update.message.reply_text(f"✅ {acao.capitalize()} atualizado com sucesso.")
            manager.update_bot_config(context.bot_data['id'], context.user_data['inicio_context'])
        elif acao == "botao":
            if update.message.photo or update.message.video:
                await update.message.reply_text(f"⛔ Envie apenas texto, midia não suportada", reply_markup=cancel_markup)
                return INICIO_RECEBER
            context.user_data['inicio_context']['button'] = mensagem
            await update.message.reply_text("✅ Botão atualizado com sucesso.")
            manager.update_bot_config(context.bot_data['id'], context.user_data['inicio_context'])

    except Exception as e:
        print('erro')
        await update.message.reply_text(f"⛔ Erro ao modificar o inicio: {str(e)}")
        context.user_data['conv_state'] = False
        return ConversationHandler.END

    context.user_data['conv_state'] = False
    return ConversationHandler.END


conv_handler_inicio = ConversationHandler(
    entry_points=[CommandHandler("inicio", inicio)],
    states={
        INICIO_ESCOLHA: [CallbackQueryHandler(inicio_escolha)],
        INICIO_ADICIONAR_OU_DELETAR: [CallbackQueryHandler(inicio_adicionar_ou_deletar)],
        INICIO_RECEBER: [MessageHandler(filters.ALL, inicio_receber)]
    },
    fallbacks=[CallbackQueryHandler(cancel)],
)