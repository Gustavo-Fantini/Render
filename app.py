from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
import logging
import sqlite3
from datetime import datetime
from database import LocalDatabase
from simple_scraper import SimpleScraper
from scheduler import ScheduledSender
import functools

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('proscraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
app.secret_key = 'proscraper-secret-key-2024'  # Chave para sessões

# Decorator para verificar login
def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# Inicializar banco de dados, scheduler e scraper
db = LocalDatabase()
scheduler = ScheduledSender(db)
scraper = SimpleScraper()

# Iniciar scheduler automaticamente
try:
    scheduler.start_scheduler()
    logger.info("Scheduler iniciado automaticamente na inicialização")
except Exception as e:
    logger.error(f"Erro ao iniciar scheduler: {e}")

# Inicializar sistema
logger.info("Sistema inicializado com banco de dados local")

@app.route('/login')
def login_page():
    """Página de login"""
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def login():
    """API de login"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'error': 'Usuário e senha são obrigatórios'
            }), 400
        
        # Verificar credenciais
        if db.verify_user(username, password):
            session['user_id'] = username
            session.permanent = True  # Manter sessão ativa
            logger.info(f"Login bem-sucedido: {username}")
            
            return jsonify({
                'success': True,
                'message': 'Login realizado com sucesso'
            })
        else:
            logger.warning(f"Tentativa de login falhou: {username}")
            return jsonify({
                'success': False,
                'error': 'Usuário ou senha incorretos'
            }), 401
            
    except Exception as e:
        logger.error(f"Erro no login: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro interno do servidor'
        }), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    """API de logout"""
    try:
        session.clear()
        logger.info("Logout realizado")
        return jsonify({
            'success': True,
            'message': 'Logout realizado com sucesso'
        })
    except Exception as e:
        logger.error(f"Erro no logout: {e}")
        return jsonify({
            'success': False,
            'error': 'Erro ao fazer logout'
        }), 500

@app.route('/')
@login_required
def index():
    """Página principal"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Erro ao renderizar template: {e}")
        return """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ProScraper Pro v10.0.1 - Sistema Profissional de Scraping e Envios Automáticos</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head>
<body class="bg-gray-900 text-white min-h-screen flex items-center justify-center">
    <div class="text-center">
        <h1 class="text-4xl font-bold mb-4">ProScraper Pro</h1>
        <p class="text-xl mb-8">Sistema de Envios Automáticos via WhatsApp</p>
        <a href="/sender" class="bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-lg inline-block">
            Ir para Sistema de Envios
        </a>
    </div>
</body>
</html>
        """

@app.route('/sender')
@login_required
def sender_page():
    """Página de gerenciamento simplificada do sistema de envios"""
    return render_template('sender_simple.html')

