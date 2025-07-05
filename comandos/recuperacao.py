import modules.manager as manager
import json

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from modules.utils import process_command, is_admin, cancel, error_callback, escape_markdown_v2

# Estados da conversa
RECUPERACAO_ESCOLHA, RECUPERACAO_ACAO, RECUPERACAO_MENSAGEM, RECUPERACAO_PORCENTAGEM, RECUPERACAO_UNIDADE_TEMPO, RECUPERACAO_TEMPO, RECUPERACAO_CONFIRMAR, RECUPERACAO_DELETAR = range(8)

keyboardc = [
    [InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]
]
cancel_markup = InlineKeyboardMarkup(keyboardc)

async def recuperacao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command_check = await process_command(update, context)
    if not command_check:
        return ConversationHandler.END
    
    if not await is_admin(context, update.message.from_user.id):
        return ConversationHandler.END
    
    context.user_data['conv_state'] = "recuperacao"
    
    # Pega as recuperações configuradas
    recoveries = manager.get_bot_recovery(context.bot_data['id'])
    
    # Monta os botões das 5 recuperações
    keyboard = []
    for i in range(5):
        emoji = "✅" if (len(recoveries) > i and recoveries[i] is not None) else ""
        keyboard.append([InlineKeyboardButton(f"{emoji} RECUPERAÇÃO {i+1}", callback_data=f"rec_{i}")])
    
    # Adiciona botão de remover se houver alguma recuperação
    has_recovery = any(r is not None for r in recoveries if recoveries)
    if has_recovery:
        keyboard.append([InlineKeyboardButton("➖ REMOVER", callback_data="remover")])
    
    keyboard.append([InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔄 Selecione qual recuperação deseja configurar:", reply_markup=reply_markup)
    return RECUPERACAO_ESCOLHA

async def recuperacao_escolha(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancelar':
        await cancel(update, context)
        return ConversationHandler.END
    
    elif query.data == 'remover':
        # Lista apenas recuperações configuradas para remover
        recoveries = manager.get_bot_recovery(context.bot_data['id'])
        keyboard = []
        
        for i in range(5):
            if len(recoveries) > i and recoveries[i] is not None:
                rec = recoveries[i]
                tempo_str = f"{rec['tempo']} {rec['unidade_tempo']}"
                keyboard.append([
                    InlineKeyboardButton(
                        f"Recuperação {i+1}: {rec['porcentagem']}% em {tempo_str}", 
                        callback_data=f"del_{i}"
                    )
                ])
        
        keyboard.append([InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text("🔄 Qual recuperação deseja remover?", reply_markup=reply_markup)
        return RECUPERACAO_DELETAR
    
    elif query.data.startswith('rec_'):
        recovery_index = int(query.data.split('_')[1])
        context.user_data['recovery_index'] = recovery_index
        
        # Inicia configuração da recuperação
        context.user_data['recovery_context'] = {
            'index': recovery_index,
            'media': False,
            'text': False,
            'porcentagem': False,
            'unidade_tempo': False,
            'tempo': False
        }
        
        await query.message.edit_text(
            f"🔄 Configurando RECUPERAÇÃO {recovery_index + 1}\n\n"
            "📝 Envie o post (mídia + texto) que será enviado nesta recuperação:",
            reply_markup=cancel_markup
        )
        return RECUPERACAO_MENSAGEM

async def recuperacao_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            return RECUPERACAO_MENSAGEM
        
        # Captura caption se houver
        if update.message.caption:
            save['text'] = update.message.caption
        
        # Salva no contexto
        context.user_data['recovery_context']['media'] = save['media']
        context.user_data['recovery_context']['text'] = save['text']
        
        await update.message.reply_text(
            "💸 Quantos % de desconto deseja aplicar nesta recuperação?\n"
            "> Digite apenas o número (ex: 10 para 10%)",
            reply_markup=cancel_markup
        )
        return RECUPERACAO_PORCENTAGEM
        
    except Exception as e:
        await update.message.reply_text(f"⛔ Erro ao salvar mensagem: {str(e)}")
        context.user_data['conv_state'] = False
        return ConversationHandler.END

async def recuperacao_porcentagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text:
        await update.message.reply_text("⛔ Por favor, envie apenas o número:", reply_markup=cancel_markup)
        return RECUPERACAO_PORCENTAGEM
    
    try:
        porcentagem = float(update.message.text.replace(',', '.'))
        if porcentagem <= 0 or porcentagem >= 100:
            await update.message.reply_text("⛔ A porcentagem deve estar entre 1 e 99:", reply_markup=cancel_markup)
            return RECUPERACAO_PORCENTAGEM
        
        context.user_data['recovery_context']['porcentagem'] = porcentagem
        
        # Monta teclado para escolher unidade de tempo
        keyboard = [
            [InlineKeyboardButton("Segundos", callback_data="tempo_segundos")],
            [InlineKeyboardButton("Minutos", callback_data="tempo_minutos")],
            [InlineKeyboardButton("Horas", callback_data="tempo_horas")],
            [InlineKeyboardButton("Dias", callback_data="tempo_dias")],
            [InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⏰ Selecione a unidade de tempo para o disparo:",
            reply_markup=reply_markup
        )
        return RECUPERACAO_UNIDADE_TEMPO
        
    except ValueError:
        await update.message.reply_text("⛔ Envie um número válido:", reply_markup=cancel_markup)
        return RECUPERACAO_PORCENTAGEM

async def recuperacao_unidade_tempo(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancelar':
        await cancel(update, context)
        return ConversationHandler.END
    
    unidade = query.data.split('_')[1]
    context.user_data['recovery_context']['unidade_tempo'] = unidade
    
    await query.message.edit_text(
        f"⏰ Quantos {unidade} após o /start deseja disparar esta recuperação?\n"
        "> Máximo permitido: 7 dias no total",
        reply_markup=cancel_markup
    )
    return RECUPERACAO_TEMPO

async def recuperacao_tempo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text:
        await update.message.reply_text("⛔ Por favor, envie apenas o número:", reply_markup=cancel_markup)
        return RECUPERACAO_TEMPO
    
    try:
        tempo = int(update.message.text)
        if tempo <= 0:
            await update.message.reply_text("⛔ O tempo deve ser maior que zero:", reply_markup=cancel_markup)
            return RECUPERACAO_TEMPO
        
        # Valida se não excede 7 dias
        unidade = context.user_data['recovery_context']['unidade_tempo']
        tempo_em_minutos = tempo
        
        if unidade == 'segundos':
            tempo_em_minutos = tempo / 60
        elif unidade == 'horas':
            tempo_em_minutos = tempo * 60
        elif unidade == 'dias':
            tempo_em_minutos = tempo * 24 * 60
        
        if tempo_em_minutos > 7 * 24 * 60:  # 7 dias em minutos
            await update.message.reply_text("⛔ O tempo máximo é 7 dias:", reply_markup=cancel_markup)
            return RECUPERACAO_TEMPO
        
        context.user_data['recovery_context']['tempo'] = tempo
        
        # Monta mensagem de confirmação
        rec = context.user_data['recovery_context']
        keyboard = [
            [InlineKeyboardButton("✅ CONFIRMAR", callback_data="confirmar")],
            [InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        tempo_str = f"{tempo} {unidade}"
        
        await update.message.reply_text(
            f"📋 CONFIRME A RECUPERAÇÃO {rec['index'] + 1}:\n\n"
            f"⏰ Tempo: {tempo_str} após /start\n"
            f"💸 Desconto: {rec['porcentagem']}%\n"
            f"📝 Mensagem configurada\n\n"
            f"Deseja criar esta recuperação?",
            reply_markup=reply_markup
        )
        return RECUPERACAO_CONFIRMAR
        
    except ValueError:
        await update.message.reply_text("⛔ Envie um número válido:", reply_markup=cancel_markup)
        return RECUPERACAO_TEMPO

async def recuperacao_confirmar(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancelar':
        await cancel(update, context)
        return ConversationHandler.END
    
    elif query.data == 'confirmar':
        try:
            # Salva a recuperação
            recovery_data = context.user_data['recovery_context']
            bot_id = context.bot_data['id']
            recovery_index = recovery_data['index']
            
            # Remove o índice do dicionário antes de salvar
            recovery_to_save = {
                'media': recovery_data['media'],
                'text': recovery_data['text'],
                'porcentagem': recovery_data['porcentagem'],
                'unidade_tempo': recovery_data['unidade_tempo'],
                'tempo': recovery_data['tempo']
            }
            
            manager.add_recovery_to_bot(bot_id, recovery_index, recovery_to_save)
            
            await query.message.edit_text(f"✅ Recuperação {recovery_index + 1} criada com sucesso!")
            
        except Exception as e:
            await query.message.edit_text(f"⛔ Erro ao criar recuperação: {str(e)}")
        
        context.user_data['conv_state'] = False
        return ConversationHandler.END

async def recuperacao_deletar(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancelar':
        await cancel(update, context)
        return ConversationHandler.END
    
    try:
        recovery_index = int(query.data.split('_')[1])
        manager.remove_recovery_from_bot(context.bot_data['id'], recovery_index)
        
        await query.message.edit_text(f"✅ Recuperação {recovery_index + 1} removida com sucesso!")
        
    except Exception as e:
        await query.message.edit_text(f"⛔ Erro ao remover recuperação: {str(e)}")
    
    context.user_data['conv_state'] = False
    return ConversationHandler.END

# ConversationHandler
conv_handler_recuperacao = ConversationHandler(
    entry_points=[CommandHandler("recuperacao", recuperacao)],
    states={
        RECUPERACAO_ESCOLHA: [CallbackQueryHandler(recuperacao_escolha)],
        RECUPERACAO_MENSAGEM: [MessageHandler(~filters.COMMAND, recuperacao_mensagem), CallbackQueryHandler(cancel)],
        RECUPERACAO_PORCENTAGEM: [MessageHandler(~filters.COMMAND, recuperacao_porcentagem), CallbackQueryHandler(cancel)],
        RECUPERACAO_UNIDADE_TEMPO: [CallbackQueryHandler(recuperacao_unidade_tempo)],
        RECUPERACAO_TEMPO: [MessageHandler(~filters.COMMAND, recuperacao_tempo), CallbackQueryHandler(cancel)],
        RECUPERACAO_CONFIRMAR: [CallbackQueryHandler(recuperacao_confirmar)],
        RECUPERACAO_DELETAR: [CallbackQueryHandler(recuperacao_deletar)]
    },
    fallbacks=[CallbackQueryHandler(error_callback)]
)