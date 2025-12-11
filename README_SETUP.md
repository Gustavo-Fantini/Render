# ProScraper - Setup e Deploy Completo

## 📋 Índice
1. [Setup Local](#setup-local)
2. [Estrutura do Projeto](#estrutura-do-projeto)
3. [Deploy no Render](#deploy-no-render)
4. [Endpoints da API](#endpoints-da-api)
5. [Troubleshooting](#troubleshooting)

## Setup Local

### Pré-requisitos
- Python 3.11+
- Git
- pip

### Instalação Rápida

```bash
# 1. Clone ou navegue até o diretório
cd teste-site-fantini

# 2. Execute o setup automático
python setup.py

# 3. Configure as variáveis de ambiente
# Edite o arquivo .env com suas credenciais

# 4. Inicie o servidor
python app.py
```

### Instalação Manual

```bash
# 1. Crie um ambiente virtual
python -m venv venv

# 2. Ative o ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
cp .env.example .env
# Edite .env com suas credenciais

# 5. Inicie o servidor
python app.py
```

## Estrutura do Projeto

```
teste-site-fantini/
├── app.py                    # Aplicação principal Flask
├── config.py                 # Configurações (dev/prod)
├── setup.py                  # Script de setup automático
├── requirements.txt          # Dependências Python
├── Procfile                  # Configuração Render
├── runtime.txt               # Versão Python
├── .env.example              # Exemplo de variáveis
├── .gitignore                # Arquivos a ignorar no Git
├── templates/
│   └── index.html            # Frontend
├── DEPLOY_RENDER.md          # Guia de deploy
├── README_SETUP.md           # Este arquivo
└── proscraper.log            # Logs (gerado)
```

## Deploy no Render

### Passo 1: Preparar Repositório Git

```bash
# Inicialize Git (se não existir)
git init

# Adicione todos os arquivos
git add .

# Commit inicial
git commit -m "ProScraper - Ready for Render deployment"

# Adicione o remote (substitua pelos seus dados)
git remote add origin https://github.com/seu-usuario/seu-repositorio.git

# Push para GitHub
git push -u origin main
```

### Passo 2: Criar Serviço no Render

1. Acesse https://dashboard.render.com
2. Clique em **"New +"** → **"Web Service"**
3. Selecione seu repositório GitHub
4. Preencha os dados:
   - **Name**: `proscraper` (ou seu nome)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: `Free` (ou pago)

### Passo 3: Configurar Variáveis de Ambiente

No dashboard do Render, vá para **"Environment"** e adicione:

```
SUPABASE_URL=https://cnwrcrpihldqejyvgysn.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
FLASK_ENV=production
PORT=5000
```

### Passo 4: Deploy

1. Clique em **"Create Web Service"**
2. Aguarde o build (2-3 minutos)
3. Seu app estará em: `https://seu-app.onrender.com`

## Endpoints da API

### 1. Analisar URL
**POST** `/analyze`

```bash
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.mercadolivre.com.br/..."}'
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "url": "https://...",
    "site_name": "Mercado Livre",
    "extraction_time": 2.5,
    "fields": {
      "title": {"found": true, "value": "..."},
      "price_current": {"found": true, "value": "R$ 99,90", "price_float": 99.90},
      "rating": {"found": true, "value": 4.5, "count": 120}
    }
  }
}
```

### 2. Health Check
**GET** `/health`

```bash
curl http://localhost:5000/health
```

### 3. Salvar Promoção
**POST** `/supabase/save-promotion`

```bash
curl -X POST http://localhost:5000/supabase/save-promotion \
  -H "Content-Type: application/json" \
  -d '{
    "mensagem": "Produto em promoção!",
    "imagem_url": "https://..."
  }'
```

### 4. Listar Promoções
**GET** `/supabase/list?limit=20`

```bash
curl http://localhost:5000/supabase/list
```

### 5. Estatísticas
**GET** `/supabase/stats`

```bash
curl http://localhost:5000/supabase/stats
```

## Sites Suportados

- ✅ **Mercado Livre** - Extração rápida via HTML
- ✅ **Amazon Brasil** - Extração com fallback Selenium
- ✅ **Shopee** - Extração via Selenium (em desenvolvimento)

## Variáveis de Ambiente

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `SUPABASE_URL` | URL do Supabase | Configurado |
| `SUPABASE_KEY` | Chave do Supabase | Configurado |
| `FLASK_ENV` | Ambiente (development/production) | development |
| `PORT` | Porta do servidor | 5000 |
| `HOST` | Host do servidor | 0.0.0.0 |

## Troubleshooting

### Erro: "ModuleNotFoundError"
```bash
# Reinstale as dependências
pip install -r requirements.txt
```

### Erro: "Supabase não configurado"
```bash
# Verifique as variáveis de ambiente
# Certifique-se que .env está configurado corretamente
cat .env
```

### Erro: "Chrome não encontrado" (Shopee)
- Selenium requer Chrome instalado
- No Render, use fallback HTML ou API

### Servidor não inicia no Render
1. Verifique os logs no dashboard
2. Confirme `Procfile` existe
3. Verifique `requirements.txt`

### Timeout em requisições
- Aumente os timeouts em `config.py`
- Verifique a conexão de rede

## Performance

- **Mercado Livre**: ~2-3 segundos
- **Amazon**: ~3-5 segundos (com Selenium)
- **Shopee**: ~15-20 segundos (com Selenium)

## Logs

Logs são salvos em `proscraper.log`:

```bash
# Ver últimas linhas
tail -f proscraper.log

# Buscar erros
grep ERROR proscraper.log
```

## Desenvolvimento

### Adicionar novo site

1. Crie método `_extract_[site]_detailed()` em `app.py`
2. Adicione o site em `_identify_site()`
3. Adicione lógica em `scrape_product()`

### Testar localmente

```bash
python app.py
# Acesse http://localhost:5000
```

## Suporte

Para problemas:
1. Verifique os logs
2. Consulte `DEPLOY_RENDER.md`
3. Verifique variáveis de ambiente

## Licença

MIT
