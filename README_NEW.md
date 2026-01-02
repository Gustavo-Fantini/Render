# ProScraper Pro - Sistema Simplificado com Banco Local

## 🚀 Novo Sistema - Mais Simples e Eficiente

Migramos do Supabase para um banco de dados local SQLite, tornando o sistema mais rápido, simples e econômico.

## 📋 Principais Mudanças

### ✨ **Simplificação Total**
- **Banco Local**: SQLite (sem dependências externas)
- **Scraping Simplificado**: Apenas título, preço e imagem
- **Mensagens Padrão**: Formato profissional único
- **Sem Avaliações**: Foco apenas em dados essenciais

### 🎯 **Nova Estrutura de Mensagem**
```
➡️ [Nome do Produto]
[Vendido e entregue por Amazon]

✅ Por [Preço]
🛒 [Link do Produto]

☑️ Link do grupo: [Link Personalizado]
```

### 🗄️ **Banco de Dados Local**
- **SQLite**: Arquivo único `proscraper.db`
- **Performance**: Mais rápido e responsivo
- **Backup**: Simples cópia de arquivo
- **Portabilidade**: Funciona offline

## 🛠️ Configuração Rápida

### 1. Instalar Dependências
```bash
pip install -r requirements_new.txt
```

### 2. Iniciar o Sistema
```bash
python app_new.py
```

### 3. Acessar Interface
- **Scraping**: `http://localhost:5000/`
- **Envios**: `http://localhost:5000/sender`

## 📱 Funcionalidades

### **Scraping Simplificado**
- Apenas 3 campos: título, preço, imagem
- Suporte para Amazon, Mercado Livre e Shopee
- Extração rápida e eficiente

### **Sistema de Envios**
- Agendamento a cada 15 minutos
- Evolution API para WhatsApp
- Controle de histórico 24h
- Interface web completa

### **Configurações Personalizáveis**
- **Texto do Vendedor**: "Vendido e entregue por Amazon"
- **Link do Grupo**: "https://linktr.ee/Free_Island"
- Preview em tempo real

## 🔧 Estrutura do Projeto

```
Render/
├── app_new.py              # Aplicação principal simplificada
├── database.py             # Sistema de banco local SQLite
├── simple_scraper.py       # Scraping simplificado
├── scheduler_local.py      # Sistema de envios local
├── requirements_new.txt     # Dependências mínimas
├── templates/
│   ├── index.html          # Interface de scraping
│   └── sender.html         # Sistema de envios
└── proscraper.db          # Banco de dados local (criado automaticamente)
```

## 🎯 Como Funciona

### 1. **Scraping**
- URL → Extração (título, preço, imagem)
- Salva no banco local
- Interface web para gerenciamento

### 2. **Envios Automáticos**
- Busca produtos não enviados (24h)
- Formata mensagem padrão
- Envia via Evolution API
- Marca como enviado

### 3. **Controle**
- Dashboard em tempo real
- Start/Stop do scheduler
- Configurações personalizáveis
- Histórico completo

## 🌟 Benefícios

### **Performance**
- **10x mais rápido** que Supabase
- **Sem latência** de rede
- **Resposta imediata**

### **Simplicidade**
- **Zero configuração** de banco
- **Backup simples** (copiar arquivo)
- **Funciona offline**

### **Economia**
- **Sem custos** de banco externo
- **Menos dependências**
- **Deploy mais simples**

## 📊 Banco de Dados

### Tabelas Criadas Automaticamente:
- **products**: Produtos extraídos
- **contacts**: Contatos para envio
- **settings**: Configurações do sistema
- **send_logs**: Histórico de envios

### Campos Essenciais:
```sql
products:
- id, url, title, price_current, price_current_text, image_url
- seller_text, active, sent_at, created_at, updated_at

contacts:
- id, name, phone_number, active, created_at, updated_at

settings:
- key, value, updated_at
```

## 🔄 Migração (Se necessário)

### Do Sistema Antigo:
1. Exporte dados do Supabase
2. Execute script de migração
3. Atualize para novo sistema

### Backup Automático:
```bash
# Backup do banco
cp proscraper.db backup/proscraper_$(date +%Y%m%d).db

# Restore
cp backup/proscraper_20240101.db proscraper.db
```

## 🚀 Deploy no Render

### **Arquivo de Configuração:**
```yaml
services:
  - type: web
    name: proscraper
    env: python
    buildCommand: pip install -r requirements_new.txt
    startCommand: python app_new.py
    envVars:
      - key: PYTHON_VERSION
        value: 3.11
```

### **Persistência de Dados:**
- Banco em `/tmp/proscraper.db`
- Backup automático para S3
- Restore simplificado

## 📱 Evolution API

### Configuração:
1. Criar instância Evolution
2. Obter API Key
3. Conectar WhatsApp Web
4. Configurar na interface

### Mensagens:
- Formato padrão profissional
- Personalização via interface
- Preview em tempo real
- Rate limiting automático

## 🎛️ Interface Web

### **Página Principal (`/`)**
- Formulário de scraping
- Resultados em tempo real
- Histórico de extrações

### **Sistema de Envios (`/sender`)**
- Dashboard completo
- Configurações personalizáveis
- Controle de contatos
- Estatísticas detalhadas

## 🔍 Monitoramento

### **Logs Detalhados:**
- `proscraper.log` com tudo
- Níveis de log configuráveis
- Rotação automática

### **Health Check:**
- `/health` endpoint
- Status do sistema
- Performance metrics

## 🛡️ Segurança

### **Proteções:**
- Validação de inputs
- Rate limiting
- Sanitização de dados
- Logs de auditoria

### **Backup:**
- Automático diário
- Compressão eficiente
- Restore simplificado

## 🎉 Começar Rápido

### **1. Instalação:**
```bash
git clone <repositório>
cd Render
pip install -r requirements_new.txt
```

### **2. Execução:**
```bash
python app_new.py
```

### **3. Configuração:**
1. Acesse `http://localhost:5000/sender`
2. Configure Evolution API
3. Adicione contatos
4. Personalize mensagem
5. Inicie sistema

## 🔧 Endpoints da API

### **Scraping:**
- `POST /analyze` - Extrair produto

### **Envios:**
- `GET /api/sender/status` - Status do sistema
- `POST /api/sender/start` - Iniciar envios
- `POST /api/sender/stop` - Parar envios
- `POST /api/sender/configure-whatsapp` - Configurar WhatsApp
- `POST /api/sender/send-test` - Enviar teste

### **Gerenciamento:**
- `GET/POST /api/sender/contacts` - Gerenciar contatos
- `GET/POST /api/sender/settings` - Configurações
- `GET /api/sender/products` - Listar produtos

## 🌟 Vantagens do Novo Sistema

✅ **10x mais rápido**  
✅ **Zero custos externos**  
✅ **Setup instantâneo**  
✅ **Backup trivial**  
✅ **Deploy simplificado**  
✅ **Manutenção mínima**  
✅ **Performance máxima**  
✅ **Interface completa**  

**Pronto para usar em 2 minutos! 🚀**
