import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QGraphicsScene, 
                           QGraphicsView, QVBoxLayout, QWidget, QMenuBar, 
                           QMenu, QAction, QFileDialog, QHBoxLayout, QPushButton,
                           QGraphicsRectItem, QGraphicsPixmapItem, QLineEdit, QLabel)
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QBrush, QPen, QColor, QPixmap, QPainter, QTransform

class ScalableRectangle(QGraphicsRectItem):
    def __init__(self, x, y, width, height):
        super().__init__(x, y, width, height)
        self.setFlag(QGraphicsRectItem.ItemIsMovable, True)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsRectItem.ItemSendsGeometryChanges, True)
        
        # Set appearance
        self.setPen(QPen(Qt.black, 0.5))  # Thinnest possible frame
        self.setBrush(QBrush(Qt.transparent))  # Completely transparent fill
        
        # Enable mouse tracking for selection
        self.setAcceptHoverEvents(True)
        self.current_rotation = 0  # Track current rotation angle
        
        # Set rotation center to the center of the rectangle
        # The transform origin should be relative to the rectangle's bounds
        rect_center = self.rect().center()
        self.setTransformOriginPoint(rect_center)
        
    def boundingRect(self):
        # Use standard bounding rect
        return super().boundingRect()
    
    def paint(self, painter, option, widget):
        # Check for overlaps with other rectangles
        overlapping = self.check_for_overlaps()
        
        if overlapping:
            # Change appearance for overlapping rectangles
            painter.setPen(QPen(Qt.red, 0.5))  # Thinnest possible red frame
            painter.setBrush(QBrush(QColor(255, 0, 0, 100)))  # Semi-transparent red fill
        else:
            # Normal appearance
            painter.setPen(QPen(Qt.black, 0.5))  # Thinnest possible black frame
            painter.setBrush(QBrush(Qt.transparent))
        
        # Draw the rectangle
        painter.drawRect(self.rect())
    
    def check_for_overlaps(self):
        """Check if this rectangle overlaps with any other rectangles"""
        if not self.scene():
            return False
            
        # Get all items in the scene
        for item in self.scene().items():
            if isinstance(item, ScalableRectangle) and item != self:
                # Check if this rectangle intersects with another
                if self.collidesWithItem(item):
                    return True
        return False
    
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        # Update all rectangles when this one is released (moved)
        self.update_all_rectangles()
    
    def itemChange(self, change, value):
        # Update all rectangles when position changes
        if change == self.ItemPositionChange and self.scene():
            # Schedule update for next event loop cycle
            self.scene().update()
        return super().itemChange(change, value)
    
    def update_all_rectangles(self):
        """Update all rectangles in the scene to refresh overlap detection"""
        if self.scene():
            for item in self.scene().items():
                if isinstance(item, ScalableRectangle):
                    item.update()
    
    def rotate_clockwise(self):
        # Rotate 1 degree clockwise
        self.current_rotation += 1
        # Clamp rotation between -45 and 45 degrees
        self.current_rotation = max(-45, min(45, self.current_rotation))
        self.setRotation(self.current_rotation)
    
    def rotate_counter_clockwise(self):
        # Rotate 1 degree counter-clockwise
        self.current_rotation -= 1
        # Clamp rotation between -45 and 45 degrees
        self.current_rotation = max(-45, min(45, self.current_rotation))
        self.setRotation(self.current_rotation)

