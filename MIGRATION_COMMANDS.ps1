# Script de ejecución rápida para Windows PowerShell
# Migración: Agregar fcm_token a tabla cliente

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Migración: Agregar fcm_token a tabla cliente" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# ==========================================
# OPCIÓN 1: ALEMBIC (RECOMENDADO)
# ==========================================
Write-Host "OPCIÓN 1: Usar Alembic (RECOMENDADO)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Paso 1: Navegar a la carpeta backend" -ForegroundColor White
Write-Host "PS> cd backend" -ForegroundColor Green
Write-Host ""

Write-Host "Paso 2: Verificar estado actual" -ForegroundColor White
Write-Host "PS> alembic current" -ForegroundColor Green
Write-Host ""

Write-Host "Paso 3: Ver migraciones disponibles" -ForegroundColor White
Write-Host "PS> alembic heads" -ForegroundColor Green
Write-Host ""

Write-Host "Paso 4: Ejecutar la migración" -ForegroundColor White
Write-Host "PS> alembic upgrade head" -ForegroundColor Green
Write-Host ""

Write-Host "Esperado: Se ejecutará 20260429_01_add_fcm_token_cliente" -ForegroundColor Cyan
Write-Host ""

Write-Host "Paso 5: Verificar que se aplicó correctamente" -ForegroundColor White
Write-Host "PS> alembic current" -ForegroundColor Green
Write-Host ""

# ==========================================
# OPCIÓN 2: SQL DIRECTO
# ==========================================
Write-Host "OPCIÓN 2: Usar Script SQL directo" -ForegroundColor Yellow
Write-Host ""
Write-Host "Paso 1: Ejecutar el script con psql" -ForegroundColor White
Write-Host "PS> psql -U postgres -d am_db -f backend/scripts/add_fcm_token_cliente.sql" -ForegroundColor Green
Write-Host ""

Write-Host "O, conectarse de forma interactiva:" -ForegroundColor White
Write-Host "PS> psql -U postgres -d am_db" -ForegroundColor Green
Write-Host "postgres=# \i backend/scripts/add_fcm_token_cliente.sql" -ForegroundColor Green
Write-Host ""

# ==========================================
# VERIFICACIÓN
# ==========================================
Write-Host ""
Write-Host "VERIFICACIÓN: Confirmar que la columna existe" -ForegroundColor Yellow
Write-Host ""
Write-Host "Opción A: Consulta SQL completa" -ForegroundColor White
Write-Host "PS> psql -U postgres -d am_db -c `"SELECT column_name, data_type FROM information_schema.columns WHERE table_name='cliente' AND column_name='fcm_token';`"" -ForegroundColor Green
Write-Host ""

Write-Host "Opción B: Desde psql interactivo" -ForegroundColor White
Write-Host "PS> psql -U postgres -d am_db" -ForegroundColor Green
Write-Host "am_db=# SELECT column_name, data_type FROM information_schema.columns WHERE table_name='cliente' AND column_name='fcm_token';" -ForegroundColor Green
Write-Host ""

Write-Host "Resultado esperado:" -ForegroundColor Cyan
Write-Host " column_name | data_type" -ForegroundColor Green
Write-Host "-------------|-------------------" -ForegroundColor Green
Write-Host " fcm_token   | character varying" -ForegroundColor Green
Write-Host ""

# ==========================================
# ROLLBACK
# ==========================================
Write-Host "ROLLBACK: Si necesitas deshacer la migración" -ForegroundColor Yellow
Write-Host ""
Write-Host "PS> cd backend" -ForegroundColor Green
Write-Host "PS> alembic downgrade 20260428_01" -ForegroundColor Green
Write-Host ""
Write-Host "Esto te devuelve a la versión anterior (create_pago)" -ForegroundColor Cyan
Write-Host ""

# ==========================================
# PRÓXIMOS PASOS
# ==========================================
Write-Host "PRÓXIMOS PASOS" -ForegroundColor Yellow
Write-Host ""

Write-Host "1. Reactivar el venv (si está inactivo)" -ForegroundColor White
Write-Host "PS> .\.venv\Scripts\Activate.ps1" -ForegroundColor Green
Write-Host ""

Write-Host "2. Reiniciar el servidor FastAPI" -ForegroundColor White
Write-Host "PS> python -m uvicorn app.main:app --reload" -ForegroundColor Green
Write-Host ""

Write-Host "3. El modelo Cliente ahora tiene fcm_token en BD" -ForegroundColor White
Write-Host ""

Write-Host "4. Probar el endpoint desde otra PowerShell:" -ForegroundColor White
Write-Host ""
Write-Host "PS> `$TOKEN = 'tu_token_jwt_aqui'" -ForegroundColor Green
Write-Host ""
Write-Host "PS> curl -X PATCH http://localhost:8001/api/auth/fcm-token `` -ForegroundColor Green
Write-Host "  -H 'Authorization: Bearer `$TOKEN' `` -ForegroundColor Green
Write-Host "  -H 'Content-Type: application/json' `` -ForegroundColor Green
Write-Host "  -d '{""fcm_token"": ""test-token-123""}'" -ForegroundColor Green
Write-Host ""

Write-Host "✅ Migración lista para ejecutar" -ForegroundColor Green
Write-Host ""

# ==========================================
# TROUBLESHOOTING
# ==========================================
Write-Host "TROUBLESHOOTING" -ForegroundColor Yellow
Write-Host ""

Write-Host "❓ ¿Cómo veo qué migraciones están aplicadas?" -ForegroundColor White
Write-Host "PS> alembic history" -ForegroundColor Green
Write-Host ""

Write-Host "❓ ¿Cómo veo la migración actual?" -ForegroundColor White
Write-Host "PS> alembic current" -ForegroundColor Green
Write-Host ""

Write-Host "❓ ¿Cómo sé si tengo pendientes?" -ForegroundColor White
Write-Host "PS> alembic heads" -ForegroundColor Green
Write-Host ""

Write-Host "❓ ¿Error 'command not found: alembic'?" -ForegroundColor White
Write-Host "→ Verifica que el venv está activado:" -ForegroundColor Cyan
Write-Host "PS> .\.venv\Scripts\Activate.ps1" -ForegroundColor Green
Write-Host ""

Write-Host "❓ ¿Necesito hacer algo en la aplicación?" -ForegroundColor White
Write-Host "→ No, Alembic se encarga de todo automáticamente." -ForegroundColor Cyan
Write-Host "→ Solo reinicia FastAPI después de la migración." -ForegroundColor Cyan
Write-Host ""

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Documentación completa en: MIGRATION_FCM_TOKEN.md" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
