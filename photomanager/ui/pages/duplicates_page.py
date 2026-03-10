# photomanager/ui/pages/duplicates_page.py
import os
import imagehash
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
)
from PyQt6.QtCore import Qt
from qfluentwidgets import (
    TitleLabel,
    PushButton,
    InfoBar,
    InfoBarPosition,
    FluentIcon,
    PrimaryPushButton,
)

from ..widgets.image_grid import ImageGrid
from ...core import database
from ... import config


class DuplicatesPage(QWidget):
    """Page to find, view, and manage duplicate images."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DuplicatesPage")

        self.duplicate_groups = []  # Holds lists of grouped image dictionaries
        self.current_group_index = -1

        self.setup_ui()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # --- Top Bar ---
        self.top_layout = QHBoxLayout()
        self.title = TitleLabel("Duplicate Finder", self)
        self.top_layout.addWidget(self.title)

        self.top_layout.addStretch()

        self.scan_btn = PushButton(FluentIcon.SEARCH, "Find Duplicates", self)
        self.scan_btn.clicked.connect(self.load_duplicates)
        self.top_layout.addWidget(self.scan_btn)
        self.main_layout.addLayout(self.top_layout)

        # --- Splitter (Master-Detail View) ---
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: List of Groups
        self.group_list = QListWidget(self)
        self.group_list.setStyleSheet(
            "QListWidget { border: 1px solid #333; border-radius: 5px; }"
        )
        self.group_list.currentRowChanged.connect(self.display_selected_group)
        self.splitter.addWidget(self.group_list)

        # Right: Image Grid + Actions
        self.right_widget = QWidget()
        self.right_layout = QVBoxLayout(self.right_widget)
        self.right_layout.setContentsMargins(0, 0, 0, 0)

        self.image_grid = ImageGrid(self)
        self.right_layout.addWidget(self.image_grid)

        # Action Buttons (hidden until a group is selected)
        self.action_layout = QHBoxLayout()
        self.action_layout.addStretch()
        self.smart_delete_btn = PrimaryPushButton(
            FluentIcon.DELETE, "Smart Clean (Keep 1st, Delete Rest)", self
        )
        self.smart_delete_btn.clicked.connect(self.smart_delete_current_group)
        self.smart_delete_btn.hide()
        self.action_layout.addWidget(self.smart_delete_btn)
        self.right_layout.addLayout(self.action_layout)

        self.splitter.addWidget(self.right_widget)
        self.splitter.setSizes([300, 900])
        self.main_layout.addWidget(self.splitter)

    def load_duplicates(self):
        """Scans the database and groups images using AI Embeddings (Cosine Similarity)."""
        from sklearn.neighbors import NearestNeighbors
        import numpy as np

        self.group_list.clear()
        self.image_grid.populate_grid([])
        self.smart_delete_btn.hide()
        self.duplicate_groups = []

        conn = database.get_db_connection()
        try:
            # Fetch images that have an AI embedding
            cursor = conn.execute(
                "SELECT id, path, filename, thumbnail_path, ai_embedding FROM images WHERE ai_embedding IS NOT NULL"
            )
            images = [dict(row) for row in cursor.fetchall()]

            if not images:
                return

            # Extract the numpy arrays for Scikit-Learn
            embeddings = np.array([img["ai_embedding"] for img in images])

            # Fit NearestNeighbors. metric="cosine" measures semantic similarity.
            # We look for the 5 closest neighbors for every image.
            nbrs = NearestNeighbors(
                n_neighbors=min(5, len(images)), metric="cosine"
            ).fit(embeddings)
            distances, indices = nbrs.kneighbors(embeddings)

            visited = set()

            for i in range(len(images)):
                if images[i]["id"] in visited:
                    continue

                current_group = [images[i]]
                visited.add(images[i]["id"])

                # Check neighbors (skip j=0 because that is the image itself)
                for j in range(1, len(indices[i])):
                    neighbor_idx = indices[i][j]
                    neighbor_img = images[neighbor_idx]

                    # Cosine distance ranges from 0 (identical) to 1 (orthogonal)
                    # 1 - distance = Cosine Similarity. > 0.95 is highly similar.
                    similarity = 1 - distances[i][j]

                    if similarity > 0.95 and neighbor_img["id"] not in visited:
                        current_group.append(neighbor_img)
                        visited.add(neighbor_img["id"])

                # Only keep groups that have actual duplicates
                if len(current_group) > 1:
                    self.duplicate_groups.append(current_group)

            # Populate UI List
            for idx, group in enumerate(self.duplicate_groups):
                item = QListWidgetItem(f"AI Group {idx + 1} ({len(group)} photos)")
                self.group_list.addItem(item)

            InfoBar.success(
                title="AI Scan Complete",
                content=f"Found {len(self.duplicate_groups)} groups of similar photos.",
                orient=Qt.Orientation.Horizontal,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3000,
                parent=self,
            )

        except Exception as e:
            print(f"Error finding AI duplicates: {e}")
        finally:
            conn.close()

    def display_selected_group(self, index):
        """Shows the images for the selected group in the grid."""
        if 0 <= index < len(self.duplicate_groups):
            self.current_group_index = index
            group_images = self.duplicate_groups[index]
            self.image_grid.populate_grid(group_images)
            self.smart_delete_btn.show()

    def smart_delete_current_group(self):
        """Keeps the first image in the group and deletes all others from disk & DB."""
        if self.current_group_index < 0:
            return

        group = self.duplicate_groups[self.current_group_index]
        if len(group) <= 1:
            return

        # Confirm with user before permanently deleting files
        reply = QMessageBox.warning(
            self,
            "Confirm Deletion",
            f"This will permanently delete {len(group) - 1} file(s) from your hard drive.\nAre you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.No:
            return

        # The first item is kept, the rest are deleted
        keep_image = group[0]
        images_to_delete = group[1:]

        conn = database.get_db_connection()
        cursor = conn.cursor()
        deleted_count = 0

        for img in images_to_delete:
            try:
                # 1. Delete from Hard Drive
                if os.path.exists(img["path"]):
                    os.remove(img["path"])

                # 2. Delete from Database (Foreign keys handle cascade deletes for faces/tags)
                cursor.execute("DELETE FROM images WHERE id = ?", (img["id"],))
                deleted_count += 1
            except Exception as e:
                print(f"Failed to delete {img['path']}: {e}")

        conn.commit()
        conn.close()

        InfoBar.success(
            title="Cleanup Successful",
            content=f"Deleted {deleted_count} duplicate file(s).",
            orient=Qt.Orientation.Horizontal,
            position=InfoBarPosition.BOTTOM_RIGHT,
            duration=3000,
            parent=self,
        )

        # Refresh the scan to remove the handled group
        self.load_duplicates()
