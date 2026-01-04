#!/usr/bin/env python3
"""
ProScraper Pro v10.0.1 - Teste de Conexão Evolution API
Testa a conexão com a Evolution API no Render
"""

import requests
import json
from database import LocalDatabase

def test_evolution_api():
    """Testa conexão com Evolution API"""
    db = LocalDatabase()
    
    # Obter configurações
    api_url = db.get_setting('evolution_api_url')
    api_key = db.get_setting('evolution_api_key')
    instance_name = db.get_setting('evolution_instance_name')
    
    print("=== Teste de Conexão Evolution API ===")
    print(f"URL: {api_url}")
    print(f"Instance: {instance_name}")
    print(f"API Key: {api_key[:20]}...")
    print()
    
    if not all([api_url, api_key, instance_name]):
        print("❌ Configurações incompletas!")
        return False
    
    try:
        # Testar conexão com a instância
        headers = {
            'apikey': api_key,
            'Content-Type': 'application/json'
        }
        
        # Endpoint correto para verificar instância
        endpoint = f"{api_url}/instance/fetchInstances"
        print(f"Testando: {endpoint}")
        
        response = requests.get(endpoint, headers=headers, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Conexão bem-sucedida!")
            
            # Verificar se a instância existe
            instances = data.get('response', [])
            found_instance = None
            
            for instance in instances:
                if instance.get('name') == instance_name:
                    found_instance = instance
                    break
            
            if found_instance:
                print(f"Instance: {found_instance.get('name')}")
                print(f"Status: {found_instance.get('state')}")
                print(f"Connected: {found_instance.get('connected')}")
                return True
            else:
                print(f"❌ Instância '{instance_name}' não encontrada!")
                print("Instâncias disponíveis:")
                for instance in instances:
                    print(f"  - {instance.get('name')}")
                return False
        else:
            print(f"❌ Erro na conexão: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Erro de conexão: {e}")
        print("Verifique se a URL está correta e a API está online")
        return False
    except requests.exceptions.Timeout as e:
        print(f"❌ Timeout: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def test_send_message():
    """Teste de envio de mensagem"""
    db = LocalDatabase()
    
    # Obter configurações
    api_url = db.get_setting('evolution_api_url')
    api_key = db.get_setting('evolution_api_key')
    instance_name = db.get_setting('evolution_instance_name')
    group_id = db.get_setting('evolution_group_id')
    
    print("\n=== Teste de Envio de Mensagem ===")
    print(f"Grupo: {group_id}")
    
    if not all([api_url, api_key, instance_name, group_id]):
        print("❌ Configurações incompletas!")
        return False
    
    try:
        headers = {
            'apikey': api_key,
            'Content-Type': 'application/json'
        }
        
        payload = {
            "number": group_id,
            "text": "🧪 Teste de conexão - ProScraper Pro v10.0.1\n\n✅ API conectada com sucesso!"
        }
        
        endpoint = f"{api_url}/message/sendText/{instance_name}"
        print(f"Enviando mensagem para: {endpoint}")
        
        response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Mensagem enviada com sucesso!")
            print(f"Message ID: {data.get('key', {}).get('id', 'N/A')}")
            return True
        else:
            print(f"❌ Erro ao enviar: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    print("ProScraper Pro v10.0.1 - Teste Evolution API Render")
    print("=" * 50)
    
    # Testar conexão
    connection_ok = test_evolution_api()
    
    if connection_ok:
        # Testar envio de mensagem
        send_ok = test_send_message()
        
        if send_ok:
            print("\n🎉 Todos os testes passaram!")
            print("✅ Evolution API está funcionando perfeitamente!")
        else:
            print("\n⚠️ Conexão OK, mas envio falhou")
    else:
        print("\n❌ Falha na conexão")
        print("Verifique as configurações e tente novamente")
