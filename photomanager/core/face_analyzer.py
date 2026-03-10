# photomanager/core/face_analyzer.py
import os
import sys
import cv2
import numpy as np
from sklearn.cluster import DBSCAN
from insightface.app import FaceAnalysis

from . import database
from .. import config


def get_resource_path(relative_path):
    """Safely gets the absolute path to resources for PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# --- Lazy-loaded InsightFace ONNX detector ---
_face_app = None


def get_face_app():
    """Initializes the InsightFace model safely per-worker process."""
    global _face_app
    if _face_app is None:
        # By default, InsightFace downloads to ~/.insightface/models/
        # We specify the providers to force CPU and avoid CUDA warnings
        _face_app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        _face_app.prepare(ctx_id=0, det_size=(320, 320))
    return _face_app


def analyze_faces(image_path):
    """
    Detects faces and extracts embeddings using InsightFace (ArcFace).
    """
    try:
        # We read with cv2 directly as InsightFace expects BGR numpy arrays
        img = cv2.imread(image_path)
        if img is None:
            print(f"Could not open or read image: {image_path}")
            return [], "error"

        h, w = img.shape[:2]

        # Optimization: Resize huge images to speed up CPU inference
        max_size = 1600
        scale = 1.0
        if h > max_size or w > max_size:
            scale = max_size / max(h, w)
            img = cv2.resize(img, (0, 0), fx=scale, fy=scale)

        app = get_face_app()
        faces = app.get(img)

        num_faces = len(faces)
        if num_faces == 0:
            return [], "no_face"
        elif num_faces == 1:
            category = "one_face"
        elif num_faces == 2:
            category = "two_faces"
        elif num_faces == 3:
            category = "three_faces"
        else:
            category = "many_faces"

        faces_data = []
        for face in faces:
            # bbox is returned as [left, top, right, bottom]
            # We scale it back to original image coordinates if we resized
            bbox = face.bbox / scale
            left, top, right, bottom = bbox.astype(int)

            # Ensure coordinates stay within image bounds
            left, top = max(0, left), max(0, top)
            right, bottom = min(w, right), min(h, bottom)

            faces_data.append(
                {
                    # Format as (top, right, bottom, left) to keep DB consistent
                    "bbox": (top, right, bottom, left),
                    # InsightFace provides a highly accurate normalized 512-D embedding
                    "embedding": face.normed_embedding,
                }
            )

        return faces_data, category

    except Exception as e:
        print(f"Unexpected error analyzing {image_path}: {e}")
        return [], "error"


def run_face_clustering():
    conn = database.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, embedding FROM faces WHERE cluster_id IS NULL")
    new_faces = cursor.fetchall()

    if not new_faces:
        print("No new faces to process.")
        conn.close()
        return

    new_face_ids = [row["id"] for row in new_faces]
    new_embeddings = np.array([row["embedding"] for row in new_faces])

    cursor.execute(
        "SELECT cluster_id, embedding FROM faces WHERE cluster_id IS NOT NULL"
    )
    existing_faces = cursor.fetchall()

    unmatched_indices = list(range(len(new_embeddings)))

    if existing_faces:
        print("Comparing new faces against known people...")
        known_embeddings = np.array([row["embedding"] for row in existing_faces])
        known_cluster_ids = [row["cluster_id"] for row in existing_faces]

        still_unmatched = []
        # InsightFace embeddings are highly separated. Euclidean distance threshold
        # for ArcFace is typically around 1.0 to 1.2.
        MATCH_TOLERANCE = 1.1

        for i, new_emb in enumerate(new_embeddings):
            distances = np.linalg.norm(known_embeddings - new_emb, axis=1)
            min_distance_idx = np.argmin(distances)

            if distances[min_distance_idx] <= MATCH_TOLERANCE:
                cluster_id = known_cluster_ids[min_distance_idx]
                cursor.execute(
                    "UPDATE faces SET cluster_id = ? WHERE id = ?",
                    (int(cluster_id), int(new_face_ids[i])),
                )
            else:
                still_unmatched.append(i)

        unmatched_indices = still_unmatched

    if len(unmatched_indices) >= config.FACE_CLUSTER_MIN_SAMPLES:
        print(f"Running DBSCAN on {len(unmatched_indices)} completely new faces...")
        unmatched_embeddings = new_embeddings[unmatched_indices]
        unmatched_ids = [new_face_ids[i] for i in unmatched_indices]

        # Use 1.1 for InsightFace DBSCAN epsilon as well
        clt = DBSCAN(
            metric="euclidean",
            eps=1.1,
            min_samples=config.FACE_CLUSTER_MIN_SAMPLES,
            n_jobs=-1,
        )
        clt.fit(unmatched_embeddings)

        label_ids = np.unique(clt.labels_)
        new_person_map = {}

        for label_id in label_ids:
            if label_id != -1:
                max_person_id_row = conn.execute(
                    "SELECT MAX(id) as max_id FROM people"
                ).fetchone()
                next_person_num = (max_person_id_row["max_id"] or 0) + 1
                person_name = f"Person {next_person_num}"

                cursor.execute("INSERT INTO people (name) VALUES (?)", (person_name,))
                new_person_map[label_id] = cursor.lastrowid

        for i, label in enumerate(clt.labels_):
            if label != -1:
                face_id = unmatched_ids[i]
                cluster_id = new_person_map[label]
                cursor.execute(
                    "UPDATE faces SET cluster_id = ? WHERE id = ?",
                    (int(cluster_id), int(face_id)),
                )

    conn.commit()
    conn.close()
    print("Face matching and clustering complete.")
