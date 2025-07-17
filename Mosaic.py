import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QMenuBar, QMenu, QAction, QVBoxLayout, QWidget, QLabel, QFileDialog, QHBoxLayout, QPushButton, QStackedWidget
from PyQt5.QtGui import QPixmap, QPainter
from PyQt5.QtCore import Qt, QPoint

class DraggableLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dragging = False
        self.offset = QPoint()
        self.image_position = QPoint(0, 0)
        self._pixmap = None
        self._original_pixmap = None
        self.scale_factor = 1.0

    def setPixmap(self, pixmap):
        self._original_pixmap = pixmap
        self._pixmap = pixmap
        self.image_position = QPoint(0, 0)
        self.scale_factor = 1.0
        self.update()

    def wheelEvent(self, event):
        if self._pixmap:
            # Check if mouse is within image bounds
            mouse_pos = event.pos()
            image_rect = self._pixmap.rect().translated(self.image_position)
            if image_rect.contains(mouse_pos):
                # Scale factor: increase/decrease by 2% per wheel step
                if event.angleDelta().y() > 0:
                    self.scale_factor *= 1.02
                else:
                    self.scale_factor *= 0.98

            # Limit scaling
            self.scale_factor = max(0.1, min(self.scale_factor, 5.0))
            
            # Scale the pixmap
            new_width = int(self._original_pixmap.width() * self.scale_factor)
            new_height = int(self._original_pixmap.height() * self.scale_factor)
            self._pixmap = self._original_pixmap.scaled(new_width, new_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            self.update()

    def paintEvent(self, event):
        if self._pixmap:
            painter = QPainter(self)
            painter.drawPixmap(self.image_position, self._pixmap)

    def mousePressEvent(self, event):
        if self._pixmap and event.button() == Qt.LeftButton:
            # Check if click is within image bounds
            click_pos = event.pos()
            image_rect = self._pixmap.rect().translated(self.image_position)
            if image_rect.contains(click_pos):
                self.dragging = True
                self.offset = click_pos - self.image_position

    def mouseMoveEvent(self, event):
        if self.dragging and self._pixmap:
            new_pos = event.pos() - self.offset
            self.image_position = new_pos
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False

class ImageEditor(QMainWindow):
    def __init__(self):
        super().__init__()

        # Set window size
        self.setWindowTitle("Image Editor")
        self.setGeometry(100, 100, 2000, 1100)

        # Create central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Create layout
        self.main_layout = QHBoxLayout()
        self.central_widget.setLayout(self.main_layout)

        # Add left sidebar with fixed width
        self.left_sidebar_widget = QWidget()
        self.left_sidebar_widget.setFixedWidth(100)
        self.left_sidebar_layout = QVBoxLayout()
        self.left_sidebar_widget.setLayout(self.left_sidebar_layout)
        self.main_layout.addWidget(self.left_sidebar_widget)

        # Add task bar buttons to the left sidebar
        task_button_1 = QPushButton("Task 1")
        self.left_sidebar_layout.addWidget(task_button_1)

        task_button_2 = QPushButton("Task 2")
        self.left_sidebar_layout.addWidget(task_button_2)

        task_button_3 = QPushButton("Task 3")
        self.left_sidebar_layout.addWidget(task_button_3)

        # Add stacked widget for canvases
        self.canvas_stack = QStackedWidget()
        self.main_layout.addWidget(self.canvas_stack)

        # First canvas
        self.canvas1 = DraggableLabel("No image loaded on Canvas 1")
        self.canvas1.setStyleSheet("border: 1px solid black;")
        self.canvas1.setAlignment(Qt.AlignCenter)
        self.canvas_stack.addWidget(self.canvas1)

        # Second canvas
        self.canvas2 = QLabel("Canvas 2")
        self.canvas2.setStyleSheet("border: 1px solid black;")
        self.canvas2.setAlignment(Qt.AlignCenter)
        self.canvas_stack.addWidget(self.canvas2)

        # Add button to switch between canvases
        switch_canvas_button = QPushButton("Switch Canvas")
        switch_canvas_button.clicked.connect(self.switch_canvas)
        self.left_sidebar_layout.addWidget(switch_canvas_button)

        # Create menu bar
        self.create_menu_bar()

        # Add black frame to canvas1
        self.frame1 = QWidget()
        self.frame1.setFixedSize(1000, 1000)
        self.frame1.setStyleSheet("border: 5px solid black;")

        # Create layout for canvas1
        canvas1_layout = QVBoxLayout()
        canvas1_layout.addWidget(self.frame1)
        canvas1_layout.setAlignment(Qt.AlignCenter)
        self.canvas1.setLayout(canvas1_layout)

    def create_menu_bar(self):
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        # File menu
        file_menu = QMenu("File", self)
        menu_bar.addMenu(file_menu)

        # Open action
        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_image)
        file_menu.addAction(open_action)

    def switch_canvas(self):
        current_index = self.canvas_stack.currentIndex()
        next_index = (current_index + 1) % self.canvas_stack.count()
        self.canvas_stack.setCurrentIndex(next_index)

    def open_image(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Image File", "", "Images (*.png *.xpm *.jpg *.jpeg *.bmp);;All Files (*)", options=options)
        if file_path:
            pixmap = QPixmap(file_path)
            self.frame1.setStyleSheet("border: 5px solid black;")  # Keep the black border
            self.frame1.setFixedSize(1000, 1000)  # Ensure the frame size remains 1000x1000
            self.canvas1.setPixmap(pixmap)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = ImageEditor()
    editor.show()
    sys.exit(app.exec_())