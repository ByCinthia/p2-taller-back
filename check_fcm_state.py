from app.db.session import SessionLocal
from app.db.models import Empleado, Cliente


def main() -> None:
    db = SessionLocal()
    try:
        empleados = db.query(Empleado).all()
        clientes = db.query(Cliente).all()

        empleados_con_token = [e for e in empleados if e.fcm_token]
        clientes_con_token = [c for c in clientes if c.fcm_token]

        print({
            "empleados_total": len(empleados),
            "empleados_con_token": len(empleados_con_token),
            "clientes_total": len(clientes),
            "clientes_con_token": len(clientes_con_token),
        })

        if empleados_con_token:
            print("Empleados con token:")
            for e in empleados_con_token:
                preview = e.fcm_token[:25] + "..." if len(e.fcm_token) > 25 else e.fcm_token
                print(f"- empleado_id={e.id} usuario_id={e.usuario_id} token={preview}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
