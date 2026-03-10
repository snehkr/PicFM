# photomanager/config.py
import os
import psutil

# --- General ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "photomanager.db")

# --- UI ---
THUMBNAIL_SIZE = (175, 175)
WINDOW_SIZE = (1280, 720)
DEFAULT_THEME = "dark"  # "light" or "dark"

# --- Scanner ---
SUPPORTED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".heic", ".heif"]

# Use multiple processes for faster scanning.
WORKER_PROCESSES = max(1, (psutil.cpu_count(logical=True) or 4) - 1)

# --- Analysis ---
FACE_CLUSTER_EPS = 1.1
FACE_CLUSTER_MIN_SAMPLES = 5  # Increased for better quality clusters

# --- Duplicate Detection ---
DUPLICATE_THRESHOLD = 5
CLIP_SIMILARITY_THRESHOLD = 0.92

# --- Image Processing ---
MAX_ANALYSIS_IMAGE_SIZE = 1600

# --- Cache ---
THUMBNAIL_CACHE_DIR = os.path.join(BASE_DIR, "thumbnails")
