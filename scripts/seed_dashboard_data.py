"""
Script para poblar datos de prueba de la empresa 14889715-e598-4fde-b815-5f6278319fdf
con datos realistas para que el dashboard muestre métricas completas.

Uso:
    cd backend
    python -m scripts.seed_dashboard_data

Requiere:
    pip install sqlalchemy psycopg2-binary python-dotenv
"""

import os
import sys
import uuid
import random
from datetime import datetime, timezone, timedelta
from decimal import Decimal

# Agregar directorio raíz al path para poder importar app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Mismo CryptContext que usa la app (app/core/seguridad.py)
pwd_ctx = CryptContext(schemes=["django_pbkdf2_sha256", "bcrypt"], deprecated="auto")

# ───────────────────────────── CONFIG ─────────────────────────────
EMPRESA_ID = "14889715-e598-4fde-b815-5f6278319fdf"
DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL no encontrada en .env")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# ───────────────────────────── HELPERS ─────────────────────────────

def uid() -> str:
    return str(uuid.uuid4())

def random_date(days_ago_min: int, days_ago_max: int) -> datetime:
    """Fecha aleatoria entre days_ago_min y days_ago_max días atrás."""
    delta = random.randint(days_ago_min, days_ago_max)
    return datetime.now(timezone.utc) - timedelta(days=delta, hours=random.randint(0, 23), minutes=random.randint(0, 59))

def random_lat() -> Decimal:
    # Coordenadas de La Paz / El Alto aprox
    return Decimal(str(round(random.uniform(-16.6, -16.3), 6)))

def random_lon() -> Decimal:
    return Decimal(str(round(random.uniform(-68.3, -68.0), 6)))

# ───────────────────────────── MAIN ─────────────────────────────

