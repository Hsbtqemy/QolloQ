import os

from django.core.exceptions import ValidationError
from django.http import FileResponse

MAX_UPLOAD_MB = 25


def validate_file_size(file):
    limit = MAX_UPLOAD_MB * 1024 * 1024
    if file.size > limit:
        raise ValidationError(f"Le fichier ne doit pas dépasser {MAX_UPLOAD_MB} Mo.")


def file_response(field_file):
    filename = os.path.basename(field_file.name)
    return FileResponse(field_file.open("rb"), as_attachment=True, filename=filename)
