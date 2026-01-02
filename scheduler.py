import threading
import time
import schedule
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
import json
from database import LocalDatabase

logger = logging.getLogger(__name__)

class WhatsAppSender:
    """# ProScraper Pro v10.0.1 - Sistema Profissional de Scraping e Envios Automáticos
# Sistema de agendamento e envio de mensagens via Evolution API"""
    
    def __init__(self, db: LocalDatabase):
        self.db = db
        self.evolution_api_url = None
        self.evolution_api_key = None
        self.instance_name = None
        self.group_id = None
        self.connected = False
        
    def load_evolution_config(self):
        """Carrega configurações da Evolution API do banco de dados"""
        try:
            api_url = self.db.get_setting('evolution_api_url')
            api_key = self.db.get_setting('evolution_api_key')
            instance_name = self.db.get_setting('evolution_instance_name')
            
            if all([api_url, api_key, instance_name]):
                self.evolution_api_url = api_url.rstrip('/')
                self.evolution_api_key = api_key
                self.instance_name = instance_name
                self.group_id = self.db.get_setting('evolution_group_id')
                self.connected = True
                logger.info("Configurações da Evolution API carregadas do banco")
                return True
            else:
                logger.warning("Configurações da Evolution API não encontradas no banco")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao carregar configurações da Evolution API: {e}")
            return False
        
    def test_connection(self) -> bool:
        """Testa conexão com Evolution API"""
        if not self.connected:
            return False
            
        try:
            headers = {
                'apikey': self.evolution_api_key,
                'Content-Type': 'application/json'
            }
            
            endpoint = f"{self.evolution_api_url}/instance/{self.instance_name}"
            logger.info(f"Testando conexão com: {endpoint}")
            
            response = requests.get(
                endpoint,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Conexão com Evolution API testada com sucesso")
                return True
            else:
                logger.error(f"Erro na conexão: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Erro de conexão com Evolution API: {e}")
            logger.error("Verifique se a Evolution API está rodando em: " + self.evolution_api_url)
            return False
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout na conexão com Evolution API: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro ao testar conexão: {e}")
            return False
    
    def get_group_id(self) -> str:
        """Retorna o ID do grupo configurado"""
        return self.group_id
    
    def send_message(self, phone_number: str, message: str, image_url: str = None) -> bool:
        """Envia mensagem via WhatsApp (texto ou imagem)"""
        if not self.connected:
            logger.error("Evolution API não configurada")
            return False
            
        try:
            headers = {
                'apikey': self.evolution_api_key,
                'Content-Type': 'application/json'
            }
            
            # Enviar com imagem se fornecida
            if image_url:
                payload = {
                    "number": phone_number.replace('+', '').replace(' ', ''),
                    "mediatype": "image",
                    "mimetype": "image/jpeg",
                    "caption": message,
                    "media": image_url,
                    "fileName": "product.jpg",
                    "delay": 0,
                    "linkPreview": True
                }
                
                endpoint = f"{self.evolution_api_url}/message/sendMedia/{self.instance_name}"
                logger.info(f"Enviando mensagem com imagem para {phone_number}")
            else:
                # Enviar apenas texto
                payload = {
                    "number": phone_number.replace('+', '').replace(' ', ''),
                    "text": message
                }
                
                endpoint = f"{self.evolution_api_url}/message/sendText/{self.instance_name}"
                logger.info(f"Enviando mensagem de texto para {phone_number}")
            
            logger.info(f"Fazendo requisição para: {endpoint}")
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Mensagem enviada para {phone_number}")
                return True
            else:
                logger.error(f"Erro ao enviar mensagem: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Erro de conexão com Evolution API: {e}")
            logger.error("Verifique se a Evolution API está rodando em: " + self.evolution_api_url)
            return False
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout na conexão com Evolution API: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            return False
    
    def format_promotion_message(self, product: Dict) -> str:
        """Formata mensagem de promoção com novo padrão"""
        title = product.get('title', 'Produto sem título')
        price_text = product.get('price_current_text', 'Preço não disponível')
        url = product.get('url', '')
        seller_text = self.db.get_setting('seller_text', 'Vendido e entregue por Amazon')
        group_link = self.db.get_setting('group_link', 'https://linktr.ee/Free_Island')
        
        # Formatar mensagem com nova estrutura
        message = f"➡️ {title}\n"
        message += f"{seller_text}\n\n"
        message += f"✅ Por {price_text}\n"
        message += f"🛒 {url}\n\n"
        message += f"☑️ Link do grupo: {group_link}"
        
        return message

class ScheduledSender:
    """Sistema de agendamento de envios automáticos com banco local"""
    
    def __init__(self, db: LocalDatabase):
        self.db = db
        self.whatsapp_sender = WhatsAppSender(db)
        self.running = False
        
        # Carregar configurações da Evolution API do banco
        self.whatsapp_sender.load_evolution_config()
        self.scheduler_thread = None
        
    def start_scheduler(self):
        """Inicia o agendador de envios"""
        if self.running:
            logger.warning("Agendador já está rodando")
            return
            
        self.running = True
        
        # Agendar envio a cada 15 minutos
        schedule.every(15).minutes.do(self._send_scheduled_messages)
        
        # Iniciar thread do agendador
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("Agendador de envios iniciado - executando a cada 15 minutos")
    
    def stop_scheduler(self):
        """Para o agendador de envios"""
        self.running = False
        schedule.clear()
        logger.info("Agendador de envios parado")
    
    def _run_scheduler(self):
        """Loop do agendador"""
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def _send_scheduled_messages(self):
        """Envia mensagens agendadas"""
        try:
            logger.info("Iniciando ciclo de envio automático")
            
            # Buscar produtos pendentes de envio
            pending_products = self.db.get_pending_products()
            
            if not pending_products:
                logger.info("Nenhum produto pendente de envio")
                return
            
            logger.info(f"Encontrados {len(pending_products)} produtos para envio")
            
            # Buscar contatos para envio
            contacts = self.db.get_active_contacts()
            
            if not contacts:
                logger.warning("Nenhum contato ativo encontrado")
                return
            
            # Enviar mensagens
            sent_count = 0
            for product in pending_products:
                product_sent = False
                
                for contact in contacts:
                    phone = contact.get('phone_number')
                    if not phone:
                        continue
                    
                    message = self.whatsapp_sender.format_promotion_message(product)
                    image_url = product.get('image_url')  # Obter URL da imagem
                    
                    success = self.whatsapp_sender.send_message(phone, message, image_url)
                    
                    # Registrar tentativa
                    self.db.log_send_attempt(
                        product['id'], 
                        contact['id'], 
                        success,
                        None if success else "Falha no envio"
                    )
                    
                    if success:
                        sent_count += 1
                        product_sent = True
                        time.sleep(2)  # Delay entre mensagens
                
                # Marcar produto como enviado
                if product_sent:
                    self.db.mark_product_as_sent(product['id'])
                    logger.info(f"Produto {product['id']} marcado como enviado")
            
            logger.info(f"Ciclo finalizado - {sent_count} mensagens enviadas")
            
        except Exception as e:
            logger.error(f"Erro no ciclo de envio: {e}")
    
    def configure_whatsapp(self, api_url: str, api_key: str, instance_name: str):
        """Configura WhatsApp para envios"""
        self.whatsapp_sender.configure_evolution_api(api_url, api_key, instance_name)
        
        # Testar conexão
        if self.whatsapp_sender.test_connection():
            logger.info("WhatsApp configurado e testado com sucesso")
            return True
        else:
            logger.error("Falha na configuração do WhatsApp")
            return False
    
    def get_status(self) -> Dict:
        """Retorna status do sistema"""
        return {
            'scheduler_running': self.running,
            'whatsapp_connected': self.whatsapp_sender.connected,
            'next_run': schedule.next_run() if schedule.jobs else None,
            'jobs_count': len(schedule.jobs)
        }
    
    def update_seller_text(self, seller_text: str):
        """Atualiza o texto do vendedor"""
        self.db.update_setting('seller_text', seller_text)
        logger.info(f"Texto do vendedor atualizado: {seller_text}")
    
    def update_group_link(self, group_link: str):
        """Atualiza o link do grupo"""
        self.db.update_setting('group_link', group_link)
        logger.info(f"Link do grupo atualizado: {group_link}")
    
    def get_settings(self) -> Dict:
        """Retorna configurações atuais"""
        return {
            'seller_text': self.db.get_setting('seller_text', 'Vendido e entregue por Amazon'),
            'group_link': self.db.get_setting('group_link', 'https://linktr.ee/Free_Island')
        }
