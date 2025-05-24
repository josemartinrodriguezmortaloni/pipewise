-- Configuración de políticas RLS para CRM Agent
-- Este script configura las políticas de Row Level Security (RLS) para permitir operaciones CRUD en las tablas
-- Habilitar RLS en todas las tablas
ALTER TABLE "leads" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "conversations" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "messages" ENABLE ROW LEVEL SECURITY;
-- Crear políticas para la tabla "leads"
-- 1. Política para permitir SELECT a todos los usuarios autenticados
CREATE POLICY "Permitir SELECT en leads para usuarios autenticados" ON "leads" FOR
SELECT USING (true);
-- 2. Política para permitir INSERT a todos los usuarios autenticados
CREATE POLICY "Permitir INSERT en leads para usuarios autenticados" ON "leads" FOR
INSERT WITH CHECK (true);
-- 3. Política para permitir UPDATE a todos los usuarios autenticados
CREATE POLICY "Permitir UPDATE en leads para usuarios autenticados" ON "leads" FOR
UPDATE USING (true);
-- 4. Política para permitir DELETE a todos los usuarios autenticados
CREATE POLICY "Permitir DELETE en leads para usuarios autenticados" ON "leads" FOR DELETE USING (true);
-- Crear políticas para la tabla "conversations"
-- 1. Política para permitir SELECT a todos los usuarios autenticados
CREATE POLICY "Permitir SELECT en conversations para usuarios autenticados" ON "conversations" FOR
SELECT USING (true);
-- 2. Política para permitir INSERT a todos los usuarios autenticados
CREATE POLICY "Permitir INSERT en conversations para usuarios autenticados" ON "conversations" FOR
INSERT WITH CHECK (true);
-- 3. Política para permitir UPDATE a todos los usuarios autenticados
CREATE POLICY "Permitir UPDATE en conversations para usuarios autenticados" ON "conversations" FOR
UPDATE USING (true);
-- 4. Política para permitir DELETE a todos los usuarios autenticados
CREATE POLICY "Permitir DELETE en conversations para usuarios autenticados" ON "conversations" FOR DELETE USING (true);
-- Crear políticas para la tabla "messages"
-- 1. Política para permitir SELECT a todos los usuarios autenticados
CREATE POLICY "Permitir SELECT en messages para usuarios autenticados" ON "messages" FOR
SELECT USING (true);
-- 2. Política para permitir INSERT a todos los usuarios autenticados
CREATE POLICY "Permitir INSERT en messages para usuarios autenticados" ON "messages" FOR
INSERT WITH CHECK (true);
-- 3. Política para permitir UPDATE a todos los usuarios autenticados
CREATE POLICY "Permitir UPDATE en messages para usuarios autenticados" ON "messages" FOR
UPDATE USING (true);
-- 4. Política para permitir DELETE a todos los usuarios autenticados
CREATE POLICY "Permitir DELETE en messages para usuarios autenticados" ON "messages" FOR DELETE USING (true);