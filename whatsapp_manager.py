import logging
from typing import Dict, List, Optional
from evolution_service import get_evolution_service, EvolutionAPIService
from database import LocalDatabase

logger = logging.getLogger(__name__)

class WhatsAppManager:
    """Gerenciador de envios WhatsApp com Evolution API"""
    
    def __init__(self, db: LocalDatabase):
        self.db = db
        self.evolution_service = get_evolution_service()
    
    def send_to_group(self, message: str, group_id: str) -> Dict:
        """Envia mensagem para grupo específico"""
        if not self.evolution_service:
            return {"success": False, "error": "Evolution API não configurada"}
        
        try:
            # Obter nome da instância
            instance_name = self.db.get_setting('whatsapp_instance', 'default')
            
            # Enviar mensagem
            result = self.evolution_service.send_to_group(instance_name, group_id, message)
            
            if result["success"]:
                logger.info(f"Mensagem enviada para grupo {group_id}")
                return {"success": True, "message": "Mensagem enviada com sucesso"}
            else:
                logger.error(f"Erro ao enviar mensagem: {result.get('error')}")
                return {"success": False, "error": result.get('error')}
                
        except Exception as e:
            logger.error(f"Erro ao enviar para grupo: {e}")
            return {"success": False, "error": str(e)}
    
    def send_to_contacts(self, message: str, contacts: List[str] = None) -> Dict:
        """Envia mensagem para lista de contatos"""
        if not self.evolution_service:
            return {"success": False, "error": "Evolution API não configurada"}
        
        if not contacts:
            # Usar contatos do banco
            contacts_data = self.db.get_active_contacts()
            contacts = [c['phone_number'] for c in contacts_data]
        
        if not contacts:
            return {"success": False, "error": "Nenhum contato encontrado"}
        
        try:
            instance_name = self.db.get_setting('whatsapp_instance', 'default')
            results = []
            
            for contact in contacts:
                result = self.evolution_service.send_message(instance_name, contact, message)
                results.append({
                    "contact": contact,
                    "success": result["success"],
                    "error": result.get("error")
                })
            
            success_count = sum(1 for r in results if r["success"])
            
            return {
                "success": True,
                "total": len(contacts),
                "success_count": success_count,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Erro ao enviar para contatos: {e}")
            return {"success": False, "error": str(e)}
    
    def test_connection(self) -> Dict:
        """Testa conexão com Evolution API"""
        if not self.evolution_service:
            return {"success": False, "error": "Evolution API não configurada"}
        
        try:
            connected = self.evolution_service.test_connection()
            
            if connected:
                # Verificar instância
                instance_name = self.db.get_setting('whatsapp_instance', 'default')
                instances = self.evolution_service.get_instances()
                
                instance_exists = any(
                    instance.get('instanceName') == instance_name 
                    for instance in instances
                )
                
                return {
                    "success": True,
                    "connected": True,
                    "instance_exists": instance_exists,
                    "instance_name": instance_name
                }
            else:
                return {"success": False, "connected": False}
                
        except Exception as e:
            logger.error(f"Erro ao testar conexão: {e}")
            return {"success": False, "error": str(e)}
    
    def get_qr_code(self) -> Optional[str]:
        """Obtém QR Code para conexão"""
        if not self.evolution_service:
            return None
        
        try:
            instance_name = self.db.get_setting('whatsapp_instance', 'default')
            return self.evolution_service.get_qr_code(instance_name)
        except Exception as e:
            logger.error(f"Erro ao obter QR Code: {e}")
            return None
    
    def create_instance(self, instance_name: str) -> Dict:
        """Cria nova instância WhatsApp"""
        if not self.evolution_service:
            return {"success": False, "error": "Evolution API não configurada"}
        
        try:
            result = self.evolution_service.create_instance(instance_name)
            
            if result.get("success", True):
                # Salvar nome da instância
                self.db.update_setting('whatsapp_instance', instance_name)
                logger.info(f"Instância {instance_name} criada com sucesso")
                return {"success": True, "message": "Instância criada"}
            else:
                return {"success": False, "error": result.get("error")}
                
        except Exception as e:
            logger.error(f"Erro ao criar instância: {e}")
            return {"success": False, "error": str(e)}
    
    def check_connection_status(self) -> Dict:
        """Verifica status da conexão WhatsApp"""
        if not self.evolution_service:
            return {"success": False, "error": "Evolution API não configurada"}
        
        try:
            instance_name = self.db.get_setting('whatsapp_instance', 'default')
            return self.evolution_service.check_connection_status(instance_name)
        except Exception as e:
            logger.error(f"Erro ao verificar status: {e}")
            return {"success": False, "error": str(e)}

# Instância global
whatsapp_manager = None

def init_whatsapp_manager(db: LocalDatabase):
    """Inicializa o gerenciador WhatsApp"""
    global whatsapp_manager
    whatsapp_manager = WhatsAppManager(db)
    return whatsapp_manager

def get_whatsapp_manager() -> Optional[WhatsAppManager]:
    """Obtém instância do gerenciador"""
    return whatsapp_manager
