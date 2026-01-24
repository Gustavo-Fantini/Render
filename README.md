# Free Island - Sistema de Promoções

Aplicação web para extração de dados de produtos de e-commerce e geração de mensagens promocionais.

## Funcionalidades

- 🔐 Login seguro com credenciais específicas
- 🛒 Scraping de produtos de múltiplos e-commerces:
  - Amazon Brasil
  - Mercado Livre
  - Magazine Luiza
  - Shopee
- 📝 Geração automática de mensagens promocionais
- 🎫 Suporte para cupons de desconto
- 🚚 Opção de frete grátis
- 💾 Salvamento direto no Supabase
- 📱 Interface responsiva e moderna

## Estrutura do Projeto

```
├── app.py                 # Aplicação principal Flask
├── requirements.txt       # Dependências Python
├── Procfile              # Configuração do Render
├── runtime.txt           # Versão Python
└── templates/
    ├── login.html        # Página de login
    └── dashboard.html    # Dashboard principal
```

## Instalação

1. Clone o repositório
2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Execute a aplicação:
```bash
python app.py
```

## Configuração

A aplicação está configurada para usar:

- **Supabase**: Banco de dados para armazenamento
- **Selenium**: WebDriver para scraping avançado
- **Flask**: Framework web

## Deploy

O projeto está configurado para deploy no Render.com com as seguintes configurações:

- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app`
- **Python Version**: 3.11.7

## Uso

1. Acesse a aplicação
2. Faça login com as credenciais
3. Cole a URL do produto
4. Configure as opções (frete grátis, cupom)
5. Extraia os dados
6. Edite a mensagem se necessário
7. Salve no Supabase

## Segurança

- Login protegido com sessões Flask
- Credenciais hardcoded no servidor
- Conexão segura com Supabase usando service-role key
