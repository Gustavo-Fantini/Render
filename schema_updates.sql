-- Schema para o Sistema de Envios Automáticos
-- Execute este SQL no seu projeto Supabase

-- 1. Tabela de contatos para envio
CREATE TABLE IF NOT EXISTS contacts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20) NOT NULL UNIQUE,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Atualizar tabela products para controle de envios
ALTER TABLE products 
ADD COLUMN IF NOT EXISTS sent TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS enviado BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS active BOOLEAN DEFAULT true;

-- 3. Criar índices para performance
CREATE INDEX IF NOT EXISTS idx_products_sent ON products(sent);
CREATE INDEX IF NOT EXISTS idx_products_enviado ON products(enviado);
CREATE INDEX IF NOT EXISTS idx_products_active ON products(active);
CREATE INDEX IF NOT EXISTS idx_contacts_active ON contacts(active);

-- 4. Tabela de log de envios (opcional, para auditoria)
CREATE TABLE IF NOT EXISTS send_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    product_id UUID REFERENCES products(id),
    contact_id UUID REFERENCES contacts(id),
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    success BOOLEAN NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Criar índices para logs
CREATE INDEX IF NOT EXISTS idx_send_logs_product_id ON send_logs(product_id);
CREATE INDEX IF NOT EXISTS idx_send_logs_sent_at ON send_logs(sent_at);

-- 6. Função para limpar produtos antigos (opcional)
CREATE OR REPLACE FUNCTION cleanup_old_sent_products()
RETURNS void AS $$
BEGIN
    -- Marcar produtos como inativos após 7 dias do envio
    UPDATE products 
    SET active = false 
    WHERE sent < NOW() - INTERVAL '7 days' AND enviado = true;
END;
$$ LANGUAGE plpgsql;

-- 7. Permissões (ajuste conforme necessário)
-- GRANT ALL ON contacts TO authenticated;
-- GRANT ALL ON contacts TO service_role;
-- GRANT ALL ON send_logs TO authenticated;
-- GRANT ALL ON send_logs TO service_role;

-- 8. Exemplo de contato para teste
INSERT INTO contacts (name, phone_number, active) 
VALUES 
    ('Contato Teste', '5511999999999', true)
ON CONFLICT (phone_number) DO NOTHING;

-- Comentários sobre o schema:
-- - products.sent: Timestamp de quando foi enviado
-- - products.enviado: Boolean para controle rápido
-- - products.active: Define se produto deve ser considerado nos envios
-- - contacts.active: Define se contato deve receber mensagens
-- - send_logs: Registro detalhado de todos os envios para auditoria
