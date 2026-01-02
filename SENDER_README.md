# Sistema de Envios Automáticos - ProScraper

## 🚀 Novidades

Adicionamos um sistema completo de envios automáticos de mensagens via WhatsApp, rodando em background a cada 15 minutos.

## 📋 Funcionalidades

### ✨ Sistema de Agendamento
- **Execução automática**: Roda a cada 15 minutos
- **Controle de histórico**: Evita envios duplicados em 24 horas
- **Interface web**: Painel completo para gerenciamento
- **Status em tempo real**: Monitoramento do sistema

### 📱 Integração WhatsApp
- **Evolution API**: Conexão robusta com WhatsApp
- **Mensagens formatadas**: Layout profissional para promoções
- **Teste de conexão**: Validação antes de iniciar
- **Mensagens de teste**: Verificação de funcionamento

### 🎯 Gestão de Contatos
- **Cadastro simplificado**: Adicione contatos via interface
- **Status ativo/inativo**: Controle quem recebe mensagens
- **Lista de contatos**: Visualização rápida dos destinatários

## 🛠️ Configuração

### 1. Atualizar Schema Supabase
Execute o SQL do arquivo `schema_updates.sql` no seu projeto Supabase.

### 2. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 3. Configurar Evolution API
Acesse a aba de envios em `/sender` e configure:
- URL da API Evolution
- API Key
- Nome da instância

### 4. Adicionar Contatos
Cadastre os números que receberão as promoções via interface.

## 📊 Como Funciona

### Ciclo de Envio
1. **Busca produtos**: Sistema busca produtos não enviados nas últimas 24h
2. **Verifica contatos**: Lista apenas contatos ativos
3. **Formata mensagens**: Cria mensagens profissionais com dados do produto
4. **Envia mensagens**: Dispara via Evolution API
5. **Atualiza status**: Marca produtos como enviados
6. **Aguarda próximo ciclo**: Repete após 15 minutos

### Controle de Duplicatas
- Produtos enviados ficam marcados por 24 horas
- Sistema só envia produtos não marcados recentemente
- Histórico completo em `send_logs`

### Formato das Mensagens
```
🔥 *OFERTA IMPERDÍVEL*

📦 [Nome do Produto]

💰 De: [Preço Original]
💎 Por: [Preço Atual]
🎯 Desconto: X% OFF

🔗 [Link do Produto]

⚡ Aproveite agora!
```

## 🔧 Endpoints da API

### Sistema de Envios
- `GET /sender` - Interface de gerenciamento
- `GET /api/sender/status` - Status do sistema
- `POST /api/sender/start` - Iniciar envios automáticos
- `POST /api/sender/stop` - Parar envios automáticos

### WhatsApp
- `POST /api/sender/configure-whatsapp` - Configurar API
- `POST /api/sender/test-connection` - Testar conexão
- `POST /api/sender/send-test` - Enviar mensagem teste

### Contatos
- `GET /api/sender/contacts` - Listar contatos
- `POST /api/sender/contacts` - Adicionar contato

### Estatísticas
- `GET /api/sender/stats` - Dados do sistema

## 🎯 Interface Web

Acesse `http://localhost:5000/sender` para:

- **Dashboard**: Status em tempo real
- **Controle**: Iniciar/parar sistema
- **Configuração**: WhatsApp e contatos
- **Testes**: Validar funcionamento
- **Estatísticas**: Produtos pendentes/enviados

## 🔄 Fluxo de Trabalho

1. **Extração**: Use o sistema normal para extrair produtos
2. **Ativação**: Inicie o scheduler via interface
3. **Configuração**: Conecte sua Evolution API
4. **Contatos**: Cadastre destinatários
5. **Monitoramento**: Acompanhe envios automáticos

## 📈 Benefícios

- **Economia**: Roda no Render, sem necessidade de servidor local
- **Automação**: Envios automáticos sem intervenção manual
- **Controle**: Histórico completo e controle de duplicatas
- **Profissionalismo**: Mensagens formatadas e bem estruturadas
- **Escalabilidade**: Suporta múltiplos contatos e produtos

## 🛡️ Segurança

- **Validação**: Todos os dados são validados antes do envio
- **Rate limiting**: Delay entre mensagens para evitar bloqueios
- **Logs completos**: Registro detalhado de todas as operações
- **Controle de acesso**: Interface protegida e controlada

## 🔍 Monitoramento

O sistema oferece:
- Status do scheduler em tempo real
- Contador de produtos pendentes/enviados
- Lista de contatos ativos
- Próxima execução agendada
- Histórico de envios

## 🚀 Deploy no Render

O sistema está pronto para rodar no Render:
- Usa threading para background tasks
- Não requer processos adicionais
- Interface web completa
- Logs detalhados para debugging

## 📞 Suporte Evolution API

Para configurar a Evolution API:
1. Crie uma instância no painel Evolution
2. Obtenha sua API Key
3. Conecte o WhatsApp Web à instância
4. Use os dados na interface do sistema

## 🎉 Começar

1. Execute o SQL no Supabase
2. Instale as dependências
3. Acesse `/sender`
4. Configure o WhatsApp
5. Adicione contatos
6. Inicie o sistema

Pronto! Seu sistema de envios automáticos está funcionando! 🚀
