#!/usr/bin/env python3
"""
ProScraper Pro v10.0.1 - Verificação Evolution API
Verifica instâncias disponíveis na Evolution API
"""

import requests
import json

def check_instances():
    """Verifica instâncias disponíveis"""
    api_url = "https://evolution-api-render-qhmq.onrender.com"
    
    print("=== Verificação Evolution API ===")
    print(f"URL: {api_url}")
    print()
    
    try:
        # Tentar verificar instâncias sem autenticação
        endpoint = f"{api_url}/instance/fetchInstances"
        print(f"Verificando: {endpoint}")
        
        response = requests.get(endpoint, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API está online!")
            
            instances = data.get('response', [])
            if instances:
                print(f"\n📱 Instâncias disponíveis ({len(instances)}):")
                for instance in instances:
                    print(f"  - Nome: {instance.get('name')}")
                    print(f"    Status: {instance.get('state')}")
                    print(f"    Conectada: {instance.get('connected')}")
                    print()
            else:
                print("❌ Nenhuma instância encontrada")
                print("Você precisa criar uma instância no manager:")
                print(f"https://evolution-api-render-qhmq.onrender.com/manager/")
                
        elif response.status_code == 401:
            print("❌ Erro de autenticação (401)")
            print("Possíveis causas:")
            print("1. API Key incorreta")
            print("2. API Key não foi gerada ainda")
            print("3. Instância não existe")
            print()
            print("Ações necessárias:")
            print("1. Acesse: https://evolution-api-render-qhmq.onrender.com/manager/")
            print("2. Crie uma instância com nome 'Whatsapp'")
            print("3. Gere uma API Key")
            print("4. Atualize a configuração com a nova API Key")
            
        else:
            print(f"❌ Erro: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Erro de conexão: {e}")
        print("Verifique se a URL está correta")
    except Exception as e:
        print(f"❌ Erro: {e}")

def show_manager_info():
    """Mostra informações do manager"""
    print("\n=== Acesso ao Manager ===")
    print("URL: https://evolution-api-render-qhmq.onrender.com/manager/")
    print()
    print("Passos para configurar:")
    print("1. Acesse o link acima")
    print("2. Clique em 'Create Instance'")
    print("3. Nome: Whatsapp")
    print("4. Número: seu número com código do país")
    print("5. Clique em 'Create'")
    print("6. Aguarde o QR Code")
    print("7. Escaneie com seu WhatsApp")
    print("8. Após conectar, vá em 'Settings'")
    print("9. Copie a 'Global ApiKey'")
    print("10. Execute: python setup_render_api.py")
    print("11. Cole a nova API Key")

if __name__ == "__main__":
    print("ProScraper Pro v10.0.1 - Verificação Evolution API")
    print("=" * 50)
    
    check_instances()
    show_manager_info()
