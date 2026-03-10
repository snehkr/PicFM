# photomanager/ui/pages/all_photos_page.py
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QSplitter
from PyQt6.QtCore import Qt
from qfluentwidgets import PushButton, FluentIcon

from ..widgets.image_grid import ImageGrid
from ..widgets.info_panel import InfoPanel
from ...core import database


class AllPhotosPage(QWidget):
    """The page that displays the main image grid and info panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AllPhotosPage")

        self.main_layout = QVBoxLayout(self)

        # --- Top Control Bar ---
        self.controls_layout = QHBoxLayout()
        self.scan_button = PushButton(FluentIcon.FOLDER_ADD, "Scan Folder", self)

        # Connect to MainWindow's method safely
        if hasattr(self.parent(), "scan_folder"):
            self.scan_button.clicked.connect(self.parent().scan_folder)

        self.controls_layout.addWidget(self.scan_button)

        # Clear Filter Button
        self.clear_filter_btn = PushButton(FluentIcon.CLOSE, "Clear Filter", self)
        self.clear_filter_btn.clicked.connect(self.clear_filter)
        self.clear_filter_btn.hide()  # Hidden by default
        self.controls_layout.addWidget(self.clear_filter_btn)

        self.controls_layout.addStretch()
        self.main_layout.addLayout(self.controls_layout)

        # --- Main Content Area with Splitter ---
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        self.image_grid = ImageGrid(self)
        self.splitter.addWidget(self.image_grid)

        self.info_panel = InfoPanel(self)
        self.splitter.addWidget(self.info_panel)

        self.splitter.setSizes([900, 300])
        self.main_layout.addWidget(self.splitter)

        self.image_grid.image_selected.connect(self.on_image_selected)

    def clear_filter(self):
        """Removes the person filter and loads all images."""
        self.load_images()

    def on_image_selected(self, image_id):
        conn = database.get_db_connection()
        try:
            cursor = conn.execute(
                "SELECT filename, date_taken, camera_model, gps_lat, gps_lon FROM images WHERE id = ?",
                (image_id,),
            )
            image_data = cursor.fetchone()
            if image_data:
                self.info_panel.update_info(dict(image_data))
            else:
                self.info_panel.update_info(None)
        except Exception as e:
            print(f"Error fetching image metadata: {e}")
        finally:
            conn.close()

    def load_images(self, category=None, person_id=None):
        """Loads images, optionally filtered by category or a specific person."""
        self.info_panel.update_info(None)

        conn = database.get_db_connection()
        try:
            params = []

            # If a person_id is provided, join with the faces table
            if person_id is not None:
                self.clear_filter_btn.show()  # Show the clear button
                query = """
                    SELECT DISTINCT i.id, i.path, i.filename, i.thumbnail_path 
                    FROM images i
                    JOIN faces f ON i.id = f.image_id
                    WHERE f.cluster_id = ?
                    ORDER BY i.date_taken DESC
                """
                params.append(person_id)
            else:
                self.clear_filter_btn.hide()  # Hide the clear button
                query = "SELECT id, path, filename, thumbnail_path FROM images"
                if category:
                    query += " WHERE category = ?"
                    params.append(category)
                query += " ORDER BY date_taken DESC"

            cursor = conn.execute(query, tuple(params))
            images = [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error loading images from database: {e}")
            images = []
        finally:
            conn.close()

        self.image_grid.populate_grid(images)
