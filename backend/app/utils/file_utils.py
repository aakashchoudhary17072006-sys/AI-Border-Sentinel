import re
import uuid
from datetime import datetime
from pathlib import Path
from app.core.config import settings


def generate_video_id() -> str:
    """Generate a unique collision-resistant ID for an uploaded video."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    short_uuid = uuid.uuid4().hex[:8]
    return f"vid_{timestamp}_{short_uuid}"


def is_allowed_extension(filename: str) -> bool:
    """Check if the filename has an allowed video extension."""
    if not filename or "." not in filename:
        return False
    suffix = Path(filename).suffix.lower()
    return suffix in settings.ALLOWED_EXTENSIONS


def sanitize_filename(original_filename: str, video_id: str) -> str:
    """
    Produce a safe, collision-proof filename incorporating the video_id
    and keeping only safe characters in the original stem.
    """
    raw_path = Path(original_filename)
    extension = raw_path.suffix.lower()
    # Replace non-alphanumeric chars in stem with underscore
    safe_stem = re.sub(r"[^\w\-]", "_", raw_path.stem)[:30]
    return f"{video_id}_{safe_stem}{extension}"


def get_safe_relative_path(stored_path: Path) -> str:
    """
    Convert internal filesystem storage path to a safe relative reference,
    preventing disclosure of root host directories.
    """
    try:
        relative = stored_path.relative_to(settings.BASE_DIR)
        return str(relative).replace("\\", "/")
    except ValueError:
        # Fallback to just uploads filename
        return f"data/uploads/{stored_path.name}"
