import json, sqlite3, datetime, requests
from datetime import datetime

def inicialize_database():
    conn = sqlite3.connect('data.db')
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS BOTS (
            id TEXT PRIMARY KEY,
            token TEXT UNIQUE,
            owner TEXT,
            config TEXT,
            admin TEXT,
            plans TEXT,
            gateway TEXT,
            users TEXT,
            upsell TEXT,
            "group" TEXT,
            expiration TEXT
        )
"""
    )
    cur.execute('''
    CREATE TABLE IF NOT EXISTS USERS (
        id_user TEXT,
        data_entrada TEXT,
        data_expiracao TEXT,
        plano TEXT,
        grupo TEXT
    )
    ''')
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS PAYMENTS (
            id TEXT,
            trans_id TEXT,
            chat TEXT,
            plano TEXT,
            bot TEXT,
            status TEXT
        )
        """
    )
def count_bots():
    try:
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM BOTS")
        count = cursor.fetchone()[0]
        
        return count
    except sqlite3.Error as e:
        print(f"Erro ao acessar o banco de dados: {e}")
        return None
    finally:
        if conn:
            conn.close()
def get_bot_by_id(bot_id):

    print(bot_id)
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM BOTS WHERE id = ?", (bot_id,))
    result = cursor.fetchone()
    if result:
        conn.close()
        return result



config_default = {
    'texto1':False,
    'texto2':"Configure o bot usando /inicio\n\nUtilize /comandos para verificar os comandos existentes",
    'button':'CLIQUE AQUI PARA VER OFERTAS'
}




