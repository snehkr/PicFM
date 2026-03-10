# photomanager/ui/widgets/info_panel.py
import webbrowser
from PyQt6.QtWidgets import QVBoxLayout, QFrame
from PyQt6.QtCore import Qt
from qfluentwidgets import SubtitleLabel, BodyLabel, FluentIcon, CardWidget, PushButton


class InfoPanel(CardWidget):
    """A sleek side-panel to display image metadata (EXIF) and map links."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(300)
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(20, 20, 20, 20)
        self.vBoxLayout.setSpacing(15)

        # Title
        self.titleLabel = SubtitleLabel("File Information", self)
        self.vBoxLayout.addWidget(self.titleLabel)

        # Metadata Labels
        self.filenameLabel = self._create_info_row("Filename", "-")
        self.dateLabel = self._create_info_row("Date Taken", "-")
        self.cameraLabel = self._create_info_row("Camera", "-")
        self.gpsLabel = self._create_info_row("Location", "-")

        # Map Button (Modern Fluent PushButton)
        self.mapButton = PushButton(FluentIcon.GLOBE, "View on Map", self)
        self.mapButton.clicked.connect(self.open_map)
        self.mapButton.hide()  # Hidden by default
        self.vBoxLayout.addWidget(self.mapButton)

        self.vBoxLayout.addStretch(1)
        self.hide()  # Hidden by default until an image is clicked

        # State variables for coordinates
        self.current_lat = None
        self.current_lon = None

    def _create_info_row(self, title, default_val):
        """Helper to create a neat row with a title and value."""
        row = QFrame(self)
        layout = QVBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        titleLabel = BodyLabel(f"{title}:", self)
        titleLabel.setStyleSheet("color: gray;")

        valueLabel = BodyLabel(default_val, self)
        valueLabel.setWordWrap(True)

        layout.addWidget(titleLabel)
        layout.addWidget(valueLabel)
        self.vBoxLayout.addWidget(row)

        return valueLabel

    def update_info(self, image_data):
        """Populates the panel with data from the database dict."""
        if not image_data:
            self.hide()
            return

        self.filenameLabel.setText(image_data.get("filename", "Unknown"))
        self.dateLabel.setText(image_data.get("date_taken") or "Unknown Date")
        self.cameraLabel.setText(image_data.get("camera_model") or "Unknown Camera")

        self.current_lat = image_data.get("gps_lat")
        self.current_lon = image_data.get("gps_lon")

        if self.current_lat and self.current_lon:
            self.gpsLabel.setText(f"{self.current_lat:.4f}, {self.current_lon:.4f}")
            self.mapButton.show()  # Show button if we have coordinates
        else:
            self.gpsLabel.setText("No GPS Data")
            self.mapButton.hide()  # Hide button if no coordinates

        self.show()

    def open_map(self):
        """Opens the default web browser to the exact GPS coordinates."""
        if self.current_lat and self.current_lon:
            url = f"https://www.google.com/maps/search/?api=1&query={self.current_lat},{self.current_lon}"
            webbrowser.open(url)
