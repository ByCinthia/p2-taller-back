# Flujos Operativos y Transiciones de Estado - AuxilioMecánico

**Documento de análisis:** Cómo se mueven los datos a través del sistema  
**Última actualización:** 2026-04-24

---

## 1. Flujo de Registro de Cliente

### Paso 1: Cliente se registra en app móvil/web
```
POST /api/auth/register/client/
{
  "nombre": "Juan Pérez",
  "username": "juanperez",
  "password": "segura123",
  "email": "juan@example.com",
  "telefono": "1234567890"
}
```

### Paso 2: Sistema crea User y Cliente
```sql
INSERT INTO auth_user (username, password, email, first_name, is_active, is_staff, date_joined)
VALUES ('juanperez', hash_password('segura123'), 'juan@example.com', 'Juan Pérez', TRUE, FALSE, NOW());

INSERT INTO cliente (id, usuario_id, nombre, email, telefono, activo)
VALUES (uuid(), user.id, 'Juan Pérez', 'juan@example.com', '1234567890', TRUE);
```

### Paso 3: Sistema devuelve token JWT
```json
{
  "access": "eyJ...",
  "refresh": "eyJ...",
  "user": {
    "id": 123,
    "username": "juanperez",
    "cliente_id": "550e8400-e29b-41d4-a716-446655440000",
    "role": "cliente"
  }
}
```

---

## 2. Flujo de Registro de Vehículos

### Paso 1: Cliente registra su vehículo
```
POST /api/clientes/me/vehiculos
{
  "marca": "Toyota",
  "modelo": "Hilux",
  "placa": "XYZ-1234",
  "anio": 2022,
  "principal": true
}
```

### Paso 2: Sistema valida e inserta
```sql
-- Validar que solo un vehículo sea principal
SELECT COUNT(*) FROM vehiculo WHERE cliente_id = ? AND principal = TRUE;
-- Si es 0, permite principal=true

INSERT INTO vehiculo (id, cliente_id, marca, modelo, placa, ano, principal)
VALUES (uuid(), client.id, 'Toyota', 'Hilux', 'XYZ-1234', 2022, TRUE);
```

### Resultado
- ✅ Vehículo guardado como principal
- ✅ Cliente puede registrar múltiples vehículos
- ✅ Solo uno es el "principal"

---

## 3. Flujo de Creación de Incidente (Emergencia)

### Paso 1: Cliente solicita auxilio con GPS y fotos
```
POST /api/incidentes
{
  "tipo": "Pinchazo",
  "descripcion": "Se me pinchó la llanta trasera",
  "vehiculo_id": "550e8400-e29b-41d4-a716-446655440000",
  "latitud": -17.783737,
  "longitud": -63.182103,
  "prioridad": 2
}
```

### Paso 2: Sistema valida coordenadas y crea incidente
```sql
-- Validar rango de coordenadas
WHERE latitud BETWEEN -90 AND 90 AND longitud BETWEEN -180 AND 180;

INSERT INTO incidente (
  id, cliente_id, vehiculo_id, tipo, descripcion,
  latitud, longitud, estado, prioridad, creado_en
) VALUES (
  uuid(),
  client.id,
  vehicle.id,
  'Pinchazo',
  'Se me pinchó la llanta trasera',
  -17.783737,
  -63.182103,
  'pendiente',    ← ESTADO INICIAL
  2,
  NOW()
);
```

### Paso 3: Cliente adjunta evidencias (fotos, audio)
```
POST /api/incidentes/{incidente_id}/evidencias
Content-Type: multipart/form-data

file: [foto.jpg]  →  S3/storage
tipo: "foto"

audio: [grabacion.mp3]  →  S3/storage
tipo: "audio"

texto: "He estado esperando a que baje la presión"
tipo: "texto"
```

### Paso 4: Sistema almacena evidencias
```sql
INSERT INTO evidencia (id, incidente_id, tipo, archivo_url, mime_type, creado_en)
VALUES 
  (uuid(), incident.id, 'foto', 's3://bucket/foto.jpg', 'image/jpeg', NOW()),
  (uuid(), incident.id, 'audio', 's3://bucket/grabacion.mp3', 'audio/mpeg', NOW()),
  (uuid(), incident.id, 'texto', NULL, NULL, NOW());

UPDATE evidencia SET texto = '...' WHERE tipo = 'texto';
```

