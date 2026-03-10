# photomanager/ui/widgets/image_grid.py
import os
from PyQt6.QtWidgets import QListView, QStyledItemDelegate, QStyle
from PyQt6.QtGui import QPixmap, QPainter, QColor, QTextOption
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QModelIndex, QRectF, QAbstractListModel

from ... import config

ImageIdRole = Qt.ItemDataRole.UserRole + 1
ImagePathRole = Qt.ItemDataRole.UserRole + 2
ImageFilenameRole = Qt.ItemDataRole.UserRole + 3


class ImageListModel(QAbstractListModel):
    """Highly optimized virtualized model for thousands of images."""

    def __init__(self, images=None, parent=None):
        super().__init__(parent)
        self._images = images or []

    def data(self, index, role):
        if not index.isValid() or not (0 <= index.row() < len(self._images)):
            return None

        image_info = self._images[index.row()]

        if role == ImageIdRole:
            return image_info["id"]
        elif role == ImagePathRole:
            return image_info.get("thumbnail_path")
        elif role == ImageFilenameRole:
            return image_info["filename"]
        elif role == Qt.ItemDataRole.ToolTipRole:
            return image_info["path"]
        return None

    def rowCount(self, index=QModelIndex()):
        return len(self._images)

    def update_data(self, new_images):
        self.beginResetModel()
        self._images = new_images
        self.endResetModel()


class ImageDelegate(QStyledItemDelegate):
    """Paints each item in the view for a rich display."""

    def paint(self, painter: QPainter, option, index: QModelIndex):
        pixmap_path = index.data(ImagePathRole)
        filename = index.data(ImageFilenameRole)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # --- Draw Background and Selection ---
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor("#0078d7"))
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(option.rect, QColor("#444444"))

        # --- Draw Thumbnail ---
        if pixmap_path and os.path.exists(pixmap_path):
            pixmap = QPixmap(pixmap_path)
            target_rect = option.rect.adjusted(5, 5, -5, -35)
            scaled_pixmap = pixmap.scaled(
                target_rect.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = target_rect.x() + (target_rect.width() - scaled_pixmap.width()) // 2
            y = target_rect.y() + (target_rect.height() - scaled_pixmap.height()) // 2
            painter.drawPixmap(x, y, scaled_pixmap)

        # --- Draw Filename ---
        text_rect = option.rect.adjusted(5, option.rect.height() - 30, -5, -5)
        text_option = QTextOption()
        text_option.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_option.setWrapMode(QTextOption.WrapMode.WordWrap)

        painter.setPen(QColor("white"))
        painter.drawText(QRectF(text_rect), filename, text_option)
        painter.restore()

    def sizeHint(self, option, index):
        return QSize(config.THUMBNAIL_SIZE[0] + 20, config.THUMBNAIL_SIZE[1] + 40)


class ImageGrid(QListView):
    """A high-performance, virtualized view for displaying thousands of thumbnails."""

    image_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = ImageListModel([], self)
        self.setModel(self.model)
        self.setItemDelegate(ImageDelegate(self))

        self.setViewMode(QListView.ViewMode.IconMode)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setMovement(QListView.Movement.Static)
        self.setSpacing(10)
        self.setUniformItemSizes(True)

        self.clicked.connect(self.on_item_clicked)

    def populate_grid(self, images: list[dict]):
        self.model.update_data(images)

    def on_item_clicked(self, index: QModelIndex):
        image_id = self.model.data(index, ImageIdRole)
        if image_id:
            self.image_selected.emit(image_id)
