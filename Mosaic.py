
import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QVBoxLayout, QHBoxLayout, QWidget, QAction, QFileDialog, QMenuBar, QFrame, QLabel
)
from PyQt5.QtGui import QPixmap, QPen
from PyQt5.QtCore import Qt
#111222
class DraggableScalablePixmapItem(QGraphicsPixmapItem):
    def __init__(self, pixmap):
        super().__init__(pixmap)
        self.setFlag(QGraphicsPixmapItem.ItemIsMovable, True)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setAcceptDrops(True)
        self.setTransformationMode(Qt.SmoothTransformation)
        self.setZValue(0)

    def wheelEvent(self, event):
        # Scale up or down with the mouse wheel (PyQt5: use delta())
        delta = event.delta() if hasattr(event, 'delta') else event.angleDelta().y()
        factor = 1.15 if delta > 0 else 0.87
        self.setScale(self.scale() * factor)
        event.accept()

    def hoverEnterEvent(self, event):
        self.setCursor(Qt.SizeAllCursor)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setCursor(Qt.ArrowCursor)
        super().hoverLeaveEvent(event)

class ImageEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt Image Editor")
        self.setGeometry(100, 100, 2000, 1100)

        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left task bar
        self.task_bar = QFrame()
        self.task_bar.setFrameShape(QFrame.StyledPanel)
        self.task_bar.setFixedWidth(120)
        main_layout.addWidget(self.task_bar)

        # Canvas area (graphics view)
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setBackgroundBrush(Qt.white)
        main_layout.addWidget(self.view)

        # Top menu bar
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        # File menu
        file_menu = menu_bar.addMenu("File")
        open_action = QAction("Open Image", self)
        open_action.triggered.connect(self.open_image)
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Project menu
        project_menu = menu_bar.addMenu("Project")
        # (Add project actions here as needed)

        # Placeholder for loaded image
        self.image_item = None

    def open_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                # Resize to fit within 1000x1000, keeping aspect ratio
                max_w, max_h = 1000, 1000
                orig_w, orig_h = pixmap.width(), pixmap.height()
                ratio = min(max_w / orig_w, max_h / orig_h, 1.0)
                new_w, new_h = int(orig_w * ratio), int(orig_h * ratio)
                scaled_pixmap = pixmap.scaled(new_w, new_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                # Remove previous image and frame if they exist
                if self.image_item:
                    self.scene.removeItem(self.image_item)
                if hasattr(self, 'frame_item') and self.frame_item:
                    self.scene.removeItem(self.frame_item)
                # Add image inside the frame, centered
                x = 0 + (1000 - new_w) // 2
                y = 0 + (1000 - new_h) // 2
                self.image_item = DraggableScalablePixmapItem(scaled_pixmap)
                self.image_item.setPos(x, y)
                self.scene.addItem(self.image_item)
                # Draw 1000x1000 frame at (0,0) and ensure it's on top
                from PyQt5.QtGui import QPen
                pen = QPen(Qt.black)
                pen.setWidth(3)
                self.frame_item = self.scene.addRect(0, 0, 1000, 1000, pen)
                self.frame_item.setZValue(1)
                # Set scene rect to show the frame and image
                self.view.setSceneRect(0, 0, 1000, 1000)
                self.view.fitInView(0, 0, 1000, 1000, Qt.KeepAspectRatio)

def main():
    app = QApplication(sys.argv)
    editor = ImageEditor()
    editor.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()


