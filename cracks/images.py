"""Photo processing: remove metadata (GPS!) and limit size before saving."""
from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

MAX_SIDE_PX = 2000


def clean_photo(uploaded_file):
    """Return a new JPEG without EXIF data, rotated upright and at most 2000 px wide/high."""
    with Image.open(uploaded_file) as img:
        img = ImageOps.exif_transpose(img)  # apply phone rotation before dropping EXIF
        img = img.convert("RGB")            # JPEG has no transparency; also drops odd modes
        img.thumbnail((MAX_SIDE_PX, MAX_SIDE_PX))  # only shrinks, keeps aspect ratio

        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85)  # no exif= argument, so no metadata

    name = Path(uploaded_file.name).stem[:50] + ".jpg"
    return ContentFile(buffer.getvalue(), name=name)
