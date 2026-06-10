-- Script SQL para agregar columna fcm_token a tabla cliente
-- Compatible con PostgreSQL
-- Idempotente: no falla si la columna ya existe

-- Agregar la columna fcm_token a la tabla cliente
-- Solo si no existe (PostgreSQL 10+)
DO $$
BEGIN
    -- Verificar si la columna ya existe
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'cliente' 
        AND column_name = 'fcm_token'
    ) THEN
        -- Agregar la columna
        ALTER TABLE cliente 
        ADD COLUMN fcm_token VARCHAR(255) NULL;
        
        -- Registrar en logs
        RAISE NOTICE 'Columna fcm_token agregada a tabla cliente';
    ELSE
        RAISE NOTICE 'La columna fcm_token ya existe en tabla cliente';
    END IF;
END $$;

-- Verificar que la columna fue creada correctamente
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'cliente' 
AND column_name = 'fcm_token';
