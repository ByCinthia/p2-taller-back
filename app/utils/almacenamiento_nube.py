import os
from typing import Optional

import cloudinary
import cloudinary.uploader


def configure_cloudinary() -> None:
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME")
    api_key = os.environ.get("CLOUDINARY_API_KEY")
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )


def upload_evidence(file_path: str, folder: str) -> str:
    """Upload a file to Cloudinary and return the secure URL.

    Uses resource_type="auto" so images, audio and other files are accepted.
    """
    configure_cloudinary()
    try:
        result = cloudinary.uploader.upload(file_path, folder=folder, resource_type="auto")
    except Exception as exc:  # broad catch to convert into HTTP layer later
        raise

    secure = result.get("secure_url") or result.get("url")
    return secure
