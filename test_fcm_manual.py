#!/usr/bin/env python3
"""
Script de prueba manual para FCM
Uso: python test_fcm_manual.py
"""

import os
import sys
from pathlib import Path

# Agregar backend al path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.db.models import Empleado, Cliente
from app.services.notification_service import send_push_notification, _init_firebase
from sqlalchemy import select


def test_firebase_initialization():
    """Test 1: Verificar inicialización de Firebase"""
    print("\n" + "="*70)
    print("TEST 1: Inicialización de Firebase")
    print("="*70)
    
    settings = get_settings()
    cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None) or getattr(settings, 'firebase_credentials_path', None)
    
    print(f"📁 Ruta configurada: {cred_path}")
    
    if cred_path:
        if os.path.exists(cred_path):
            print(f"✅ Archivo de credenciales encontrado: {cred_path}")
        else:
            print(f"❌ ARCHIVO NO ENCONTRADO: {cred_path}")
            return False
    else:
        print("❌ FIREBASE_CREDENTIALS_PATH no configurado en .env")
        return False
    
    app = _init_firebase()
    if app:
        print("✅ Firebase inicializado correctamente")
        return True
    else:
        print("❌ Error al inicializar Firebase")
        return False


def test_fcm_tokens_in_db():
    """Test 2: Verificar tokens FCM en base de datos"""
    print("\n" + "="*70)
    print("TEST 2: Tokens FCM en Base de Datos")
    print("="*70)
    
    db = SessionLocal()
    try:
        # Buscar empleados con token
        empleados = db.execute(
            select(Empleado).where(Empleado.fcm_token != None)
        ).scalars().all()
        
        print(f"\n👷 EMPLEADOS con FCM token: {len(empleados)}")
        for emp in empleados:
            token_preview = emp.fcm_token[:50] + "..." if len(emp.fcm_token) > 50 else emp.fcm_token
            disponible = "✅ Disponible" if emp.disponible else "❌ No disponible"
            print(f"  - ID: {emp.id} | Disponible: {disponible} | Token: {token_preview}")
        
        # Buscar clientes con token
        clientes = db.execute(
            select(Cliente).where(Cliente.fcm_token != None)
        ).scalars().all()
        
        print(f"\n👤 CLIENTES con FCM token: {len(clientes)}")
        for cli in clientes:
            token_preview = cli.fcm_token[:50] + "..." if len(cli.fcm_token) > 50 else cli.fcm_token
            print(f"  - ID: {cli.id} | Token: {token_preview}")
        
        return len(empleados) > 0 or len(clientes) > 0
    finally:
        db.close()


def test_send_fcm_to_all_available():
    """Test 3: Enviar notificación de prueba a todos los técnicos disponibles"""
    print("\n" + "="*70)
    print("TEST 3: Enviar Notificación de Prueba")
    print("="*70)
    
    db = SessionLocal()
    try:
        empleados = db.execute(
            select(Empleado).where(
                (Empleado.fcm_token != None) & (Empleado.disponible == True)
            )
        ).scalars().all()
        
        if not empleados:
            print("❌ No hay técnicos disponibles con FCM token")
            return False
        
        print(f"\n📢 Enviando notificación a {len(empleados)} técnico(s)...\n")
        
        success_count = 0
        for emp in empleados:
            try:
                print(f"📤 Enviando a empleado {emp.id}...", end=" ")
                send_push_notification(
                    token=emp.fcm_token,
                    title="🧪 Prueba de Notificación FCM",
                    body="Este es un mensaje de prueba del sistema",
                    data={
                        "incidente_id": "TEST-001",
                        "tipo": "PRUEBA",
                        "estado": "test",
                        "timestamp": "2026-04-29T00:00:00Z"
                    }
                )
                print("✅ Enviada correctamente")
                success_count += 1
            except Exception as e:
                print(f"❌ Error: {str(e)[:50]}")
        
        print(f"\n✅ {success_count}/{len(empleados)} notificaciones enviadas correctamente")
        return success_count > 0
    finally:
        db.close()


def print_summary():
    """Imprimir resumen de configuración"""
    print("\n" + "="*70)
    print("RESUMEN DE CONFIGURACIÓN")
    print("="*70)
    
    settings = get_settings()
    
    print(f"\n🔧 Configuración:")
    print(f"  - DEBUG: {settings.debug}")
    print(f"  - DATABASE: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'N/A'}")
    print(f"  - FIREBASE_CREDENTIALS_PATH: {getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None) or getattr(settings, 'firebase_credentials_path', None)}")
    
    cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None) or getattr(settings, 'firebase_credentials_path', None)
    if cred_path and os.path.exists(cred_path):
        print(f"  - Archivo credenciales: ✅ Existe")
    else:
        print(f"  - Archivo credenciales: ❌ NO EXISTE o NO CONFIGURADO")


def main():
    """Ejecutar todos los tests"""
    print("\n")
    print("╔" + "═"*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  🔔 TEST MANUAL DE FIREBASE CLOUD MESSAGING (FCM)".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "═"*68 + "╝")
    
    print_summary()
    
    results = {
        "Firebase Initialization": test_firebase_initialization(),
        "FCM Tokens in Database": test_fcm_tokens_in_db(),
        "Send Test Notification": test_send_fcm_to_all_available(),
    }
    
    print("\n" + "="*70)
    print("RESULTADOS")
    print("="*70)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*70)
    if all_passed:
        print("🎉 TODOS LOS TESTS PASARON CORRECTAMENTE")
        print("FCM está funcionando correctamente en el backend")
    else:
        print("⚠️  ALGUNOS TESTS FALLARON")
        print("Revisar la configuración según los errores arriba")
    print("="*70 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
