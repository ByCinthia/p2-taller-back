#!/bin/bash
# Script de ejecución rápida para la migración FCM Token
# Copiar y ejecutar los comandos según tu entorno

echo "=========================================="
echo "Migración: Agregar fcm_token a tabla cliente"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# ==========================================
# OPCIÓN 1: ALEMBIC (RECOMENDADO)
# ==========================================
echo -e "${YELLOW}OPCIÓN 1: Usar Alembic (RECOMENDADO)${NC}"
echo ""
echo "Paso 1: Verificar estado actual"
echo -e "${GREEN}$ cd backend${NC}"
echo -e "${GREEN}$ alembic current${NC}"
echo ""
echo "Paso 2: Ver migraciones disponibles"
echo -e "${GREEN}$ alembic heads${NC}"
echo ""
echo "Paso 3: Ejecutar migraciones pendientes"
echo -e "${GREEN}$ alembic upgrade head${NC}"
echo ""
echo "Paso 4: Verificar que se aplicó"
echo -e "${GREEN}$ alembic current${NC}"
echo ""
echo "Resultado esperado:"
echo -e "${GREEN}20260429_01_add_fcm_token_cliente${NC}"
echo ""

# ==========================================
# OPCIÓN 2: SQL DIRECTO
# ==========================================
echo -e "${YELLOW}OPCIÓN 2: Usar Script SQL directo${NC}"
echo ""
echo "Paso 1: Ejecutar el script"
echo -e "${GREEN}$ psql -U postgres -d am_db -f backend/scripts/add_fcm_token_cliente.sql${NC}"
echo ""
echo "O, conectarse y ejecutar manualmente:"
echo -e "${GREEN}$ psql -U postgres -d am_db${NC}"
echo -e "${GREEN}am_db=# \\i backend/scripts/add_fcm_token_cliente.sql${NC}"
echo ""

# ==========================================
# VERIFICACIÓN
# ==========================================
echo ""
echo -e "${YELLOW}VERIFICACIÓN: Confirmar que la columna existe${NC}"
echo ""
echo "En PostgreSQL:"
echo -e "${GREEN}$ psql -U postgres -d am_db${NC}"
echo -e "${GREEN}am_db=# SELECT column_name, data_type FROM information_schema.columns${NC}"
echo -e "${GREEN}         WHERE table_name='cliente' AND column_name='fcm_token';${NC}"
echo ""
echo "Resultado esperado:"
echo -e "${GREEN} column_name | data_type${NC}"
echo -e "${GREEN}-------------|-------------------${NC}"
echo -e "${GREEN} fcm_token   | character varying${NC}"
echo ""

# ==========================================
# O DESDE COMANDO DIRECTO
# ==========================================
echo "O ejecutar directamente:"
echo -e "${GREEN}$ psql -U postgres -d am_db -c \"SELECT column_name FROM information_schema.columns WHERE table_name='cliente' AND column_name='fcm_token';\"${NC}"
echo ""

# ==========================================
# ROLLBACK
# ==========================================
echo -e "${YELLOW}ROLLBACK (si necesitas deshacer)${NC}"
echo ""
echo -e "${GREEN}$ cd backend${NC}"
echo -e "${GREEN}$ alembic downgrade 20260428_01${NC}"
echo ""
echo "Esto te llevará de vuelta a la migración anterior (create_pago)"
echo ""

# ==========================================
# PRÓXIMOS PASOS
# ==========================================
echo -e "${YELLOW}PRÓXIMOS PASOS${NC}"
echo ""
echo "1. Reiniciar el servidor FastAPI:"
echo -e "${GREEN}$ python -m uvicorn app.main:app --reload${NC}"
echo ""
echo "2. El modelo Cliente ahora funciona con FCM tokens"
echo ""
echo "3. Verificar que el endpoint funciona:"
echo -e "${GREEN}$ curl -X PATCH http://localhost:8001/api/auth/fcm-token \\${NC}"
echo -e "${GREEN}  -H \"Authorization: Bearer YOUR_TOKEN\" \\${NC}"
echo -e "${GREEN}  -H \"Content-Type: application/json\" \\${NC}"
echo -e "${GREEN}  -d '{\"fcm_token\": \"test-token-123\"}'${NC}"
echo ""

echo -e "${GREEN}✅ Migración lista para ejecutar${NC}"
echo ""
