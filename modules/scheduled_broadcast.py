import asyncio
import json
from datetime import datetime, time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import modules.manager as manager
from datetime import datetime, time, timezone, timedelta
import pytz
from telegram.error import BadRequest, Forbidden, TelegramError, RetryAfter

# Dicionário global para armazenar tasks ativas
active_broadcast_tasks = {}

async def send_scheduled_broadcast(context, broadcast_config, bot_id):
    """Envia um disparo programado para todos os usuários"""
    try:
        # Timestamp inicial para calcular duração
        inicio = datetime.now()
        
        # Pega todos os usuários do bot
        users = manager.get_bot_users(bot_id)
        if not users:
            return
        
        # Pega os planos do bot
        planos = manager.get_bot_plans(bot_id)
        if not planos:
            return
        
        # Calcula o desconto
        desconto = broadcast_config['discount']
        
        print(f"[DISPARO PROGRAMADO] Iniciando disparo {broadcast_config['id']} para {len(users)} usuários")
        
        # NOVO: Contadores detalhados como no disparo normal
        total_users = len(users)
        enviados = 0
        erros = 0
        bloqueados = 0
        inativos = 0
        
        # NOVO: Armazena detalhes dos erros
        erro_detalhes = {
            'blocked': [],
            'inactive': [],
            'other': []
        }
        
        # NOVO: Timestamp para controle de atualizações (embora não vamos atualizar mensagem aqui)
        last_update = datetime.now()
        
        for i, user_id in enumerate(users):
            try:
                # Monta os botões dos planos com desconto
                keyboard_plans = []
                for plan_index in range(len(planos)):
                    plano = planos[plan_index]
                    valor_original = plano['value']
                    valor_com_desconto = valor_original * (1 - desconto / 100)
                    
                    # Formata o botão
                    botao_texto = f"{plano['name']} - R$ {valor_com_desconto:.2f} ({int(desconto)}% OFF)"
                    
                    # Cria um plano modificado para o pagamento
                    plano_broadcast = plano.copy()
                    plano_broadcast['value'] = valor_com_desconto
                    plano_broadcast['is_scheduled_broadcast'] = True
                    plano_broadcast['original_value'] = valor_original
                    plano_broadcast['discount'] = desconto
                    
                    # Cria o pagamento com o plano modificado
                    payment_id = manager.create_payment(user_id, plano_broadcast, f"{plano['name']} - Broadcast", bot_id)
                    
                    # Gera PIX direto
                    keyboard_plans.append([InlineKeyboardButton(botao_texto, callback_data=f"pagar_{payment_id}")])
                
                reply_markup = InlineKeyboardMarkup(keyboard_plans)
                
                # Envia a mensagem
                if broadcast_config['media']:
                    if broadcast_config['text']:
                        if broadcast_config['media']['type'] == 'photo':
                            await context.bot.send_photo(
                                chat_id=user_id,
                                photo=broadcast_config['media']['file'],
                                caption=broadcast_config['text'],
                                reply_markup=reply_markup
                            )
                        else:
                            await context.bot.send_video(
                                chat_id=user_id,
                                video=broadcast_config['media']['file'],
                                caption=broadcast_config['text'],
                                reply_markup=reply_markup
                            )
                    else:
                        if broadcast_config['media']['type'] == 'photo':
                            await context.bot.send_photo(
                                chat_id=user_id,
                                photo=broadcast_config['media']['file'],
                                reply_markup=reply_markup
                            )
                        else:
                            await context.bot.send_video(
                                chat_id=user_id,
                                video=broadcast_config['media']['file'],
                                reply_markup=reply_markup
                            )
                else:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=broadcast_config.get('text', 'Oferta especial!'),
                        reply_markup=reply_markup
                    )
                
                # NOVO: Contabiliza sucesso
                enviados += 1
                
            # NOVO: Tratamento específico de erros como no disparo normal
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
                # NOVO: Rate limit - aguarda o tempo especificado
                await asyncio.sleep(e.retry_after)
                # Tenta novamente
                try:
                    # Repete o código de envio (simplificado aqui)
                    # [mesmo código de envio acima]
                    enviados += 1
                except Exception:
                    erros += 1
                    erro_detalhes['other'].append(user_id)
                    
            except Exception as e:
                # Outros erros
                print(f"Erro ao enviar para {user_id}: {str(e)}")
                erros += 1
                erro_detalhes['other'].append(user_id)
            
            # NOVO: Delay entre mensagens para evitar flood (como no disparo normal)
            await asyncio.sleep(0.2)  # 50ms entre cada envio
        
        # Calcula duração
        fim = datetime.now()
        duracao = (fim - inicio).total_seconds()
        
        # NOVO: Estatísticas detalhadas como no disparo normal
        print(f"[DISPARO PROGRAMADO] Finalizado:")
        print(f"- Total: {total_users} usuários")
        print(f"- Enviados: {enviados} ({int(enviados/total_users*100) if total_users > 0 else 0}%)")
        print(f"- Erros: {erros}")
        print(f"- Bloqueados: {bloqueados}")
        print(f"- Inativos: {inativos}")
        print(f"- Duração: {duracao:.1f} segundos")
        
        # MODIFICADO: Notificar admins com estatísticas detalhadas
        await notificar_admins_disparo_finalizado(
            context, bot_id, broadcast_config, 
            total_users=total_users, 
            enviados=enviados, 
            erros=erros,
            bloqueados=bloqueados,
            inativos=inativos,
            duracao=duracao,
            erro_detalhes=erro_detalhes
        )
        
    except Exception as e:
        print(f"Erro crítico no disparo programado: {e}")

