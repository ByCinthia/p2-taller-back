# Migración: Agregar columna fcm_token a tabla cliente

## Problema
El modelo SQLAlchemy `Cliente` tiene el campo `fcm_token`, pero la tabla `cliente` en PostgreSQL no tiene esta columna.

```python
# En models.py
class Cliente(Base):
    ...
    fcm_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
```

## Solución

Hay dos opciones para aplicar la migración:

### Opción 1: Usar Alembic (RECOMENDADO)

**Paso 1: Ejecutar la migración**
```bash
# Desde la carpeta backend
alembic upgrade head
```

Esto ejecutará automáticamente:
- Todas las migraciones pendientes
- Incluyendo: `20260429_01_add_fcm_token_cliente`

**Paso 2: Verificar**
```bash
# Conectarse a PostgreSQL
psql -U postgres -d am_db

# Listar columnas de la tabla cliente
\d cliente

# Deberías ver:
# ...
# fcm_token       | character varying(255) | 
# ...
```

---

### Opción 2: Script SQL Manual

Si Alembic tiene problemas o prefieres hacerlo manualmente:

**Paso 1: Conectarse a la BD**
```bash
psql -U postgres -d am_db
```

**Paso 2: Ejecutar el script**
```sql
-- El script es idempotente (no falla si ya existe)
\i backend/scripts/add_fcm_token_cliente.sql
```

O copiar y ejecutar directamente:
```sql
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'cliente' 
        AND column_name = 'fcm_token'
    ) THEN
        ALTER TABLE cliente 
        ADD COLUMN fcm_token VARCHAR(255) NULL;
        RAISE NOTICE 'Columna fcm_token agregada a tabla cliente';
    ELSE
        RAISE NOTICE 'La columna fcm_token ya existe en tabla cliente';
    END IF;
END $$;
```

**Paso 3: Verificar**
```sql
-- Ver la estructura de la tabla
\d cliente

-- O ver solo la columna
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'cliente' 
AND column_name = 'fcm_token';
```

---

## Verificación Final

Después de aplicar la migración:

### 1. En PostgreSQL
```sql
-- Verificar que la columna existe
SELECT * FROM information_schema.columns 
WHERE table_name = 'cliente' AND column_name = 'fcm_token';

-- Resultado esperado:
-- table_catalog | table_schema | table_name | column_name | ordinal_position | column_default | is_nullable | data_type | ...
-- am_db         | public       | cliente    | fcm_token   | 21              | [null]         | YES         | character varying | ...
```

### 2. En Python FastAPI
```python
from app.db.session import get_db
from app.db.models import Cliente

# Crear una sesión de prueba
with next(get_db()) as db:
    cliente = db.query(Cliente).first()
    # Deberías poder acceder a:
    print(cliente.fcm_token)  # None o un token si ya existe
```

### 3. Probar la API
```bash
# Login de cliente
curl -X POST http://localhost:8001/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "cliente_user", "password": "password"}'

# Enviar FCM token
curl -X PATCH http://localhost:8001/api/auth/fcm-token \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"fcm_token": "test-token-123"}'
```

---

## Cambios en la BD

**Antes:**
```
Table "public.cliente"
Column      | Type                     | Collation | Nullable | Default
------------|--------------------------|-----------|----------|----------
id          | character varying(36)    |           | not null |
usuario_id  | integer                  |           |          |
nombre      | character varying(150)   |           | not null |
email       | character varying(254)   |           |          |
telefono    | character varying(20)    |           |          |
activo      | boolean                  |           |          | true
```

**Después:**
```
Table "public.cliente"
Column      | Type                     | Collation | Nullable | Default
------------|--------------------------|-----------|----------|----------
id          | character varying(36)    |           | not null |
usuario_id  | integer                  |           |          |
nombre      | character varying(150)   |           | not null |
email       | character varying(254)   |           |          |
telefono    | character varying(20)    |           |          |
fcm_token   | character varying(255)   |           |          |          ← NUEVO
activo      | boolean                  |           |          | true
```

---

## Reversión (si es necesario)

Si necesitas deshacer la migración:

```bash
# Volver a la migración anterior
alembic downgrade 20260428_01

# O volver N pasos atrás
alembic downgrade -1
```

---

## Notas Importantes

✅ **La migración es idempotente** - No falla si ejecutas `upgrade` múltiples veces  
✅ **Compatible con datos existentes** - No borra ni modifica datos  
✅ **Null by default** - Los clientes existentes tendrán `fcm_token = NULL`  
✅ **Tipo VARCHAR(255)** - Igual al modelo SQLAlchemy  
✅ **No hay índices** - Se puede agregar después si es necesario  

⚠️ **IMPORTANTE:** Ejecuta esto en tu entorno:
1. Primero en **desarrollo** local
2. Luego en **testing** si tienes
3. Finalmente en **producción**

---

## Historial de Migraciones

```
20260422_01: initial_schema_reset
20260423_01: add_cliente_vehiculo
20260424_01: cliente_credentials_and_vehiculo_principal
20260424_02: sync_cliente_usuario_id
20260424_03: incidentes_tracking_and_locations
20260424_04: asignacion_servicio_operativa
20260425_01: incidente_split_assignation
20260425_02: incidente_titulo (reverted)
20260425_03: drop_incidente_titulo
20260425_04: restore_incidente_core_tables
20260428_01: create_pago
20260429_01: add_fcm_token_cliente  ← NUEVA (Esta)
```

---

## Contacto / Soporte

Si tienes problemas:

1. **Error: "Column already exists"**
   - Significa que ya está creada
   - Ignora el error, la migración es idempotente

2. **Error: "Column not found after migration"**
   - Verifica que `alembic upgrade head` se ejecutó sin errores
   - Revisa los logs: `alembic history`

3. **¿Cómo verificar qué migraciones están aplicadas?**
   ```bash
   alembic history
   alembic current
   ```

4. **¿Cómo ver el estado de la migración?**
   ```bash
   alembic heads
   ```
