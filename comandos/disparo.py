import modules.manager as manager
import json, re, requests, asyncio
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from telegram.error import BadRequest, Forbidden, TelegramError, RetryAfter

from modules.utils import process_command, is_admin, cancel, error_callback, error_message, escape_markdown_v2, check_link
from modules.actions import send_disparo

DISPARO_TIPO, DISPARO_MENSAGEM, DISPARO_VALOR_CONFIRMA, DISPARO_VALOR, DISPARO_PLANO, DISPARO_LINK, DISPARO_CONFIRMA, DISPARO_PROGRAMADO_ESCOLHA, DISPARO_PROGRAMADO_DESCONTO, DISPARO_PROGRAMADO_HORARIO, DISPARO_PROGRAMADO_CONFIRMA, DISPARO_PROGRAMADO_REMOVER = range(12)

keyboardc = [
    [InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]
]
cancel_markup = InlineKeyboardMarkup(keyboardc)

async def disparo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command_check = await process_command(update, context)
    if not command_check:
        return ConversationHandler.END

    if not await is_admin(context, update.message.from_user.id):
        return ConversationHandler.END
    
    context.user_data['inicio_context'] = manager.get_bot_config(context.bot_data['id'])
    context.user_data['conv_state'] = "disparo"

    # NOVO KEYBOARD COM PROGRAMADO
    keyboard = [
        [InlineKeyboardButton("Livre", callback_data="livre"), InlineKeyboardButton("Plano", callback_data="plano")],
        [InlineKeyboardButton("Programado", callback_data="programado")],
        [InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🛠️ Qual tipo de disparo deseja realizar?", reply_markup=reply_markup)
    return DISPARO_TIPO

async def disparo_escolha(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.user_data['disparo_payload'] = {
        'tipo': False
    }
    if query.data == 'cancelar':
        await cancel(update, context)
        return ConversationHandler.END
    elif query.data == 'programado':
        # Verifica quantos disparos programados já existem
        broadcasts = manager.get_bot_scheduled_broadcasts(context.bot_data['id'])
        
        # CORREÇÃO: Sempre mostra as opções, mesmo com 3 disparos
        keyboard = []
        
        # Só mostra adicionar se tiver menos de 3
        if len(broadcasts) < 3:
            keyboard.append([InlineKeyboardButton("➕ ADICIONAR", callback_data="prog_adicionar")])
        
        # Sempre mostra remover se tiver algum disparo
        if len(broadcasts) > 0:
            keyboard.append([InlineKeyboardButton("➖ REMOVER", callback_data="prog_remover")])
        
        keyboard.append([InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Mostra disparos existentes
        msg = "📅 DISPAROS PROGRAMADOS:\n\n"
        if broadcasts:
            for b in broadcasts:
                msg += f"• Disparo {b['id']+1}: {b['time']} - {b['discount']}% OFF\n"
        else:
            msg += "Nenhum disparo programado ainda.\n"
        
        # Adiciona aviso se já tem 3
        if len(broadcasts) >= 3:
            msg += "\n⚠️ Limite máximo de 3 disparos atingido.\n"
        
        msg += "\nO que deseja fazer?"
        
        await query.message.edit_text(msg, reply_markup=reply_markup)
        return DISPARO_PROGRAMADO_ESCOLHA
    elif query.data == 'livre':
        context.user_data['disparo_payload']['tipo'] = 'livre'
        await query.message.edit_text("💎 Envie o link para enviar no disparo:", reply_markup=reply_markup)
        return DISPARO_LINK
    elif query.data == 'plano':
        context.user_data['disparo_payload']['tipo'] = 'plano'
        planos = manager.get_bot_plans(context.bot_data['id'])
        keyboard_plans = []
        for plan_index in range(len(planos)):
            keyboard_plans.append([InlineKeyboardButton(f'{planos[plan_index]['name']} - R$ {planos[plan_index]['value']}', callback_data=f"planod_{plan_index}")])
        keyboard_plans.append([InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")])
        markup_plans = InlineKeyboardMarkup(keyboard_plans)
        await query.message.edit_text("💎 Qual plano você deseja disparar:", reply_markup=markup_plans, parse_mode='MarkdownV2')
        return DISPARO_PLANO

async def disparo_plano(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    if query.data == 'cancelar':
        await cancel(update, context)
        return ConversationHandler.END
    plano_index = query.data.split('_')[-1]
    try:
        plano_index = int(plano_index)
        planos = manager.get_bot_plans(context.bot_data['id'])
        plano = planos[plano_index]
        plano['recovery'] = False
        context.user_data['disparo_payload']['plano'] = plano
        keyboard = [
            [InlineKeyboardButton("Sim", callback_data="sim"), InlineKeyboardButton("Não", callback_data="nao")],
            [InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(f"Deseja inserir um valor diferente para o plano?", reply_markup=reply_markup)
        return DISPARO_VALOR_CONFIRMA
    except:
        await query.message.edit_text("⛔ Erro ao identificar ação, Todos os comandos cancelados")
        context.user_data['conv_state'] = False
        return ConversationHandler.END

async def disparo_valor_confirma(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancelar':
        await cancel(update, context)
        return ConversationHandler.END
    elif query.data == 'sim':
        await query.message.edit_text("Qual valor você deseja inserir no disparo:", reply_markup=cancel_markup)
        return DISPARO_VALOR
    elif query.data == 'nao':
        await query.message.edit_text("Envie a mensagem que deseja enviar no disparo:\n>Pode conter midia", reply_markup=cancel_markup)
        return DISPARO_MENSAGEM
    else:
        await query.message.edit_text("⛔ Erro ao identificar ação, Todos os comandos cancelados")
        context.user_data['conv_state'] = False
        return ConversationHandler.END

async def disparo_valor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message.text:
            await update.message.reply_text(text=f"⛔ ID Invalido, por favor envie um valido")
            return DISPARO_VALOR
        keyboard = [[InlineKeyboardButton("✅ Confirmar", callback_data="confirmar")],
                   [InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        valor = float(update.message.text.replace(',', '.'))
        if valor < 4:
            await update.message.reply_text("⛔ O valor deve ser positivo e maior que 4:", reply_markup=cancel_markup)
            return DISPARO_VALOR
        context.user_data['disparo_payload']['plano']['value'] = valor
        await update.message.reply_text("Envie a mensagem que deseja enviar no disparo:\n>Pode conter midia", reply_markup=cancel_markup)
        return DISPARO_MENSAGEM
    except Exception as e:
        print(e)
        await update.message.reply_text("⛔ Envie um valor numerico valido:")
        return DISPARO_VALOR

async def disparo_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text:
        await update.message.reply_text(text=f"⛔ Link invalido, por favor envie um valido")
        return DISPARO_LINK
    
    link_recebido = update.message.text.strip()
    keyboard = [[InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if not check_link(link_recebido):
        await update.message.reply_text("❌ Insira um link valido:", reply_markup=reply_markup)
        return DISPARO_LINK
    
    context.user_data['disparo_payload']['link'] = link_recebido
    await update.message.reply_text("Envie a mensagem que deseja enviar no disparo:\n>Pode conter midia", reply_markup=cancel_markup)
    return DISPARO_MENSAGEM

async def disparo_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        save = {
            'media': False,
            'text': False
        }
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
            await update.message.reply_text("⛔ Somente texto ou midia:")
            return DISPARO_MENSAGEM

        if update.message.caption:
            save['text'] = update.message.caption
        
        context.user_data['upsell_context'] = save
        
        # Verifica se é disparo programado
        if context.user_data.get('disparo_programado'):
            context.user_data['disparo_programado']['media'] = save['media']
            context.user_data['disparo_programado']['text'] = save['text']
            
            await update.message.reply_text(
                "💸 Qual desconto (%) deseja aplicar em todos os planos?\n"
                "Digite apenas o número (ex: 10 para 10%)",
                reply_markup=cancel_markup
            )
            return DISPARO_PROGRAMADO_DESCONTO
        
        # Continua com o fluxo normal (livre/plano)
        keyboard = [[
            InlineKeyboardButton("✅ CONFIRMAR", callback_data="confirmar"),
            InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        disparo = context.user_data['disparo_payload']
        context.user_data['disparo_payload']['mensagem'] = save
        
        if disparo.get('tipo', False) == 'livre':
            await update.message.reply_text(f"Confirme o disparo\:", reply_markup=reply_markup)
            return DISPARO_CONFIRMA
        elif disparo.get('tipo', False) == 'plano':
            plano = disparo.get('plano', False)
            if not plano:
                await update.message.reply_text(text="⛔ Erro ao identificar plano de disparo", parse_mode='MarkdownV2')
                context.user_data['conv_state'] = False
                return ConversationHandler.END
            names = {
                'dia': 'dias',
                'semana': 'semanas',
                'mes': 'meses',
                'ano': 'anos',
                'eterno': ''
            }
            if plano['time'] == 1:
                names = {
                    'dia': 'dia',
                    'semana': 'semana',
                    'mes': 'mes',
                    'ano': 'ano',
                    'eterno': ''
                }
            if plano['time_type'] != 'eterno':
                await update.message.reply_text(f"Confirme o disparo\:\n>Nome\: {escape_markdown_v2(plano['name'])}\n>Tempo\: {escape_markdown_v2(plano['time'])} {names[plano['time_type']]}\n>Valor\: {escape_markdown_v2(str(plano['value']))}", parse_mode='MarkdownV2', reply_markup=reply_markup)
            else:
                await update.message.reply_text(f"Confirme o disparo\:\n>Nome\: {escape_markdown_v2(plano['name'])}\n>Tempo\: Vitalicio\n>Valor\: {escape_markdown_v2(str(plano['value']))}", parse_mode='MarkdownV2', reply_markup=reply_markup)
            return DISPARO_CONFIRMA
        else:
            await update.message.reply_text(text="⛔ Erro ao identificar tipo de disparo", parse_mode='MarkdownV2')
            context.user_data['conv_state'] = False
            return ConversationHandler.END
    
    except Exception as e:
        await update.message.reply_text(text=f"⛔ Erro ao receber mensagem de disparo {str(e)}")
        context.user_data['conv_state'] = False
        return ConversationHandler.END

async def disparo_confirma(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancelar':
        await cancel(update, context)
        return ConversationHandler.END
    elif query.data == 'confirmar':
        users = manager.get_bot_users(context.bot_data['id'])
        total_users = len(users)
        
        # Mensagem inicial
        message = await context.bot.send_message(
            query.from_user.id, 
            f'🚀 𝗗𝗜𝗦𝗣𝗔𝗥𝗢 𝗜𝗡𝗜𝗖𝗜𝗔𝗗𝗢:\n\n'
            f'👤 Total: {total_users} usuários\n'
            f'⏳ Processando...'
        )
        
        # Contadores
        enviados = 0
        erros = 0
        bloqueados = 0
        inativos = 0
        
        # Armazena detalhes dos erros
        erro_detalhes = {
            'blocked': [],
            'inactive': [],
            'other': []
        }
        
        # Timestamp para controle de atualizações
        last_update = datetime.now()
        update_interval = 5  # Atualiza a cada 5 segundos
        
        # Loop principal de envio
        for i, user_id in enumerate(users):
            try:
                # Envia mensagem
                sucesso = await send_disparo(context, user_id, context.user_data['disparo_payload'])
                
                if sucesso:
                    enviados += 1
                else:
                    erros += 1
                    erro_detalhes['other'].append(user_id)
                
            except Forbidden as e:
                # Usuário bloqueou o bot
                bloqueados += 1
                erro_detalhes['blocked'].append(user_id)
                erros += 1
                
            except BadRequest as e:
                if "user is deactivated" in str(e).lower():
                    # Usuário desativou a conta
                    inativos += 1
                    erro_detalhes['inactive'].append(user_id)
                    erros += 1
                else:
                    # Outros erros BadRequest
                    erros += 1
                    erro_detalhes['other'].append(user_id)
                    
            except RetryAfter as e:
                # Rate limit - aguarda o tempo especificado
                await asyncio.sleep(e.retry_after)
                # Tenta novamente
                try:
                    sucesso = await send_disparo(context, user_id, context.user_data['disparo_payload'])
                    if sucesso:
                        enviados += 1
                    else:
                        erros += 1
                        erro_detalhes['other'].append(user_id)
                except Exception:
                    erros += 1
                    erro_detalhes['other'].append(user_id)
                    
            except Exception as e:
                # Outros erros
                print(f"Erro ao enviar para {user_id}: {str(e)}")
                erros += 1
                erro_detalhes['other'].append(user_id)
            
            # Delay entre mensagens para evitar flood
            await asyncio.sleep(0.2)  # 50ms entre cada envio (~20 msgs/seg)
            
            # Atualiza mensagem de progresso periodicamente
            now = datetime.now()
            if (now - last_update).seconds >= update_interval:
                try:
                    progress = int((i + 1) / total_users * 100)
                    await message.edit_text(
                        f'🚀 𝗗𝗜𝗦𝗣𝗔𝗥𝗢 𝗘𝗠 𝗣𝗥𝗢𝗚𝗥𝗘𝗦𝗦𝗢:\n\n'
                        f'📊 Progresso: {progress}%\n'
                        f'✅ Enviados: {enviados}\n'
                        f'⛔ Erros: {erros}\n'
                        f'🚫 Bloqueados: {bloqueados}\n'
                        f'💤 Inativos: {inativos}\n'
                        f'⏳ Restantes: {total_users - (i + 1)}'
                    )
                    last_update = now
                except Exception:
                    # Ignora erros ao atualizar mensagem
                    pass
        
        # Mensagem final com resumo
        await message.edit_text(
            f'✅ 𝗗𝗜𝗦𝗣𝗔𝗥𝗢 𝗙𝗜𝗡𝗔𝗟𝗜𝗭𝗔𝗗𝗢!\n\n'
            f'📊 Resumo:\n'
            f'👤 Total: {total_users} usuários\n'
            f'✅ Enviados: {enviados} ({int(enviados/total_users*100)}%)\n'
            f'⛔ Erros: {erros}\n'
            f'🚫 Bloqueados: {bloqueados}\n'
            f'💤 Inativos: {inativos}'
        )
        
        # Relatório detalhado de erros se houver
        if erros > 0:
            relatorio = f'📋 RELATÓRIO DE ERROS:\n\n'
            
            if bloqueados > 0:
                relatorio += f'🚫 Usuários que bloquearam o bot: {bloqueados}\n'
                # Opcional: remover usuários bloqueados da lista
                # for blocked_id in erro_detalhes['blocked']:
                #     users.remove(blocked_id)
                # manager.update_bot_users(context.bot_data['id'], users)
            
            if inativos > 0:
                relatorio += f'💤 Usuários com conta desativada: {inativos}\n'
            
            if len(erro_detalhes['other']) > 0:
                relatorio += f'❓ Outros erros: {len(erro_detalhes['other'])}\n'
            
            await context.bot.send_message(query.from_user.id, relatorio)
        
        context.user_data['conv_state'] = False
        return ConversationHandler.END
    
async def disparo_programado_escolha(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancelar':
        await cancel(update, context)
        return ConversationHandler.END
    
    elif query.data == 'prog_adicionar':
        context.user_data['disparo_programado'] = {
            'media': False,
            'text': False,
            'discount': False,
            'time': False
        }
        
        await query.message.edit_text(
            "📅 NOVO DISPARO PROGRAMADO\n\n"
            "Envie a mensagem que será disparada (pode conter mídia):",
            reply_markup=cancel_markup
        )
        return DISPARO_MENSAGEM
    
    elif query.data == 'prog_remover':
        broadcasts = manager.get_bot_scheduled_broadcasts(context.bot_data['id'])
        keyboard = []
        
        for broadcast in broadcasts:
            keyboard.append([
                InlineKeyboardButton(
                    f"Disparo {broadcast['id']+1}: {broadcast['time']} - {broadcast['discount']}% OFF",
                    callback_data=f"remover_{broadcast['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(
            "📅 Qual disparo programado deseja remover?",
            reply_markup=reply_markup
        )
        return DISPARO_PROGRAMADO_REMOVER

async def disparo_programado_remover(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancelar':
        await cancel(update, context)
        return ConversationHandler.END
    
    broadcast_id = int(query.data.split('_')[1])
    manager.remove_scheduled_broadcast(context.bot_data['id'], broadcast_id)
    
    # Reinicia as tasks do bot
    import modules.scheduled_broadcast as scheduled_broadcast
    scheduled_broadcast.start_scheduled_broadcasts_for_bot(context, context.bot_data['id'])
    
    await query.message.edit_text("✅ Disparo programado removido com sucesso!")
    context.user_data['conv_state'] = False
    return ConversationHandler.END

async def disparo_programado_desconto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text:
        await update.message.reply_text("⛔ Envie apenas o número do desconto:", reply_markup=cancel_markup)
        return DISPARO_PROGRAMADO_DESCONTO
    
    try:
        desconto = float(update.message.text.replace(',', '.'))
        if desconto <= 0 or desconto >= 100:
            await update.message.reply_text("⛔ O desconto deve estar entre 1 e 99:", reply_markup=cancel_markup)
            return DISPARO_PROGRAMADO_DESCONTO
        
        context.user_data['disparo_programado']['discount'] = desconto
        
        await update.message.reply_text(
            "⏰ Agora envie o horário para o disparo diário.\n"
            "Formato: HH:MM (exemplo: 20:00)",
            reply_markup=cancel_markup
        )
        return DISPARO_PROGRAMADO_HORARIO
        
    except ValueError:
        await update.message.reply_text("⛔ Envie um número válido:", reply_markup=cancel_markup)
        return DISPARO_PROGRAMADO_DESCONTO

async def disparo_programado_horario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text:
        await update.message.reply_text("⛔ Envie o horário no formato HH:MM:", reply_markup=cancel_markup)
        return DISPARO_PROGRAMADO_HORARIO
    
    import re
    horario = update.message.text.strip()
    
    # Valida formato HH:MM
    if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', horario):
        await update.message.reply_text(
            "⛔ Formato inválido! Use HH:MM\n"
            "Exemplos: 09:30, 14:00, 20:15",
            reply_markup=cancel_markup
        )
        return DISPARO_PROGRAMADO_HORARIO
    
    context.user_data['disparo_programado']['time'] = horario
    
    # Monta resumo
    config = context.user_data['disparo_programado']
    keyboard = [
        [InlineKeyboardButton("✅ CRIAR", callback_data="confirmar")],
        [InlineKeyboardButton("❌ CANCELAR", callback_data="cancelar")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📅 CONFIRME O DISPARO PROGRAMADO:\n\n"
        f"⏰ Horário: {config['time']} (Horário de Brasília - todos os dias)\n"
        f"💸 Desconto: {config['discount']}%\n"
        f"📝 Mensagem configurada\n\n"
        f"Deseja criar este disparo?",
        reply_markup=reply_markup
    )
    return DISPARO_PROGRAMADO_CONFIRMA

async def disparo_programado_confirma(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancelar':
        await cancel(update, context)
        return ConversationHandler.END
    
    elif query.data == 'confirmar':
        broadcast_data = context.user_data['disparo_programado']
        
        # Adiciona o disparo programado
        success = manager.add_scheduled_broadcast(context.bot_data['id'], broadcast_data)
        
        if success:
            # Reinicia as tasks do bot para incluir o novo disparo
            import modules.scheduled_broadcast as scheduled_broadcast
            scheduled_broadcast.start_scheduled_broadcasts_for_bot(context, context.bot_data['id'])
            
            await query.message.edit_text(
                f"✅ Disparo programado criado com sucesso!\n\n"
                f"Será enviado todos os dias às {broadcast_data['time']}"
            )
        else:
            await query.message.edit_text("⛔ Erro ao criar disparo programado.")
        
        context.user_data['conv_state'] = False
        return ConversationHandler.END

# ConversationHandler permanece igual
conv_handler_disparo = ConversationHandler(
    entry_points=[CommandHandler("disparo", disparo)],
    states={
        DISPARO_TIPO: [CallbackQueryHandler(disparo_escolha)],
        DISPARO_PLANO: [CallbackQueryHandler(disparo_plano)],
        DISPARO_VALOR_CONFIRMA: [CallbackQueryHandler(disparo_valor_confirma)],
        DISPARO_VALOR: [MessageHandler(~filters.COMMAND, disparo_valor), CallbackQueryHandler(cancel)],
        DISPARO_MENSAGEM: [MessageHandler(~filters.COMMAND, disparo_mensagem), CallbackQueryHandler(cancel)],
        DISPARO_LINK: [MessageHandler(~filters.COMMAND, disparo_link), CallbackQueryHandler(cancel)],
        DISPARO_CONFIRMA: [CallbackQueryHandler(disparo_confirma)],
        DISPARO_PROGRAMADO_ESCOLHA: [CallbackQueryHandler(disparo_programado_escolha)],
        DISPARO_PROGRAMADO_DESCONTO: [MessageHandler(~filters.COMMAND, disparo_programado_desconto), CallbackQueryHandler(cancel)],
        DISPARO_PROGRAMADO_HORARIO: [MessageHandler(~filters.COMMAND, disparo_programado_horario), CallbackQueryHandler(cancel)],
        DISPARO_PROGRAMADO_CONFIRMA: [CallbackQueryHandler(disparo_programado_confirma)],
        DISPARO_PROGRAMADO_REMOVER: [CallbackQueryHandler(disparo_programado_remover)]
    },
    fallbacks=[CallbackQueryHandler(error_callback)]
)