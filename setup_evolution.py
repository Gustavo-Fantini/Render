#!/usr/bin/env python3
"""
Script para configurar automaticamente a Evolution API
"""

import requests
import json

# Configurações da Evolution API
API_CONFIG = {
    "api_url": "https://api.evolution-api.com",  # URL padrão da Evolution API
    "api_key": "20ED95D0125E-45BC-BB26-F5DACB955FA7",
    "instance_name": "Whatsapp",
    "group_id": "120363043462339912@g.us"  # ID do grupo (você precisará atualizar isso)
}

def configure_evolution_api():
    """Configura a Evolution API automaticamente"""
    
    # URL local da aplicação
    base_url = "http://localhost:5000"
    
    print("🔧 Configurando Evolution API...")
    print(f"📡 API URL: {API_CONFIG['api_url']}")
    print(f"🔑 Instance Name: {API_CONFIG['instance_name']}")
    print(f"👥 Group ID: {API_CONFIG['group_id']}")
    print()
    
    try:
        # Configurar WhatsApp
        response = requests.post(
            f"{base_url}/api/sender/configure-whatsapp",
            json={
                "api_url": API_CONFIG["api_url"],
                "api_key": API_CONFIG["api_key"],
                "instance_name": API_CONFIG["instance_name"]
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print("✅ Evolution API configurada com sucesso!")
                
                # Salvar ID do grupo nas configurações
                save_group_id(base_url)
                
                # Testar conexão
                test_connection(base_url)
                
            else:
                print(f"❌ Erro na configuração: {data.get('error')}")
        else:
            print(f"❌ Erro HTTP {response.status_code}: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Não foi possível conectar à aplicação local")
        print("💡 Certifique-se de que a aplicação está rodando em http://localhost:5000")
    except Exception as e:
        print(f"❌ Erro: {e}")

def save_group_id(base_url):
    """Salva o ID do grupo nas configurações"""
    try:
        response = requests.post(
            f"{base_url}/api/sender/settings",
            json={
                "group_id": API_CONFIG["group_id"]
            },
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ ID do grupo salvo nas configurações")
        else:
            print(f"⚠️ Não foi possível salvar o ID do grupo: {response.text}")
            
    except Exception as e:
        print(f"⚠️ Erro ao salvar ID do grupo: {e}")

def test_connection(base_url):
    """Testa a conexão com a Evolution API"""
    try:
        response = requests.post(
            f"{base_url}/api/sender/test-connection",
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print("✅ Conexão com Evolution API testada com sucesso!")
            else:
                print(f"⚠️ Teste de conexão falhou: {data.get('error')}")
        else:
            print(f"⚠️ Erro no teste de conexão: {response.text}")
            
    except Exception as e:
        print(f"⚠️ Erro ao testar conexão: {e}")

def show_status():
    """Mostra o status atual"""
    try:
        base_url = "http://localhost:5000"
        response = requests.get(f"{base_url}/api/sender/status", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                status = data.get("status", {})
                print("📊 Status Atual:")
                print(f"   Scheduler: {'🟢 Rodando' if status.get('scheduler_running') else '🔴 Parado'}")
                print(f"   WhatsApp: {'🟢 Conectado' if status.get('whatsapp_connected') else '🔴 Desconectado'}")
                print(f"   Produtos na fila: {status.get('queue_count', 0)}")
                print(f"   Contatos ativos: {status.get('active_contacts', 0)}")
            else:
                print(f"❌ Erro ao obter status: {data.get('error')}")
        else:
            print(f"❌ Erro HTTP {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"❌ Erro ao obter status: {e}")

if __name__ == "__main__":
    print("🚀 ProScraper Pro - Configuração Evolution API")
    print("=" * 50)
    
    # Mostrar status atual
    show_status()
    print()
    
    # Configurar API
    configure_evolution_api()
    print()
    
    # Mostrar status final
    show_status()
    
    print()
    print("🎯 Próximos passos:")
    print("1. Acesse: http://localhost:5000/sender")
    print("2. Verifique o status da conexão")
    print("3. Extraia produtos e salve na fila")
    print("4. Envios automáticos começarão a cada 15 minutos")
