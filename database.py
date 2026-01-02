import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class LocalDatabase:
    """Sistema de banco de dados local com SQLite"""
    
    def __init__(self, db_path: str = "proscraper.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Inicializa o banco de dados com as tabelas necessárias"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Tabela de produtos
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS products (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT UNIQUE NOT NULL,
                        title TEXT,
                        price_current REAL,
                        price_current_text TEXT,
                        image_url TEXT,
                        seller_text TEXT,
                        message TEXT,
                        active BOOLEAN DEFAULT 1,
                        sent_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Tabela de contatos
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS contacts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        phone_number TEXT UNIQUE NOT NULL,
                        active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Tabela de configurações
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Tabela de logs de envio
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS send_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        product_id INTEGER,
                        contact_id INTEGER,
                        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        success BOOLEAN NOT NULL,
                        error_message TEXT,
                        FOREIGN KEY (product_id) REFERENCES products (id),
                        FOREIGN KEY (contact_id) REFERENCES contacts (id)
                    )
                ''')
                
                # Migração: Adicionar coluna message se não existir
                try:
                    cursor.execute('ALTER TABLE products ADD COLUMN message TEXT')
                    logger.info("Coluna 'message' adicionada à tabela products")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e).lower():
                        logger.info("Coluna 'message' já existe na tabela products")
                    else:
                        raise e
                
                # Índices para performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_sent_at ON products(sent_at)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_active ON products(active)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_contacts_active ON contacts(active)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_send_logs_sent_at ON send_logs(sent_at)')
                
                # Configurações padrão
                default_settings = {
                    'group_link': 'https://linktr.ee/Free_Island',
                    'seller_text': 'Vendido e entregue por Amazon'
                }
                
                for key, value in default_settings.items():
                    cursor.execute('''
                        INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)
                    ''', (key, value))
                
                # Contato de teste
                cursor.execute('''
                    INSERT OR IGNORE INTO contacts (name, phone_number) VALUES (?, ?)
                ''', ('Contato Teste', '5511999999999'))
                
                conn.commit()
                logger.info("Banco de dados local inicializado com sucesso")
                
        except Exception as e:
            logger.error(f"Erro ao inicializar banco de dados: {e}")
            raise
    
    def save_product(self, product_data: Dict) -> int:
        """Salva ou atualiza um produto"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Verificar se produto já existe
                cursor.execute('SELECT id FROM products WHERE url = ?', (product_data['url'],))
                existing = cursor.fetchone()
                
                if existing:
                    # Atualizar produto existente
                    cursor.execute('''
                        UPDATE products SET 
                            title = ?, 
                            price_current = ?, 
                            price_current_text = ?, 
                            image_url = ?, 
                            message = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE url = ?
                    ''', (
                        product_data.get('title'),
                        product_data.get('price_current'),
                        product_data.get('price_current_text'),
                        product_data.get('image_url'),
                        product_data.get('message'),
                        product_data['url']
                    ))
                    product_id = existing[0]
                else:
                    # Inserir novo produto
                    cursor.execute('''
                        INSERT INTO products (url, title, price_current, price_current_text, image_url, message)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        product_data['url'],
                        product_data.get('title'),
                        product_data.get('price_current'),
                        product_data.get('price_current_text'),
                        product_data.get('image_url'),
                        product_data.get('message')
                    ))
                    product_id = cursor.lastrowid
                
                conn.commit()
                logger.info(f"Produto salvo: ID {product_id}")
                return product_id
                
        except Exception as e:
            logger.error(f"Erro ao salvar produto: {e}")
            raise
    
    def get_pending_products(self, limit: int = 10) -> List[Dict]:
        """Busca produtos pendentes de envio (não enviados nas últimas 24h)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
                
                cursor.execute('''
                    SELECT * FROM products 
                    WHERE active = 1 
                    AND (sent_at IS NULL OR sent_at < ?)
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (twenty_four_hours_ago, limit))
                
                products = [dict(row) for row in cursor.fetchall()]
                logger.info(f"Encontrados {len(products)} produtos pendentes")
                return products
                
        except Exception as e:
            logger.error(f"Erro ao buscar produtos pendentes: {e}")
            return []
    
    def mark_product_as_sent(self, product_id: int):
        """Marca produto como enviado"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE products SET sent_at = CURRENT_TIMESTAMP WHERE id = ?
                ''', (product_id,))
                conn.commit()
                logger.info(f"Produto {product_id} marcado como enviado")
                
        except Exception as e:
            logger.error(f"Erro ao marcar produto como enviado: {e}")
    
    def get_active_contacts(self) -> List[Dict]:
        """Busca contatos ativos"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('SELECT * FROM contacts WHERE active = 1')
                contacts = [dict(row) for row in cursor.fetchall()]
                logger.info(f"Encontrados {len(contacts)} contatos ativos")
                return contacts
                
        except Exception as e:
            logger.error(f"Erro ao buscar contatos: {e}")
            return []
    
    def add_contact(self, name: str, phone_number: str) -> int:
        """Adiciona um novo contato"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO contacts (name, phone_number) VALUES (?, ?)
                ''', (name, phone_number))
                contact_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Contato adicionado: ID {contact_id}")
                return contact_id
                
        except sqlite3.IntegrityError:
            logger.warning(f"Contato com telefone {phone_number} já existe")
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM contacts WHERE phone_number = ?', (phone_number,))
            return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Erro ao adicionar contato: {e}")
            raise
    
    def log_send_attempt(self, product_id: int, contact_id: int, success: bool, error_message: str = None):
        """Registra tentativa de envio"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO send_logs (product_id, contact_id, success, error_message)
                    VALUES (?, ?, ?, ?)
                ''', (product_id, contact_id, success, error_message))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Erro ao registrar log de envio: {e}")
    
    def get_setting(self, key: str, default: str = None) -> str:
        """Obtém uma configuração"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
                result = cursor.fetchone()
                return result[0] if result else default
                
        except Exception as e:
            logger.error(f"Erro ao obter configuração {key}: {e}")
            return default
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas do sistema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Estatísticas de produtos
                cursor.execute('SELECT COUNT(*) FROM products')
                total_products = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM products WHERE sent_at IS NOT NULL')
                sent_products = cursor.fetchone()[0]
                
                pending_products = total_products - sent_products
                
                # Estatísticas de contatos
                cursor.execute('SELECT COUNT(*) FROM contacts WHERE active = 1')
                active_contacts = cursor.fetchone()[0]
                
                # Estatísticas de envios (últimas 24h)
                twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
                cursor.execute('''
                    SELECT COUNT(*) FROM send_logs 
                    WHERE success = 1 AND sent_at > ?
                ''', (twenty_four_hours_ago,))
                recent_sends = cursor.fetchone()[0]
                
                return {
                    'products': {
                        'total': total_products,
                        'sent': sent_products,
                        'pending': pending_products
                    },
                    'contacts': {
                        'active': active_contacts
                    },
                    'sends': {
                        'last_24h': recent_sends
                    }
                }
                
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {
                'products': {'total': 0, 'sent': 0, 'pending': 0},
                'contacts': {'active': 0},
                'sends': {'last_24h': 0}
            }
