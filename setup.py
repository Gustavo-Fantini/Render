#!/usr/bin/env python
"""Setup script para ProScraper"""

import os
import sys
import subprocess

def install_dependencies():
    """Instala dependências do projeto"""
    print("📦 Instalando dependências...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("✅ Dependências instaladas com sucesso!")

def create_env_file():
    """Cria arquivo .env se não existir"""
    if not os.path.exists('.env'):
        print("📝 Criando arquivo .env...")
        with open('.env', 'w') as f:
            with open('.env.example', 'r') as example:
                f.write(example.read())
        print("✅ Arquivo .env criado! Configure as variáveis de ambiente.")
    else:
        print("✅ Arquivo .env já existe")

def create_templates_dir():
    """Cria diretório templates se não existir"""
    if not os.path.exists('templates'):
        os.makedirs('templates')
        print("✅ Diretório templates criado")
    else:
        print("✅ Diretório templates já existe")

def main():
    """Executa setup completo"""
    print("🚀 ProScraper - Setup Inicial\n")
    
    try:
        create_templates_dir()
        create_env_file()
        install_dependencies()
        
        print("\n" + "="*50)
        print("✅ Setup concluído com sucesso!")
        print("="*50)
        print("\nPróximos passos:")
        print("1. Configure as variáveis em .env")
        print("2. Execute: python app.py")
        print("3. Acesse: http://localhost:5000")
        
    except Exception as e:
        print(f"\n❌ Erro durante setup: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
