# Backend FastAPI - Gestion de Usuarios

API de gestion de usuarios para AuxilioMecanico, construida con FastAPI + SQLAlchemy + Alembic.

## Estructura actual

```text
backend/
  alembic.ini
  requirements.txt
  .env.example
  alembic/
    env.py
    versions/
      20260415_01_initial_schema.py
      20260415_02_seed_default_permissions.py
  app/
    main.py
    core/
      config.py
      security.py
    db/
      models.py
      session.py
    deps/
      auth.py
    routers/
      auth.py
      empleados.py
      permisos.py
      roles.py
    schemas/
      auth.py
      common.py
      empleado.py
      permiso.py
      register.py
      role.py
      theme.py
    services/
      auth_service.py
      file_storage.py
      permission_service.py
      user_management.py
```

## Requisitos

1. Python 3.11 o superior.
2. PostgreSQL disponible.
3. Estar ubicado en la carpeta `backend/` para ejecutar los comandos.

## Instalacion y configuracion (paso a paso)

1. Entrar a la carpeta del backend.

```powershell
cd backend
```

2. Crear y activar entorno virtual.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Instalar dependencias.

```powershell
pip install -r requirements.txt
```

4. Crear archivo de variables de entorno.

```powershell
Copy-Item .env.example .env
```

5. Ajustar valores importantes en `.env`:

- `DATABASE_URL`: conexion a PostgreSQL.
- `SECRET_KEY`: clave segura para JWT.
- `CORS_ORIGINS`: origenes permitidos del frontend.
- `MEDIA_ROOT`: ruta donde se guardan archivos subidos.
- `FRONTEND_BASE_URL`: URL del frontend para construir enlaces de invitacion.

## Configuracion SMTP (invitaciones de empleados)

Para que el correo de invitacion funcione, completa estas variables en `.env`:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_USE_TLS`
- `SMTP_FROM_EMAIL`

Ejemplo (Gmail con App Password):

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=tu_correo@gmail.com
SMTP_PASSWORD=tu_app_password
SMTP_USE_TLS=true
SMTP_FROM_EMAIL=tu_correo@gmail.com
FRONTEND_BASE_URL=http://localhost:4200
```

Notas:

- Con Gmail debes usar App Password (no la contrasena normal).
- Si `SMTP_HOST` esta vacio, el backend crea el empleado pero no envia correo.
- El enlace de invitacion usa la ruta frontend: `/activate-invite?token=...`.

## Migraciones (Alembic)

Aplicar migraciones pendientes:

```powershell
alembic upgrade head
```

Crear una nueva migracion (si cambias modelos):

```powershell
alembic revision --autogenerate -m "descripcion_del_cambio"
alembic upgrade head
```

## Ejecutar la API

Con el entorno virtual activo y desde `backend/`:
## instala cloudinary 
pip install cloudinary openai python-multipart
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

## Endpoints principales

- Auth:
  - `POST /api/auth/token/` - obtener tokens (login)
  - `POST /api/auth/token/refresh/` - refrescar token de acceso
  - `POST /api/auth/register/company/` - registrar empresa (paso 1)
  - `POST /api/auth/register/admin/` - completar registro admin (paso final)
  - `POST /api/auth/employee-invitations/activate/` - activar invitación de empleado
  - `POST /api/auth/register/` - registro combinado (empresa + admin)

  - `GET /api/auth/my-permissions/` - permisos del usuario autenticado
- Empleados:
  - `GET /api/empleados/`
  - `GET /api/empleados/{empleado_id}/`
  - `POST /api/empleados/`
  - `PUT/PATCH /api/empleados/{empleado_id}/`
  - `DELETE /api/empleados/{empleado_id}/`
- Roles:
  - `GET /api/roles/`
  - `GET /api/roles/{role_id}/`
  - `POST /api/roles/`
  - `PUT/PATCH /api/roles/{role_id}/`
  - `DELETE /api/roles/{role_id}/`
- Permisos:
  - `GET /api/permisos/`
  - `GET /api/permisos/{permiso_id}/`
  - `POST /api/permisos/`
  - `PUT/PATCH /api/permisos/{permiso_id}/`
  - `DELETE /api/permisos/{permiso_id}/`