def create_bot(id, token, owner, config=config_default, admin=[], plans=[], gateway={}, users=[], upsell={}, group='', expiration={}):
    # Conecta ao banco de dados
    conn = sqlite3.connect('data.db')
    cur = conn.cursor()


    # Insere um novo registro na tabela BOTS
    try:
        cur.execute("""
            INSERT INTO BOTS (id, token, owner, config, admin, plans, gateway, users, upsell, "group", expiration)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (id, token, owner, json.dumps(config), json.dumps(admin), json.dumps(plans), json.dumps(gateway), json.dumps(users), json.dumps(upsell), group, json.dumps(expiration)))
        
        # Confirma a transação
        conn.commit()
        print("Bot criado com sucesso!")
    except sqlite3.IntegrityError as e:
        print("Erro ao criar bot:", e)
    finally:
        # Fecha a conexão
        conn.close()

def check_bot_token(token):
    response = requests.get(f'https://api.telegram.org/bot{token}/getMe')
    if response.status_code == 200:
        return json.loads(response.text)
    else:
        return False
    
def bot_exists(token):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM BOTS WHERE token = ?", (token,))
    exists = cursor.fetchone() is not None
    
    conn.close()
    return exists

def get_all_bots():
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM BOTS")
    exists = cursor.fetchall()
    print(exists)
    conn.close()
    return exists


def bot_banned(id):
    ban = open('blacklist.txt', 'r').read()
    banned_list = ban.split('\n')
    if id in banned_list:
        print('banned '+id)
        return True
    print('ok '+id)
    return False

def update_bot_config(bot_id, config):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE BOTS SET config = ? WHERE id = ?", (json.dumps(config), bot_id))
    conn.commit()
    conn.close()

def update_bot_admin(bot_id, admin):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE BOTS SET admin = ? WHERE id = ?", (json.dumps(admin), bot_id))
    conn.commit()
    conn.close()

def update_bot_token(bot_id, admin):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE BOTS SET token = ? WHERE id = ?", (json.dumps(admin), bot_id))
    conn.commit()
    conn.close()

def update_bot_plans(bot_id, plans):
    print(plans)
    print(json.dumps(plans))
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE BOTS SET plans = ? WHERE id = ?", (json.dumps(plans), bot_id))
    conn.commit()
    conn.close()

def update_bot_gateway(bot_id, gateway):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE BOTS SET gateway = ? WHERE id = ?", (json.dumps(gateway), bot_id))
    conn.commit()
    conn.close()

def update_bot_users(bot_id, users):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE BOTS SET users = ? WHERE id = ?", (json.dumps(users), bot_id))
    conn.commit()
    conn.close()

def update_bot_upsell(bot_id, upsell):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE BOTS SET upsell = ? WHERE id = ?", (json.dumps(upsell), bot_id))
    conn.commit()
    conn.close()

def update_bot_expiration(bot_id, expiration):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE BOTS SET expiration = ? WHERE id = ?", (json.dumps(expiration), bot_id))
    conn.commit()
    conn.close()

def update_bot_group(bot_id, group):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE BOTS SET 'group' = ? WHERE id = ?", (group, bot_id))
    conn.commit()
    conn.close()



def get_bot_users(bot_id):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute('SELECT "users" FROM BOTS WHERE "id" = ?', (bot_id,))
    result = cursor.fetchone()
    print(result)
    if result:
        conn.close()
        return json.loads(result[0])

def get_bot_gateway(bot_id):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute('SELECT "gateway" FROM BOTS WHERE "id" = ?', (bot_id,))
    result = cursor.fetchone()
    if result:
        conn.close()
        return json.loads(result[0])





def get_bot_config(bot_id):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute('SELECT "config" FROM BOTS WHERE "id" = ?', (bot_id,))
    result = cursor.fetchone()
    if result:
        conn.close()
        return json.loads(result[0])


def get_bot_group(bot_id):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute('SELECT "group" FROM BOTS WHERE "id" = ?', (bot_id,))
    result = cursor.fetchone()
    if result:
        conn.close()
        return result[0]

def get_bot_upsell(bot_id):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute('SELECT "upsell" FROM BOTS WHERE "id" = ?', (bot_id,))
    result = cursor.fetchone()
    if result:
        conn.close()
        return json.loads(result[0])

def get_bot_plans(bot_id):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute('SELECT "plans" FROM BOTS WHERE "id" = ?', (bot_id,))
    result = cursor.fetchone()
    if result:
        conn.close()
        return json.loads(result[0])

def get_bot_expiration(bot_id):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute('SELECT "expiration" FROM BOTS WHERE "id" = ?', (bot_id,))
    result = cursor.fetchone()
    if result:
        conn.close()
        return json.loads(result[0])

# Administração

def get_bot_owner(bot_id):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute('SELECT "owner" FROM BOTS WHERE "id" = ?', (bot_id,))
    result = cursor.fetchone()
    if result:
        conn.close()
        return str(result[0])
def get_bot_admin(bot_id):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute('SELECT "admin" FROM BOTS WHERE "id" = ?', (bot_id,))
    result = cursor.fetchone()
    if result:
        conn.close()
        return json.loads(result[0])
    



def add_user_to_expiration(id_user, data_entrada, data_expiracao, plano_dict, grupo):
    # Converter o plano (dicionário) em uma string JSON
    plano_json = json.dumps(plano_dict)
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    # Inserir a nova linha na tabela
    cursor.execute('''
    INSERT INTO USERS (id_user, data_entrada, data_expiracao, plano, grupo)
    VALUES (?, ?, ?, ?, ?)
    ''', (id_user, data_entrada, data_expiracao, plano_json, grupo))
    
    # Salvar as alterações e fechar
    conn.commit()


def remover_usuario(id_user, id_group):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute('''
    DELETE FROM USERS 
    WHERE id_user = ? and grupo = ?
    ''', (id_user, id_group,))
    
    # Salvar as alterações
    conn.commit()

def verificar_expirados(grupo):
    data_atual = datetime.now()
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute('''
    SELECT id_user, data_expiracao FROM USERS 
    WHERE grupo = ?
    ''', (grupo,))

    expirados = []
    
    for id_user, data_expiracao in cursor.fetchall():
        # Converter a data de expiração para objeto datetime
        data_expiracao_dt = datetime.strptime(data_expiracao, '%Y-%m-%d %H:%M:%S')
        
        # Verificar se o usuário está expirado
        if data_expiracao_dt < data_atual:
            print(expirados)
            expirados.append(id_user)
    
    return expirados


def get_user_expiration(id_user, grupo):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM USERS WHERE "id_user" = ? and grupo = ?', (id_user, grupo,))
    result = cursor.fetchone()
    if result and len(result) > 0:
        conn.close()
        return result[0]
    else:
        return False
    

def count_payments():
    try:
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM PAYMENTS")
        count = cursor.fetchone()[0]
        
        return count
    except sqlite3.Error as e:
        print(f"Erro ao acessar o banco de dados: {e}")
        return None
    finally:
        if conn:
            conn.close()

def create_payment(chat, plano, nome_plano, bot, status='idle', trans_id='false'):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    id  = count_payments()
    cursor.execute(
        "INSERT INTO PAYMENTS (id, trans_id, chat, plano, bot, status) VALUES (?, ?, ?, ?, ?, ?)",
        (id, trans_id, chat, json.dumps(plano), bot, status,)
    )
    print('criei um pagamento')
    conn.commit()
    conn.close()
    return id



def update_payment_status(id, status):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    id = str(id)
    cursor.execute("UPDATE PAYMENTS SET status = ? WHERE trans_id = ?", (status, id))
    conn.commit()
    conn.close()

def update_payment_id(id, trans):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    id = str(id)
    cursor.execute("UPDATE PAYMENTS SET trans_id = ? WHERE id = ?", (trans, id))
    conn.commit()
    conn.close()

def get_payment_by_trans_id(id):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM PAYMENTS WHERE trans_id = ?", (id,))
    payment = cursor.fetchone()
    conn.close()
    return payment


def get_payment_by_id(id):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM PAYMENTS WHERE id = ?", (id,))
    payment = cursor.fetchone()
    conn.close()
    return payment

def get_payment_plan_by_id(id):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT plano FROM PAYMENTS WHERE id = ?", (id,))
    payment = cursor.fetchone()
    conn.close()
    return payment[0]


def get_payment_by_chat(id):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM PAYMENTS WHERE chat = ?", (id,))
    payment = cursor.fetchone()
    conn.close()
    return payment


def get_payment_by_chat(id):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM PAYMENTS WHERE chat = ?", (id,))
    payment = cursor.fetchone()
    conn.close()
    return payment

def get_payments_by_status(status, bot_id):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM PAYMENTS WHERE status = ? AND bot = ?", (status, bot_id,))
    payment = cursor.fetchall()
    conn.close()
    return payment

def get_all_payments_by_status(status):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM PAYMENTS WHERE status = ?", (status,))
    payment = cursor.fetchall()
    conn.close()
    return payment

# ADICIONAR NO FINAL DO ARQUIVO manager.py

def update_bot_orderbump(bot_id, orderbump):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    # Primeiro, verifica se a coluna orderbump existe
    cursor.execute("PRAGMA table_info(BOTS)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'orderbump' not in columns:
        # Adiciona a coluna se não existir
        cursor.execute("ALTER TABLE BOTS ADD COLUMN orderbump TEXT DEFAULT '{}'")
        conn.commit()
    
    cursor.execute("UPDATE BOTS SET orderbump = ? WHERE id = ?", (json.dumps(orderbump), bot_id))
    conn.commit()
    conn.close()

def get_bot_orderbump(bot_id):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    
    # Verifica se a coluna existe
    cursor.execute("PRAGMA table_info(BOTS)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'orderbump' not in columns:
        conn.close()
        return []
    
    cursor.execute('SELECT "orderbump" FROM BOTS WHERE "id" = ?', (bot_id,))
    result = cursor.fetchone()
    if result and result[0]:
        conn.close()
        try:
            return json.loads(result[0])
        except:
            return []
    return []

def add_orderbump_to_plan(bot_id, plan_index, orderbump_data):
    """Adiciona order bump a um plano específico"""
    orderbumps = get_bot_orderbump(bot_id)
    
    # Remove order bump anterior do mesmo plano se existir
    orderbumps = [ob for ob in orderbumps if ob.get('plano_id') != plan_index]
    
    # Adiciona o novo order bump
    orderbump_data['plano_id'] = plan_index
    orderbumps.append(orderbump_data)
    
    update_bot_orderbump(bot_id, orderbumps)

def remove_orderbump_from_plan(bot_id, plan_index):
    """Remove order bump de um plano específico"""
    orderbumps = get_bot_orderbump(bot_id)
    orderbumps = [ob for ob in orderbumps if ob.get('plano_id') != plan_index]
    update_bot_orderbump(bot_id, orderbumps)

def get_orderbump_by_plan(bot_id, plan_index):
    """Retorna o order bump de um plano específico"""
    orderbumps = get_bot_orderbump(bot_id)
    for ob in orderbumps:
        if ob.get('plano_id') == plan_index:
            return ob
    return None

def update_payment_plan(payment_id, plan):
    """Atualiza o plano de um pagamento"""
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE PAYMENTS SET plano = ? WHERE id = ?", (json.dumps(plan), payment_id))
    conn.commit()
    conn.close()
    
# ADICIONAR NO FINAL DO ARQUIVO manager.py

def update_bot_downsell(bot_id, downsell):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    
    # Verifica se a coluna downsell existe
    cursor.execute("PRAGMA table_info(BOTS)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'downsell' not in columns:
        # Adiciona a coluna se não existir
        cursor.execute("ALTER TABLE BOTS ADD COLUMN downsell TEXT DEFAULT '{}'")
        conn.commit()
    
    cursor.execute("UPDATE BOTS SET downsell = ? WHERE id = ?", (json.dumps(downsell), bot_id))
    conn.commit()
    conn.close()

def get_bot_downsell(bot_id):
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    
    # Verifica se a coluna existe
    cursor.execute("PRAGMA table_info(BOTS)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'downsell' not in columns:
        conn.close()
        return {}
    
    cursor.execute('SELECT "downsell" FROM BOTS WHERE "id" = ?', (bot_id,))
    result = cursor.fetchone()
    if result and result[0]:
        conn.close()
        try:
            return json.loads(result[0])
        except:
            return {}
    return {}

def delete_bot(bot_id):
    """Remove completamente um bot do banco de dados"""
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM BOTS WHERE id = ?", (bot_id,))
    conn.commit()
    conn.close()

# ADICIONAR NO FINAL DO ARQUIVO manager.py

def update_bot_recovery(bot_id, recovery):
    """Atualiza as recuperações de um bot"""
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    
    # Verifica se a coluna recovery existe
    cursor.execute("PRAGMA table_info(BOTS)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'recovery' not in columns:
        # Adiciona a coluna se não existir
        cursor.execute("ALTER TABLE BOTS ADD COLUMN recovery TEXT DEFAULT '[]'")
        conn.commit()
    
    cursor.execute("UPDATE BOTS SET recovery = ? WHERE id = ?", (json.dumps(recovery), bot_id))
    conn.commit()
    conn.close()

def get_bot_recovery(bot_id):
    """Retorna as recuperações de um bot"""
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    
    # Verifica se a coluna existe
    cursor.execute("PRAGMA table_info(BOTS)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'recovery' not in columns:
        conn.close()
        return []
    
    cursor.execute('SELECT "recovery" FROM BOTS WHERE "id" = ?', (bot_id,))
    result = cursor.fetchone()
    if result and result[0]:
        conn.close()
        try:
            return json.loads(result[0])
        except:
            return []
    return []

def add_recovery_to_bot(bot_id, recovery_index, recovery_data):
    """Adiciona uma recuperação específica"""
    recoveries = get_bot_recovery(bot_id)
    
    # Garante que temos uma lista de 5 elementos
    while len(recoveries) < 5:
        recoveries.append(None)
    
    # Adiciona a recuperação no índice especificado
    recoveries[recovery_index] = recovery_data
    
    update_bot_recovery(bot_id, recoveries)

def remove_recovery_from_bot(bot_id, recovery_index):
    """Remove uma recuperação específica"""
    recoveries = get_bot_recovery(bot_id)
    
    if len(recoveries) > recovery_index:
        recoveries[recovery_index] = None
        update_bot_recovery(bot_id, recoveries)

def get_recovery_by_index(bot_id, recovery_index):
    """Retorna uma recuperação específica por índice"""
    recoveries = get_bot_recovery(bot_id)
    if len(recoveries) > recovery_index:
        return recoveries[recovery_index]
    return None

# Tabela para rastrear recuperações em andamento
def create_recovery_tracking_table():
    """Cria tabela para rastrear recuperações em andamento"""
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS RECOVERY_TRACKING (
            user_id TEXT,
            bot_id TEXT,
            start_time TEXT,
            recovery_index INTEGER,
            status TEXT,
            PRIMARY KEY (user_id, bot_id)
        )
    """)
    
    conn.commit()
    conn.close()

