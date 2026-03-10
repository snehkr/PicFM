# photomanager/core/database.py

import sqlite3
import numpy as np
import io
from .. import config


def adapt_array(arr):
    out = io.BytesIO()
    np.save(out, arr)
    out.seek(0)
    return sqlite3.Binary(out.read())


def convert_array(text):
    out = io.BytesIO(text)
    out.seek(0)
    return np.load(out)


sqlite3.register_adapter(np.ndarray, adapt_array)
sqlite3.register_converter("ARRAY", convert_array)


def get_db_connection():
    conn = sqlite3.connect(config.DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    # Enforce foreign keys and enable Write-Ahead Logging for faster concurrency
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def init_db():
    """Initializes the database with the required schema and indexes."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Images table - ADD the thumbnail_path column
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT NOT NULL UNIQUE,
        filename TEXT NOT NULL,
        file_hash TEXT NOT NULL,
        phash TEXT,
        date_taken TEXT,
        camera_model TEXT,
        gps_lat REAL,
        gps_lon REAL,
        category TEXT,
        last_modified REAL NOT NULL,
        thumbnail_path TEXT,
        ai_embedding ARRAY
    )
    """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_images_path ON images (path)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_images_category ON images (category)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_images_date_taken ON images (date_taken)"
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS faces (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        image_id INTEGER,
        bbox TEXT NOT NULL,
        embedding ARRAY,
        cluster_id INTEGER,
        FOREIGN KEY (image_id) REFERENCES images (id) ON DELETE CASCADE,
        FOREIGN KEY (cluster_id) REFERENCES people (id) ON DELETE SET NULL
    )
    """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_faces_image_id ON faces (image_id)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_faces_cluster_id ON faces (cluster_id)"
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS people (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
    """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_people_name ON people (name)")

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS image_tags (
        image_id INTEGER,
        tag_id INTEGER,
        PRIMARY KEY (image_id, tag_id),
        FOREIGN KEY (image_id) REFERENCES images (id) ON DELETE CASCADE,
        FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
    )
    """
    )

    conn.commit()
    conn.close()
    print("Database initialized successfully.")
