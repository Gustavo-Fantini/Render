# ProScraper Pro v10.0.1

🚀 **Sistema Profissional de Scraping e Envios Automáticos via WhatsApp**

## 📋 **Visão Geral**

O ProScraper Pro é uma aplicação web completa para extração de dados de e-commerce e envio automatizado de mensagens promocionais via WhatsApp através da Evolution API.

### ✨ **Recursos Principais**

- 🛒 **Scraping Multiplataforma**: Mercado Livre, Amazon, Magazine Luiza
- 📱 **Envios Automáticos**: WhatsApp via Evolution API
- 🔐 **Sistema de Login**: Acesso seguro com autenticação
- ⏰ **Agendador Inteligente**: Envios programados
- 🎯 **Gestão de Produtos**: CRUD completo
- 📊 **Painel Administrativo**: Interface moderna e responsiva
- 🔍 **Logs Detalhados**: Monitoramento completo

## 🚀 **Versão 10.0.1**

### 🆕 **Novidades**
- ✅ Sistema de login seguro
- ✅ Configuração simplificada para Evolution API
- ✅ Tratamento robusto de erros
- ✅ Interface otimizada
- ✅ Código limpo e documentado

### 🔧 **Melhorias**
- Performance otimizada
- Segurança aprimorada
- Logs mais detalhados
- Tratamento de exceções

## 🛠️ **Tecnologias Utilizadas**

### **Backend**
- **Flask**: Framework web Python
- **SQLite**: Banco de dados local
- **BeautifulSoup4**: Web scraping
- **Requests**: Cliente HTTP
- **Schedule**: Agendador de tarefas

### **Frontend**
- **HTML5**: Estrutura semântica
- **Tailwind CSS**: Framework CSS moderno
- **JavaScript**: Interatividade
- **Fetch API**: Requisições assíncronas

### **Infraestrutura**
- **Docker**: Contêineres
- **Render**: Hospedagem na nuvem
- **Evolution API**: Integração WhatsApp
- **Git**: Controle de versão

## 📦 **Instalação**

### **Pré-requisitos**
- Python 3.8+
- Docker
- Git

### **Passos**

1. **Clone o repositório**
   ```bash
   git clone https://github.com/Gustavo-Fantini/Render.git
   cd Render
   ```

2. **Instale dependências**
   ```bash
   pip install -r requirements.txt
   ```

3. **Inicie a aplicação**
   ```bash
   python app.py
   ```

4. **Acesse o sistema**
   - URL: `http://localhost:5000`
   - Login: `gustavofantini`
   - Senha: `Gustavinho12`

## 🔧 **Configuração**

### **Evolution API**

1. **Configure a Evolution API**
   ```bash
   python setup_render_api.py
   ```

2. **Informe os dados solicitados**
   - URL do Render da Evolution API
   - API Key
   - Instance Name
   - Group ID

### **Variáveis de Ambiente**

```bash
FLASK_ENV=development
FLASK_DEBUG=True
```

## 📱 **Funcionalidades**

### **Scraping**
- **Mercado Livre**: Extração completa de produtos
- **Amazon**: Scraping robusto com fallbacks
- **Magazine Luiza**: Dados de produtos e preços

### **Envios**
- **Mensagens de Texto**: Envio imediato
- **Mensagens com Imagem**: Produtos com fotos
- **Agendamento**: Envios programados
- **Grupos**: Suporte a grupos WhatsApp

### **Gestão**
- **Produtos**: Adicionar, editar, excluir
- **Contatos**: Gerenciamento de destinatários
- **Logs**: Histórico de envios
- **Estatísticas**: Dashboard informativo

## 🏗️ **Estrutura do Projeto**

```
Render/
├── app.py                 # Aplicação Flask principal
├── database.py            # Gerenciamento do banco de dados
├── scheduler.py           # Sistema de agendamento
├── simple_scraper.py      # Web scraping
├── templates/             # Templates HTML
│   ├── index.html         # Dashboard principal
│   ├── login.html        # Página de login
│   └── sender_simple.html # Painel de envios
├── setup_render_api.py    # Configuração Evolution API
├── requirements.txt       # Dependências Python
└── README.md            # Documentação
```

## 🔐 **Segurança**

- **Autenticação**: Sistema de login seguro
- **Hash de Senhas**: SHA256 para armazenamento
- **Sessões**: Gerenciamento seguro de sessões
- **Validação**: Sanitização de dados
- **CORS**: Configuração segura de cross-origin

## 📊 **Monitoramento**

### **Logs**
- **Arquivo de Log**: `proscraper.log`
- **Níveis**: INFO, WARNING, ERROR
- **Rotação**: Logs organizados por data

### **Estatísticas**
- **Produtos**: Total, enviados, pendentes
- **Contatos**: Ativos e inativos
- **Envios**: Sucesso e falhas
- **Performance**: Tempo de resposta

## 🚀 **Deploy**

### **Render**
1. **Conecte o repositório** ao Render
2. **Configure as variáveis de ambiente**
3. **Configure a Evolution API**
4. **Teste a aplicação**

### **Docker**
```bash
docker build -t proscraper-pro .
docker run -p 5000:5000 proscraper-pro
```

## 🔄 **Atualizações**

### **Controle de Versões**
- **Major**: Mudanças estruturais
- **Minor**: Novas funcionalidades
- **Patch**: Correções e melhorias

### **Histórico**
- **v10.0.1**: Sistema de login + segurança
- **v10.0.0**: Versão inicial completa

## 🤝 **Suporte**

### **Documentação**
- **README**: Informações gerais
- **Código**: Comentários detalhados
- **Logs**: Mensagens informativas

### **Contato**
- **Desenvolvedor**: Gustavo Fantini
- **Versão**: 10.0.1
- **Status**: Produção

## 📝 **Licença**

Este projeto é proprietário e confidencial.

---

**ProScraper Pro v10.0.1** - *Sistema Profissional de Scraping e Envios Automáticos*

🚀 **Desenvolvido com ❤️ por Gustavo Fantini**