def start_recovery_tracking(user_id, bot_id):
    """Inicia o rastreamento de recuperação para um usuário"""
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    
    # Verifica se já existe um rastreamento ativo
    cursor.execute("""
        SELECT * FROM RECOVERY_TRACKING 
        WHERE user_id = ? AND bot_id = ? AND status = 'active'
    """, (user_id, bot_id))
    
    existing = cursor.fetchone()
    
    if existing:
        # Já existe rastreamento ativo, não faz nada
        conn.close()
        return False
    
    # Remove rastreamentos antigos inativos
    cursor.execute("""
        DELETE FROM RECOVERY_TRACKING 
        WHERE user_id = ? AND bot_id = ? AND status != 'active'
    """, (user_id, bot_id))
    
    # Insere novo rastreamento
    cursor.execute("""
        INSERT INTO RECOVERY_TRACKING (user_id, bot_id, start_time, recovery_index, status)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, bot_id, datetime.now().isoformat(), -1, 'active'))
    
    conn.commit()
    conn.close()
    return True

def stop_recovery_tracking(user_id, bot_id):
    """Para o rastreamento de recuperação (quando compra ou cancela)"""
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    
    cursor.execute("UPDATE RECOVERY_TRACKING SET status = 'completed' WHERE user_id = ? AND bot_id = ?", (user_id, bot_id))
    
    conn.commit()
    conn.close()

def get_recovery_tracking(user_id, bot_id):
    """Retorna o status de rastreamento de recuperação"""
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM RECOVERY_TRACKING WHERE user_id = ? AND bot_id = ? AND status = 'active'", (user_id, bot_id))
    result = cursor.fetchone()
    
    conn.close()
    return result

def update_recovery_tracking_index(user_id, bot_id, recovery_index):
    """Atualiza o índice da última recuperação enviada"""
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE RECOVERY_TRACKING 
        SET recovery_index = ? 
        WHERE user_id = ? AND bot_id = ? AND status = 'active'
    """, (recovery_index, user_id, bot_id))
    
    conn.commit()
    conn.close()
    