---

## 4. Flujo de Buscar Técnicos Cercanos

### Paso 1: Sistema identifica incidente sin asignar
```sql
SELECT * FROM incidente WHERE estado = 'pendiente' AND latitud IS NOT NULL;
```

### Paso 2: Frontend solicita técnicos en radio de 10km
```
GET /api/incidentes/tecnicos/cercanos?latitud=-17.783737&longitud=-63.182103&radio_km=10
```

### Paso 3: Sistema calcula distancia (Haversine)
```sql
-- Pseudocódigo: Buscar técnicos disponibles
SELECT 
  e.id,
  e.nombre_completo,
  e.latitud_actual,
  e.longitud_actual,
  -- Haversine formula
  ROUND(
    6371 * ACOS(
      COS(RADIANS(90 - e.latitud_actual)) * COS(RADIANS(90 - (-17.783737))) +
      SIN(RADIANS(90 - e.latitud_actual)) * SIN(RADIANS(90 - (-17.783737))) *
      COS(RADIANS(e.longitud_actual - (-63.182103)))
    ), 3
  ) AS distancia_km,
  e.disponible
FROM empleado e
WHERE e.latitud_actual IS NOT NULL
  AND e.longitud_actual IS NOT NULL
  AND e.empresa_id = incident.empresa_id
  AND distancia_km <= 10
ORDER BY distancia_km ASC;
```

### Resultado: Lista de técnicos cercanos
```json
[
  {
    "empleado_id": "abc123",
    "nombre_completo": "Carlos López",
    "latitud": -17.781,
    "longitud": -63.185,
    "distancia_km": 0.450,
    "disponible": true
  },
  {
    "empleado_id": "def456",
    "nombre_completo": "Miguel Torres",
    "latitud": -17.790,
    "longitud": -63.175,
    "distancia_km": 1.230,
    "disponible": true
  }
]
```

---

## 5. Flujo de Asignación de Servicio

### Paso 1: Despachador selecciona técnico y servicio
```
POST /api/incidentes/{incidente_id}/asignacion
{
  "empleado_id": "abc123",
  "servicio_id": "srv-pinchazo-001",
  "costo_servicio": 50.00,
  "porcentaje_comision": 10,
  "tiempo_estimado_llegada_minutos": 12
}
```

### Paso 2: Sistema crea registro de asignación
```sql
INSERT INTO asignacion_servicio (
  id,
  incidente_id,
  empleado_id,
  servicio_id,
  empresa_id,
  estado_tarea,
  tiempo_estimado_llegada_minutos,
  costo_servicio,
  porcentaje_comision,
  monto_comision,
  fecha_asignacion
) VALUES (
  uuid(),
  'incident-123',
  'emp-carlos-001',
  'srv-pinchazo-001',
  'empresa-taller-001',
  'asignada',     ← ESTADO INICIAL
  12,
  50.00,
  10,
  5.00,           ← 10% de 50
  NOW()
);
```

### Paso 3: Sistema actualiza estado del incidente
```sql
UPDATE incidente
SET estado = 'en_proceso'
WHERE id = 'incident-123';
```

### Paso 4: Notificación a técnico (FCM/Push)
```
{
  "titulo": "Nueva solicitud",
  "cuerpo": "Pinchazo en Av. Monseñor Rivero - $50.00",
  "acciones": ["Aceptar", "Rechazar"]
}
```

---

## 6. Transiciones de Estado de Asignación

```
┌─────────────────────────────────────────────────────────────────┐
│                   ESTADOS DE ASIGNACION_SERVICIO                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. ASIGNADA (inicial)                                           │
│     ├─→ Técnico acepta                                           │
│     │   └─→ 2. ACEPTADA                                          │
│     │       └─→ Técnico se mueve                                │
│     │           └─→ 3. EN_PROCESO                               │
│     │               └─→ Técnico completa                        │
│     │                   └─→ 4. COMPLETADA (terminal)            │
│     │               └─→ Sistema cancela (timeout)               │
│     │                   └─→ 5. CANCELADA (terminal)             │
│     │                                                             │
│     └─→ Técnico rechaza                                          │
│         └─→ 6. RECHAZADA (terminal)                             │
│                                                                   │
│  Notas:                                                          │
│  - Si pasa tiempo en ASIGNADA → CANCELADA                       │
│  - Una sola asignación activa por incidente                     │
│  - Una sola asignación activa por técnico                       │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Flujo de Actualización de Ubicación en Tiempo Real

### Paso 1: Técnico acepta asignación
```
PATCH /api/incidentes/{incidente_id}/asignacion/aceptar
```

### Paso 2: Sistema registra aceptación
```sql
UPDATE asignacion_servicio
SET 
  estado_tarea = 'aceptada',
  fecha_aceptacion = NOW()
