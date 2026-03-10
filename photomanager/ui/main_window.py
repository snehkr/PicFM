# photomanager/ui/main_window.py
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread
from qfluentwidgets import (
    FluentWindow,
    FluentIcon,
    StateToolTip,
    InfoBar,
    InfoBarPosition,
    NavigationItemPosition,
    setTheme,
    Theme,
    isDarkTheme,
)

from .pages.all_photos_page import AllPhotosPage
from .pages.people_page import PeoplePage
from .pages.duplicates_page import DuplicatesPage
from ..core import scanner


class ScannerWorker(QObject):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal()

    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path
        self.is_running = True

    def run(self):
        if self.is_running:
            scanner.scan_directory(self.folder_path, self.progress, self)
        self.finished.emit()

    def stop(self):
        self.is_running = False


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setObjectName("MainWindow")
        self.setWindowTitle("Photo Manager 2.0")

        # --- Create Pages ---
        self.all_photos_page = AllPhotosPage(self)
        self.people_page = PeoplePage(self)
        self.duplicates_page = DuplicatesPage(self)

        self.state_tooltip = None  # To hold our modern progress notification

        self.init_navigation()
        self.init_window()

        # Load initial data into pages
        self.all_photos_page.load_images()
        self.people_page.load_people()

    def init_navigation(self):
        self.addSubInterface(self.all_photos_page, FluentIcon.PHOTO, "All Photos")
        self.addSubInterface(self.people_page, FluentIcon.PEOPLE, "People")
        self.addSubInterface(self.duplicates_page, FluentIcon.COPY, "Duplicates")

        # Add a modern Theme Toggle button at the bottom of the sidebar
        self.navigationInterface.addItem(
            routeKey="ThemeToggle",
            icon=FluentIcon.BRUSH,
            text="Toggle Theme",
            onClick=self.toggle_theme,
            position=NavigationItemPosition.BOTTOM,
        )

    def init_window(self):
        self.resize(1280, 720)
        desktop = self.screen().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

    def toggle_theme(self):
        """Flips between Dark and Light mode dynamically."""
        if isDarkTheme():
            setTheme(Theme.LIGHT)
        else:
            setTheme(Theme.DARK)

    def scan_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder to Scan")
        if folder_path:
            # Modern UI: Non-blocking state tooltip instead of ugly modal dialog
            if self.state_tooltip:
                self.state_tooltip.setContent("Scanning already in progress...")
                self.state_tooltip.setState(True)
                self.state_tooltip = None

            self.state_tooltip = StateToolTip(
                "Scanning Folder", "Initializing...", self
            )
            self.state_tooltip.move(self.state_tooltip.getSuitablePos())
            self.state_tooltip.show()

            self.thread = QThread()
            self.worker = ScannerWorker(folder_path)
            self.worker.moveToThread(self.thread)

            self.thread.started.connect(self.worker.run)
            self.worker.finished.connect(self.on_scan_finished)
            self.worker.progress.connect(self.update_progress)

            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.thread.finished.connect(lambda: setattr(self, "thread", None))

            self.thread.start()
            self.all_photos_page.scan_button.setEnabled(False)

    def update_progress(self, value, message):
        """Updates the modern tooltip without freezing the app."""
        if self.state_tooltip:
            # Keep title static, update the content with the current file/status
            self.state_tooltip.setContent(f"{value}% - {message}")

    def on_scan_finished(self):
        # Gracefully transition the tooltip to a success state
        if self.state_tooltip:
            self.state_tooltip.setContent("Scan Complete!")
            self.state_tooltip.setState(True)
            self.state_tooltip = None

        self.all_photos_page.scan_button.setEnabled(True)

        # Show a beautiful modern toast notification
        InfoBar.success(
            title="Scan Finished",
            content="Folder has been successfully imported and processed.",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=4000,
            parent=self,
        )

        # Refresh both pages after a scan
        self.all_photos_page.load_images()
        self.people_page.load_people()

    def closeEvent(self, event):
        try:
            if hasattr(self, "thread") and self.thread:
                if self.thread.isRunning():
                    print("Closing... Telling worker to stop.")
                    self.worker.stop()
                    self.thread.quit()
                    self.thread.wait(1000)
        except RuntimeError:
            # QThread object already deleted by Qt
            pass

        event.accept()

    def filter_by_person(self, person_id, person_name):
        """Switches to the All Photos page and filters by the selected person."""
        # 1. Switch the UI tab to the All Photos page
        self.switchTo(self.all_photos_page)

        # 2. Tell the page to load only photos of this person
        self.all_photos_page.load_images(person_id=person_id)

        # 3. Show a nice toast notification
        InfoBar.success(
            title="Gallery Filtered",
            content=f"Showing all photos of {person_name}.",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3000,
            parent=self,
        )
