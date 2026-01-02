#!/usr/bin/env python3
"""
Script para configurar Evolution API diretamente no banco de dados
"""

import sqlite3
import json
from datetime import datetime

# Configurações da Evolution API
API_CONFIG = {
    "api_url": "https://api.evolution-api.com",
    "api_key": "20ED95D0125E-45BC-BB26-F5DACB955FA7",
    "instance_name": "Whatsapp",
    "group_id": "120363043462339912@g.us"  # Você pode atualizar isso depois
}

def configure_database():
    """Configura a Evolution API diretamente no banco SQLite"""
    
    db_path = "proscraper.db"
    
    try:
        print("🔧 Configurando Evolution API no banco de dados...")
        print(f"📡 API URL: {API_CONFIG['api_url']}")
        print(f"🔑 Instance Name: {API_CONFIG['instance_name']}")
        print(f"👥 Group ID: {API_CONFIG['group_id']}")
        print()
        
        # Conectar ao banco de dados
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Salvar configurações da Evolution API
        settings_to_save = {
            "evolution_api_url": API_CONFIG["api_url"],
            "evolution_api_key": API_CONFIG["api_key"],
            "evolution_instance_name": API_CONFIG["instance_name"],
            "whatsapp_group_id": API_CONFIG["group_id"]
        }
        
        for key, value in settings_to_save.items():
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (key, value))
            print(f"✅ Configuração salva: {key}")
        
        # Salvar configurações padrão de mensagem
        default_settings = {
            "group_link": "https://linktr.ee/Free_Island",
            "seller_text": ""  # Vazio conforme solicitado
        }
        
        for key, value in default_settings.items():
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (key, value))
            print(f"✅ Configuração padrão salva: {key}")
        
        conn.commit()
        conn.close()
        
        print()
        print("✅ Todas as configurações foram salvas com sucesso!")
        print()
        print("📋 Configurações salvas:")
        for key, value in settings_to_save.items():
            print(f"   • {key}: {value}")
        print()
        print("🎯 Próximos passos:")
        print("1. Inicie a aplicação: python app.py")
        print("2. Acesse: http://localhost:5000/sender")
        print("3. Verifique o status da conexão")
        print("4. Teste a conexão com a Evolution API")
        print()
        print("📱 Para usar:")
        print("• Extraia produtos em http://localhost:5000")
        print("• Salve os produtos na fila")
        print("• Envios automáticos começarão a cada 15 minutos")
        
    except sqlite3.Error as e:
        print(f"❌ Erro no banco de dados: {e}")
    except Exception as e:
        print(f"❌ Erro: {e}")

def show_database_config():
    """Mostra as configurações atuais do banco"""
    
    db_path = "proscraper.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT key, value FROM settings ORDER BY key')
        settings = cursor.fetchall()
        
        if settings:
            print("📊 Configurações atuais no banco:")
            for key, value in settings:
                if "api_key" in key.lower():
                    print(f"   • {key}: {'*' * 10}...{value[-10:]}")
                else:
                    print(f"   • {key}: {value}")
        else:
            print("❌ Nenhuma configuração encontrada")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ Erro ao ler configurações: {e}")
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    print("🚀 ProScraper Pro - Configuração Evolution API (Banco de Dados)")
    print("=" * 60)
    print()
    
    # Mostrar configurações atuais
    show_database_config()
    print()
    
    # Configurar Evolution API
    configure_database()
    print()
    
    # Mostrar configurações finais
    show_database_config()
