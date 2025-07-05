import modules.manager as manager
import json, re, requests


from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters, Updater, CallbackContext, ChatJoinRequestHandler
from telegram.error import BadRequest, Conflict

from modules.utils import process_command, is_admin, cancel, error_callback, error_message, escape_markdown_v2

PLANOS_ESCOLHA, PLANOS_DELETAR, PLANOS_NOME, PLANOS_VALOR, PLANOS_TEMPO_TIPO, PLANOS_TEMPO, PLANOS_CONFIRMAR = range(7)


# /planos função
async def planos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command_check = await process_command(update, context)
    if not command_check:
        return ConversationHandler.END
    if not await is_admin(context, update.message.from_user.id):
        
        return ConversationHandler.END
    context.user_data['conv_state'] = "planos"

    keyboard = False

    plan_list = manager.get_bot_plans(context.bot_data['id'])
    if len(plan_list) > 0:
        keyboard = [
            [InlineKeyboardButton("➕ ADICIONAR", callback_data="adicionar"), InlineKeyboardButton("➖ REMOVER", callback_data="remover")],
            [InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]]
    else:
        keyboard = [
            [InlineKeyboardButton("➕ ADICIONAR", callback_data="adicionar")],
            [InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("💎 Qual ação deseja fazer com os planos:", reply_markup=reply_markup)
    return PLANOS_ESCOLHA

async def planos_escolha(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query.data == 'cancelar':
        await cancel(update, context)
        return ConversationHandler.END
    elif query.data == 'adicionar':
        context.user_data['plan_context'] = {
            'name':False,
            'value':False,
            'time_type':False,
            'time':False
            }
        await query.message.edit_text("💎 Envie o nome do plano:", reply_markup=reply_markup)
        return PLANOS_NOME
    elif query.data == 'remover':
        planos = manager.get_bot_plans(context.bot_data['id'])
        keyboard_plans = []
        for plan_index in range(len(planos)):
            keyboard_plans.append([InlineKeyboardButton(planos[plan_index]['name'], callback_data=f"planor_{plan_index}")])
        keyboard_plans.append([InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")])
        markup_plans = InlineKeyboardMarkup(keyboard_plans)
        await query.message.edit_text("💎 Qual plano você deseja deletar:", reply_markup=markup_plans, parse_mode='MarkdownV2')
        return PLANOS_DELETAR

async def planos_deletar(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    if query.data == 'cancelar':
        await cancel(update, context)
        return ConversationHandler.END
    plano_index = query.data.split('_')[-1]
    try:
        plano_index = int(plano_index)
        planos = manager.get_bot_plans(context.bot_data['id'])
        planos.pop(plano_index)
        manager.update_bot_plans(context.bot_data['id'] ,planos)
        await query.message.edit_text("✅ Plano deletado com sucesso")
    except:
        await query.message.edit_text("⛔ Erro ao identificar ação, Todos os comandos cancelados")
    finally:
        context.user_data['conv_state'] = False
        return ConversationHandler.END

async def plano_nome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text:
        await update.message.reply_text(text=f"⛔ Formato de midia invalido, por favor envie apenas textos")
        return PLANOS_NOME
    keyboard = [
        [InlineKeyboardButton(f"Dias", callback_data='unidade_dia')],
        [InlineKeyboardButton(f"Semanas", callback_data='unidade_semana')],
        [InlineKeyboardButton(f"Meses", callback_data='unidade_mes')],
        [InlineKeyboardButton(f"Anos", callback_data='unidade_ano')],
        [InlineKeyboardButton(f"Vitalicio", callback_data='unidade_eterno')],
        [InlineKeyboardButton('Cancelar', callback_data='cancelar')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.user_data['plan_context']['name'] = update.message.text
    await update.message.reply_text("💎 Escolha abaixo a unidade de tempo do seu plano\:\n>Exemplo\: Semanas \- 3 Semanas\(O numero sera inserido a seguir\)", reply_markup=reply_markup, parse_mode='MarkdownV2')
    return PLANOS_TEMPO_TIPO

async def plano_tempo_tipo(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query.data == 'cancelar':
        await cancel(update, context)
        return ConversationHandler.END
    context.user_data['plan_context']['time_type'] = query.data.split('_')[-1]
    if query.data.split('_')[-1] == "eterno":
        context.user_data['plan_context']['time'] = 'eterno'
        await query.message.edit_text("💎 Envie o valor que deseja para o plano", reply_markup=reply_markup)
        return PLANOS_VALOR
    else:
        names = {
            'dia':'dias',
            'semana':'semanas',
            'mes':'meses',
            'ano':'anos'
        }
        await query.message.edit_text(f"💎 Envie o numero de {names[context.user_data['plan_context']['time_type']]} deseja para o plano", reply_markup=reply_markup)
        return PLANOS_TEMPO


async def plano_tempo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text:
        await update.message.reply_text(text=f"⛔ Formato de midia invalido, por favor envie apenas textos")
        return PLANOS_TEMPO
    try:
        keyboard = [[InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        tempo = int(update.message.text)
        if tempo < 0:
        
            await update.message.reply_text("⛔ O tempo deve ser positivo:", reply_markup=reply_markup)
            return PLANOS_TEMPO
        

        context.user_data['plan_context']['time'] = tempo
        await update.message.reply_text("💎 Envie o valor que deseja para o plano:", reply_markup=reply_markup)
        return PLANOS_VALOR
    except:
        await update.message.reply_text("⛔ Envie um tempo valido:", reply_markup=reply_markup)
        return PLANOS_TEMPO

async def plano_valor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text:
        await update.message.reply_text(text=f"⛔ Formato de midia invalido, por favor envie apenas textos")
        return PLANOS_VALOR
    try:
        keyboard = [[InlineKeyboardButton("✅ Confirmar", callback_data="confirmar")],
            [InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]]


        keyboard2 = [[InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        reply_markup2 = InlineKeyboardMarkup(keyboard2)
        valor = float(update.message.text.replace(',','.'))
        if valor < 4:
            await update.message.reply_text("⛔ O valor deve ser positivo e maior que 4: ", reply_markup=reply_markup2)
            return PLANOS_VALOR
        
        names = {
            'dia':'dias',
            'semana':'semanas',
            'mes':'meses',
            'ano':'anos'
        }
        plano = context.user_data['plan_context']
        if plano['time'] == 1:
            names = {
            'dia':'dia',
            'semana':'semana',
            'mes':'mes',
            'ano':'ano'
        }
        context.user_data['plan_context']['value'] = valor
        
        print(context.user_data['plan_context'])
        if plano['time_type'] == 'eterno':
            await update.message.reply_text(f"Plano selecionado com sucesso\.\n\n>• Título\: {escape_markdown_v2(plano['name'])}\n>• Duração\: Vitalicio\n>• Valor\: R\$ {escape_markdown_v2(str(valor))}", reply_markup=reply_markup, parse_mode='MarkdownV2')
        else: 
            await update.message.reply_text(f"Plano selecionado com sucesso\.\n\n>• Título\: {escape_markdown_v2(plano['name'])}\n>• Duração\: {plano['time']} {names[plano['time_type']]}\n>• Valor\: R\$ {escape_markdown_v2(str(valor))}", reply_markup=reply_markup, parse_mode='MarkdownV2')
        return PLANOS_CONFIRMAR
    except Exception as e:
        print(e)
        await update.message.reply_text("⛔ Envie um valor numerico valido:")
        return PLANOS_VALOR

async def plano_confirmar(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    print('query:'+query.data)
    if query.data == 'cancelar':
        await cancel(update, context)
        return ConversationHandler.END

    plano = context.user_data['plan_context']
    planos = manager.get_bot_plans(context.bot_data['id'])
    planos.append(plano)
    print(planos)
    manager.update_bot_plans(context.bot_data['id'] , planos)
    await query.message.edit_text("✅ Plano criado com sucesso")
    context.user_data['plan_context'] = False
    context.user_data['conv_state'] = False
    return ConversationHandler.END



conv_handler_planos = ConversationHandler(
    entry_points=[CommandHandler("planos", planos)],
    states={
        PLANOS_ESCOLHA: [CallbackQueryHandler(planos_escolha)],
        PLANOS_DELETAR: [CallbackQueryHandler(planos_deletar)],
        PLANOS_NOME: [MessageHandler(~filters.COMMAND, plano_nome), CallbackQueryHandler(cancel)],
        PLANOS_TEMPO_TIPO:[CallbackQueryHandler(plano_tempo_tipo)],
        PLANOS_TEMPO:[MessageHandler(~filters.COMMAND, plano_tempo), CallbackQueryHandler(cancel)],
        PLANOS_VALOR:[MessageHandler(~filters.COMMAND, plano_valor), CallbackQueryHandler(cancel)],
        PLANOS_CONFIRMAR:[CallbackQueryHandler(plano_confirmar)],
    },
    fallbacks=[CallbackQueryHandler(error_callback)]
    )


#PLANO
#{
#'nome'
#'valor'
#'tempo'
#'recuperação' - não solicitado
#}
