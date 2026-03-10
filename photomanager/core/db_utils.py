# photomanager/core/db_utils.py

import imagehash
from collections import defaultdict
from . import database


def get_all_people_summary():
    """
    Fetches all people with a thumbnail and a count of their photos.
    """
    conn = database.get_db_connection()
    # Get all people
    people = conn.execute("SELECT id, name FROM people ORDER BY name").fetchall()

    people_summary = []
    for person in people:
        # Find the first face's image for this person to use as a thumbnail
        thumb_row = conn.execute(
            """
            SELECT i.thumbnail_path
            FROM images i
            JOIN faces f ON i.id = f.image_id
            WHERE f.cluster_id = ? AND i.thumbnail_path IS NOT NULL
            LIMIT 1
        """,
            (person["id"],),
        ).fetchone()

        # Get the count of unique photos for this person
        photo_count_row = conn.execute(
            """
            SELECT COUNT(DISTINCT image_id) as count
            FROM faces
            WHERE cluster_id = ?
        """,
            (person["id"],),
        ).fetchone()

        people_summary.append(
            {
                "id": person["id"],
                "name": person["name"],
                "thumbnail_path": thumb_row["thumbnail_path"] if thumb_row else None,
                "photo_count": photo_count_row["count"] if photo_count_row else 0,
            }
        )

    conn.close()
    return people_summary


def get_images_for_person(person_id: int):
    """
    Fetches all images that contain a specific person.
    """
    conn = database.get_db_connection()
    images = conn.execute(
        """
        SELECT DISTINCT i.id, i.path, i.filename, i.thumbnail_path
        FROM images i
        JOIN faces f ON i.id = f.image_id
        WHERE f.cluster_id = ?
        ORDER BY i.date_taken DESC
    """,
        (person_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in images]


def update_person_name(person_id: int, new_name: str):
    """
    Updates the name of a person/cluster in the database.
    """
    conn = database.get_db_connection()
    try:
        conn.execute("UPDATE people SET name = ? WHERE id = ?", (new_name, person_id))
        conn.commit()
        conn.close()
        return True, "Name updated successfully."
    except conn.IntegrityError:
        conn.close()
        return False, "This name is already in use."
    except Exception as e:
        conn.close()
        return False, f"An error occurred: {e}"


# --- Tagging Functions ---
def get_tags_for_image(image_id: int):
    """Fetches all tags for a given image."""
    conn = database.get_db_connection()
    cursor = conn.execute(
        """
        SELECT t.name FROM tags t
        JOIN image_tags it ON t.id = it.tag_id
        WHERE it.image_id = ?
    """,
        (image_id,),
    )
    tags = [row["name"] for row in cursor.fetchall()]
    conn.close()
    return tags


def get_all_tags():
    """Fetches all unique tags from the database."""
    conn = database.get_db_connection()
    cursor = conn.execute("SELECT name FROM tags ORDER BY name")
    all_tags = [row["name"] for row in cursor.fetchall()]
    conn.close()
    return all_tags


def add_tag_to_image(image_id: int, tag_name: str):
    """Adds a tag to an image. Creates the tag if it doesn't exist."""
    tag_name = tag_name.strip().lower()
    if not tag_name:
        return

    conn = database.get_db_connection()
    cursor = conn.cursor()

    # Find or create the tag
    cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
    tag = cursor.fetchone()
    if tag:
        tag_id = tag["id"]
    else:
        cursor.execute("INSERT INTO tags (name) VALUES (?)", (tag_name,))
        tag_id = cursor.lastrowid

    # Associate the tag with the image, ignoring if it already exists
    cursor.execute(
        "INSERT OR IGNORE INTO image_tags (image_id, tag_id) VALUES (?, ?)",
        (image_id, tag_id),
    )

    conn.commit()
    conn.close()


def remove_tag_from_image(image_id: int, tag_name: str):
    """Removes a tag from a specific image."""
    conn = database.get_db_connection()
    cursor = conn.cursor()
    # Get tag_id
    cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
    tag = cursor.fetchone()
    if tag:
        tag_id = tag["id"]
        cursor.execute(
            "DELETE FROM image_tags WHERE image_id = ? AND tag_id = ?",
            (image_id, tag_id),
        )
        conn.commit()
    conn.close()


def find_duplicate_sets(threshold: int):
    """
    Finds sets of duplicate or near-duplicate images.
    Returns a list of lists, where each inner list is a group of duplicate image dicts.
    """
    conn = database.get_db_connection()
    # Fetch all images with a perceptual hash
    images = conn.execute(
        "SELECT id, path, filename, phash, thumbnail_path FROM images WHERE phash IS NOT NULL"
    ).fetchall()
    conn.close()

    if not images:
        return []

    hashes = {row["id"]: imagehash.hex_to_hash(row["phash"]) for row in images}
    image_map = {row["id"]: dict(row) for row in images}

    # Use a Disjoint Set Union (DSU) data structure to efficiently group images
    parent = {image_id: image_id for image_id in hashes.keys()}

    def find_set(i):
        if parent[i] == i:
            return i
        parent[i] = find_set(parent[i])
        return parent[i]

    def unite_sets(i, j):
        i = find_set(i)
        j = find_set(j)
        if i != j:
            parent[j] = i

    image_ids = list(hashes.keys())

    # Pre-group by first few bits to reduce comparisons
    prefix_groups = defaultdict(list)
    for image_id in image_ids:
        prefix = str(hashes[image_id])[:4]
        prefix_groups[prefix].append(image_id)

    for group in prefix_groups.values():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                id1 = group[i]
                id2 = group[j]

                if hashes[id1] - hashes[id2] <= threshold:
                    unite_sets(id1, id2)

    # Group images by their set's root parent
    groups = defaultdict(list)
    for image_id in image_ids:
        root = find_set(image_id)
        groups[root].append(image_map[image_id])

    # Return only the groups with more than one image (i.e., actual duplicates)
    return [group for group in groups.values() if len(group) > 1]
