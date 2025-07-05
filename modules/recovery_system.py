import asyncio
import json
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import modules.manager as manager

async def send_recovery(context, user_id, recovery_data, recovery_index, bot_id):
    """Envia uma recuperação específica para o usuário"""
    try:
        # Pega os planos do bot
        planos = manager.get_bot_plans(bot_id)
        if not planos:
            return False
        
        # Calcula o desconto
        desconto = recovery_data['porcentagem']
        
        # Monta os botões dos planos com desconto
        keyboard_plans = []
        for plan_index in range(len(planos)):
            plano = planos[plan_index]
            valor_original = plano['value']
            valor_com_desconto = valor_original * (1 - desconto / 100)
            
            # Formata o botão
            botao_texto = f"{plano['name']} - R$ {valor_com_desconto:.2f} ({int(desconto)}% OFF)"
            
            # Cria um plano modificado para o pagamento
            plano_recovery = plano.copy()
            plano_recovery['value'] = valor_com_desconto
            plano_recovery['is_recovery'] = True
            plano_recovery['recovery_index'] = recovery_index
            plano_recovery['original_value'] = valor_original
            plano_recovery['discount'] = desconto
            
            # Cria o pagamento com o plano modificado
            payment_id = manager.create_payment(user_id, plano_recovery, f"{plano['name']} - Recovery", bot_id)
            
            # MUDANÇA: Gera PIX direto ao invés de mostrar detalhes
            keyboard_plans.append([InlineKeyboardButton(botao_texto, callback_data=f"pagar_{payment_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard_plans)
        
        # Envia a mensagem da recuperação
        if recovery_data['media']:
            if recovery_data['text']:
                if recovery_data['media']['type'] == 'photo':
                    await context.bot.send_photo(
                        chat_id=user_id,
                        photo=recovery_data['media']['file'],
                        caption=recovery_data['text'],
                        reply_markup=reply_markup
                    )
                else:
                    await context.bot.send_video(
                        chat_id=user_id,
                        video=recovery_data['media']['file'],
                        caption=recovery_data['text'],
                        reply_markup=reply_markup
                    )
            else:
                if recovery_data['media']['type'] == 'photo':
                    await context.bot.send_photo(
                        chat_id=user_id,
                        photo=recovery_data['media']['file'],
                        reply_markup=reply_markup
                    )
                else:
                    await context.bot.send_video(
                        chat_id=user_id,
                        video=recovery_data['media']['file'],
                        reply_markup=reply_markup
                    )
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text=recovery_data.get('text', 'Oferta especial para você!'),
                reply_markup=reply_markup
            )
        
        return True
        
    except Exception as e:
        print(f"Erro ao enviar recuperação: {e}")
        return False

async def calculate_delay(recovery_data):
    """Calcula o delay em segundos baseado na configuração"""
    tempo = recovery_data['tempo']
    unidade = recovery_data['unidade_tempo']
    
    if unidade == 'segundos':
        return tempo
    elif unidade == 'minutos':
        return tempo * 60
    elif unidade == 'horas':
        return tempo * 3600
    elif unidade == 'dias':
        return tempo * 86400
    
    return tempo * 60  # Default para minutos

async def process_recovery_sequence(context, user_id, bot_id):
    """Processa a sequência de recuperações para um usuário"""
    try:
        # Pega as recuperações configuradas
        recoveries = manager.get_bot_recovery(bot_id)
        if not recoveries:
            return
        
        # Filtra e ordena as recuperações por tempo
        valid_recoveries = []
        for i, recovery in enumerate(recoveries):
            if recovery is not None:
                delay = await calculate_delay(recovery)
                valid_recoveries.append((i, recovery, delay))
        
        # Ordena por delay (tempo)
        valid_recoveries.sort(key=lambda x: x[2])
        
        # Processa cada recuperação
        for recovery_index, recovery_data, delay in valid_recoveries:
            # Aguarda o tempo configurado
            await asyncio.sleep(delay)
            
            # Verifica se o usuário ainda está sendo rastreado (não comprou)
            tracking = manager.get_recovery_tracking(user_id, bot_id)
            if not tracking or tracking[4] != 'active':
                print(f"Recuperação cancelada para usuário {user_id} - já comprou ou foi cancelado")
                return
            
            # Envia a recuperação
            success = await send_recovery(context, user_id, recovery_data, recovery_index, bot_id)
            
            if success:
                # Atualiza o índice da última recuperação enviada
                manager.update_recovery_tracking_index(user_id, bot_id, recovery_index)
                print(f"Recuperação {recovery_index + 1} enviada para usuário {user_id}")
        
        # ADICIONAR ESTAS DUAS LINHAS AQUI!!!
        manager.stop_recovery_tracking(user_id, bot_id)
        print(f"Ciclo de recuperação completo para usuário {user_id}")
            
    except Exception as e:
        print(f"Erro no processo de recuperação: {e}")

def start_recovery_for_user(context, user_id, bot_id):
    """Inicia o processo de recuperação para um usuário"""
    # Cria a tabela se não existir
    manager.create_recovery_tracking_table()
    
    # NOVA VERIFICAÇÃO: Verifica se já existe um rastreamento ativo
    existing_tracking = manager.get_recovery_tracking(user_id, bot_id)
    
    if existing_tracking:
        print(f"Usuário {user_id} já tem recuperação ativa - ignorando novo /start")
        return
    
    # Inicia o rastreamento
    manager.start_recovery_tracking(user_id, bot_id)
    
    # Cria uma task assíncrona para processar as recuperações
    asyncio.create_task(process_recovery_sequence(context, user_id, bot_id))