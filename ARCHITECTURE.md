# Arquitetura do ProScraper

## Visão Geral

ProScraper é uma aplicação Flask que extrai dados de produtos de e-commerce brasileiros (Mercado Livre, Amazon, Shopee) e os armazena no Supabase.

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (index.html)                    │
│                   (HTML/CSS/JavaScript)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Flask API (app.py)                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Endpoints:                                           │  │
│  │ - POST /analyze (extração de dados)                 │  │
│  │ - GET /health (status)                              │  │
│  │ - POST /supabase/save-promotion (salvar)            │  │
│  │ - GET /supabase/list (listar)                       │  │
│  │ - GET /supabase/stats (estatísticas)                │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
   ┌─────────┐    ┌──────────┐    ┌──────────┐
   │ Mercado │    │ Amazon   │    │ Shopee   │
   │ Livre   │    │ Brasil   │    │ Brasil   │
   │ (HTML)  │    │ (HTML+SE)│    │(Selenium)│
   └────┬────┘    └────┬─────┘    └────┬─────┘
        │              │              │
        └──────────────┼──────────────┘
                       ▼
        ┌──────────────────────────────┐
        │   Supabase (PostgreSQL)      │
        │  - Tabela: produtos          │
        │  - Armazena promoções        │
        └──────────────────────────────┘
```

## Componentes Principais

### 1. **app.py** (Aplicação Principal)
- **ProScraper**: Classe principal que orquestra a extração
- **ShopeeAutomationChrome**: Classe para automação Shopee com Selenium
- **Endpoints Flask**: Rotas da API

### 2. **config.py** (Configurações)
- Variáveis de ambiente
- Configurações por ambiente (dev/prod)
- Timeouts e limites

### 3. **requirements.txt** (Dependências)
```
Flask - Framework web
requests - HTTP requests
beautifulsoup4 - Parsing HTML
selenium - Automação de browser
supabase - Cliente Supabase
python-dotenv - Variáveis de ambiente
gunicorn - Servidor WSGI para produção
```

## Fluxo de Extração

### Mercado Livre
```
URL → Identificar site → HTTP Request → Parse HTML → 
Extract (título, preço, rating) → Retornar dados
Tempo: ~2-3 segundos
```

### Amazon
```
URL → Identificar site → HTTP Request → Parse HTML → 
Extract → Se falhar → Selenium headless → Extract → Retornar
Tempo: ~3-5 segundos
```

### Shopee
```
URL → Identificar site → Selenium Chrome → Navegar → 
Aguardar carregamento → Extract → Retornar
Tempo: ~15-20 segundos
```

## Métodos de Extração

### HTML Parsing (BeautifulSoup)
- Rápido
- Não requer browser
- Funciona bem para sites estáticos
- Usado em: Mercado Livre, Amazon (fallback)

### Selenium WebDriver
- Mais lento
- Renderiza JavaScript
- Necessário para sites dinâmicos
- Usado em: Shopee, Amazon (fallback)

## Estrutura de Dados

### Produto (Dataclass)
```python
@dataclass
class Produto:
    url: str
    site_name: str
    title: Optional[str]
    price_current: Optional[float]
    price_current_text: Optional[str]
    price_original: Optional[float]
    price_original_text: Optional[str]
    discount_percentage: Optional[float]
    rating: Optional[float]
    rating_count: Optional[int]
    image_url: Optional[str]
    condition: Optional[str]
    sold_quantity: Optional[int]
    errors: List[str]
    extraction_time: float
```

### Promoção (Supabase)
```json
{
  "id": "uuid",
  "mensagem": "string",
  "imagem_url": "string",
  "enviado": boolean,
  "criado_em": "timestamp"
}
```

## Tratamento de Erros

1. **URL inválida**: Retorna erro 400
2. **Site não suportado**: Retorna erro 404
3. **Timeout**: Retorna erro com timeout
4. **Supabase indisponível**: Retorna erro 500
5. **Extração parcial**: Retorna dados disponíveis + erros

## Performance

### Otimizações
- Sessão HTTP reutilizável
- Timeouts agressivos (3-5s)
- Cache de drivers Selenium
- Parsing eficiente com BeautifulSoup

### Limites
- Timeout máximo: 30 segundos
- Tamanho mínimo HTML: 1000 bytes
- Máximo de retries: 2

## Segurança

### Implementado
- User-Agent realista
- Headers HTTP completos
- Referer headers
- Tratamento de exceções
- Validação de entrada

### Não Implementado (Considerar)
- Rate limiting
- Autenticação de API
- CORS restrito
- Validação de HTTPS

## Deploy

### Local
```bash
python app.py
```

### Render (Produção)
```bash
gunicorn app:app
```

### Variáveis Necessárias
- SUPABASE_URL
- SUPABASE_KEY
- FLASK_ENV
- PORT

## Monitoramento

### Logs
- Arquivo: `proscraper.log`
- Nível: INFO
- Rotação: Manual

### Métricas
- Tempo de extração
- Taxa de sucesso
- Erros por site
- Requisições por hora

## Escalabilidade

### Limitações Atuais
- Single-threaded
- Sem cache
- Sem fila de requisições
- Sem load balancing

### Melhorias Futuras
- Celery para tasks assíncronas
- Redis para cache
- Message queue (RabbitMQ)
- Múltiplas instâncias

## Integração Supabase

### Tabela: produtos
```sql
CREATE TABLE produtos (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  mensagem TEXT NOT NULL,
  imagem_url TEXT,
  enviado BOOLEAN DEFAULT FALSE,
  criado_em TIMESTAMP DEFAULT NOW()
);
```

### Operações
- INSERT: Salvar promoção
- SELECT: Listar promoções
- UPDATE: Marcar como enviado
- COUNT: Estatísticas

## Troubleshooting

### Problema: Extração lenta
**Solução**: Aumentar timeouts em config.py

### Problema: Selenium não funciona
**Solução**: Instalar ChromeDriver ou usar undetected-chromedriver

### Problema: Supabase não conecta
**Solução**: Verificar SUPABASE_URL e SUPABASE_KEY

## Próximas Melhorias

1. **Automação Shopee**: Implementar com sucesso
2. **Cache**: Adicionar Redis
3. **Fila**: Implementar Celery
4. **Autenticação**: Proteger endpoints
5. **Documentação**: Swagger/OpenAPI
6. **Testes**: Unit tests e integration tests
7. **CI/CD**: GitHub Actions
8. **Monitoring**: Sentry/DataDog