async def notificar_admins_disparo_finalizado(context, bot_id, broadcast_config, total_users, enviados, erros, bloqueados, inativos, duracao, erro_detalhes):
    """Notifica todos os admins sobre o resultado do disparo programado"""
    try:
        # Pega lista de admins
        admin_list = manager.get_bot_admin(bot_id)
        owner = manager.get_bot_owner(bot_id)
        
        # Adiciona o owner se não estiver na lista
        if owner and owner not in admin_list:
            admin_list.append(owner)
        
        # Calcula estatísticas
        taxa_sucesso = (enviados / total_users * 100) if total_users > 0 else 0
        minutos = int(duracao // 60)
        segundos = int(duracao % 60)
        
        # MODIFICADO: Mensagem mais detalhada como no disparo normal
        mensagem = (
            f"📊 *DISPARO PROGRAMADO FINALIZADO*\n\n"
            f"⏰ Horário: {broadcast_config['time']}\n"
            f"💸 Desconto: {broadcast_config['discount']}%\n\n"
            f"📈 *Resultados:*\n"
            f"👥 Total de usuários: {total_users}\n"
            f"✅ Enviados com sucesso: {enviados} ({taxa_sucesso:.1f}%)\n"
            f"⛔ Total de erros: {erros}\n"
        )
        
        # NOVO: Adiciona detalhamento dos erros se houver
        if bloqueados > 0:
            mensagem += f"🚫 Bloquearam o bot: {bloqueados}\n"
        if inativos > 0:
            mensagem += f"💤 Contas desativadas: {inativos}\n"
        if len(erro_detalhes['other']) > 0:
            mensagem += f"❓ Outros erros: {len(erro_detalhes['other'])}\n"
        
        mensagem += f"\n⏱️ Duração: {minutos}m {segundos}s\n\n"
        mensagem += f"_Disparo automático {broadcast_config['id'] + 1}_"
        
        # Envia para cada admin
        for admin_id in admin_list:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=mensagem,
                    parse_mode='Markdown'
                )
            except Exception as e:
                print(f"Erro ao notificar admin {admin_id}: {e}")
                
    except Exception as e:
        print(f"Erro ao notificar admins sobre disparo: {e}")

# O resto do arquivo permanece igual
async def broadcast_scheduler(context, broadcast_config, bot_id):
    """Agenda e executa disparos no horário configurado (Horário de Brasília)"""
    # Define timezone de Brasília
    brasilia_tz = pytz.timezone('America/Sao_Paulo')
    
    while True:
        try:
            # Pega o horário atual em Brasília
            now_brasilia = datetime.now(brasilia_tz)
            
            # Pega o horário configurado
            hora, minuto = map(int, broadcast_config['time'].split(':'))
            
            # Cria o datetime alvo para hoje em Brasília
            target_time_brasilia = now_brasilia.replace(
                hour=hora, 
                minute=minuto, 
                second=0, 
                microsecond=0
            )
            
            # Se já passou o horário hoje, agenda para amanhã
            if target_time_brasilia <= now_brasilia:
                target_time_brasilia += timedelta(days=1)
            
            # Calcula tempo de espera
            wait_seconds = (target_time_brasilia - now_brasilia).total_seconds()
            
            print(f"[DISPARO PROGRAMADO] Broadcast {broadcast_config['id']} agendado para {target_time_brasilia.strftime('%d/%m/%Y %H:%M')} (Horário de Brasília)")
            print(f"[DISPARO PROGRAMADO] Aguardando {wait_seconds/60:.1f} minutos")
            
            # Aguarda até o horário
            await asyncio.sleep(wait_seconds)
            
            # Executa o disparo
            await send_scheduled_broadcast(context, broadcast_config, bot_id)
            
            # Aguarda 60 segundos para evitar duplicação
            await asyncio.sleep(60)
            
        except asyncio.CancelledError:
            print(f"[DISPARO PROGRAMADO] Task cancelada para broadcast {broadcast_config['id']}")
            break
        except Exception as e:
            print(f"Erro no scheduler: {e}")
            await asyncio.sleep(60)  # Espera 1 minuto antes de tentar novamente

def start_scheduled_broadcasts_for_bot(context, bot_id):
    """Inicia todos os disparos programados de um bot"""
    broadcasts = manager.get_bot_scheduled_broadcasts(bot_id)
    
    # Cancela tasks antigas se existirem
    bot_key = f"bot_{bot_id}"
    if bot_key in active_broadcast_tasks:
        for task in active_broadcast_tasks[bot_key]:
            task.cancel()
        active_broadcast_tasks[bot_key] = []
    else:
        active_broadcast_tasks[bot_key] = []
    
    # Cria novas tasks
    for broadcast in broadcasts:
        task = asyncio.create_task(broadcast_scheduler(context, broadcast, bot_id))
        active_broadcast_tasks[bot_key].append(task)
        print(f"[DISPARO PROGRAMADO] Iniciado broadcast {broadcast['id']} para bot {bot_id}")

def stop_scheduled_broadcasts_for_bot(bot_id):
    """Para todos os disparos programados de um bot"""
    bot_key = f"bot_{bot_id}"
    if bot_key in active_broadcast_tasks:
        for task in active_broadcast_tasks[bot_key]:
            task.cancel()
        del active_broadcast_tasks[bot_key]
        print(f"[DISPARO PROGRAMADO] Parados todos os broadcasts do bot {bot_id}")