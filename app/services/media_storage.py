from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

CHUNK_SIZE = 1024 * 1024
ALLOWED_MEDIA_TYPES = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
    "video/x-matroska": ".mkv",
    "video/x-msvideo": ".avi",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/avif": ".avif",
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mp4": ".m4a",
    "audio/aac": ".aac",
    "audio/ogg": ".ogg",
    "audio/flac": ".flac",
    "audio/webm": ".webm",
}


def media_path(storage_key: str) -> Path:
    root = Path(settings.media_root).resolve()
    path = (root / storage_key).resolve()
    if not path.is_relative_to(root):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found")
    return path


def display_filename(filename: str | None) -> str:
    name = (filename or "untitled").replace("\\", "/").rsplit("/", 1)[-1].strip()
    safe_name = "".join(char for char in name if char.isprintable())[:255]
    return safe_name or "untitled"


def validate_media_type(content_type: str | None) -> tuple[str, str]:
    mime_type = (content_type or "").split(";", 1)[0].strip().lower()
    extension = ALLOWED_MEDIA_TYPES.get(mime_type)
    if not extension:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="This media type is not supported")
    return mime_type, extension


def save_upload(upload: UploadFile, storage_key: str) -> int:
    destination = media_path(storage_key)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    total = 0
    try:
        with NamedTemporaryFile(mode="wb", dir=destination.parent, prefix=".upload-", delete=False) as target:
            temporary_path = Path(target.name)
            while chunk := upload.file.read(CHUNK_SIZE):
                total += len(chunk)
                if total > settings.media_max_bytes:
                    raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Media file exceeds the upload size limit")
                target.write(chunk)
        if total == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded media file is empty")
        temporary_path.replace(destination)
        return total
    except Exception:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()
        raise