def seed():
    db = SessionLocal()
    try:
        # 1. Verificar que la empresa existe
        empresa = db.execute(
            text("SELECT id FROM empresa WHERE id = :eid"),
            {"eid": EMPRESA_ID}
        ).fetchone()
        if not empresa:
            print(f"❌ Empresa {EMPRESA_ID} no encontrada.")
            return
        print(f"✅ Empresa encontrada: {EMPRESA_ID}")

        # 2. Encontrar o crear usuario admin para la empresa
        admin_user = db.execute(
            text("""
                SELECT u.id, u.username
                FROM auth_user u
                JOIN empleado e ON e.usuario_id = u.id
                WHERE e.empresa_id = :eid AND (u.is_staff = TRUE OR u.is_superuser = TRUE)
                LIMIT 1
            """),
            {"eid": EMPRESA_ID}
        ).fetchone()

        if not admin_user:
            # Buscar cualquier empleado de la empresa
            admin_user = db.execute(
                text("""
                    SELECT u.id, u.username
                    FROM auth_user u
                    JOIN empleado e ON e.usuario_id = u.id
                    WHERE e.empresa_id = :eid
                    LIMIT 1
                """),
                {"eid": EMPRESA_ID}
            ).fetchone()

        if not admin_user:
            # Buscar cualquier is_staff global
            admin_user = db.execute(
                text("SELECT id, username FROM auth_user WHERE is_staff = TRUE ORDER BY id LIMIT 1")
            ).fetchone()

        if not admin_user:
            # Crear usuario admin on-the-fly
            db.execute(
                text("""
                    INSERT INTO auth_user (password, is_superuser, username, first_name, last_name,
                                           email, is_staff, is_active, date_joined)
                    VALUES (:pwd, TRUE, :uname, :fname, :lname, :email, TRUE, TRUE, :dj)
                """),
                {
                    "pwd": pwd_ctx.hash("admin123", scheme="django_pbkdf2_sha256"),
                    "uname": f"admin_{EMPRESA_ID[:8]}",
                    "fname": "Admin",
                    "lname": "Seed",
                    "email": f"admin_{EMPRESA_ID[:8]}@taller.com",
                    "dj": datetime.now(timezone.utc),
                }
            )
            db.flush()
            admin_user = db.execute(
                text("SELECT id, username FROM auth_user WHERE username = :uname"),
                {"uname": f"admin_{EMPRESA_ID[:8]}"}
            ).fetchone()
            print(f"  ✅ Usuario admin creado: {admin_user.username}")

        print(f"✅ Admin encontrado: {admin_user.username} (id={admin_user.id})")
        admin_id = admin_user.id

        # 3. Crear servicios si no existen
        servicios_data = [
            ("Grua", "Servicio de grúa y remolque"),
            ("Mecánica General", "Reparación mecánica general"),
            ("Electricidad", "Diagnóstico y reparación eléctrica"),
            ("Llantería", "Cambio y reparación de llantas"),
            ("Baterías", "Venta e instalación de baterías"),
        ]
        servicios_ids = []
        for nombre, desc in servicios_data:
            existing = db.execute(
                text("SELECT id_servicio FROM servicio WHERE empresa_id = :eid AND nombre = :nom"),
                {"eid": EMPRESA_ID, "nom": nombre}
            ).fetchone()
            if existing:
                print(f"  ↪ Servicio ya existe: {nombre}")
                servicios_ids.append(existing[0])
            else:
                sid = uid()
                db.execute(
                    text("""
                        INSERT INTO servicio (id_servicio, empresa_id, nombre, descripcion, activo)
                        VALUES (:sid, :eid, :nom, :desc, TRUE)
                    """),
                    {"sid": sid, "eid": EMPRESA_ID, "nom": nombre, "desc": desc}
                )
                servicios_ids.append(sid)
                print(f"  ✅ Servicio creado: {nombre}")

        # 4. Crear cargos
        cargos_data = ["Mecánico", "Electricista", "Gruero", "Ayudante", "Supervisor"]
        cargos_ids = []
        for nombre in cargos_data:
            existing = db.execute(
                text("SELECT id FROM cargo WHERE empresa_id = :eid AND nombre = :nom"),
                {"eid": EMPRESA_ID, "nom": nombre}
            ).fetchone()
            if existing:
                print(f"  ↪ Cargo ya existe: {nombre}")
                cargos_ids.append(existing[0])
            else:
                cid = uid()
                db.execute(
                    text("""
                        INSERT INTO cargo (id, empresa_id, nombre, descripcion)
                        VALUES (:cid, :eid, :nom, :desc)
                    """),
                    {"cid": cid, "eid": EMPRESA_ID, "nom": nombre, "desc": f"Cargo de {nombre.lower()}"}
                )
                cargos_ids.append(cid)
                print(f"  ✅ Cargo creado: {nombre}")

        # 5. Crear empleados (técnicos) — cada uno necesita su propio usuario (unique)
        tecnicos_data = [
            ("87654321", "Carlos Mamani", "carlos@taller.com", "77711111", 3500),
            ("87654322", "Ana Choque", "ana@taller.com", "77722222", 3800),
            ("87654323", "Pedro Quispe", "pedro@taller.com", "77733333", 3200),
            ("87654324", "Lucia Fernandez", "lucia@taller.com", "77744444", 3600),
            ("87654325", "Jorge Condori", "jorge@taller.com", "77755555", 3400),
        ]
        empleados_ids = []
        for ci, nombre, email, tel, sueldo in tecnicos_data:
            existing = db.execute(
                text("SELECT id FROM empleado WHERE empresa_id = :eid AND ci = :ci"),
                {"eid": EMPRESA_ID, "ci": ci}
            ).fetchone()
            if existing:
                print(f"  ↪ Empleado ya existe: {nombre}")
                empleados_ids.append(existing[0])
            else:
                # Crear usuario para el empleado
                uname = nombre.lower().replace(" ", ".") + "_tec"
                db.execute(
                    text("""
                        INSERT INTO auth_user (password, is_superuser, username, first_name, last_name,
                                               email, is_staff, is_active, date_joined)
                        VALUES (:pwd, FALSE, :uname, :fname, :lname, :email, FALSE, TRUE, :dj)
                    """),
                    {
                        "pwd": pwd_ctx.hash("tecnico123", scheme="django_pbkdf2_sha256"),
                        "uname": uname,
                        "fname": nombre.split()[0],
                        "lname": " ".join(nombre.split()[1:]) if len(nombre.split()) > 1 else "",
                        "email": email,
                        "dj": datetime.now(timezone.utc),
                    }
                )
                db.flush()

                user_row = db.execute(
                    text("SELECT id FROM auth_user WHERE username = :uname"),
                    {"uname": uname}
                ).fetchone()

                eid = uid()
                db.execute(
                    text("""
                        INSERT INTO empleado (id, usuario_id, empresa_id, ci, nombre_completo,
                                              direccion, telefono, sueldo, disponible, latitud_actual, longitud_actual)
                        VALUES (:eid, :uid, :emp, :ci, :nom, :dir, :tel, :sue, TRUE, :lat, :lon)
                    """),
                    {
                        "eid": eid, "uid": user_row.id, "emp": EMPRESA_ID,
                        "ci": ci, "nom": nombre, "dir": "Dirección de prueba",
                        "tel": tel, "sue": sueldo,
                        "lat": random_lat(), "lon": random_lon()
                    }
                )
                empleados_ids.append(eid)
                print(f"  ✅ Empleado creado: {nombre} (usuario: {uname} / tecnico123)")

        # Asignar roles admin a los empleados
        admin_role = db.execute(
            text("SELECT id FROM roles WHERE empresa_id = :eid AND nombre = 'admin'"),
            {"eid": EMPRESA_ID}
        ).fetchone()
        if admin_role:
            for emp_id in empleados_ids:
                existing = db.execute(
                    text("SELECT id FROM empleado_roles WHERE empleado_id = :eid AND roles_id = :rid"),
                    {"eid": emp_id, "rid": admin_role[0]}
                ).fetchone()
                if not existing:
                    db.execute(
                        text("INSERT INTO empleado_roles (id, empleado_id, roles_id) VALUES (:id, :eid, :rid)"),
                        {"id": uid(), "eid": emp_id, "rid": admin_role[0]}
                    )

        # 6. Crear clientes
        clientes_data = [
            ("Juan Pérez", "juan@email.com", "70011111"),
            ("María García", "maria@email.com", "70022222"),
            ("Roberto López", "roberto@email.com", "70033333"),
            ("Carmen Ochoa", "carmen@email.com", "70044444"),
            ("Diego Vargas", "diego@email.com", "70055555"),
            ("Sofia Rivas", "sofia@email.com", "70066666"),
            ("Miguel Ángel", "miguel@email.com", "70077777"),
            ("Gabriela Paz", "gabriela@email.com", "70088888"),
            ("Fernando Ruiz", "fernando@email.com", "70099999"),
            ("Patricia Méndez", "patricia@email.com", "70000000"),
        ]
        clientes_ids = []
        for nombre, email, tel in clientes_data:
            existing = db.execute(
                text("SELECT id FROM cliente WHERE nombre = :nom AND telefono = :tel"),
                {"nom": nombre, "tel": tel}
            ).fetchone()
            if existing:
                print(f"  ↪ Cliente ya existe: {nombre}")
                clientes_ids.append(existing[0])
            else:
                cid = uid()
                db.execute(
                    text("""
                        INSERT INTO cliente (id, usuario_id, nombre, email, telefono, activo)
                        VALUES (:cid, NULL, :nom, :email, :tel, TRUE)
                    """),
                    {"cid": cid, "nom": nombre, "email": email, "tel": tel}
                )
                clientes_ids.append(cid)
                print(f"  ✅ Cliente creado: {nombre}")

        # 7. Crear vehículos para los clientes
        marcas_modelos = [
            ("Toyota", "Hilux", 2020), ("Toyota", "Corolla", 2022),
            ("Suzuki", "Swift", 2021), ("Nissan", "Frontier", 2019),
            ("Honda", "Civic", 2023), ("Mitsubishi", "Montero", 2020),
            ("Chevrolet", "Sail", 2022), ("Kia", "Sportage", 2021),
            ("Hyundai", "Tucson", 2023), ("Volkswagen", "Gol", 2020),
        ]
        placas = ["ABC123", "DEF456", "GHI789", "JKL012", "MNO345",
                  "PQR678", "STU901", "VWX234", "YZA567", "BCD890"]
        
        for i, cliente_id in enumerate(clientes_ids):
            marca, modelo, anio = marcas_modelos[i]
            placa = placas[i]
            existing = db.execute(
                text("SELECT id FROM vehiculo WHERE cliente_id = :cid AND placa = :placa"),
                {"cid": cliente_id, "placa": placa}
            ).fetchone()
            if not existing:
                vid = uid()
                db.execute(
                    text("""
                        INSERT INTO vehiculo (id, cliente_id, ano, placa, marca, modelo, principal)
                        VALUES (:vid, :cid, :anio, :placa, :marca, :modelo, TRUE)
                    """),
                    {"vid": vid, "cid": cliente_id, "anio": anio, "placa": placa, "marca": marca, "modelo": modelo}
                )
                print(f"  ✅ Vehículo creado: {marca} {modelo} ({placa})")

        # 8. Crear incidentes en varios estados y fechas
        tipos_incidente = ["grua", "mecanica", "electrica", "llanteria", "bateria"]
        estados = ["pendiente", "aceptada", "asignada", "en_proceso", "atendido", "completada", "cancelada"]
        
        # Distribución: 50 incidentes aproximadamente
        num_incidentes = 50
        incidentes_ids = []
        
        incidentes_para_asignar = []  # (id, estado) para crear asignaciones después

        print(f"\n  Creando {num_incidentes} incidentes...")
        for i in range(num_incidentes):
            inc_id = uid()
            cliente = random.choice(clientes_ids)
            tipo = random.choice(tipos_incidente)
            estado = random.choices(
                estados,
                weights=[15, 10, 10, 10, 8, 25, 22],  # más pendientes, completados y cancelados
                k=1
            )[0]
            dias_atras = random.randint(0, 60)
            creado = random_date(0, 60)
            prioridad = random.choice([1, 2, 3, 4, 5])
            lat = random_lat()
            lon = random_lon()

            # Algunos incidentes sin ubicación para probar ese caso
            if random.random() < 0.15:
                lat = None
                lon = None

            db.execute(
                text("""
                    INSERT INTO incidente (id, cliente_id, tipo, descripcion, estado,
                                           prioridad, latitud, longitud, creado_en)
                    VALUES (:id, :cid, :tipo, :desc, :estado,
                            :prio, :lat, :lon, :creado)
                """),
                {
                    "id": inc_id, "cid": cliente, "tipo": tipo,
                    "desc": f"Incidente de {tipo} - {i+1}",
                    "estado": estado, "prio": prioridad,
                    "lat": lat, "lon": lon, "creado": creado
                }
            )
            incidentes_ids.append(inc_id)

            # Si el estado lo requiere, asignar accepted_empresa_id
            if estado in ("aceptada", "asignada", "en_proceso", "atendido", "completada"):
                db.execute(
                    text("UPDATE incidente SET accepted_empresa_id = :eid WHERE id = :iid"),
                    {"eid": EMPRESA_ID, "iid": inc_id}
                )

            if estado in ("asignada", "en_proceso", "atendido", "completada", "cancelada"):
                incidentes_para_asignar.append((inc_id, estado, creado))

        print(f"  ✅ {num_incidentes} incidentes creados")

        # 9. Crear asignaciones (asignacion_servicio) para incidentes asignados o más avanzados
        print(f"\n  Creando asignaciones...")
        asignaciones_ids = []
        for inc_id, estado, creado in incidentes_para_asignar:
            empleado = random.choice(empleados_ids)
            servicio = random.choice(servicios_ids)
            asig_id = uid()
            fecha_asignacion = creado + timedelta(minutes=random.randint(5, 180))
            
            fecha_cierre = None
            if estado in ("atendido", "completada"):
                fecha_cierre = fecha_asignacion + timedelta(minutes=random.randint(15, 300))
            
            tiempo_estimado = random.choice([15, 20, 30, 45, 60])
            costo = Decimal(str(round(random.uniform(100, 2000), 2)))

            db.execute(
                text("""
                    INSERT INTO asignacion_servicio
                        (id, incidente_id, empleado_id, servicio_id, empresa_id,
                         estado_tarea, tiempo_estimado_llegada_minutos, costo_servicio,
                         porcentaje_comision, monto_comision,
                         fecha_asignacion, fecha_cierre)
                    VALUES
                        (:id, :iid, :eid, :sid, :emp,
                         :est, :tel, :costo,
                         15.00, :comision,
                         :fa, :fc)
                """),
                {
                    "id": asig_id, "iid": inc_id, "eid": empleado, "sid": servicio,
                    "emp": EMPRESA_ID, "est": estado, "tel": tiempo_estimado,
                    "costo": costo, "comision": round(costo * Decimal("0.15"), 2),
                    "fa": fecha_asignacion, "fc": fecha_cierre
                }
            )
            asignaciones_ids.append(asig_id)

            # 10. Crear pagos para las asignaciones completadas
            if estado in ("atendido", "completada"):
                pago_id = uid()
                db.execute(
                    text("""
                        INSERT INTO pago (id, asignacion_id, incidente_id, cliente_id, empresa_id,
                                          monto_total, metodo_pago, estado,
                                          comision_plataforma, monto_taller,
                                          fecha_creacion, fecha_confirmacion)
                        VALUES (:id, :aid, :iid, :cid, :eid,
                                :monto, :metodo, 'confirmado',
                                :comision, :taller,
                                :fc, :fconf)
                    """),
                    {
                        "id": pago_id, "aid": asig_id, "iid": inc_id,
                        "cid": random.choice(clientes_ids), "eid": EMPRESA_ID,
                        "monto": costo,
                        "metodo": random.choice(["efectivo", "qr_simulado", "tarjeta_simulada"]),
                        "comision": round(costo * Decimal("0.15"), 2),
                        "taller": round(costo * Decimal("0.85"), 2),
                        "fc": fecha_asignacion,
                        "fconf": fecha_cierre or fecha_asignacion + timedelta(minutes=5)
                    }
                )

        print(f"  ✅ {len(asignaciones_ids)} asignaciones creadas con sus pagos")

        # 11. Crear algunos diagnósticos y evidencias
        print(f"\n  Creando diagnósticos y evidencias...")
        for inc_id in random.sample(incidentes_ids, min(15, len(incidentes_ids))):
            diag_id = uid()
            db.execute(
                text("""
                    INSERT INTO diagnostico (id, incidente_id, clasificacion, resumen, prioridad, creado_en)
                    VALUES (:id, :iid, :clasif, :resumen, :prio, :creado)
                """),
                {
                    "id": diag_id, "iid": inc_id,
                    "clasif": random.randint(1, 5),
                    "resumen": random.choice([
                        "Falla en el motor", "Batería descargada",
                        "Pinchazo de llanta", "Problema eléctrico",
                        "Sobrecalentamiento", "Freno desgastado"
                    ]),
                    "prio": random.randint(1, 5),
                    "creado": random_date(0, 30)
                }
            )

        for inc_id in random.sample(incidentes_ids, min(10, len(incidentes_ids))):
            ev_id = uid()
            db.execute(
                text("""
                    INSERT INTO evidencia (id, incidente_id, tipo, url_archivo, texto)
                    VALUES (:id, :iid, :tipo, :url, :texto)
                """),
                {
                    "id": ev_id, "iid": inc_id,
                    "tipo": random.choice(["foto", "texto", "audio"]),
                    "url": f"https://ejemplo.com/evidencias/{ev_id}.jpg",
                    "texto": random.choice([
                        "Se observa daño en el motor",
                        "Llanta ponchada en costado derecho",
                        "Cables pelados en el sistema eléctrico",
                        "Batería con fugas",
                        "Sin novedades adicionales"
                    ])
                }
            )

        db.commit()
        print(f"\n{'='*60}")
        print(f"  ✅ ¡Datos de seed completados con éxito!")
        print(f"  Empresa: {EMPRESA_ID}")
        print(f"  Técnicos: {len(empleados_ids)}")
        print(f"  Clientes: {len(clientes_ids)}")
        print(f"  Incidentes: {len(incidentes_ids)}")
        print(f"  Asignaciones: {len(asignaciones_ids)}")
        print(f"{'='*60}")

        # Mostrar resumen de incidentes por estado
        print("\n  Resumen por estado:")
        for estado in estados:
            count = db.execute(
                text("SELECT COUNT(*) FROM incidente WHERE estado = :est"),
                {"est": estado}
            ).scalar()
            print(f"    {estado}: {count}")

    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
