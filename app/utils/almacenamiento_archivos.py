from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import get_settings

settings = get_settings()


def save_profile_image(file: UploadFile, empresa_id: str) -> str:
    base_path = Path(settings.media_root)
    rel_dir = Path(f"tenant_{empresa_id}") / "fotos_perfil"
    target_dir = base_path / rel_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename or "").suffix.lower() or ".jpg"
    name = f"{uuid4().hex}{suffix}"
    target_path = target_dir / name

    with target_path.open("wb") as out:
        out.write(file.file.read())

    return str((rel_dir / name).as_posix())


def save_base64(content_b64: str, subdir: str = "incidentes", filename_hint: str | None = None) -> str:
    """Guardar un archivo enviado en base64 dentro de media_root/subdir.
    Devuelve la ruta relativa (POSIX) donde se guardó el archivo.
    """
    import base64
    from pathlib import Path
    from uuid import uuid4

    base_path = Path(settings.media_root)
    rel_dir = Path(subdir)
    target_dir = base_path / rel_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    # determinar sufijo por hint, por defecto .jpg
    suffix = ".jpg"
    if filename_hint:
        p = Path(filename_hint)
        if p.suffix:
            suffix = p.suffix.lower()

    name = f"{uuid4().hex}{suffix}"
    target_path = target_dir / name

    data = base64.b64decode(content_b64)
    with target_path.open("wb") as out:
        out.write(data)

    return str((rel_dir / name).as_posix())


def save_incidente_evidence(file: UploadFile, incidente_id: str) -> str:
    base_path = Path(settings.media_root)
    rel_dir = Path("incidentes") / incidente_id
    target_dir = base_path / rel_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename or "").suffix.lower() or ".bin"
    name = f"{uuid4().hex}{suffix}"
    target_path = target_dir / name

    with target_path.open("wb") as out:
        out.write(file.file.read())

    return str((rel_dir / name).as_posix())
