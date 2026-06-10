from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers.clientes_router import router as clientes_router
from app.routers.autenticacion_router import router as auth_router
from app.routers.cargos_router import router as cargos_router
from app.routers.empleados_router import router as empleados_router
from app.routers.permisos_router import router as permisos_router
from app.routers.roles_router import router as roles_router
from app.routers.vehiculos_router import router as vehiculos_router
from app.routers.incidentes_router import router as incidentes_router
from app.routers.notificaciones_router import router as notificaciones_router
from app.routers.servicios_router import router as servicios_router
from app.routers.empresas_router import router as empresa_router
from app.routers.pagos_router import router as pagos_router
from app.routers.websocket_router import router as websocket_router


settings = get_settings()

app = FastAPI(title=settings.app_name)

origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
if not origins:
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Expose auth endpoints at both root (e.g. /token/) and under /api/auth (e.g. /api/auth/token/)
app.include_router(auth_router)
app.include_router(auth_router, prefix="/api/auth")

# Resource routers exposed under /api
# Note: `clientes` router already defines prefix "/api/clientes" so include it directly
app.include_router(clientes_router)
app.include_router(cargos_router, prefix="/api")
app.include_router(permisos_router, prefix="/api")
app.include_router(roles_router, prefix="/api")
app.include_router(empleados_router, prefix="/api")
app.include_router(servicios_router, prefix="/api")
app.include_router(vehiculos_router, prefix="/api")
app.include_router(incidentes_router, prefix="/api")
app.include_router(notificaciones_router, prefix="/api")
app.include_router(empresa_router, prefix="/api")
app.include_router(pagos_router)
app.include_router(websocket_router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
