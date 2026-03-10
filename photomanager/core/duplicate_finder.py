# photomanager/core/duplicate_finder.py
import imagehash
from PIL import Image
import torch
import open_clip
import numpy as np
from .. import config

# --- Lazy-loaded CLIP Model ---
_clip_model = None
_clip_preprocess = None


def get_clip_model():
    """Initializes the CLIP model safely per-worker process."""
    global _clip_model, _clip_preprocess

    if _clip_model is None:
        device = "cpu"

        _clip_model, _, _clip_preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained="openai"
        )

        _clip_model = _clip_model.to(device)
        _clip_model.eval()

    return _clip_model, _clip_preprocess


def calculate_phash(image_path):
    """Calculates the traditional perceptual hash (Stage 1 Filter)."""
    try:
        with Image.open(image_path) as img:
            return str(imagehash.phash(img))
    except Exception:
        return None


def get_ai_embedding(image_path):
    try:
        model, preprocess = get_clip_model()

        with Image.open(image_path) as img:
            img = img.convert("RGB")

            # Resize very large images
            max_size = 1024
            if max(img.size) > max_size:
                img.thumbnail((max_size, max_size))

            img_tensor = preprocess(img).unsqueeze(0)

        with torch.no_grad():
            embedding = model.encode_image(img_tensor)

        embedding = embedding / embedding.norm(dim=-1, keepdim=True)

        return embedding.cpu().numpy()[0].astype(np.float32)

    except Exception as e:
        print(f"Error getting AI embedding for {image_path}: {e}")
        return None
