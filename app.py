from flask import Flask, jsonify, request, send_file, session, redirect, url_for
import modules.manager as manager
import asyncio, json, requests, datetime, time
import mercadopago, os, signal
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler
from multiprocessing import Process
from bot import run_bot_sync

# Configurações do Mercado Pago
CLIENT_ID = os.environ.get("CLIENT_ID", "4714763730515747")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "i33hQ8VZ11pYH1I3xMEMECphRJjT0CiP")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", 'kekel')

# Carrega configurações
try:
    config = json.loads(open('./config.json', 'r').read())
except:
    config = {}

# Usa variáveis de ambiente com fallback para config.json
IP_DA_VPS = os.environ.get("URL", config.get("url", "https://localhost:4040"))
REGISTRO_TOKEN = os.environ.get("REGISTRO_TOKEN", config.get("registro", ""))
ADMIN_PASSWORD = os.environ.get("PASSWORD", config.get("password", "adminadmin"))

# Porta do Railway ou padrão
port = int(os.environ.get("PORT", 4040))

dashboard_data = {
    "botsActive": 0,
    "usersCount": 0,
    "salesCount": 0
}

bots_data = {}
processes = {}
tokens = []
event_loop = asyncio.new_event_loop()

def initialize_all_registered_bots():
    """Inicializa todos os bots registrados e ativos."""
    print('Inicializando bots registrados...')
    global bots_data, processes
    bots = manager.get_all_bots()
    print(f'Encontrados {len(bots)} bots')
    
    for bot in bots:
        bot_id = bot[0]

        # Verifica se já existe um processo rodando para este bot
        if bot_id in processes and processes[str(bot_id)].is_alive():
            print(f"Bot {bot_id} já está em execução. Ignorando nova inicialização.")
            continue

        try:
            start_bot(bot[1], bot_id)
            print(f"Bot {bot_id} iniciado com sucesso.")
            
        except Exception as e:
            print(f"Erro ao iniciar o bot {bot_id}: {e}")
    
    # Aguarda um pouco para garantir que todos os bots iniciaram
    time.sleep(2)
    
    # Inicia disparos programados para todos os bots
    print('Inicializando disparos programados...')
    bots_with_broadcasts = manager.get_all_bots_with_scheduled_broadcasts()
    print(f'Encontrados {len(bots_with_broadcasts)} bots com disparos programados')
    
    # Nota: Os disparos serão iniciados individualmente por cada bot quando ele iniciar

