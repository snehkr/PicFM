# photomanager/core/thumbnailer.py
import os
from PIL import Image
from .. import config

THUMBNAIL_CACHE_DIR = os.path.join(config.BASE_DIR, ".cache", "thumbnails")
THUMBNAIL_SIZE = (256, 256)  # A bit larger for quality scaling

# Ensure the cache directory exists
os.makedirs(THUMBNAIL_CACHE_DIR, exist_ok=True)


def create_thumbnail(image_path: str, file_hash: str) -> str | None:
    """
    Creates a thumbnail for the given image path and saves it using the file hash.
    Returns the path to the created thumbnail.
    """
    try:
        # Use the file hash for a unique, stable thumbnail filename
        thumbnail_filename = f"{file_hash}.jpg"
        thumbnail_path = os.path.join(THUMBNAIL_CACHE_DIR, thumbnail_filename)

        # If thumbnail already exists, no need to recreate it
        if os.path.exists(thumbnail_path):
            return thumbnail_path

        with Image.open(image_path) as img:
            # Convert to RGB to handle formats like PNG with alpha channels
            img = img.convert("RGB")
            img.thumbnail(THUMBNAIL_SIZE)
            img.save(thumbnail_path, "JPEG", quality=85)

        return thumbnail_path
    except Exception as e:
        print(f"Error creating thumbnail for {image_path}: {e}")
        return None
