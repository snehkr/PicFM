# photomanager/core/scanner.py
import os
import hashlib
import sqlite3
from concurrent.futures import ProcessPoolExecutor, as_completed
from . import database, exif_utils, duplicate_finder, face_analyzer, thumbnailer
from .. import config


def get_file_hash(filepath):
    sha256 = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    except (IOError, OSError) as e:
        print(f"Error reading file {filepath}: {e}")
        return None


def process_image(image_path):
    """
    Full processing pipeline for a single image, now including thumbnail generation.
    """
    try:
        # ...
        file_hash = get_file_hash(image_path)
        if not file_hash:
            return "Skipped (hashing failed)", image_path

        # *** GENERATE THUMBNAIL ***
        thumbnail_path = thumbnailer.create_thumbnail(image_path, file_hash)

        phash = duplicate_finder.calculate_phash(image_path)
        ai_embedding = duplicate_finder.get_ai_embedding(image_path)

        exif_data = exif_utils.get_exif_data(image_path)
        faces, category = face_analyzer.analyze_faces(image_path)

        image_data = {
            "path": image_path,
            "filename": os.path.basename(image_path),
            "file_hash": file_hash,
            "thumbnail_path": thumbnail_path,
            "phash": phash,
            "ai_embedding": ai_embedding,
            "date_taken": exif_data.get("date_taken"),
            "camera_model": exif_data.get("camera_model"),
            "gps_lat": exif_data.get("gps_lat"),
            "gps_lon": exif_data.get("gps_lon"),
            "category": category,
            "last_modified": os.path.getmtime(image_path),
            "faces": faces,
        }
        return "Processed", image_data
    except Exception as e:
        import traceback

        return (
            "Error",
            f"ERROR processing {os.path.basename(image_path)}: {e}\n{traceback.format_exc()}",
        )


def update_database_batch(results):
    """
    Updates the database with a batch of processed image data.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()

    for result_type, data in results:
        if result_type == "Processed":
            try:
                # --- Skip unchanged images ---
                existing = cursor.execute(
                    "SELECT last_modified FROM images WHERE path=?", (data["path"],)
                ).fetchone()

                if existing and existing["last_modified"] == data["last_modified"]:
                    continue

                # --- Insert / update image ---
                cursor.execute(
                    """
                    INSERT INTO images (path, filename, file_hash, phash, ai_embedding, date_taken, camera_model, gps_lat, gps_lon, category, last_modified, thumbnail_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(path) DO UPDATE SET
                    file_hash=excluded.file_hash, phash=excluded.phash, ai_embedding=excluded.ai_embedding,date_taken=excluded.date_taken, camera_model=excluded.camera_model,
                    gps_lat=excluded.gps_lat, gps_lon=excluded.gps_lon, category=excluded.category, last_modified=excluded.last_modified, thumbnail_path=excluded.thumbnail_path
                    """,
                    (
                        data["path"],
                        data["filename"],
                        data["file_hash"],
                        data["phash"],
                        data["ai_embedding"],
                        data["date_taken"],
                        data["camera_model"],
                        data["gps_lat"],
                        data["gps_lon"],
                        data["category"],
                        data["last_modified"],
                        data["thumbnail_path"],
                    ),
                )

                cursor.execute("SELECT id FROM images WHERE path=?", (data["path"],))
                image_id_row = cursor.fetchone()
                if not image_id_row:
                    continue
                image_id = image_id_row["id"]

                cursor.execute("DELETE FROM faces WHERE image_id = ?", (image_id,))
                for face in data["faces"]:
                    cursor.execute(
                        "INSERT INTO faces (image_id, bbox, embedding) VALUES (?, ?, ?)",
                        (image_id, str(face["bbox"]), face["embedding"]),
                    )
            except sqlite3.Error as e:
                print(f"Database error for {data['path']}: {e}")

    conn.commit()
    conn.close()


def scan_directory(path, progress_callback, worker):
    """
    Scans a directory recursively for images and processes them in parallel.
    """
    image_paths = []
    for root, _, files in os.walk(path):
        for file in files:
            if file.lower().endswith(tuple(config.SUPPORTED_EXTENSIONS)):
                image_paths.append(os.path.join(root, file))

    total_images = len(image_paths)
    if total_images == 0:
        progress_callback.emit(100, "No images found.")
        return

    processed_count = 0
    batch_size = 100
    results_batch = []

    with ProcessPoolExecutor(max_workers=config.WORKER_PROCESSES) as executor:
        futures = {executor.submit(process_image, p): p for p in image_paths}

        for future in as_completed(futures):
            # Before processing each result, check if we've been told to stop.
            if not worker.is_running:
                # If so, attempt to cancel remaining tasks and exit gracefully.
                executor.shutdown(wait=False, cancel_futures=True)
                print("Scan cancelled.")
                return

            path = futures[future]
            try:
                result_type, data = future.result()
                results_batch.append((result_type, data))

                if len(results_batch) >= batch_size:
                    update_database_batch(results_batch)
                    results_batch = []

                if result_type == "Error":
                    print(data)

            except Exception as exc:
                print(f"{path} generated an exception: {exc}")

            processed_count += 1
            progress = int((processed_count / total_images) * 100)
            progress_callback.emit(progress, f"Processing: {os.path.basename(path)}")

    if results_batch and worker.is_running:
        update_database_batch(results_batch)

    if worker.is_running:
        progress_callback.emit(100, "Scanning complete. Clustering faces...")
        try:
            face_analyzer.run_face_clustering()
            progress_callback.emit(100, "All tasks finished.")
        except Exception as e:
            progress_callback.emit(100, f"Error during face clustering: {e}")
