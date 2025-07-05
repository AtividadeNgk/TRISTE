import modules.manager as manager
import json

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from modules.utils import process_command, is_admin, cancel, error_callback, escape_markdown_v2

# Estados da conversa
ORDERBUMP_ESCOLHA, ORDERBUMP_PLANO, ORDERBUMP_MENSAGEM, ORDERBUMP_VALOR, ORDERBUMP_CONFIRMAR, ORDERBUMP_DELETAR = range(6)

keyboardc = [
    [InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]
]
cancel_markup = InlineKeyboardMarkup(keyboardc)

async def orderbump(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command_check = await process_command(update, context)
    if not command_check:
        return ConversationHandler.END
    
    if not await is_admin(context, update.message.from_user.id):
        return ConversationHandler.END
    
    context.user_data['conv_state'] = "orderbump"
    
    # Verifica se existem planos
    planos = manager.get_bot_plans(context.bot_data['id'])
    if len(planos) == 0:
        await update.message.reply_text("⛔ Nenhum plano cadastrado. Crie planos primeiro usando /planos")
        context.user_data['conv_state'] = False
        return ConversationHandler.END
    
    # Verifica quais planos já tem order bump
    orderbumps = manager.get_bot_orderbump(context.bot_data['id'])
    planos_com_ob = [ob.get('plano_id') for ob in orderbumps]
    
    keyboard = []
    if len(planos) > len(planos_com_ob):  # Ainda há planos sem order bump
        keyboard.append([InlineKeyboardButton("➕ ADICIONAR", callback_data="adicionar")])
    if len(planos_com_ob) > 0:  # Há order bumps para remover
        keyboard.append([InlineKeyboardButton("➖ REMOVER", callback_data="remover")])
    keyboard.append([InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("💰 Qual ação deseja fazer com os Order Bumps?", reply_markup=reply_markup)
    return ORDERBUMP_ESCOLHA

async def orderbump_escolha(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancelar':
        await cancel(update, context)
        return ConversationHandler.END
    
    elif query.data == 'adicionar':
        context.user_data['orderbump_action'] = 'adicionar'
        planos = manager.get_bot_plans(context.bot_data['id'])
        orderbumps = manager.get_bot_orderbump(context.bot_data['id'])
        planos_com_ob = [ob.get('plano_id') for ob in orderbumps]
        
        keyboard_plans = []
        for plan_index in range(len(planos)):
            if plan_index not in planos_com_ob:  # Só mostra planos sem order bump
                keyboard_plans.append([
                    InlineKeyboardButton(
                        f'{planos[plan_index]["name"]} - R$ {planos[plan_index]["value"]}',
                        callback_data=f"ob_plano_{plan_index}"
                    )
                ])
        
        keyboard_plans.append([InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")])
        markup_plans = InlineKeyboardMarkup(keyboard_plans)
        
        await query.message.edit_text(
            "💰 Em qual plano deseja adicionar o Order Bump?",
            reply_markup=markup_plans
        )
        return ORDERBUMP_PLANO
    
    elif query.data == 'remover':
        context.user_data['orderbump_action'] = 'remover'
        planos = manager.get_bot_plans(context.bot_data['id'])
        orderbumps = manager.get_bot_orderbump(context.bot_data['id'])
        
        keyboard_plans = []
        for ob in orderbumps:
            plan_index = ob.get('plano_id')
            if plan_index < len(planos):
                keyboard_plans.append([
                    InlineKeyboardButton(
                        f'{planos[plan_index]["name"]} - R$ {ob.get("value", 0)}',
                        callback_data=f"ob_del_{plan_index}"
                    )
                ])
        
        keyboard_plans.append([InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")])
        markup_plans = InlineKeyboardMarkup(keyboard_plans)
        
        await query.message.edit_text(
            "💰 Qual Order Bump deseja remover?",
            reply_markup=markup_plans
        )
        return ORDERBUMP_DELETAR

async def orderbump_plano(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancelar':
        await cancel(update, context)
        return ConversationHandler.END
    
    plano_index = int(query.data.split('_')[-1])
    context.user_data['orderbump_plano_index'] = plano_index
    
    # Inicializa o contexto do order bump
    context.user_data['orderbump_context'] = {
        'plano_id': plano_index,
        'media': False,
        'text': False,
        'value': False
    }
    
    await query.message.edit_text(
        "💰 Envie o texto junto com a mídia para o Order Bump\n"
        "> Esta será a oferta adicional mostrada ao cliente",
        reply_markup=cancel_markup
    )
    return ORDERBUMP_MENSAGEM

async def orderbump_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        save = {
            'media': False,
            'text': False
        }
        
        # Verifica se tem mídia
        if update.message.photo:
            photo_file = await update.message.photo[-1].get_file()
            save['media'] = {
                'file': photo_file.file_id,
                'type': 'photo'
            }
        elif update.message.video:
            video_file = await update.message.video.get_file()
            save['media'] = {
                'file': video_file.file_id,
                'type': 'video'
            }
        elif update.message.text:
            save['text'] = update.message.text
        else:
            await update.message.reply_text("⛔ Somente texto ou mídia são permitidos:", reply_markup=cancel_markup)
            return ORDERBUMP_MENSAGEM
        
        # Captura caption se houver
        if update.message.caption:
            save['text'] = update.message.caption
        
        # Valida se tem conteúdo
        if not save['text'] and not save['media']:
            await update.message.reply_text("⛔ Envie pelo menos um texto ou mídia:", reply_markup=cancel_markup)
            return ORDERBUMP_MENSAGEM
        
        # Salva no contexto
        context.user_data['orderbump_context']['media'] = save['media']
        context.user_data['orderbump_context']['text'] = save['text']
        
        await update.message.reply_text(
            "💰 Agora, selecione qual o valor do seu Order Bump\n"
            "> Este valor será somado ao valor do plano",
            reply_markup=cancel_markup
        )
        return ORDERBUMP_VALOR
        
    except Exception as e:
        await update.message.reply_text(f"⛔ Erro ao salvar mensagem: {str(e)}")
        context.user_data['conv_state'] = False
        return ConversationHandler.END

async def orderbump_valor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text:
        await update.message.reply_text("⛔ Por favor, envie apenas o valor numérico:", reply_markup=cancel_markup)
        return ORDERBUMP_VALOR
    
    try:
        valor = float(update.message.text.replace(',', '.'))
        if valor <= 0:
            await update.message.reply_text("⛔ O valor deve ser maior que zero:", reply_markup=cancel_markup)
            return ORDERBUMP_VALOR
        
        context.user_data['orderbump_context']['value'] = valor
        
        # Pega informações do plano
        planos = manager.get_bot_plans(context.bot_data['id'])
        plano_index = context.user_data['orderbump_plano_index']
        plano = planos[plano_index]
        
        # Monta mensagem de confirmação
        keyboard = [
            [InlineKeyboardButton("✅ CRIAR", callback_data="confirmar")],
            [InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        valor_total = plano['value'] + valor
        
        await update.message.reply_text(
            f"💰 Confirme o Order Bump:\n\n"
            f"📦 Plano: {escape_markdown_v2(plano['name'])}\n"
            f"💵 Valor do plano: R$ {escape_markdown_v2(str(plano['value']))}\n"
            f"➕ Valor do Order Bump: R$ {escape_markdown_v2(str(valor))}\n"
            f"💰 Valor total se aceitar: R$ {escape_markdown_v2(str(valor_total))}\n\n"
            f"Deseja criar este Order Bump?",
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )
        return ORDERBUMP_CONFIRMAR
        
    except ValueError:
        await update.message.reply_text("⛔ Envie um valor numérico válido:", reply_markup=cancel_markup)
        return ORDERBUMP_VALOR

async def orderbump_confirmar(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancelar':
        await cancel(update, context)
        return ConversationHandler.END
    
    elif query.data == 'confirmar':
        try:
            # Salva o order bump
            orderbump_data = context.user_data['orderbump_context']
            bot_id = context.bot_data['id']
            plan_index = context.user_data['orderbump_plano_index']
            
            manager.add_orderbump_to_plan(bot_id, plan_index, orderbump_data)
            
            await query.message.edit_text("✅ Order Bump criado com sucesso!")
            
        except Exception as e:
            await query.message.edit_text(f"⛔ Erro ao criar Order Bump: {str(e)}")
        
        context.user_data['conv_state'] = False
        return ConversationHandler.END

async def orderbump_deletar(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancelar':
        await cancel(update, context)
        return ConversationHandler.END
    
    try:
        plano_index = int(query.data.split('_')[-1])
        manager.remove_orderbump_from_plan(context.bot_data['id'], plano_index)
        
        await query.message.edit_text("✅ Order Bump removido com sucesso!")
        
    except Exception as e:
        await query.message.edit_text(f"⛔ Erro ao remover Order Bump: {str(e)}")
    
    context.user_data['conv_state'] = False
    return ConversationHandler.END

# ConversationHandler
conv_handler_orderbump = ConversationHandler(
    entry_points=[CommandHandler("orderbump", orderbump)],
    states={
        ORDERBUMP_ESCOLHA: [CallbackQueryHandler(orderbump_escolha)],
        ORDERBUMP_PLANO: [CallbackQueryHandler(orderbump_plano)],
        ORDERBUMP_MENSAGEM: [MessageHandler(~filters.COMMAND, orderbump_mensagem), CallbackQueryHandler(cancel)],
        ORDERBUMP_VALOR: [MessageHandler(~filters.COMMAND, orderbump_valor), CallbackQueryHandler(cancel)],
        ORDERBUMP_CONFIRMAR: [CallbackQueryHandler(orderbump_confirmar)],
        ORDERBUMP_DELETAR: [CallbackQueryHandler(orderbump_deletar)]
    },
    fallbacks=[CallbackQueryHandler(error_callback)]
)