@app.route('/analyze', methods=['POST'])
def analyze_url():
    """Endpoint principal de scraping simplificado"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'success': False, 'error': 'URL é obrigatória'}), 400
        
        if not url.startswith(('http://', 'https://')):
            return jsonify({'success': False, 'error': 'URL deve começar com http:// ou https://'}), 400
        
        logger.info(f"Nova requisição de scraping: {url}")
        
        # Executar scraping simplificado
        product_data = scraper.scrape_product(url)
        
        # Salvar no banco local
        if product_data.get('title') and product_data.get('price_current_text'):
            db.save_product(product_data)
        
        # Formatar resposta
        response_data = {
            'success': bool(product_data.get('title') and product_data.get('price_current_text')),
            'data': {
                'url': product_data['url'],
                'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                'site_name': product_data.get('site_name'),
                'extraction_time': round(product_data.get('extraction_time', 0), 2),
                'fields': {
                    'title': {
                        'found': bool(product_data.get('title')),
                        'value': product_data.get('title')
                    },
                    'price_current': {
                        'found': bool(product_data.get('price_current')),
                        'value': product_data.get('price_current_text'),
                        'price_float': product_data.get('price_current')
                    },
                    'image_url': {
                        'found': bool(product_data.get('image_url')),
                        'value': product_data.get('image_url')
                    }
                },
                'error': product_data.get('error')
            }
        }
        
        logger.info(f"Scraping concluído - Sucesso: {response_data['success']}")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Erro no endpoint de análise: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Erro interno: {str(e)}'}), 500

@app.route('/api/save-product', methods=['POST'])
def save_product():
    """Salva produto com mensagem no banco local"""
    try:
        data = request.get_json()
        
        title = data.get('title')
        url = data.get('url')
        image_url = data.get('image_url')
        message = data.get('message')
        
        if not all([title, url, message]):
            return jsonify({
                'success': False,
                'error': 'Título, URL e mensagem são obrigatórios'
            }), 400
        
        # Salvar no banco local
        product_data = {
            'title': title,
            'url': url,
            'image_url': image_url,
            'message': message
        }
        
        product_id = db.save_product(product_data)
        
        logger.info(f"Produto salvo: {title}")
        
        return jsonify({
            'success': True,
            'message': 'Produto salvo com sucesso',
            'product_id': product_id
        })
        
    except Exception as e:
        logger.error(f"Erro ao salvar produto: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/queue', methods=['GET'])
def get_queue():
    """Retorna fila de produtos pendentes"""
    try:
        # Buscar produtos não enviados recentemente
        pending_products = db.get_pending_products(limit=10)
        
        # Formatar para resposta
        queue = []
        for product in pending_products:
            queue.append({
                'id': product['id'],
                'title': product['title'],
                'url': product['url'],
                'image_url': product['image_url'],
                'message': f"➡️ {product['title']}\n\n✅ Por {product['price_current_text']}\n🛒 {product['url']}\n\n☑️ Link do grupo: https://linktr.ee/Free_Island",
                'status': 'pendente',
                'sent_count': 0,
                'created_at': product['created_at']
            })
        
        return jsonify({
            'success': True,
            'queue': queue
        })
        
    except Exception as e:
        logger.error(f"Erro ao carregar fila: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """Retorna dados de um produto específico"""
    try:
        with sqlite3.connect('proscraper.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
            product = cursor.fetchone()
            
            if product:
                return jsonify({
                    'success': True,
                    'product': dict(product)
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Produto não encontrado'
                }), 404
                
    except Exception as e:
        logger.error(f"Erro ao buscar produto {product_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """Atualiza dados de um produto"""
    try:
        data = request.get_json()
        
        with sqlite3.connect('proscraper.db') as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE products SET 
                    title = ?, 
                    price_current_text = ?, 
                    url = ?, 
                    image_url = ?, 
                    message = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                data.get('title'),
                data.get('price_current_text'),
                data.get('url'),
                data.get('image_url'),
                data.get('message'),
                product_id
            ))
            
            if cursor.rowcount > 0:
                conn.commit()
                logger.info(f"Produto {product_id} atualizado")
                return jsonify({
                    'success': True,
                    'message': 'Produto atualizado com sucesso'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Produto não encontrado'
                }), 404
                
    except Exception as e:
        logger.error(f"Erro ao atualizar produto {product_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/products/<int:product_id>/send', methods=['POST'])
def send_product_now(product_id):
    """Envia um produto imediatamente"""
    try:
        with sqlite3.connect('proscraper.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Buscar produto
            cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
            product = cursor.fetchone()
            
            if not product:
                return jsonify({
                    'success': False,
                    'error': 'Produto não encontrado'
                }), 404
            
            # Enviar mensagem via Evolution API
            from scheduler import WhatsAppSender
            sender = WhatsAppSender(db)
            sender.load_evolution_config()  # Carregar configurações
            
            # Converter Row para dicionário
            product_dict = dict(product)
            
            message = product_dict['message']
            image_url = product_dict.get('image_url')  # Obter URL da imagem
            group_id = sender.get_group_id()
            
            if not group_id:
                return jsonify({
                    'success': False,
                    'error': 'Grupo não configurado'
                }), 400
            
            success = sender.send_message(group_id, message, image_url)
            
            if success:
                # Registrar log de envio
                cursor.execute('''
                    INSERT INTO send_logs (product_id, sent_at, success, error_message)
                    VALUES (?, CURRENT_TIMESTAMP, ?, ?)
                ''', (product_id, True, None))
                
                # Atualizar contador de envios
                cursor.execute('''
                    UPDATE products SET sent_count = sent_count + 1, last_sent = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (product_id,))
                
                conn.commit()
                logger.info(f"Produto {product_id} enviado imediatamente com sucesso")
                
                return jsonify({
                    'success': True,
                    'message': 'Produto enviado com sucesso'
                })
            else:
                # Registrar falha
                cursor.execute('''
                    INSERT INTO send_logs (product_id, sent_at, success, error_message)
                    VALUES (?, CURRENT_TIMESTAMP, ?, ?)
                ''', (product_id, False, 'Falha no envio'))
                
                conn.commit()
                
                return jsonify({
                    'success': False,
                    'error': 'Falha ao enviar mensagem'
                }), 500
                
    except Exception as e:
        logger.error(f"Erro ao enviar produto {product_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Exclui um produto"""
    try:
        with sqlite3.connect('proscraper.db') as conn:
            cursor = conn.cursor()
            
            # Excluir logs relacionados primeiro
            cursor.execute('DELETE FROM send_logs WHERE product_id = ?', (product_id,))
            
            # Excluir o produto
            cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
            
            if cursor.rowcount > 0:
                conn.commit()
                logger.info(f"Produto {product_id} excluído")
                return jsonify({
                    'success': True,
                    'message': 'Produto excluído com sucesso'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Produto não encontrado'
                }), 404
                
    except Exception as e:
        logger.error(f"Erro ao excluir produto {product_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sender/status', methods=['GET'])
def get_sender_status():
    """Retorna status do sistema de envios"""
    try:
        # Verificar configurações da Evolution API
        api_url = db.get_setting('evolution_api_url')
        api_key = db.get_setting('evolution_api_key')
        instance_name = db.get_setting('evolution_instance_name')
        group_id = db.get_setting('evolution_group_id')
        
        # Criar sender e carregar configurações
        from scheduler import WhatsAppSender
        sender = WhatsAppSender(db)
        sender.load_evolution_config()
        
        # Testar conexão
        connected = sender.test_connection() if sender.connected else False
        
        return jsonify({
            'success': True,
            'status': {
                'configured': bool(api_url and api_key and instance_name),
                'connected': connected,
                'group_configured': bool(group_id),
                'api_url': api_url,
                'instance_name': instance_name,
                'group_id': group_id
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'database': 'local_sqlite',
        'scheduler_running': scheduler.get_status()['scheduler_running']
    })

# ==================== INICIALIZAÇÃO ====================

@app.route('/api/scheduler/interval', methods=['GET'])
def get_scheduler_interval():
    """Retorna o intervalo atual do agendamento"""
    try:
        with sqlite3.connect('proscraper.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT value FROM settings WHERE key = "scheduler_interval"')
            result = cursor.fetchone()
            
            interval = int(result['value']) if result else 15
            
            return jsonify({
                'success': True,
                'interval': interval
            })
            
    except Exception as e:
        logger.error(f"Erro ao buscar intervalo: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/scheduler/interval', methods=['POST'])
def update_scheduler_interval():
    """Atualiza o intervalo do agendamento"""
    try:
        data = request.get_json()
        interval = data.get('interval', 15)
        
        # Validar intervalo (mínimo 5 minutos)
        if interval < 5:
            return jsonify({
                'success': False,
                'error': 'Intervalo mínimo é 5 minutos'
            }), 400
        
        with sqlite3.connect('proscraper.db') as conn:
            cursor = conn.cursor()
            
            # Atualizar ou inserir configuração
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES ('scheduler_interval', ?, CURRENT_TIMESTAMP)
            ''', (interval,))
            
            conn.commit()
            
            # Atualizar scheduler em execução
            if scheduler and scheduler.running:
                scheduler.stop_scheduler()
                scheduler.interval = interval * 60  # Converter para segundos
                scheduler.start_scheduler()
                logger.info(f"Scheduler atualizado para {interval} minutos")
            
            return jsonify({
                'success': True,
                'message': f'Intervalo atualizado para {interval} minutos',
                'interval': interval
            })
            
    except Exception as e:
        logger.error(f"Erro ao atualizar intervalo: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/scheduler/status', methods=['GET'])
def get_scheduler_status():
    """Retorna o status atual do agendamento"""
    try:
        return jsonify({
            'success': True,
            'running': scheduler.running if scheduler else False,
            'interval': scheduler.interval // 60 if scheduler else 15
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/scheduler/start', methods=['POST'])
def start_scheduler():
    """Inicia o agendamento"""
    try:
        if scheduler and not scheduler.running:
            scheduler.start_scheduler()
            logger.info("Scheduler iniciado manualmente")
            
            return jsonify({
                'success': True,
                'message': 'Scheduler iniciado com sucesso'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Scheduler já está em execução'
            }), 400
            
    except Exception as e:
        logger.error(f"Erro ao iniciar scheduler: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/scheduler/stop', methods=['POST'])
def stop_scheduler():
    """Para o agendamento"""
    try:
        if scheduler and scheduler.running:
            scheduler.stop_scheduler()
            logger.info("Scheduler parado manualmente")
            
            return jsonify({
                'success': True,
                'message': 'Scheduler parado com sucesso'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Scheduler não está em execução'
            }), 400
            
    except Exception as e:
        logger.error(f"Erro ao parar scheduler: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    logger.info("Iniciando ProScraper Pro com banco local")
    logger.info("ENDPOINTS:")
    logger.info("   - GET  / - Página principal")
    logger.info("   - GET  /sender - Sistema de envios")
    logger.info("   - POST /analyze - Scraping simplificado")
    logger.info("   - GET  /health - Status do sistema")
    logger.info("")
    logger.info("Banco de dados: proscraper.db (SQLite)")
    logger.info("Servidor iniciado em: http://localhost:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