class WorkspaceView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        
        # Enable mouse tracking for smooth interactions
        self.setMouseTracking(True)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        
        # Set up zooming parameters
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        
        # Initialize scene
        self.scene.setSceneRect(QRectF(0, 0, 2000, 1100))
        self.background_item = None
        self.rectangle_size = 10  # Default rectangle size
        
        # Enable keyboard events
        self.setFocusPolicy(Qt.StrongFocus)
        
    def wheelEvent(self, event):
        # Zoom factor
        zoomInFactor = 1.15
        zoomOutFactor = 1 / zoomInFactor
        
        # Save the scene pos
        oldPos = self.mapToScene(event.pos())
        
        # Zoom
        if event.angleDelta().y() > 0:
            zoomFactor = zoomInFactor
        else:
            zoomFactor = zoomOutFactor
        self.scale(zoomFactor, zoomFactor)
        
        # Get the new position and move scene to old position
        newPos = self.mapToScene(event.pos())
        delta = newPos - oldPos
        self.translate(delta.x(), delta.y())
    
    def set_background_image(self, pixmap):
        # Remove existing background
        if self.background_item:
            self.scene.removeItem(self.background_item)
        
        # Get original image dimensions
        original_width = pixmap.width()
        original_height = pixmap.height()
        
        # Find the greater dimension and calculate scale factor
        max_dimension = max(original_width, original_height)
        scale_factor = 1000 / max_dimension
        
        # Calculate new dimensions
        new_width = int(original_width * scale_factor)
        new_height = int(original_height * scale_factor)
        
        # Scale the pixmap while maintaining aspect ratio
        scaled_pixmap = pixmap.scaled(
            new_width,
            new_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        # Add scaled background
        self.background_item = QGraphicsPixmapItem(scaled_pixmap)
        self.background_item.setZValue(-1)  # Put it behind everything
        self.scene.addItem(self.background_item)
        
        # Update scene rect to fit the scaled image
        self.scene.setSceneRect(QRectF(scaled_pixmap.rect()))
    
    def add_rectangle(self, x, y, width=100, height=100):
        rect = ScalableRectangle(x, y, width, height)
        self.scene.addItem(rect)
        return rect
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_T:
            # Add rectangle at center of current view when 'T' is pressed
            center = self.mapToScene(self.rect().center())
            self.add_rectangle(center.x() - self.rectangle_size/2, center.y() - self.rectangle_size/2, 
                             self.rectangle_size, self.rectangle_size)
        elif event.key() == Qt.Key_R:
            # Rotate selected rectangles counter-clockwise
            self.rotate_selected_rectangles(False)
        elif event.key() == Qt.Key_Y:
            # Rotate selected rectangles clockwise
            self.rotate_selected_rectangles(True)
        elif event.key() == Qt.Key_Delete:
            # Delete selected rectangles
            self.delete_selected_rectangles()
        elif event.key() == Qt.Key_Left:
            # Move workspace left
            self.pan_workspace(-50, 0)
        elif event.key() == Qt.Key_Right:
            # Move workspace right
            self.pan_workspace(50, 0)
        elif event.key() == Qt.Key_Up:
            # Move workspace up
            self.pan_workspace(0, -50)
        elif event.key() == Qt.Key_Down:
            # Move workspace down
            self.pan_workspace(0, 50)
        else:
            super().keyPressEvent(event)
    
    def set_rectangle_size(self, size):
        """Set the size for new rectangles"""
        self.rectangle_size = size
    
    def rotate_selected_rectangles(self, clockwise):
        # Rotate all selected rectangles
        for item in self.scene.selectedItems():
            if isinstance(item, ScalableRectangle):
                if clockwise:
                    item.rotate_clockwise()
                else:
                    item.rotate_counter_clockwise()
    
    def delete_selected_rectangles(self):
        # Delete all selected rectangles
        selected_items = self.scene.selectedItems()
        for item in selected_items:
            if isinstance(item, ScalableRectangle):
                self.scene.removeItem(item)
    
    def pan_workspace(self, dx, dy):
        """Pan the workspace view by the specified amount"""
        # Get current scroll bar values
        h_scroll = self.horizontalScrollBar()
        v_scroll = self.verticalScrollBar()
        
        # Move the scroll bars
        h_scroll.setValue(h_scroll.value() + dx)
        v_scroll.setValue(v_scroll.value() + dy)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tessera - Interactive Workspace")
        self.setGeometry(100, 100, 2000, 1100)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create toolbar
        toolbar_layout = QHBoxLayout()
        
        load_bg_btn = QPushButton("Load Background")
        load_bg_btn.clicked.connect(self.load_background)
        toolbar_layout.addWidget(load_bg_btn)
        
        add_rect_btn = QPushButton("Add Rectangle")
        add_rect_btn.clicked.connect(self.add_rectangle)
        toolbar_layout.addWidget(add_rect_btn)
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear_all)
        toolbar_layout.addWidget(clear_btn)
        
        # Add rectangle size input
        size_label = QLabel("Rectangle Size:")
        toolbar_layout.addWidget(size_label)
        
        self.size_input = QLineEdit("10")
        self.size_input.setMaximumWidth(80)
        self.size_input.setPlaceholderText("Size")
        self.size_input.textChanged.connect(self.update_rectangle_size)
        toolbar_layout.addWidget(self.size_input)
        
        toolbar_layout.addStretch()
        main_layout.addLayout(toolbar_layout)
        
        # Create and add workspace view
        self.workspace = WorkspaceView()
        main_layout.addWidget(self.workspace)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Add initial instructions
        self.add_instructions()
    
    def create_menu_bar(self):
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("File")
        
        load_bg_action = QAction("Load Background Image", self)
        load_bg_action.triggered.connect(self.load_background)
        file_menu.addAction(load_bg_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menu_bar.addMenu("Edit")
        
        add_rect_action = QAction("Add Rectangle", self)
        add_rect_action.triggered.connect(self.add_rectangle)
        edit_menu.addAction(add_rect_action)
        
        clear_action = QAction("Clear All", self)
        clear_action.triggered.connect(self.clear_all)
        edit_menu.addAction(clear_action)
    
    def add_instructions(self):
        # Instructions removed - clean workspace
        pass
    
    def load_background(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Background Image", "", 
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
        )
        if file_path:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                self.workspace.set_background_image(pixmap)
    
    def add_rectangle(self):
        # Add rectangle at center of current view
        center = self.workspace.mapToScene(self.workspace.rect().center())
        size = self.workspace.rectangle_size
        self.workspace.add_rectangle(center.x() - size/2, center.y() - size/2, size, size)
    
    def update_rectangle_size(self, text):
        """Update the rectangle size based on input"""
        try:
            size = int(text) if text else 10
            # Clamp size between 10 and 500
            size = max(10, min(500, size))
            self.workspace.set_rectangle_size(size)
        except ValueError:
            # If invalid input, keep current size
            pass
    
    def clear_all(self):
        # Clear all items except background
        for item in self.workspace.scene.items():
            if item != self.workspace.background_item and not item.type() == 8:  # 8 is QGraphicsTextItem
                self.workspace.scene.removeItem(item)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