def update_bot_scheduled_broadcasts(bot_id, broadcasts):
    """Atualiza os disparos programados de um bot"""
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    
    # Verifica se a coluna scheduled_broadcasts existe
    cursor.execute("PRAGMA table_info(BOTS)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'scheduled_broadcasts' not in columns:
        # Adiciona a coluna se não existir
        cursor.execute("ALTER TABLE BOTS ADD COLUMN scheduled_broadcasts TEXT DEFAULT '[]'")
        conn.commit()
    
    cursor.execute("UPDATE BOTS SET scheduled_broadcasts = ? WHERE id = ?", (json.dumps(broadcasts), bot_id))
    conn.commit()
    conn.close()

def get_bot_scheduled_broadcasts(bot_id):
    """Retorna os disparos programados de um bot"""
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    
    # Verifica se a coluna existe
    cursor.execute("PRAGMA table_info(BOTS)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'scheduled_broadcasts' not in columns:
        conn.close()
        return []
    
    cursor.execute('SELECT "scheduled_broadcasts" FROM BOTS WHERE "id" = ?', (bot_id,))
    result = cursor.fetchone()
    if result and result[0]:
        conn.close()
        try:
            return json.loads(result[0])
        except:
            return []
    return []

def add_scheduled_broadcast(bot_id, broadcast_data):
    """Adiciona um disparo programado"""
    broadcasts = get_bot_scheduled_broadcasts(bot_id)
    
    # Limita a 3 disparos
    if len(broadcasts) >= 3:
        return False
    
    # Adiciona ID único ao broadcast
    broadcast_data['id'] = len(broadcasts)
    broadcasts.append(broadcast_data)
    
    update_bot_scheduled_broadcasts(bot_id, broadcasts)
    return True

def remove_scheduled_broadcast(bot_id, broadcast_id):
    """Remove um disparo programado específico"""
    broadcasts = get_bot_scheduled_broadcasts(bot_id)
    
    # Filtra removendo o broadcast com o ID especificado
    broadcasts = [b for b in broadcasts if b.get('id') != broadcast_id]
    
    # Reindexar IDs
    for i, broadcast in enumerate(broadcasts):
        broadcast['id'] = i
    
    update_bot_scheduled_broadcasts(bot_id, broadcasts)

def get_all_bots_with_scheduled_broadcasts():
    """Retorna todos os bots que têm disparos programados"""
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    
    # Verifica se a coluna existe
    cursor.execute("PRAGMA table_info(BOTS)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'scheduled_broadcasts' not in columns:
        conn.close()
        return []
    
    cursor.execute("""
        SELECT id, token, scheduled_broadcasts 
        FROM BOTS 
        WHERE scheduled_broadcasts != '[]' 
        AND scheduled_broadcasts IS NOT NULL
    """)
    
    results = cursor.fetchall()
    conn.close()
    
    bots_with_broadcasts = []
    for bot_id, token, broadcasts_json in results:
        try:
            broadcasts = json.loads(broadcasts_json)
            if broadcasts:  # Se tem broadcasts configurados
                bots_with_broadcasts.append({
                    'bot_id': bot_id,
                    'token': token,
                    'broadcasts': broadcasts
                })
        except:
            pass
    
    return bots_with_broadcasts