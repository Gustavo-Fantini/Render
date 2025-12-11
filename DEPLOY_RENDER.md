# Deploy no Render - ProScraper

## Pré-requisitos
- Conta no Render (https://render.com)
- Repositório Git com o código
- Variáveis de ambiente configuradas

## Passo 1: Preparar o Repositório Git

```bash
git init
git add .
git commit -m "Initial commit - ProScraper ready for Render"
git remote add origin https://github.com/seu-usuario/seu-repositorio.git
git push -u origin main
```

## Passo 2: Configurar no Render

1. Acesse https://dashboard.render.com
2. Clique em "New +" → "Web Service"
3. Conecte seu repositório GitHub
4. Preencha os dados:
   - **Name**: proscraper (ou seu nome preferido)
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: Free (ou pago se preferir)

## Passo 3: Configurar Variáveis de Ambiente

No dashboard do Render, vá para "Environment":

```
SUPABASE_URL=https://cnwrcrpihldqejyvgysn.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
FLASK_ENV=production
```

## Passo 4: Deploy

1. Clique em "Create Web Service"
2. Aguarde o build (2-3 minutos)
3. Seu app estará disponível em: `https://seu-app.onrender.com`

## Endpoints Disponíveis

- **POST /analyze** - Extrai dados de URL
- **GET /health** - Status do servidor
- **POST /supabase/save-promotion** - Salva promoção
- **GET /supabase/list** - Lista promoções
- **GET /supabase/stats** - Estatísticas

## Teste de Saúde

```bash
curl https://seu-app.onrender.com/health
```

## Teste de Extração

```bash
curl -X POST https://seu-app.onrender.com/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.mercadolivre.com.br/..."}'
```

## Notas Importantes

- O Render fornece 750 horas/mês grátis
- Instâncias free dormem após 15 min de inatividade
- Para produção, considere usar instâncias pagas
- Logs disponíveis no dashboard do Render

## Troubleshooting

### Build falha
- Verifique se `requirements.txt` está correto
- Certifique-se de que `Procfile` existe

### App não inicia
- Verifique logs no dashboard
- Confirme variáveis de ambiente

### Selenium não funciona
- Render não suporta Chrome/Selenium por padrão
- Para Shopee, use a API ou fallback HTML

## Estrutura do Projeto

```
teste-site-fantini/
├── app.py                 # Aplicação principal
├── requirements.txt       # Dependências Python
├── Procfile              # Configuração Render
├── runtime.txt           # Versão Python
├── .env.example          # Exemplo de variáveis
├── templates/
│   └── index.html        # Frontend
├── proscraper.log        # Logs (gerado)
└── README.md             # Documentação
```

## Próximos Passos

1. Faça push do código para GitHub
2. Conecte o repositório no Render
3. Configure as variáveis de ambiente
4. Deploy automático ao fazer push