- Cargos:
  - `GET /api/cargos/`
  - `GET /api/cargos/{cargo_id}/`
  - `POST /api/cargos/`
  - `PUT/PATCH /api/cargos/{cargo_id}/`
  - `DELETE /api/cargos/{cargo_id}/`

- Servicios:
  - `GET /api/servicios/`
  - `GET /api/servicios/{servicio_id}/`
  - `POST /api/servicios/`
  - `PUT/PATCH /api/servicios/{servicio_id}/`
  - `DELETE /api/servicios/{servicio_id}/`

- Clientes (móvil y panel):
  - POST /api/auth/register/client/ - registro de cliente
  - `GET /api/clientes/` - listar clientes (permiso)
  - `GET /api/clientes/me/` - obtener cliente asociado al usuario autenticado
  - `PUT /api/clientes/me/` - actualizar datos del cliente autenticado
  - `GET /api/clientes/me/vehiculos` - listar vehículos del cliente autenticado
  - `POST /api/clientes/me/vehiculos` - registrar nuevo vehículo para el cliente autenticado
  - `GET /api/clientes/me/vehiculos/{vehiculo_id}` - detalle de vehículo del cliente
  - `DELETE /api/clientes/me/vehiculos/{vehiculo_id}` - borrar vehículo del cliente
  - `GET /api/clientes/me/vehiculos/count` - contar vehículos del cliente
  - `GET /api/clientes/{cliente_id}/` - obtener cliente por id
  - `PUT /api/clientes/{cliente_id}/` - actualizar cliente (admin)
  - `GET /api/clientes/{cliente_id}/historial` - historial relacionado al cliente
  - `POST /api/clientes/verificar-sms` - flujo de verificación SMS (enviar/validar código)

- Vehículos (operativo/backoffice):
  - `PUT /api/vehiculos/{vehiculo_id}/` - actualizar vehículo
  - `DELETE /api/vehiculos/{vehiculo_id}/` - eliminar vehículo
  - `PATCH /api/vehiculos/{vehiculo_id}/principal` - marcar vehículo principal
  - `GET /api/vehiculos/atendidos` - listar vehículos con incidentes (personal)

- Incidentes:
  - `GET /api/incidentes/` - listar incidentes
  - `POST /api/incidentes/` - crear incidente (cliente autenticado)
  - `GET /api/incidentes/{incidente_id}/` - detalle
  - `PATCH /api/incidentes/{incidente_id}/` - actualizar incidente (operativo)
  - `POST /api/incidentes/{incidente_id}/asignacion` - asignar técnico
  - `PATCH /api/incidentes/tecnicos/mi-ubicacion` - actualizar ubicación técnico
  - `PATCH /api/incidentes/{incidente_id}/tecnico/ubicacion` - actualizar ubicación técnico para incidente
  - `GET /api/incidentes/{incidente_id}/tracking` - tracking del incidente
  - `PATCH /api/incidentes/{incidente_id}/estado` - actualizar solo estado (móvil)
  - `POST /api/incidentes/{incidente_id}/diagnosticos` - agregar diagnóstico
  - `GET /api/incidentes/{incidente_id}/diagnosticos` - listar diagnósticos
  - `POST /api/incidentes/{incidente_id}/evidencias` - agregar evidencia (url/texto)
  - `POST /api/incidentes/{incidente_id}/evidencias/upload` - subir archivo (multipart)
 
- Pagos:
  - `POST /api/asignaciones/{asignacion_id}/pago` - crear pago para una asignación
  - `GET /api/pagos/` - listar pagos (para empleados/empresa o para cliente autenticado)
  - `GET /api/pagos/{pago_id}` - obtener detalle de un pago
  - `PATCH /api/pagos/{pago_id}/confirmar` - confirmar pago
  - `PATCH /api/pagos/{pago_id}/rechazar` - rechazar pago

## Verificacion rapida

- Health check: `GET /health`
- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`

## Notas

- La app carga configuracion desde `.env`.
- Alembic toma la URL de base de datos desde `app/core/config.py`.