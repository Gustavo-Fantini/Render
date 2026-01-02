import requests
import json
import logging
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class EvolutionAPIService:
    """Serviço para integração com Evolution API v2"""
    
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'apikey': api_key,
            'Content-Type': 'application/json'
        }
    
    def test_connection(self) -> bool:
        """Testa conexão com a Evolution API"""
        try:
            response = requests.get(
                f"{self.api_url}/instance",
                headers=self.headers,
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Erro ao testar conexão: {e}")
            return False
    
    def create_instance(self, instance_name: str, number: str = None) -> Dict:
        """Cria uma nova instância do WhatsApp"""
        try:
            data = {
                "instanceName": instance_name,
                "token": self.api_key,
                "qrcode": True,
                "number": number
            }
            
            response = requests.post(
                f"{self.api_url}/instance/create",
                headers=self.headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 201:
                return response.json()
            else:
                logger.error(f"Erro ao criar instância: {response.text}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logger.error(f"Erro ao criar instância: {e}")
            return {"success": False, "error": str(e)}
    
    def get_instances(self) -> List[Dict]:
        """Lista todas as instâncias"""
        try:
            response = requests.get(
                f"{self.api_url}/instance",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return []
                
        except Exception as e:
            logger.error(f"Erro ao listar instâncias: {e}")
            return []
    
    def get_qr_code(self, instance_name: str) -> Optional[str]:
        """Obtém o QR Code para conexão"""
        try:
            response = requests.get(
                f"{self.api_url}/instance/qrcode/{instance_name}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('qrcode', {}).get('base64')
            else:
                return None
                
        except Exception as e:
            logger.error(f"Erro ao obter QR Code: {e}")
            return None
    
    def check_connection_status(self, instance_name: str) -> Dict:
        """Verifica status da conexão"""
        try:
            response = requests.get(
                f"{self.api_url}/instance/connect/{instance_name}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"connected": False, "error": response.text}
                
        except Exception as e:
            logger.error(f"Erro ao verificar status: {e}")
            return {"connected": False, "error": str(e)}
    
    def send_message(self, instance_name: str, number: str, message: str) -> Dict:
        """Envia mensagem WhatsApp"""
        try:
            data = {
                "number": number,
                "textMessage": {
                    "text": message
                }
            }
            
            response = requests.post(
                f"{self.api_url}/message/sendText/{instance_name}",
                headers=self.headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                logger.error(f"Erro ao enviar mensagem: {response.text}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            return {"success": False, "error": str(e)}
    
    def send_to_group(self, instance_name: str, group_id: str, message: str) -> Dict:
        """Envia mensagem para grupo"""
        try:
            data = {
                "groupJid": group_id,
                "textMessage": {
                    "text": message
                }
            }
            
            response = requests.post(
                f"{self.api_url}/message/sendText/{instance_name}",
                headers=self.headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                logger.error(f"Erro ao enviar para grupo: {response.text}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logger.error(f"Erro ao enviar para grupo: {e}")
            return {"success": False, "error": str(e)}
    
    def get_group_info(self, instance_name: str, group_id: str) -> Dict:
        """Obtém informações do grupo"""
        try:
            response = requests.get(
                f"{self.api_url}/group/{instance_name}/{group_id}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logger.error(f"Erro ao obter info do grupo: {e}")
            return {"success": False, "error": str(e)}

# Instância global do serviço
evolution_service = None

def init_evolution_service(api_url: str, api_key: str):
    """Inicializa o serviço Evolution API"""
    global evolution_service
    evolution_service = EvolutionAPIService(api_url, api_key)
    return evolution_service

def get_evolution_service() -> Optional[EvolutionAPIService]:
    """Obtém a instância do serviço"""
    return evolution_service
