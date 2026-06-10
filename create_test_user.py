from app.db.session import engine
from app.db.models import User, Empleado
from sqlalchemy.orm import Session
from django.contrib.auth.hashers import make_password
import uuid
from datetime import datetime, timezone

session = Session(engine)

# Crear un usuario de prueba
user = User(
    username='TestEmpleado',
    password='pbkdf2_sha256$600000$test123test123$test123',  # dummy hash
    email='test@example.com',
    is_staff=False,
    is_active=True,
    date_joined=datetime.now(timezone.utc),
)
session.add(user)
session.flush()

# Crear empleado asociado
empleado = Empleado(
    id=str(uuid.uuid4()),
    usuario_id=user.id,
    empresa_id='ba3bc2c4-2d64-437b-b727-6f7e1bb167ff',  # Empresa del Pedro
    ci='123456',
    nombre_completo='Test Empleado',
)
session.add(empleado)
session.commit()

print('Usuario de prueba creado:')
print('  Username: TestEmpleado')
print('  Empleado ID: ' + empleado.id)

session.close()