WHERE id = 'asignacion-123';
```

### Paso 3: Técnico se desplaza → App envía GPS cada 5-10 segundos
```
PATCH /api/incidentes/{incidente_id}/tecnico/ubicacion
{
  "latitud": -17.775,
  "longitud": -63.185,
  "disponible": true
}
```

### Paso 4: Sistema actualiza ubicación
```sql
UPDATE empleado
SET 
  latitud_actual = -17.775,
  longitud_actual = -63.185,
  ubicacion_actualizada_en = NOW()
WHERE id = 'emp-carlos-001';

-- Nota: Sobrescribe la anterior, NO guarda historial
--       (historial es para fase 2 con tracking_tecnico)
```

### Paso 5: Cliente consulta tracking en tiempo real
```
GET /api/incidentes/{incidente_id}/tracking
```

### Respuesta: Estado actual del servicio
```json
{
  "incidente_id": "incident-123",
  "estado": "en_proceso",
  "latitud_incidente": -17.783737,
  "longitud_incidente": -63.182103,
  "empleado_asignado_id": "emp-carlos-001",
  "tecnico_nombre": "Carlos López",
  "tecnico_latitud": -17.775,
  "tecnico_longitud": -63.185,
  "tecnico_disponible": true,
  "tecnico_ubicacion_actualizada_en": "2026-04-24T14:32:15Z"
}
```

---

## 8. Flujo de Cierre de Servicio

### Paso 1: Técnico llega al sitio
```
PATCH /api/incidentes/{incidente_id}/asignacion/llegada
```

### Paso 2: Sistema registra llegada
```sql
UPDATE asignacion_servicio
SET 
  estado_tarea = 'en_sitio',
  fecha_llegada = NOW()
WHERE id = 'asignacion-123';
```

### Paso 3: Técnico completa servicio y adjunta fotos antes/después
```
POST /api/incidentes/{incidente_id}/evidencias
{
  "tipo": "foto",
  "archivo": [foto_reparacion.jpg]
}
```

### Paso 4: Técnico marca como completado
```
PATCH /api/incidentes/{incidente_id}/asignacion/completar
{
  "diagnostico": "Se cambió la llanta. OK",
  "costo_final": 50.00
}
```

### Paso 5: Sistema cierra asignación e incidente
```sql
UPDATE asignacion_servicio
SET 
  estado_tarea = 'completada',
  fecha_cierre = NOW(),
  costo_servicio = 50.00
WHERE id = 'asignacion-123';

UPDATE incidente
SET estado = 'atendido'
WHERE id = 'incident-123';

-- Técnico vuelve disponible
UPDATE empleado
SET disponible = TRUE
WHERE id = 'emp-carlos-001';
```

---

## 9. Matriz de Validaciones por Tabla

| Tabla | Campo | Validación | Ubicación |
|-------|-------|-----------|-----------|
| empleado | latitud_actual | -90 ≤ lat ≤ 90 | BD + API |
| empleado | longitud_actual | -180 ≤ lon ≤ 180 | BD + API |
| incidente | latitud | -90 ≤ lat ≤ 90 | BD + API |
| incidente | longitud | -180 ≤ lon ≤ 180 | BD + API |
| incidente | estado | IN (pendiente, en_proceso, atendido, cancelado) | API |
| asignacion_servicio | estado_tarea | IN (enum) | BD + API |
| asignacion_servicio | costo_servicio | >= 0 | BD |
| asignacion_servicio | porcentaje_comision | 0 ≤ x ≤ 100 | BD |
| asignacion_servicio | monto_comision | <= costo_servicio | BD |
| vehiculo | principal | Solo 1 por cliente | BD (índice) |
| cliente | usuario_id | UNIQUE | BD |
| empleado | usuario_id | UNIQUE | BD |

---

## 10. Métricas de Negocio que se pueden extraer

```sql
-- ¿Cuántos incidentes sin asignar después de 10 minutos?
SELECT COUNT(*) FROM incidente
WHERE estado = 'pendiente'
AND creado_en < NOW() - INTERVAL '10 minutes';

