# main.py

import os
import sys
import multiprocessing
from PyQt6.QtWidgets import QApplication
from qfluentwidgets import setTheme, Theme

from photomanager.ui.main_window import MainWindow
from photomanager.core import database

# Disable QFluentWidgets tips (optional)
os.environ["QFLUENTWIDGETS_DISABLE_TIPS"] = "1"


def main():
    # 1. Initialize the database schema if it doesn't exist
    database.init_db()

    # 2. Create and run the Qt Application
    app = QApplication(sys.argv)

    # Apply a modern theme (Light / Dark / Auto)
    setTheme(Theme.DARK)

    window = MainWindow()
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    # Required for multiprocessing on Windows
    multiprocessing.freeze_support()

    # Recommended start method for stability
    multiprocessing.set_start_method("spawn", force=True)

    sys.exit(main())
