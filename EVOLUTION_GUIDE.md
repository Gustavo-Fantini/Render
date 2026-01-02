# 🚀 Evolution API Integration Guide

## 📋 Opções de Instalação

### Opção 1: Evolution API Externa (Recomendado para Render)

Use um serviço Evolution API separado e conecte sua aplicação via HTTP.

#### Passos:

1. **Configure Evolution API separadamente:**
   ```bash
   # Clone o repositório oficial
   git clone https://github.com/EvolutionAPI/evolution-api.git
   cd evolution-api
   
   # Copie o arquivo de ambiente
   cp .env.example .env
   
   # Configure suas credenciais
   nano .env
   ```

2. **Configure o .env:**
   ```env
   AUTHENTICATION_API_KEY=429683C4C977415CAAFCCE10F7D57E11
   SERVER_URL=https://seu-dominio.com:8080
   DATABASE_ENABLED=false
   CACHE_LOCAL_ENABLED=true
   ```

3. **Inicie com Docker:**
   ```bash
   docker-compose up -d
   ```

4. **Configure sua aplicação:**
   - Acesse: `http://localhost:5000/sender`
   - URL da API: `https://seu-dominio.com:8080`
   - API Key: `429683C4C977415CAAFCCE10F7D57E11`
   - Nome da Instância: `default`

### Opção 2: Docker Compose Local (Desenvolvimento)

Execute tudo junto usando o docker-compose.yml fornecido:

```bash
# Iniciar Evolution API
docker-compose up -d

# Iniciar sua aplicação
python app.py
```

### Opção 3: Render Services (Produção)

Para deploy no Render, crie dois serviços:

1. **Web Service** (sua aplicação)
2. **Background Worker** (Evolution API)

## 🔧 Configuração na Aplicação

### 1. Configurar Evolution API

```javascript
// POST /api/whatsapp/configure
{
  "api_url": "https://sua-api.com:8080",
  "api_key": "429683C4C977415CAAFCCE10F7D57E11",
  "instance_name": "minha-instancia"
}
```

### 2. Criar Instância WhatsApp

```javascript
// POST /api/whatsapp/create-instance
{
  "instance_name": "minha-instancia"
}
```

### 3. Obter QR Code

```javascript
// GET /api/whatsapp/qrcode
// Retorna base64 do QR Code para escanear
```

### 4. Enviar Mensagem

```javascript
// POST /api/whatsapp/send-test
{
  "message": "Mensagem de teste",
  "group_id": "123456789-123456@g.us"
}
```

## 📱 Como Conectar WhatsApp

1. **Configure a API** na interface `/sender`
2. **Crie uma instância** WhatsApp
3. **Escaneie o QR Code** com seu WhatsApp
4. **Teste a conexão** enviando mensagem
5. **Configure o ID do grupo** para envios automáticos

## 🌐 Serviços Evolution API

### Online Services:
- **EvoAPI.pro**: Serviço gerenciado
- **WppConnect.me**: Alternativa popular
- **Venom.com.br**: Serviço brasileiro

### Self-Hosted:
- **Docker**: Controle total
- **VPS**: Dedicado ou compartilhado
- **Render**: Background worker

## 🚀 Deploy no Render

### Serviço Principal (Web Service):
```yaml
# render.yaml
services:
  - type: web
    name: proscraper-app
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app --bind 0.0.0.0:$PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.9.16
```

### Serviço Evolution API (Background Worker):
```yaml
# render.yaml
services:
  - type: worker
    name: evolution-api
    dockerfilePath: ./Dockerfile.evolution
    envVars:
      - key: AUTHENTICATION_API_KEY
        value: 429683C4C977415CAAFCCE10F7D57E11
```

## 📊 Endpoints Disponíveis

### WhatsApp:
- `POST /api/whatsapp/configure` - Configurar API
- `POST /api/whatsapp/test` - Testar conexão
- `GET /api/whatsapp/qrcode` - Obter QR Code
- `POST /api/whatsapp/create-instance` - Criar instância
- `GET /api/whatsapp/status` - Status completo
- `POST /api/whatsapp/send-test` - Enviar teste

### Sistema:
- `GET /api/queue` - Fila de mensagens
- `POST /api/save-product` - Salvar produto
- `GET /health` - Health check

## 🔍 Troubleshooting

### Problemas Comuns:

1. **"gunicorn: command not found"**
   - ✅ Adicione `gunicorn` ao requirements.txt

2. **"table products has no column named message"**
   - ✅ Migração automática já implementada

3. **"Evolution API não configurada"**
   - ✅ Configure URL e API Key na interface

4. **"QR Code não disponível"**
   - ✅ Crie instância primeiro
   - ✅ Aguarde alguns segundos

5. **"Conexão falhou"**
   - ✅ Verifique se API está online
   - ✅ Confirme API Key correta
   - ✅ Teste com curl/postman

## 🎯 Recomendações

### Para Produção:
- Use Evolution API externa
- Configure domínio próprio
- Use HTTPS obrigatório
- Monitore logs de erro

### Para Desenvolvimento:
- Use Docker Compose local
- Teste com grupo de teste
- Use ambiente separado

### Para Render:
- Dois serviços separados
- Variáveis de ambiente
- Logs centralizados
- Backup automático

## 📞 Suporte

- **Documentação Evolution API**: https://doc.evolution-api.com
- **Discord Oficial**: https://discord.gg/evolution
- **GitHub Issues**: https://github.com/EvolutionAPI/evolution-api/issues

---

**Pronto! Agora sua aplicação está integrada com Evolution API v2! 🎉**