-- ¿Técnico promedio tarda cuánto en llegar?
SELECT AVG(EXTRACT(EPOCH FROM (fecha_llegada - fecha_asignacion)) / 60) as min_promedio
FROM asignacion_servicio
WHERE estado_tarea = 'completada';

-- ¿Ingresos totales por empresa?
SELECT 
  empresa_id,
  SUM(costo_servicio) as ingresos_brutos,
  SUM(monto_comision) as comisiones
FROM asignacion_servicio
WHERE estado_tarea = 'completada'
GROUP BY empresa_id;

-- ¿Técnico más ocupado?
SELECT 
  empleado_id,
  COUNT(*) as tareas_completadas,
  AVG(EXTRACT(EPOCH FROM (fecha_cierre - fecha_asignacion)) / 60) as duracion_promedio
FROM asignacion_servicio
WHERE estado_tarea = 'completada'
GROUP BY empleado_id
ORDER BY tareas_completadas DESC;

-- ¿Técnicos disponibles ahora?
SELECT COUNT(*) FROM empleado WHERE disponible = TRUE;

-- ¿Cobertura de servicios por zona?
SELECT 
  ROUND(latitud_actual::numeric, 1) as zona_lat,
  ROUND(longitud_actual::numeric, 1) as zona_lon,
  COUNT(*) as tecnicos
FROM empleado
WHERE latitud_actual IS NOT NULL
GROUP BY ROUND(latitud_actual::numeric, 1), ROUND(longitud_actual::numeric, 1);
```

---

## 11. Consideraciones Operativas Futuras

### Fase 2 (No implementado aún):
- [ ] Tabla `tracking_tecnico` para historial de ruta
- [ ] WebSockets para tracking en vivo (en lugar de polling)
- [ ] Auditoría completa (creado_por, actualizado_por, motivos)
- [ ] PostGIS para búsquedas espaciales avanzadas
- [ ] Caché de técnicos cercanos en Redis
- [ ] Sistema de reasesinación automática por timeout

### Reglas de Negocio Pendientes:
- [ ] Validación de técnico con habilitación para servicio X
- [ ] Límite de asignaciones concurrentes por técnico
- [ ] Escalamiento automático si técnico no acepta
- [ ] Cálculo dinámico de ETA basado en histórico
- [ ] Notificación si técnico se desvía del ruta

---

## 12. Ejemplo Completo: Cliente Solicitador de Auxilio

```
HORA 14:00 - Cliente abre app, autoriza GPS
HORA 14:01 - Cliente reporta pinchazo en Av. Monseñor
  └─ CREATE incidente (estado=pendiente)
  └─ CREATE evidencia (foto del pinchazo)

HORA 14:02 - Despachador ve incidente pendiente
  └─ GET /tecnicos/cercanos (10 km)
  └─ Selecciona Carlos López (0.45 km)

HORA 14:03 - Sistema crea asignación
  └─ CREATE asignacion_servicio (estado=asignada)
  └─ UPDATE incidente (estado=en_proceso)
  └─ FCM push a Carlos: "Pinchazo - $50"

HORA 14:04 - Carlos acepta por app
  └─ UPDATE asignacion (estado=aceptada, fecha_aceptacion)

HORA 14:05 - 14:10 - Carlos se desplaza
  └─ PATCH ubicacion cada 30 seg (latitud, longitud)
  └─ Cliente consulta tracking cada 10 seg
  └─ App muestra ubicación en vivo de Carlos

HORA 14:12 - Carlos llega al sitio
  └─ PATCH ubicacion última
  └─ UPDATE asignacion (estado=en_sitio, fecha_llegada)

HORA 14:25 - Carlos termina reparación
  └─ CREATE evidencia (foto después de reparar)
  └─ PATCH asignacion/completar (estado=completada)
  └─ UPDATE incidente (estado=atendido)

HORA 14:26 - Sistema calcula comisión
  └─ monto_comision = 50 * 10% = $5
  └─ Taller retiene: $45, Plataforma: $5
```

---

Este documento es tu referencia paso a paso para entender cómo fluyen los datos.
