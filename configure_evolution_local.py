#!/usr/bin/env python3
"""
Script para configurar Evolution API com os dados fornecidos
"""

import sqlite3
import logging
from datetime import datetime

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def configure_evolution_api():
    """Configura a Evolution API com os dados fornecidos"""
    
    # Dados fornecidos
    api_url = "http://localhost:8080"
    api_key = "429683C4C977415CAAFCCE10F7D57E11"
    instance_name = "Whatsapp"
    group_id = "120363043462339912@g.us"
    
    try:
        # Conectar ao banco de dados
        conn = sqlite3.connect('proscraper.db')
        cursor = conn.cursor()
        
        # Criar tabela settings se não existir
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Inserir configurações
        settings = [
            ('evolution_api_url', api_url),
            ('evolution_api_key', api_key),
            ('evolution_instance_name', instance_name),
            ('evolution_group_id', group_id),
            ('scheduler_interval', '15')  # Intervalo padrão de 15 minutos
        ]
        
        for key, value in settings:
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (key, value))
            logger.info(f"Configuração salva: {key} = {value}")
        
        # Confirmar transação
        conn.commit()
        conn.close()
        
        logger.info("✅ Configuração da Evolution API concluída com sucesso!")
        logger.info(f"📋 Resumo das configurações:")
        logger.info(f"   🔗 URL da API: {api_url}")
        logger.info(f"   🔑 API Key: {api_key[:10]}...")
        logger.info(f"   📱 Instância: {instance_name}")
        logger.info(f"   👥 Grupo ID: {group_id}")
        logger.info(f"   ⏰ Intervalo: 15 minutos")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao configurar Evolution API: {e}")
        return False

def test_configuration():
    """Testa a configuração salva"""
    
    try:
        conn = sqlite3.connect('proscraper.db')
        cursor = conn.cursor()
        
        # Buscar configurações
        cursor.execute('SELECT key, value FROM settings ORDER BY key')
        settings = cursor.fetchall()
        
        logger.info("📋 Configurações atuais no banco:")
        for key, value in settings:
            if 'key' in key.lower():
                # Mascarar chaves sensíveis
                masked_value = value[:10] + "..." if len(value) > 10 else value
                logger.info(f"   {key}: {masked_value}")
            else:
                logger.info(f"   {key}: {value}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao testar configuração: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚀 Iniciando configuração da Evolution API...")
    
    # Configurar API
    if configure_evolution_api():
        logger.info("\n🧪 Testando configuração...")
        test_configuration()
        
        logger.info("\n✅ Próximos passos:")
        logger.info("1. Inicie a Evolution API em localhost:8080")
        logger.info("2. Execute: python app.py")
        logger.info("3. Acesse: http://localhost:5000/sender")
        logger.info("4. Verifique o status da conexão WhatsApp")
        
    else:
        logger.error("❌ Falha na configuração. Verifique os logs acima.")
