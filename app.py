from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import logging
from datetime import datetime
from database import LocalDatabase
from evolution_service import init_evolution_service
from whatsapp_manager import init_whatsapp_manager, get_whatsapp_manager
from simple_scraper import SimpleScraper
from scheduler import ScheduledSender

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

# Inicialização do banco de dados e serviços
db = LocalDatabase()
scraper = SimpleScraper()
scheduler = ScheduledSender(db)

# Inicializar serviços WhatsApp
whatsapp_manager = init_whatsapp_manager(db)

# Configurações da Evolution API (se existirem)
api_url = db.get_setting('evolution_api_url')
api_key = db.get_setting('evolution_api_key')

if api_url and api_key:
    evolution_service = init_evolution_service(api_url, api_key)
    logger.info("Evolution API configurada")
else:
    logger.info("Evolution API não configurada - usando modo local")

logger.info("Sistema inicializado com banco de dados local")

@app.route('/')
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
    <title>ProScraper Pro - Sistema de Envios Automáticos</title>
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

# ==================== ROTAS DO SISTEMA DE ENVIOS ====================

@app.route('/api/sender/status', methods=['GET'])
def get_sender_status():
    """Retorna status do sistema de envios"""
    try:
        status = scheduler.get_status()
        stats = db.get_stats()
        
        return jsonify({
            'success': True,
            'status': status,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Erro ao obter status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sender/start', methods=['POST'])
def start_sender():
    """Inicia o sistema de envios automáticos"""
    try:
        scheduler.start_scheduler()
        logger.info("Sistema de envios iniciado via API")
        
        return jsonify({
            'success': True,
            'message': 'Sistema de envios iniciado com sucesso'
        })
    except Exception as e:
        logger.error(f"Erro ao iniciar sender: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sender/stop', methods=['POST'])
def stop_sender():
    """Para o sistema de envios automáticos"""
    try:
        scheduler.stop_scheduler()
        logger.info("Sistema de envios parado via API")
        
        return jsonify({
            'success': True,
            'message': 'Sistema de envios parado com sucesso'
        })
    except Exception as e:
        logger.error(f"Erro ao parar sender: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sender/configure-whatsapp', methods=['POST'])
def configure_whatsapp():
    """Configura a conexão com Evolution API"""
    try:
        data = request.get_json()
        
        api_url = data.get('api_url')
        api_key = data.get('api_key')
        instance_name = data.get('instance_name')
        
        if not all([api_url, api_key, instance_name]):
            return jsonify({
                'success': False,
                'error': 'Todos os campos são obrigatórios: api_url, api_key, instance_name'
            }), 400
        
        success = scheduler.configure_whatsapp(api_url, api_key, instance_name)
        
        if success:
            logger.info("WhatsApp configurado via API")
            return jsonify({
                'success': True,
                'message': 'WhatsApp configurado com sucesso'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Falha ao configurar WhatsApp'
            }), 500
            
    except Exception as e:
        logger.error(f"Erro ao configurar WhatsApp: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sender/test-connection', methods=['POST'])
def test_whatsapp_connection():
    """Testa conexão com Evolution API"""
    try:
        if not scheduler.whatsapp_sender.connected:
            return jsonify({
                'success': False,
                'error': 'WhatsApp não configurado'
            }), 400
        
        success = scheduler.whatsapp_sender.test_connection()
        
        return jsonify({
            'success': success,
            'message': 'Conexão bem-sucedida' if success else 'Falha na conexão'
        })
        
    except Exception as e:
        logger.error(f"Erro ao testar conexão: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sender/send-test', methods=['POST'])
def send_test_message():
    """Envia mensagem de teste"""
    try:
        data = request.get_json()
        phone_number = data.get('phone_number')
        
        if not phone_number:
            return jsonify({
                'success': False,
                'error': 'Número de telefone é obrigatório'
            }), 400
        
        if not scheduler.whatsapp_sender.connected:
            return jsonify({
                'success': False,
                'error': 'WhatsApp não configurado'
            }), 400
        
        # Mensagem de teste
        test_message = f"🧪 *Mensagem de Teste*\n\nSistema de envios automático funcionando!\n\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        
        success = scheduler.whatsapp_sender.send_message(phone_number, test_message)
        
        if success:
            logger.info(f"Mensagem de teste enviada para {phone_number}")
            return jsonify({
                'success': True,
                'message': 'Mensagem de teste enviada com sucesso'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Falha ao enviar mensagem de teste'
            }), 500
            
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem de teste: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sender/contacts', methods=['GET', 'POST'])
def manage_contacts():
    """Gerencia contatos para envio"""
    try:
        if request.method == 'GET':
            # Listar contatos
            contacts = db.get_active_contacts()
            return jsonify({
                'success': True,
                'contacts': contacts
            })
        
        elif request.method == 'POST':
            # Adicionar contato
            data = request.get_json()
            name = data.get('name')
            phone_number = data.get('phone_number')
            
            if not all([name, phone_number]):
                return jsonify({
                    'success': False,
                    'error': 'Nome e número de telefone são obrigatórios'
                }), 400
            
            contact_id = db.add_contact(name, phone_number)
            
            logger.info(f"Contato {name} adicionado")
            return jsonify({
                'success': True,
                'message': 'Contato adicionado com sucesso',
                'contact_id': contact_id
            })
            
    except Exception as e:
        logger.error(f"Erro ao gerenciar contatos: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sender/settings', methods=['GET', 'POST'])
def manage_settings():
    """Gerencia configurações do sistema"""
    try:
        if request.method == 'GET':
            # Obter configurações
            settings = scheduler.get_settings()
            return jsonify({
                'success': True,
                'settings': settings
            })
        
        elif request.method == 'POST':
            # Atualizar configurações
            data = request.get_json()
            
            if 'seller_text' in data:
                scheduler.update_seller_text(data['seller_text'])
            
            if 'group_link' in data:
                scheduler.update_group_link(data['group_link'])
            
            return jsonify({
                'success': True,
                'message': 'Configurações atualizadas com sucesso'
            })
            
    except Exception as e:
        logger.error(f"Erro ao gerenciar configurações: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sender/products', methods=['GET'])
def list_products():
    """Lista produtos recentes"""
    try:
        limit = request.args.get('limit', 20, type=int)
        products = db.get_pending_products(limit)
        
        return jsonify({
            'success': True,
            'products': products
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar produtos: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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
                'message': f"➡️ {product['title']}\nVendido e entregue por Amazon\n\n✅ Por {product['price_current_text']}\n🛒 {product['url']}\n\n☑️ Link do grupo: https://linktr.ee/Free_Island",
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

@app.route('/api/whatsapp/configure', methods=['POST'])
def configure_whatsapp():
    """Configura Evolution API"""
    try:
        data = request.get_json()
        
        api_url = data.get('api_url')
        api_key = data.get('api_key')
        instance_name = data.get('instance_name')
        
        if not all([api_url, api_key]):
            return jsonify({
                'success': False,
                'error': 'API URL e API Key são obrigatórios'
            }), 400
        
        # Salvar configurações no banco
        db.update_setting('evolution_api_url', api_url)
        db.update_setting('evolution_api_key', api_key)
        if instance_name:
            db.update_setting('whatsapp_instance', instance_name)
        
        # Inicializar serviço
        evolution_service = init_evolution_service(api_url, api_key)
        
        # Testar conexão
        whatsapp_mgr = get_whatsapp_manager()
        if whatsapp_mgr:
            result = whatsapp_mgr.test_connection()
            return jsonify(result)
        else:
            return jsonify({
                'success': False,
                'error': 'Erro ao inicializar gerenciador WhatsApp'
            }), 500
            
    except Exception as e:
        logger.error(f"Erro ao configurar WhatsApp: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/whatsapp/test', methods=['POST'])
def test_whatsapp():
    """Testa conexão WhatsApp"""
    try:
        whatsapp_mgr = get_whatsapp_manager()
        if not whatsapp_mgr:
            return jsonify({
                'success': False,
                'error': 'Gerenciador WhatsApp não inicializado'
            }), 400
        
        result = whatsapp_mgr.test_connection()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erro ao testar WhatsApp: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/whatsapp/send-test', methods=['POST'])
def send_test_message():
    """Envia mensagem de teste"""
    try:
        data = request.get_json()
        message = data.get('message', 'Mensagem de teste - ProScraper Pro')
        group_id = data.get('group_id')
        
        if not group_id:
            return jsonify({
                'success': False,
                'error': 'ID do grupo é obrigatório'
            }), 400
        
        whatsapp_mgr = get_whatsapp_manager()
        if not whatsapp_mgr:
            return jsonify({
                'success': False,
                'error': 'Gerenciador WhatsApp não inicializado'
            }), 400
        
        result = whatsapp_mgr.send_to_group(message, group_id)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem teste: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/whatsapp/qrcode', methods=['GET'])
def get_qr_code():
    """Obtém QR Code para conexão"""
    try:
        whatsapp_mgr = get_whatsapp_manager()
        if not whatsapp_mgr:
            return jsonify({
                'success': False,
                'error': 'Gerenciador WhatsApp não inicializado'
            }), 400
        
        qr_code = whatsapp_mgr.get_qr_code()
        if qr_code:
            return jsonify({
                'success': True,
                'qr_code': qr_code
            })
        else:
            return jsonify({
                'success': False,
                'error': 'QR Code não disponível'
            }), 404
        
    except Exception as e:
        logger.error(f"Erro ao obter QR Code: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/whatsapp/create-instance', methods=['POST'])
def create_whatsapp_instance():
    """Cria nova instância WhatsApp"""
    try:
        data = request.get_json()
        instance_name = data.get('instance_name', 'default')
        
        whatsapp_mgr = get_whatsapp_manager()
        if not whatsapp_mgr:
            return jsonify({
                'success': False,
                'error': 'Gerenciador WhatsApp não inicializado'
            }), 400
        
        result = whatsapp_mgr.create_instance(instance_name)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erro ao criar instância: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/whatsapp/status', methods=['GET'])
def get_whatsapp_status():
    """Obtém status detalhado do WhatsApp"""
    try:
        whatsapp_mgr = get_whatsapp_manager()
        if not whatsapp_mgr:
            return jsonify({
                'success': False,
                'error': 'Gerenciador WhatsApp não inicializado'
            }), 400
        
        # Status da conexão
        connection_status = whatsapp_mgr.test_connection()
        
        # Status da instância
        instance_status = whatsapp_mgr.check_connection_status()
        
        return jsonify({
            'success': True,
            'connection': connection_status,
            'instance': instance_status
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter status WhatsApp: {e}")
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
