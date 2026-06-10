from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.core.config import get_settings


settings = get_settings()


def send_employee_invitation_email(*, to_email: str, employee_name: str, invitation_url: str) -> bool:
    if not settings.smtp_host:
        return False

    message = EmailMessage()
    message["Subject"] = "Invitacion para activar tu cuenta"
    message["From"] = settings.smtp_from_email
    message["To"] = to_email
    message.set_content(
        (
            f"Hola {employee_name},\n\n"
            "Te han invitado a AuxilioMecanico.\n"
            "Activa tu cuenta creando tu usuario y contrasena aqui:\n"
            f"{invitation_url}\n\n"
            "Si no esperabas este correo, puedes ignorarlo.\n"
        )
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)

    return True
