"""Validators for uploaded files.

They only inspect files that are being uploaded right now. A file that is
already stored (``_committed`` is True) was validated when it was uploaded.
"""
import os

from django.conf import settings
from django.core.exceptions import ValidationError

CV_EXTENSIONS = (".pdf", ".doc", ".docx")
PICTURE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp")

# First bytes of each allowed CV type. Extensions alone are trivial to fake.
_DOC_SIGNATURE = b"\xd0\xcf\x11\xe0"  # legacy Word (OLE2 container)
_DOCX_SIGNATURE = b"PK\x03\x04"  # .docx is a zip archive


def _is_already_stored(file):
    return bool(getattr(file, "_committed", False))


def _extension(file):
    return os.path.splitext(file.name or "")[1].lower()


def _read_head(file, size=1024):
    try:
        file.seek(0)
        head = file.read(size)
    finally:
        try:
            file.seek(0)
        except Exception:  # pragma: no cover - best effort rewind
            pass
    return head if isinstance(head, bytes) else b""


def validate_cv_file(file):
    """Allow only PDF, DOC and DOCX files up to ``CV_MAX_UPLOAD_MB``."""
    if _is_already_stored(file):
        return

    ext = _extension(file)
    if ext not in CV_EXTENSIONS:
        raise ValidationError("Upload a PDF, DOC or DOCX file.", code="invalid_extension")

    max_mb = getattr(settings, "CV_MAX_UPLOAD_MB", 5)
    if file.size > max_mb * 1024 * 1024:
        raise ValidationError(f"The CV must be {max_mb} MB or smaller.", code="too_large")

    head = _read_head(file)
    if ext == ".pdf":
        valid = b"%PDF-" in head
    elif ext == ".docx":
        valid = head.startswith(_DOCX_SIGNATURE)
    else:
        valid = head.startswith(_DOC_SIGNATURE)
    if not valid:
        raise ValidationError(
            "The file content does not match its extension. "
            "Upload a genuine PDF, DOC or DOCX file.",
            code="invalid_content",
        )


def validate_profile_picture(file):
    """Allow common image formats up to ``PROFILE_PICTURE_MAX_UPLOAD_MB``.

    ImageField itself verifies that the content really is an image.
    """
    if _is_already_stored(file):
        return

    if _extension(file) not in PICTURE_EXTENSIONS:
        raise ValidationError("Upload a JPG, PNG, GIF or WEBP image.", code="invalid_extension")

    max_mb = getattr(settings, "PROFILE_PICTURE_MAX_UPLOAD_MB", 2)
    if file.size > max_mb * 1024 * 1024:
        raise ValidationError(f"The picture must be {max_mb} MB or smaller.", code="too_large")
