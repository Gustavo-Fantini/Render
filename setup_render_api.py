#!/usr/bin/env python3
"""
ProScraper Pro v10.0.1 - Sistema Profissional de Scraping e Envios Automáticos
Script para configurar Evolution API no Render
Execute este script quando tiver a URL do Render da Evolution API
"""

from database import LocalDatabase
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_render_evolution_api():
    """Configura a Evolution API do Render"""
    db = LocalDatabase()
    
    print("=== Configuração Evolution API - Render ===\n")
    
    # Obter informações do usuário
    print("Por favor, informe os dados da Evolution API no Render:")
    render_url = input("URL do Render (ex: https://sua-api.onrender.com): ").strip()
    api_key = input("API Key (deixe em branco para manter a atual): ").strip()
    instance_name = input("Instance Name (padrão: Whatsapp): ").strip() or "Whatsapp"
    group_id = input("Group ID (padrão: 120363404998433610@g.us): ").strip() or "120363404998433610@g.us"
    
    # Validar URL
    if not render_url:
        print("❌ URL do Render é obrigatória!")
        return False
    
    # Remover barra final se existir
    render_url = render_url.rstrip('/')
    
    # Atualizar configurações
    try:
        db.update_setting('evolution_api_url', render_url)
        print(f"✅ URL atualizada: {render_url}")
        
        if api_key:
            db.update_setting('evolution_api_key', api_key)
            print(f"✅ API Key atualizada")
        else:
            print(f"ℹ️ API Key mantida: {db.get_setting('evolution_api_key')}")
        
        db.update_setting('evolution_instance_name', instance_name)
        print(f"✅ Instance Name: {instance_name}")
        
        db.update_setting('evolution_group_id', group_id)
        print(f"✅ Group ID: {group_id}")
        
        print("\n=== Configurações Atualizadas ===")
        print(f"API URL: {db.get_setting('evolution_api_url')}")
        print(f"Instance: {db.get_setting('evolution_instance_name')}")
        print(f"Group: {db.get_setting('evolution_group_id')}")
        
        print("\n✅ Configuração concluída com sucesso!")
        print("🚀 Reinicie a aplicação para aplicar as alterações")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao configurar: {e}")
        return False

def show_current_config():
    """Mostra configurações atuais"""
    db = LocalDatabase()
    
    print("=== Configurações Atuais ===")
    print(f"API URL: {db.get_setting('evolution_api_url')}")
    print(f"API Key: {db.get_setting('evolution_api_key')}")
    print(f"Instance: {db.get_setting('evolution_instance_name')}")
    print(f"Group: {db.get_setting('evolution_group_id')}")

if __name__ == "__main__":
    print("Script de Configuração - Evolution API Render\n")
    print("1. Mostrar configurações atuais")
    print("2. Configurar Evolution API do Render")
    
    choice = input("\nEscolha uma opção (1 ou 2): ").strip()
    
    if choice == "1":
        show_current_config()
    elif choice == "2":
        setup_render_evolution_api()
    else:
        print("Opção inválida!")