@app.route('/callback', methods=['GET'])
def callback():
    """
    Endpoint para receber o webhook de redirecionamento do Mercado Pago.
    """
    TOKEN_URL = "https://api.mercadopago.com/oauth/token"

    authorization_code = request.args.get('code')
    bot_id = request.args.get('state')

    if not authorization_code:
        return jsonify({"error": "Authorization code not provided"}), 400

    try:
        payload = {
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": authorization_code,
            "redirect_uri": IP_DA_VPS+'/callback',
            "state":bot_id,
        }
        
        response = requests.post(TOKEN_URL, data=payload)
        response_data = response.json()

        if response.status_code == 200:
            access_token = response_data.get("access_token")
            print(f"Token MP recebido para bot {bot_id}")
            manager.update_bot_gateway(bot_id, {'type':"MP", 'token':access_token})
            return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Token Cadastrado</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f4f9;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            color: #333;
        }
        .container {
            background-color: #fff;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            padding: 20px 30px;
            text-align: center;
            max-width: 400px;
        }
        .container h1 {
            color: #4caf50;
            font-size: 24px;
            margin-bottom: 10px;
        }
        .container p {
            font-size: 16px;
            margin-bottom: 20px;
        }
        .btn {
            display: inline-block;
            padding: 10px 20px;
            font-size: 14px;
            color: #fff;
            background-color: #4caf50;
            text-decoration: none;
            border-radius: 4px;
            transition: background-color 0.3s ease;
        }
        .btn:hover {
            background-color: #45a049;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Token Cadastrado com Sucesso!</h1>
        <p>O seu token Mercado Pago está pronto para uso.</p>
    </div>
</body>
</html>
"""
        else:
            return jsonify({"error": response_data}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/webhook/mp', methods=['POST'])
def handle_webhook():
    data = request.get_json(silent=True)
    print(f"Webhook MP recebido: {data}")
    
    if data and data.get('type') == 'payment':
        transaction_id = (data.get('data').get('id'))
        print(f'Pagamento {transaction_id} recebido - Mercado Pago')
        payment = manager.get_payment_by_trans_id(transaction_id)
        
        if payment:
            print(payment)
            bot_id = json.loads(payment[4])
            token = manager.get_bot_gateway(bot_id)
            sdk = mercadopago.SDK(token['token'])
            pagamento = sdk.payment().get(transaction_id)
            pagamento_status = pagamento["response"]["status"]

            if pagamento_status == "approved":
                print(f'Pagamento {transaction_id} aprovado - Mercado Pago')
                manager.update_payment_status(transaction_id, 'paid')
                return jsonify({"message": "Webhook recebido com sucesso."}), 200
    
    return jsonify({"message": "Evento ignorado."}), 400

@app.route('/webhook/pp', methods=['POST'])
def webhook():
    if request.content_type == 'application/json':
        data = request.get_json()
    elif request.content_type == 'application/x-www-form-urlencoded':
        data = request.form.to_dict()
    else:
        print("[ERRO] Tipo de conteúdo não suportado")
        return jsonify({"error": "Unsupported Media Type"}), 415

    if not data:
        print("[ERRO] Dados JSON ou Form Data inválidos")
        return jsonify({"error": "Invalid JSON or Form Data"}), 400
    
    print(f"[DEBUG] Webhook PP recebido: {data}")
    transaction_id = data.get("id", "").lower()
    
    if data.get('status', '').lower() == 'paid':
        print(f'Pagamento {transaction_id} pago - PushinPay')
        manager.update_payment_status(transaction_id, 'paid')
    else:
        print(f"[ERRO] Status do pagamento não é 'paid': {data.get('status')}")

    return jsonify({"status": "success"})

@app.route('/', methods=['GET'])
def home():
    if session.get("auth", False):
        return redirect(url_for('admin'))
    return redirect(url_for('login'))

@app.route('/delete/<id>', methods=['DELETE'])
async def delete(id):
    if session.get("auth", False):
        # Adiciona owner na blacklist
        if id in bots_data:
            open('blacklist.txt', 'a').write(str(bots_data[id]['owner'])+'\n')
        
        # IMPORTANTE: Para o processo ANTES de remover das listas
        if id in processes:
            try:
                processes[id].terminate()
                processes[id].join(timeout=5)
                if processes[id].is_alive():
                    processes[id].kill()
            except:
                pass
            finally:
                processes.pop(id)
        
        # Remove dos dados
        if id in bots_data:
            bots_data.pop(id)
        
        # Atualiza no banco
        manager.update_bot_config(id, [])
        manager.update_bot_token(id, f'BANIDO-{id}')
        
        print(f"Bot {id} deletado e processo parado")
        return 'true'
    else:
        return 'Unauthorized', 403
    
@app.route('/login', methods=['POST', 'GET'])
def login():
    if session.get('auth', False):
        return redirect(url_for('admin'))
    
    if request.method == 'POST':
        password = request.form['password']
        if password == ADMIN_PASSWORD:
            session['auth'] = True
            session.permanent = True
            return redirect(url_for('admin'))
        else:
            return redirect(url_for('login', error=1))
    
    return send_file('./templates/login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
def admin():
    if not session.get("auth", False):
        return redirect(url_for('login'))
    return send_file('./templates/admin.html')

@app.route('/api/bots')
def api_bots():
    if not session.get("auth", False):
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        all_bots = manager.get_all_bots()
        bots_data = []
        banned_count = 0
        active_count = 0
        
        # Lê a blacklist
        with open('blacklist.txt', 'r') as f:
            blacklist = f.read().strip().split('\n')
        
        for bot in all_bots:
            bot_id, token, owner, config, *_ = bot
            
            # Verifica se está banido
            is_banned = token.startswith('BANIDO-') or str(owner) in blacklist
            
            if is_banned:
                banned_count += 1
            else:
                active_count += 1
            
            # Pega informações do bot
            bot_info = {"name": "Bot Inválido", "username": "invalido"}
            if not token.startswith('BANIDO-'):
                bot_details = manager.check_bot_token(token)
                if bot_details and bot_details.get('ok'):
                    bot_info = bot_details.get('result', {})
            
            bots_data.append({
                'id': bot_id,
                'token': token,
                'owner': owner,
                'name': bot_info.get('first_name', 'Bot Inválido'),
                'username': bot_info.get('username', 'invalido'),
                'is_banned': is_banned
            })
        
        return jsonify({
            'bots': bots_data,
            'stats': {
                'total': len(all_bots),
                'active': active_count,
                'banned': len(set(blacklist)) - 1  # -1 para remover linha vazia
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ban/<bot_id>', methods=['POST'])
def api_ban_bot(bot_id):
    if not session.get("auth", False):
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        data = request.get_json()
        owner_id = data.get('owner_id')
        
        # Adiciona owner na blacklist
        with open('blacklist.txt', 'a') as f:
            f.write(str(owner_id) + '\n')
        
        # IMPORTANTE: Primeiro pega o token original antes de banir
        bot = manager.get_bot_by_id(bot_id)
        original_token = bot[1] if bot else None
        
        # Marca token como banido
        manager.update_bot_token(bot_id, f'BANIDO-{bot_id}')
        
        # CORREÇÃO: Para o processo se estiver rodando
        # Verifica em processes (que usa string como chave)
        bot_id_str = str(bot_id)
        if bot_id_str in processes:
            try:
                # Termina o processo
                processes[bot_id_str].terminate()
                processes[bot_id_str].join(timeout=5)  # Espera até 5 segundos
                
                # Se ainda estiver vivo, força o kill
                if processes[bot_id_str].is_alive():
                    processes[bot_id_str].kill()
                    
            except Exception as e:
                print(f"Erro ao parar processo do bot {bot_id}: {e}")
            finally:
                # Remove da lista de processos
                processes.pop(bot_id_str)
        
        # Remove também do bots_data se existir
        if bot_id_str in bots_data:
            bots_data.pop(bot_id_str)
        
        print(f"Bot {bot_id} banido e processo parado com sucesso")
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"Erro ao banir bot: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/unban/<bot_id>', methods=['POST'])
def api_unban_bot(bot_id):
    if not session.get("auth", False):
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        data = request.get_json()
        owner_id = str(data.get('owner_id'))
        
        # Remove da blacklist
        with open('blacklist.txt', 'r') as f:
            lines = f.readlines()
        
        with open('blacklist.txt', 'w') as f:
            for line in lines:
                if line.strip() != owner_id:
                    f.write(line)
        
        # Precisa do token original - buscar do banco
        bot = manager.get_bot_by_id(bot_id)
        if bot and bot[1].startswith('BANIDO-'):
            # Não temos o token original, precisaria armazenar em outro lugar
            # Por ora, apenas remove o prefixo BANIDO
            return jsonify({"error": "Token original não encontrado. Delete e recrie o bot."}), 400
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/delete/<bot_id>', methods=['DELETE'])
def api_delete_bot(bot_id):
    if not session.get("auth", False):
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # Para o processo se estiver rodando
        if bot_id in processes:
            processes[bot_id].terminate()
            processes.pop(bot_id)
        
        # Remove do banco (você precisa criar esta função no manager.py)
        # manager.delete_bot(bot_id)
        
        # Por enquanto, só marca como banido
        manager.update_bot_token(bot_id, f'DELETED-{bot_id}')
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# REMOVER a rota dashboard-data antiga (se não for mais usada)
# Ou mantê-la se outros componentes ainda usam

def start_bot(new_token, bot_id):
    """Inicia um novo bot em um processo separado."""
    bot_id = str(bot_id)
    if not str(bot_id) in processes.keys():
        process = Process(target=run_bot_sync, args=(new_token, bot_id))
        process.start()
        tokens.append(new_token)
        bot = manager.get_bot_by_id(bot_id)
        bot_details = manager.check_bot_token(new_token)
        bot_obj = {
            'id': bot_id,
            'url':f'https://t.me/{bot_details['result'].get('username', "INDEFINIDO")}',
            'token': bot[1],
            'owner': bot[2],
            'data': json.loads(bot[4])
        }
        bots_data[str(bot_id)] = bot_obj
        processes[str(bot_id)] = process
        print(f"Bot {bot_id} processo iniciado")
        return True

async def receive_token_register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_token = update.message.text.strip()
    admin_id = update.effective_user.id
    
    if manager.bot_exists(new_token):
        await update.message.reply_text('Token já registrado no sistema.')
    elif manager.bot_banned(str(admin_id)):
        await update.message.reply_photo('https://media.tenor.com/BosnE3kdeu8AAAAM/banned-pepe.gif', caption='Você foi banido do sistema.')
    else:
        telegram_bot = manager.check_bot_token(new_token)
        if telegram_bot:
            print(f'Novo BOT registrado: {telegram_bot}')
            id = telegram_bot.get('result', {}).get('id', False)
            if id:
                bot = manager.create_bot(str(id), new_token, admin_id)
                start_bot(new_token, id)
                await update.message.reply_text(f'Bot t.me/{telegram_bot['result']['username']} registrado e iniciado. Apenas você pode gerenciá-lo.')
            else:
                await update.message.reply_text('Erro ao obter ID do bot.')
        else:
            await update.message.reply_text('O token inserido é inválido.')
    return ConversationHandler.END

async def start_func(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if manager.bot_banned(str(update.message.from_user.id)):
        await update.message.reply_photo('https://media.tenor.com/BosnE3kdeu8AAAAM/banned-pepe.gif', caption='Você foi banido do sistema.')
    else:
        await update.message.reply_text('Envie seu token')
    return ConversationHandler.END

def main():
    """Função principal para rodar o bot de registro"""
    if not REGISTRO_TOKEN:
        print("Token de registro não configurado!")
        return
        
    registro_token = REGISTRO_TOKEN
    application = Application.builder().token(registro_token).build()
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_token_register))
    application.add_handler(CommandHandler('start', start_func))
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print('Iniciando BOT de Registro')
    application.run_polling()

def start_register():
    register = Process(target=main)
    register.start()

@app.route('/bots', methods=['GET'])
def bots():
    if session.get("auth", False):
        bot_list = manager.get_all_bots()
        bots = []

        for bot in bot_list:
            bot_details = manager.check_bot_token(bot[1])
            bot_structure = {
                'id': bot[0],
                'token': bot[1],
                'url': "Token Inválido",
                'owner': bot[2],
                'data': json.loads(bot[3])
            }
            if bot_details:
                bot_structure['url'] = f'https://t.me/{bot_details['result'].get('username', "INDEFINIDO")}'
            
            bots_data[str(bot[0])] = bot_structure
            bots.append(bot_structure)
        return jsonify(bots)
    return jsonify({"error": "Unauthorized"}), 403

@app.route('/health', methods=['GET'])
def health():
    """Endpoint de health check para o Railway"""
    return jsonify({
        "status": "healthy",
        "bots_active": len(processes),
        "timestamp": datetime.datetime.now().isoformat()
    })

if __name__ == '__main__':
    print(f"Iniciando aplicação na porta {port}")
    print(f"URL configurada: {IP_DA_VPS}")
    
    # Cria arquivo blacklist.txt se não existir
    if not os.path.exists('blacklist.txt'):
        open('blacklist.txt', 'w').close()
    
    manager.inicialize_database()
    manager.create_recovery_tracking_table()  # ADICIONAR ESTA LINHA
    initialize_all_registered_bots()
    start_register()
    
    app.run(debug=False, host='0.0.0.0', port=port)