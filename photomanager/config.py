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
# Set to None to use os.cpu_count() - 1, or a specific number.
WORKER_PROCESSES = max(1, psutil.cpu_count(logical=False) - 1)

# --- Analysis ---
# DBSCAN epsilon: Lower values mean clusters are more dense. Adjust based on results.
# A value between 0.4 and 0.6 is typical for face_recognition's 128d embeddings.
FACE_CLUSTER_EPS = 0.45
FACE_CLUSTER_MIN_SAMPLES = 5  # Increased for better quality clusters

# Hamming distance threshold for near-duplicates.
# A lower value means images must be more similar to be considered duplicates.
DUPLICATE_THRESHOLD = 5

# --- Face Detection ---
# Model can be "hog" (faster, less accurate) or "cnn" (slower, more accurate, needs GPU)
FACE_DETECTION_MODEL = "hog"

# Resize images larger than this for faster face detection
MAX_IMAGE_SIZE = 2048
