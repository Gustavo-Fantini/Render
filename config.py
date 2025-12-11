import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuração base da aplicação"""
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = FLASK_ENV == 'development'
    
    # Supabase
    SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://cnwrcrpihldqejyvgysn.supabase.co')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNud3JjcnBpaGxkcWVqeXZneXNuIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MTU5NzM3OSwiZXhwIjoyMDY3MTczMzc5fQ.GdZPPZvSAslVIgzbmq8rhstK94qxh7WUwH623GUvb4g')
    
    # Flask
    PORT = int(os.getenv('PORT', 5000))
    HOST = os.getenv('HOST', '0.0.0.0')
    
    # Timeouts
    REQUEST_TIMEOUT = 10
    SELENIUM_TIMEOUT = 20

class DevelopmentConfig(Config):
    """Configuração para desenvolvimento"""
    DEBUG = True

class ProductionConfig(Config):
    """Configuração para produção (Render)"""
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
