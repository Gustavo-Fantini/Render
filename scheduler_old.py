import threading
import time
import schedule
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
import json
from supabase import create_client, Client

logger = logging.getLogger(__name__)

class WhatsAppSender:
    """Sistema de envio automático de mensagens via WhatsApp Evolution API"""
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self.evolution_api_url = None
        self.evolution_api_key = None
        self.instance_name = None
        self.connected = False
        
    def configure_evolution_api(self, api_url: str, api_key: str, instance_name: str):
        """Configura a conexão com Evolution API"""
        self.evolution_api_url = api_url.rstrip('/')
        self.evolution_api_key = api_key
        self.instance_name = instance_name
        self.connected = True
        logger.info(f"Evolution API configurada: {api_url}")
        
    def test_connection(self) -> bool:
        """Testa conexão com Evolution API"""
        if not self.connected:
            return False
            
        try:
            headers = {
                'apikey': self.evolution_api_key,
                'Content-Type': 'application/json'
            }
            
            # Verificar status da instância
            response = requests.get(
                f"{self.evolution_api_url}/instance/{self.instance_name}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Conexão com Evolution API testada com sucesso")
                return True
            else:
                logger.error(f"Erro na conexão: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao testar conexão: {e}")
            return False
    
    def send_message(self, phone_number: str, message: str) -> bool:
        """Envia mensagem via WhatsApp"""
        if not self.connected:
            logger.error("Evolution API não configurada")
            return False
            
        try:
            headers = {
                'apikey': self.evolution_api_key,
                'Content-Type': 'application/json'
            }
            
            payload = {
                "number": phone_number.replace('+', '').replace(' ', ''),
                "text": message
            }
            
            response = requests.post(
                f"{self.evolution_api_url}/message/sendText/{self.instance_name}",
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
                
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            return False
    
    def format_promotion_message(self, product: Dict) -> str:
        """Formata mensagem de promoção"""
        title = product.get('title', 'Produto sem título')
        price_current = product.get('price_current_text', 'Preço não disponível')
        price_original = product.get('price_original_text', '')
        url = product.get('url', '')
        
        message = f"🔥 *OFERTA IMPERDÍVEL*\n\n"
        message += f"📦 {title}\n\n"
        
        if price_original and price_original != price_current:
            message += f"💰 De: {price_original}\n"
            message += f"💎 Por: {price_current}\n"
            
            # Calcular desconto
            try:
                current_num = float(price_current.replace('R$', '').replace('.', '').replace(',', '.'))
                original_num = float(price_original.replace('R$', '').replace('.', '').replace(',', '.'))
                if original_num > 0:
                    discount = ((original_num - current_num) / original_num) * 100
                    message += f"🎯 Desconto: {discount:.0f}% OFF\n"
            except:
                pass
        else:
            message += f"💰 Preço: {price_current}\n"
        
        message += f"\n🔗 {url}\n\n"
        message += "⚡ Aproveite agora!"
        
        return message

class ScheduledSender:
    """Sistema de agendamento de envios automáticos"""
    
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self.whatsapp_sender = WhatsAppSender(supabase_client)
        self.running = False
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
            pending_products = self._get_pending_products()
            
            if not pending_products:
                logger.info("Nenhum produto pendente de envio")
                return
            
            logger.info(f"Encontrados {len(pending_products)} produtos para envio")
            
            # Buscar contatos para envio
            contacts = self._get_active_contacts()
            
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
                    
                    if self.whatsapp_sender.send_message(phone, message):
                        sent_count += 1
                        product_sent = True
                        time.sleep(2)  # Delay entre mensagens
                
                # Marcar produto como enviado
                if product_sent:
                    self._mark_product_as_sent(product['id'])
                    logger.info(f"Produto {product['id']} marcado como enviado")
            
            logger.info(f"Ciclo finalizado - {sent_count} mensagens enviadas")
            
        except Exception as e:
            logger.error(f"Erro no ciclo de envio: {e}")
    
    def _get_pending_products(self) -> List[Dict]:
        """Busca produtos pendentes de envio"""
        try:
            # Verificar produtos que não foram enviados nas últimas 24h
            twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
            
            response = self.supabase.table('products').select('*').eq('active', True).or_(
                f"sent.is.null,sent.lt.{twenty_four_hours_ago.isoformat()}"
            ).order('created_at', desc=True).limit(10).execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Erro ao buscar produtos pendentes: {e}")
            return []
    
    def _get_active_contacts(self) -> List[Dict]:
        """Busca contatos ativos para envio"""
        try:
            response = self.supabase.table('contacts').select('*').eq('active', True).execute()
            return response.data or []
            
        except Exception as e:
            logger.error(f"Erro ao buscar contatos: {e}")
            return []
    
    def _mark_product_as_sent(self, product_id: str):
        """Marca produto como enviado"""
        try:
            self.supabase.table('products').update({
                'sent': datetime.now().isoformat(),
                'enviado': True
            }).eq('id', product_id).execute()
            
        except Exception as e:
            logger.error(f"Erro ao marcar produto como enviado: {e}")
    
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
