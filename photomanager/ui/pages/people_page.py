# photomanager/ui/pages/people_page.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from qfluentwidgets import TitleLabel, SearchLineEdit, InfoBar, InfoBarPosition
from PyQt6.QtCore import Qt

from ..widgets.image_grid import ImageGrid
from ...core import database


class PeoplePage(QWidget):
    """Displays clusters of recognized faces."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PeoplePage")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # --- Top Bar (Title & Search) ---
        self.top_layout = QHBoxLayout()
        self.title = TitleLabel("People & Faces", self)
        self.top_layout.addWidget(self.title)

        self.top_layout.addStretch()

        self.search_box = SearchLineEdit(self)
        self.search_box.setPlaceholderText("Search people...")
        self.search_box.setFixedWidth(250)
        self.search_box.textChanged.connect(self.filter_people)
        self.top_layout.addWidget(self.search_box)

        self.main_layout.addLayout(self.top_layout)

        # --- Main Grid ---
        # We reuse our highly optimized ImageGrid!
        self.image_grid = ImageGrid(self)
        self.main_layout.addWidget(self.image_grid)

        # Cache for our data so searching is instant
        self._all_people_data = []

        # --- Connections ---
        self.image_grid.image_selected.connect(self.on_person_clicked)

    def load_people(self):
        """Loads unique people from the database and grabs a representative thumbnail."""
        conn = database.get_db_connection()
        try:
            # We map p.name to 'filename' so our ImageGrid knows how to display the text
            query = """
                SELECT p.id, p.name as filename, i.thumbnail_path, i.path
                FROM people p
                JOIN faces f ON p.id = f.cluster_id
                JOIN images i ON f.image_id = i.id
                GROUP BY p.id
                ORDER BY p.name ASC
            """
            cursor = conn.execute(query)
            self._all_people_data = [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error loading people from database: {e}")
            self._all_people_data = []
        finally:
            conn.close()

        self.image_grid.populate_grid(self._all_people_data)

    def filter_people(self, text):
        """Filters the grid instantly based on the search box."""
        if not text:
            self.image_grid.populate_grid(self._all_people_data)
            return

        filtered = [
            p for p in self._all_people_data if text.lower() in p["filename"].lower()
        ]
        self.image_grid.populate_grid(filtered)

    def on_person_clicked(self, person_id):
        """Action when a person's profile is clicked."""
        person_name = next(
            (p["filename"] for p in self._all_people_data if p["id"] == person_id),
            "Unknown",
        )

        # Retrieve the top-level MainWindow instance safely
        main_window = self.window()

        # Trigger the navigation and filtering
        if hasattr(main_window, "filter_by_person"):
            main_window.filter_by_person(person_id, person_name)
