# Modelo de Base de Datos - AuxilioMecánico SI2

**Última actualización:** 2026-04-24  
**Estado actual:** Migración `20260424_04` (asignacion_servicio_operativa)

---

## Índice de Tablas

1. [auth_user](#auth_user) - Autenticación base del sistema
2. [empresa](#empresa) - Taller/Empresa que ofrece servicios
3. [cargo](#cargo) - Catálogo de cargos por empresa
4. [permisos](#permisos) - Permisos globales del sistema
5. [roles](#roles) - Roles por empresa
6. [empleado](#empleado) - Técnicos/Personal del taller
7. [servicio](#servicio) - Catálogo de servicios ofrecidos
8. [cliente](#cliente) - Cliente que solicita servicios
9. [vehiculo](#vehiculo) - Vehículos registrados por cliente
10. [incidente](#incidente) - Solicitud de emergencia/asistencia
11. [evidencia](#evidencia) - Fotos, audio, texto del incidente
12. [diagnostico](#diagnostico) - Diagnóstico de la falla
13. [asignacion_servicio](#asignacion_servicio) - Asignación operativa de servicio a técnico
14. [suscripcion](#suscripcion) - Suscripción de empresa

---

## Tablas Detalladas

### auth_user
**Tabla de autenticación base (Django compatible)**

| Campo | Tipo | Nullable | Constrains | Notas |
|-------|------|----------|-----------|-------|
| id | INTEGER | ✗ | PK | Auto-incremental |
| username | VARCHAR(150) | ✗ | UNIQUE | Identificador único de login |
| password | VARCHAR(128) | ✗ | | Hash de contraseña |
| first_name | VARCHAR(150) | ✓ | | Nombre |
| last_name | VARCHAR(150) | ✓ | | Apellido |
| email | VARCHAR(254) | ✓ | | Correo electrónico |
| is_staff | BOOLEAN | ✗ | | Indica si es admin |
| is_active | BOOLEAN | ✗ | | Estado activo/inactivo |
| is_superuser | BOOLEAN | ✗ | | Superusuario |
| date_joined | TIMESTAMPTZ | ✗ | | Fecha de creación |
| last_login | TIMESTAMPTZ | ✓ | | Último acceso |

**Relaciones:**
- 1:1 con empleado (vía usuario_id)
- 1:1 con cliente (vía usuario_id)

---

### empresa (Taller)
**Información del taller/empresa que atiende incidentes**

| Campo | Tipo | Nullable | Constrains | Notas |
|-------|------|----------|-----------|-------|
| id | STRING(36) | ✗ | PK, UUID | Identificador único |
| nombre | VARCHAR(100) | ✗ | UNIQUE | Nombre de la empresa |
| nit | VARCHAR(20) | ✗ | UNIQUE | NIT único |
| telefono | VARCHAR(20) | ✓ | | Teléfono de contacto |
| email | VARCHAR(100) | ✓ | | Email corporativo |
| direccion | VARCHAR(255) | ✓ | | Dirección física |
| latitud | NUMERIC(9,6) | ✓ | | Ubicación geográfica |
| longitud | NUMERIC(9,6) | ✓ | | Ubicación geográfica |
| fecha_creacion | TIMESTAMPTZ | ✗ | | Fecha de registro |

**Relaciones:**
- 1:N con empleado
- 1:N con cargo
- 1:N con roles
- 1:N con servicio
- 1:1 con suscripcion

---

### cargo
**Catálogo de cargos por empresa**

| Campo | Tipo | Nullable | Constrains | Notas |
|-------|------|----------|-----------|-------|
| id | STRING(36) | ✗ | PK, UUID | Identificador único |
| empresa_id | STRING(36) | ✗ | FK → empresa.id | Relación a empresa |
| nombre | VARCHAR(100) | ✗ | | Nombre del cargo |
| descripcion | TEXT | ✓ | | Descripción |

---

### permisos
**Permisos globales del sistema**

| Campo | Tipo | Nullable | Constrains | Notas |
|-------|------|----------|-----------|-------|
| id | STRING(36) | ✗ | PK, UUID | Identificador único |
| nombre | VARCHAR(100) | ✗ | UNIQUE | Nombre del permiso |
| descripcion | TEXT | ✗ | | Descripción detallada |

---

### roles
**Roles por empresa (Admin, Técnico, etc.)**

| Campo | Tipo | Nullable | Constrains | Notas |
|-------|------|----------|-----------|-------|
| id | STRING(36) | ✗ | PK, UUID | Identificador único |
| empresa_id | STRING(36) | ✗ | FK → empresa.id | Relación a empresa |
| nombre | VARCHAR(100) | ✗ | | Nombre del rol |

**Relaciones:**
- M:N con permisos (tabla roles_permisos)
- M:N con empleado (tabla empleado_roles)

---

### empleado (Técnico)
**Personal/Técnicos del taller**

| Campo | Tipo | Nullable | Constrains | Notas |
|-------|------|----------|-----------|-------|
| id | STRING(36) | ✗ | PK, UUID | Identificador único |
| usuario_id | INTEGER | ✗ | FK → auth_user.id, UNIQUE | Relación 1:1 con usuario |
| empresa_id | STRING(36) | ✗ | FK → empresa.id | Taller al que pertenece |
| nombre_completo | VARCHAR(201) | ✗ | | Nombre completo |
| ci | VARCHAR(20) | ✗ | | Cédula de identidad |
| telefono | VARCHAR(20) | ✓ | | Teléfono personal |
| direccion | VARCHAR(255) | ✓ | | Dirección |
| sueldo | NUMERIC(10,2) | ✓ | | Sueldo base |
| cargo_id | STRING(36) | ✓ | FK → cargo.id | Cargo actual |
| foto_perfil | VARCHAR(100) | ✓ | | URL de foto |
| fcm_token | VARCHAR(255) | ✓ | | Token para push notifications |
| latitud_actual | NUMERIC(9,6) | ✓ | | Ubicación actual GPS |
| longitud_actual | NUMERIC(9,6) | ✓ | | Ubicación actual GPS |
| ubicacion_actualizada_en | TIMESTAMPTZ | ✓ | | Fecha de última ubicación |
| disponible | BOOLEAN | ✗ | DEFAULT=true | Estado disponible |

**Relaciones:**
- M:N con roles (tabla empleado_roles)
- 1:N con asignacion_servicio

---

### servicio (Catálogo)
**Tipos de servicios ofrecidos por taller**

| Campo | Tipo | Nullable | Constrains | Notas |
|-------|------|----------|-----------|-------|
| id_servicio | STRING(36) | ✗ | PK, UUID | Identificador único |
| empresa_id | STRING(36) | ✗ | FK → empresa.id | Taller que ofrece |
| nombre | VARCHAR(100) | ✗ | | Nombre del servicio (Grúa, Batería, etc.) |
| descripcion | TEXT | ✓ | | Descripción |
| activo | BOOLEAN | ✗ | DEFAULT=true | Servicio disponible |

**Relaciones:**
- 1:N con asignacion_servicio

---

### cliente
**Usuarios clientes que solicitan asistencia**

| Campo | Tipo | Nullable | Constrains | Notas |
|-------|------|----------|-----------|-------|
| id | STRING(36) | ✗ | PK, UUID | Identificador único |
| usuario_id | INTEGER | ✓ | FK → auth_user.id, UNIQUE | Relación 1:1 con usuario auth |
| nombre | VARCHAR(150) | ✗ | | Nombre del cliente |
| email | VARCHAR(254) | ✓ | | Email de contacto |
| telefono | VARCHAR(20) | ✓ | | Teléfono de contacto |
| activo | BOOLEAN | ✗ | DEFAULT=true | Cuenta activa |

**Relaciones:**
- 1:N con vehiculo
- 1:N con incidente

---

### vehiculo
**Vehículos registrados por cliente**

| Campo | Tipo | Nullable | Constrains | Notas |
|-------|------|----------|-----------|-------|
| id | STRING(36) | ✗ | PK, UUID | Identificador único |
| cliente_id | STRING(36) | ✗ | FK → cliente.id | Cliente propietario |
| placa | VARCHAR(20) | ✓ | | Placa del vehículo |
| marca | VARCHAR(50) | ✓ | | Marca (Toyota, Ford, etc.) |
| modelo | VARCHAR(50) | ✓ | | Modelo |
| ano | INTEGER | ✓ | | Año de fabricación |
| color | VARCHAR(50) | ✓ | | Color (opcional) |
| principal | BOOLEAN | ✗ | DEFAULT=false | Vehículo principal del cliente |

**Restricción especial:**
- Índice parcial UNIQUE para principal=true por cliente_id (solo un vehículo principal)

---

### incidente
**Solicitud de emergencia/asistencia del cliente**

| Campo | Tipo | Nullable | Constrains | Notas |
|-------|------|----------|-----------|-------|
| id | STRING(36) | ✗ | PK, UUID | Identificador único |
| cliente_id | STRING(36) | ✓ | FK → cliente.id | Cliente solicitante |
| vehiculo_id | STRING(36) | ✓ | FK → vehiculo.id | Vehículo afectado |
| taller_id | STRING(36) | ✓ | FK → empresa.id | Taller asignado |
| empleado_asignado_id | STRING(36) | ✓ | FK → empleado.id | Técnico asignado (legado) |
| tipo | VARCHAR(100) | ✓ | | Tipo de emergencia (Grúa, Batería, etc.) |
| descripcion | TEXT | ✓ | | Descripción del problema |
| estado | VARCHAR(50) | ✗ | DEFAULT='pendiente' | Estado actual |
| prioridad | INTEGER | ✓ | | Nivel de prioridad (1-5) |
| latitud | NUMERIC(9,6) | ✓ | | Ubicación del incidente |
| longitud | NUMERIC(9,6) | ✓ | | Ubicación del incidente |
| tiempo_estimado_minutos | INTEGER | ✓ | | ETA estimada |
| creado_en | TIMESTAMPTZ | ✗ | | Fecha de creación |

**Estados permitidos:** pendiente, en_proceso, atendido, cancelado

**Relaciones:**
- 1:N con evidencia
- 1:N con diagnostico
- 1:N con asignacion_servicio

---

### evidencia
**Multimedia del incidente (fotos, audio, texto adicional)**

| Campo | Tipo | Nullable | Constrains | Notas |
|-------|------|----------|-----------|-------|
| id | STRING(36) | ✗ | PK, UUID | Identificador único |
| incidente_id | STRING(36) | ✗ | FK → incidente.id | Incidente asociado |
| tipo | VARCHAR(50) | ✗ | | foto, audio, texto |
| archivo_url | VARCHAR(255) | ✓ | | URL del archivo (S3, almacenamiento) |
| mime_type | VARCHAR(100) | ✓ | | Tipo MIME (image/jpeg, audio/mp3, etc.) |
| duracion_segundos | INTEGER | ✓ | | Duración si es audio |
| texto | TEXT | ✓ | | Texto si es de tipo texto |
| creado_en | TIMESTAMPTZ | ✗ | | Fecha de registro |

**Validaciones:**
- Si tipo=foto o audio: archivo_url requerido
- Si tipo=texto: texto requerido

---

### diagnostico
**Diagnóstico del problema (resultado del análisis)**

| Campo | Tipo | Nullable | Constrains | Notas |
|-------|------|----------|-----------|-------|
| id | STRING(36) | ✗ | PK, UUID | Identificador único |
| incidente_id | STRING(36) | ✗ | FK → incidente.id | Incidente diagnosticado |
| clasificacion | INTEGER | ✓ | | Código de clasificación |
| resumen | TEXT | ✓ | | Resumen del diagnóstico |
| prioridad | INTEGER | ✓ | | Prioridad asignada |
| creado_en | TIMESTAMPTZ | ✗ | | Fecha de creación |

---

### asignacion_servicio ⭐
**Tabla intermedia operativa - Une Servicio + Empleado + Incidente**

| Campo | Tipo | Nullable | Constrains | Notas |
|-------|------|----------|-----------|-------|
| id | STRING(36) | ✗ | PK, UUID | Identificador único |
| incidente_id | STRING(36) | ✗ | FK → incidente.id | Incidente a atender |
| empleado_id | STRING(36) | ✗ | FK → empleado.id | Técnico asignado |
| servicio_id | STRING(36) | ✗ | FK → servicio.id_servicio | Tipo de servicio |
| empresa_id | STRING(36) | ✗ | FK → empresa.id | Taller (desnormalizado para rapidez) |
| estado_tarea | ENUM | ✗ | DEFAULT='asignada' | Estado operativo |
| tiempo_estimado_llegada_minutos | INTEGER | ✓ | CHECK >= 0 | ETA en minutos |
| costo_servicio | NUMERIC(12,2) | ✓ | CHECK >= 0 | Costo del servicio |
| porcentaje_comision | NUMERIC(5,2) | ✓ | CHECK 0-100 | % de comisión plataforma |
| monto_comision | NUMERIC(12,2) | ✓ | CHECK >= 0 | Monto de comisión |
| fecha_asignacion | TIMESTAMPTZ | ✗ | DEFAULT=NOW() | Cuándo se asignó |
| fecha_aceptacion | TIMESTAMPTZ | ✓ | | Cuándo técnico aceptó |
| fecha_llegada | TIMESTAMPTZ | ✓ | | Cuándo llegó técnico |
| fecha_cierre | TIMESTAMPTZ | ✓ | | Cuándo se completó |
| motivo_cancelacion | TEXT | ✓ | | Razón de cancelación si aplica |

**Estados permitidos:**
- asignada, aceptada, en_proceso, completada, cancelada, rechazada

**Índices:**
- `ix_asignacion_incidente_estado` (incidente_id, estado_tarea)
- `ix_asignacion_empleado_estado` (empleado_id, estado_tarea)
- `ix_asignacion_empresa_fecha` (empresa_id, fecha_asignacion)
- `uq_asignacion_incidente_activa` (incidente_id) PARTIAL WHERE estado IN (asignada, aceptada, en_proceso)
- `uq_asignacion_empleado_activa` (empleado_id) PARTIAL WHERE estado IN (asignada, aceptada, en_proceso)

**Restricciones especiales:**
- Una asignación activa por incidente
- Una asignación activa por empleado
- monto_comision <= costo_servicio

---

### suscripcion
**Plan de suscripción de empresa**

| Campo | Tipo | Nullable | Constrains | Notas |
|-------|------|----------|-----------|-------|
| id | STRING(36) | ✗ | PK, UUID | Identificador único |
| empresa_id | STRING(36) | ✗ | FK → empresa.id, UNIQUE | Empresa suscrita |
| plan | VARCHAR(20) | ✗ | DEFAULT='basico' | basico, profesional, empresarial |
| estado | VARCHAR(20) | ✗ | DEFAULT='activa' | activa, suspendida, cancelada |
| fecha_inicio | DATE | ✗ | | Inicio de plan |
| fecha_fin | DATE | ✗ | | Fin de plan |
| max_usuarios | INTEGER | ✗ | DEFAULT=5 | Máximo de usuarios |
| max_activos | INTEGER | ✗ | DEFAULT=50 | Máximo incidentes activos |

---

## Enums (Tipos Especiales)

### estado_tarea_enum
Estados de asignación de servicio:
```
asignada      -> Asignada pero no aceptada por técnico
aceptada      -> Aceptada, esperando desplazamiento
en_proceso    -> Técnico en camino o en sitio
completada    -> Servicio completado
cancelada     -> Cancelada por sistema o usuario
rechazada     -> Rechazada por técnico
```

---

## Diagrama de Relaciones (Resumen)

```
auth_user (1) ──── (1) empleado
auth_user (1) ──── (1) cliente

empresa (1) ────── (N) empleado
empresa (1) ────── (N) cargo
empresa (1) ────── (N) roles
empresa (1) ────── (N) servicio
empresa (1) ────── (1) suscripcion

permisos (N) ────── (M) ────── (N) roles

roles (N) ────── (M) ────── (N) empleado

cliente (1) ────── (N) vehiculo
cliente (1) ────── (N) incidente

vehiculo (1) ────── (N) incidente

incidente (1) ────── (N) evidencia
incidente (1) ────── (N) diagnostico
incidente (1) ────── (N) asignacion_servicio

servicio (1) ────── (N) asignacion_servicio

empleado (1) ────── (N) asignacion_servicio

asignacion_servicio (N) ────── (1) empresa  [desnormalizado]
```

---

## Migraciones Aplicadas

| Revisión | Descripción | Cambios |
|----------|-------------|---------|
| 20260422_01 | Initial schema reset | auth_user, empresa, cargo, roles, permisos |
| 20260423_01 | Add cliente & vehiculo | cliente, vehiculo |
| 20260424_01 | Cliente credentials & vehiculo principal | usuario_id en cliente, principal en vehiculo |
| 20260424_02 | Sync cliente.usuario_id | Sincronización defensiva de FK |
| 20260424_03 | Incidentes tracking & locations | latitud/longitud en empresa, empleado, incidente |
| 20260424_04 | Asignacion servicio operativa | asignacion_servicio tabla con enum estados |

---

## Campos de Auditoria Recomendados (No implementados aún)

Para fase 2, considerar agregar:
- `creado_por` (user_id)
- `actualizado_en` (TIMESTAMPTZ)
- `actualizado_por` (user_id)

---

## Validaciones de Negocio (Implementadas en BD)

✅ Coordenadas válidas (latitud -90 a 90, longitud -180 a 180)  
✅ Costos no negativos  
✅ Una asignación activa por incidente  
✅ Una asignación activa por empleado  
✅ Comisión <= costo del servicio  
✅ Un vehículo principal por cliente  

---

## Notas Operacionales

1. **Ubicación en tiempo real:** Se guarda en `empleado.latitud_actual` + `empleado.ubicacion_actualizada_en`
2. **Tracking histórico:** No implementado (marcado para fase 2)
3. **Búsquedas por proximidad:** Usar Haversine en backend o migrar a PostGIS en fase 2
4. **Privacidad:** Cliente solo ve ubicación de técnico si hay asignación activa
5. **Comisiones:** Configurables por asignación (flexibilidad operativa)
