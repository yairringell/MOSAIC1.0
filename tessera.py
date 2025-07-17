import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QGraphicsScene, 
                           QGraphicsView, QVBoxLayout, QWidget, QMenuBar, 
                           QMenu, QAction, QFileDialog, QHBoxLayout, QPushButton,
                           QGraphicsRectItem, QGraphicsPixmapItem, QLineEdit, QLabel,
                           QGraphicsLineItem, QGraphicsPathItem)
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QBrush, QPen, QColor, QPixmap, QPainter, QTransform, QPainterPath, QCursor

class ScalableRectangle(QGraphicsRectItem):
    def __init__(self, x, y, width, height):
        super().__init__(x, y, width, height)
        self.setFlag(QGraphicsRectItem.ItemIsMovable, True)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsRectItem.ItemSendsGeometryChanges, True)
        
        # Set appearance
        self.setPen(QPen(QColor(139, 69, 19), 0.5))  # Brown frame (saddle brown)
        self.setBrush(QBrush(Qt.transparent))  # Completely transparent fill
        
        # Enable mouse tracking for selection
        self.setAcceptHoverEvents(True)
        self.current_rotation = 0  # Track current rotation angle
        self.is_filled = False  # Track if rectangle is filled with average color
        self.fill_color = Qt.transparent  # Store the fill color
        
        # Set rotation center to the center of the rectangle
        # The transform origin should be relative to the rectangle's bounds
        rect_center = self.rect().center()
        self.setTransformOriginPoint(rect_center)
        
    def boundingRect(self):
        # Use standard bounding rect
        return super().boundingRect()
    
    def paint(self, painter, option, widget):
        # Only check for overlaps if we're not in a batch operation
        if hasattr(self.scene(), 'batch_operation') and self.scene().batch_operation:
            # During batch operations, use normal appearance
            painter.setPen(QPen(QColor(139, 69, 19), 0.5))
            if self.is_filled:
                painter.setBrush(QBrush(self.fill_color))
            else:
                painter.setBrush(QBrush(Qt.transparent))
        else:
            # Check for overlaps with other rectangles (only when necessary)
            overlapping = self.check_for_overlaps()
            
            if overlapping:
                # Change appearance for overlapping rectangles
                painter.setPen(QPen(Qt.red, 0.5))  # Thinnest possible red frame
                painter.setBrush(QBrush(QColor(255, 0, 0, 100)))  # Semi-transparent red fill
            else:
                # Normal appearance
                painter.setPen(QPen(QColor(139, 69, 19), 0.5))  # Brown frame (saddle brown)
                if self.is_filled:
                    painter.setBrush(QBrush(self.fill_color))
                else:
                    painter.setBrush(QBrush(Qt.transparent))
        
        # Draw the rectangle
        painter.drawRect(self.rect())
    
    def check_for_overlaps(self):
        """Check if this rectangle overlaps with any other rectangles - optimized version"""
        if not self.scene():
            return False
        
        # Get nearby items only (within a reasonable distance)
        search_rect = self.sceneBoundingRect().adjusted(-50, -50, 50, 50)
        nearby_items = self.scene().items(search_rect)
        
        # Check only nearby rectangles
        for item in nearby_items:
            if isinstance(item, ScalableRectangle) and item != self:
                # Quick bounding box check first
                if self.collidesWithItem(item):
                    return True
        return False
    
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        # Only update nearby rectangles when this one is released (moved)
        self.update_nearby_rectangles()
    
    def itemChange(self, change, value):
        # Reduce the frequency of updates during position changes
        if change == self.ItemPositionChange and self.scene():
            # Don't update during every position change, only on release
            pass
        return super().itemChange(change, value)
    
    def update_nearby_rectangles(self):
        """Update only nearby rectangles for better performance"""
        if not self.scene():
            return
        
        # Get nearby items only
        search_rect = self.sceneBoundingRect().adjusted(-100, -100, 100, 100)
        nearby_items = self.scene().items(search_rect)
        
        for item in nearby_items:
            if isinstance(item, ScalableRectangle):
                item.update()
    
    def rotate_clockwise(self):
        # Rotate 1 degree clockwise
        self.current_rotation += 1
        # Clamp rotation between -89 and 89 degrees
        self.current_rotation = max(-89, min(89, self.current_rotation))
        self.setRotation(self.current_rotation)
    
    def rotate_counter_clockwise(self):
        # Rotate 1 degree counter-clockwise
        self.current_rotation -= 1
        # Clamp rotation between -89 and 89 degrees
        self.current_rotation = max(-89, min(89, self.current_rotation))
        self.setRotation(self.current_rotation)
    
    def fill_with_average_color(self):
        """Fill the rectangle with the average color of pixels in its area"""
        if not self.scene():
            return
        
        # Find the background image item
        background_item = None
        for item in self.scene().items():
            if isinstance(item, QGraphicsPixmapItem):
                background_item = item
                break
        
        if not background_item:
            return
        
        # Get the rectangle's bounds in scene coordinates
        rect_in_scene = self.mapToScene(self.rect()).boundingRect()
        
        # Get the background pixmap
        pixmap = background_item.pixmap()
        image = pixmap.toImage()
        
        # Calculate the intersection of rectangle with image bounds
        image_rect = QRectF(background_item.pos(), QRectF(pixmap.rect()).size())
        intersection = rect_in_scene.intersected(image_rect)
        
        if intersection.isEmpty():
            return
        
        # Convert to image coordinates (relative to background item position)
        bg_pos = background_item.pos()
        sample_rect = QRectF(
            intersection.x() - bg_pos.x(),
            intersection.y() - bg_pos.y(),
            intersection.width(),
            intersection.height()
        )
        
        # Ensure we don't go outside image bounds
        sample_rect = sample_rect.intersected(QRectF(0, 0, image.width(), image.height()))
        
        if sample_rect.isEmpty():
            return
        
        # Sample pixels and calculate average color
        total_red = 0
        total_green = 0
        total_blue = 0
        pixel_count = 0
        
        x_start = max(0, int(sample_rect.x()))
        y_start = max(0, int(sample_rect.y()))
        x_end = min(image.width(), int(sample_rect.x() + sample_rect.width()))
        y_end = min(image.height(), int(sample_rect.y() + sample_rect.height()))
        
        for y in range(y_start, y_end):
            for x in range(x_start, x_end):
                pixel = image.pixel(x, y)
                color = QColor(pixel)
                total_red += color.red()
                total_green += color.green()
                total_blue += color.blue()
                pixel_count += 1
        
        if pixel_count > 0:
            avg_red = total_red // pixel_count
            avg_green = total_green // pixel_count
            avg_blue = total_blue // pixel_count
            
            self.fill_color = QColor(avg_red, avg_green, avg_blue)
            self.is_filled = True
            self.update()  # Trigger repaint
    
    def set_transparent(self):
        """Make the rectangle transparent"""
        self.is_filled = False
        self.update()  # Trigger repaint

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
        
        # Performance optimization flag
        self.scene.batch_operation = False
        
        # Drawing mode variables
        self.drawing_mode = False
        self.drawing_path = []
        self.current_path_item = None
        self.is_drawing = False
        self.rectangle_spacing = 1.3  # Default spacing multiplier
        
        # Enable keyboard events
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Create custom drawing cursor
        self.drawing_cursor = self.create_drawing_cursor()
        
    def create_drawing_cursor(self):
        """Create a 3x3 black square cursor"""
        # Create a 3x3 pixmap
        pixmap = QPixmap(3, 3)
        pixmap.fill(QColor(0, 0, 0))  # Fill with black
        
        # Create cursor with the pixmap, hotspot at center (1, 1)
        cursor = QCursor(pixmap, 1, 1)
        return cursor
        
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
        elif event.key() == Qt.Key_C:
            # Fill selected rectangles with average color
            self.fill_selected_rectangles()
        elif event.key() == Qt.Key_P:
            # Add rectangle with regular height and half width when 'P' is pressed
            center = self.mapToScene(self.rect().center())
            half_width = self.rectangle_size / 2
            self.add_rectangle(center.x() - half_width/2, center.y() - self.rectangle_size/2, 
                             half_width, self.rectangle_size)
        elif event.key() == Qt.Key_O:
            # Add rectangle with half the size when 'O' is pressed
            center = self.mapToScene(self.rect().center())
            half_size = self.rectangle_size / 2
            self.add_rectangle(center.x() - half_size/2, center.y() - half_size/2, 
                             half_size, half_size)
        elif event.key() == Qt.Key_D:
            # Toggle drawing mode
            self.drawing_mode = not self.drawing_mode
            if self.drawing_mode:
                self.setDragMode(QGraphicsView.NoDrag)
                self.setCursor(self.drawing_cursor)  # Set custom cursor
            else:
                self.setDragMode(QGraphicsView.RubberBandDrag)
                self.setCursor(Qt.ArrowCursor)  # Reset to default cursor
        else:
            super().keyPressEvent(event)
    
    def set_rectangle_size(self, size):
        """Set the size for new rectangles"""
        self.rectangle_size = size
    
    def set_rectangle_spacing(self, spacing):
        """Set the spacing multiplier for rectangles along drawn lines"""
        self.rectangle_spacing = spacing
    
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
    
    def fill_selected_rectangles(self):
        # Fill all selected rectangles with their average color
        selected_items = self.scene.selectedItems()
        for item in selected_items:
            if isinstance(item, ScalableRectangle):
                item.fill_with_average_color()
    
    def pan_workspace(self, dx, dy):
        """Pan the workspace view by the specified amount"""
        # Get current scroll bar values
        h_scroll = self.horizontalScrollBar()
        v_scroll = self.verticalScrollBar()
        
        # Move the scroll bars
        h_scroll.setValue(h_scroll.value() + dx)
        v_scroll.setValue(v_scroll.value() + dy)
    
    def mousePressEvent(self, event):
        if self.drawing_mode and event.button() == Qt.LeftButton:
            # Start drawing a path
            self.is_drawing = True
            self.drawing_path = []
            start_pos = self.mapToScene(event.pos())
            self.drawing_path.append(start_pos)
            
            # Create a path item for visual feedback
            path = QPainterPath()
            path.moveTo(start_pos)
            self.current_path_item = QGraphicsPathItem(path)
            self.current_path_item.setPen(QPen(QColor(139, 69, 19), 2))
            self.scene.addItem(self.current_path_item)
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self.drawing_mode and self.is_drawing and self.current_path_item:
            # Continue drawing the path
            current_pos = self.mapToScene(event.pos())
            self.drawing_path.append(current_pos)
            
            # Update the path for visual feedback
            path = QPainterPath()
            if self.drawing_path:
                path.moveTo(self.drawing_path[0])
                for point in self.drawing_path[1:]:
                    path.lineTo(point)
            self.current_path_item.setPath(path)
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        if self.drawing_mode and event.button() == Qt.LeftButton and self.is_drawing:
            # Finish drawing and create rectangles along the path
            self.is_drawing = False
            
            # Remove the temporary path visual
            if self.current_path_item:
                self.scene.removeItem(self.current_path_item)
                self.current_path_item = None
            
            # Create rectangles along the drawn path
            self.create_rectangles_along_path()
            
            # Clear the path
            self.drawing_path = []
        else:
            super().mouseReleaseEvent(event)
    
    def create_rectangles_along_path(self):
        """Create rectangles along the drawn path"""
        if len(self.drawing_path) < 2:
            return
        
        # Enable batch operation mode for better performance
        self.scene.batch_operation = True
        
        # Calculate spacing between rectangles based on rectangle size
        spacing = self.rectangle_size * self.rectangle_spacing  # Use adjustable spacing
        
        # Smooth the path by averaging neighboring points
        smoothed_path = self.smooth_path(self.drawing_path)
        
        # Sample points along the path at regular intervals
        total_distance = 0
        path_segments = []
        
        # Calculate distances between consecutive points
        for i in range(len(smoothed_path) - 1):
            p1 = smoothed_path[i]
            p2 = smoothed_path[i + 1]
            distance = ((p2.x() - p1.x()) ** 2 + (p2.y() - p1.y()) ** 2) ** 0.5
            path_segments.append((p1, p2, distance))
            total_distance += distance
        
        # Place rectangles at regular intervals
        current_distance = 0
        target_distance = 0
        
        for segment_idx, (p1, p2, segment_distance) in enumerate(path_segments):
            while target_distance <= current_distance + segment_distance:
                # Calculate position along this segment
                if segment_distance > 0:
                    ratio = (target_distance - current_distance) / segment_distance
                    x = p1.x() + ratio * (p2.x() - p1.x())
                    y = p1.y() + ratio * (p2.y() - p1.y())
                    
                    # Calculate smooth angle using neighboring segments
                    angle_degrees = self.calculate_smooth_angle(smoothed_path, segment_idx, ratio)
                    
                    # Clamp angle to the allowed range (-89 to 89 degrees)
                    angle_degrees = max(-89, min(89, angle_degrees))
                    
                    # Create rectangle at this position
                    rect = self.add_rectangle(x - self.rectangle_size/2, y - self.rectangle_size/2, 
                                            self.rectangle_size, self.rectangle_size)
                    
                    # Rotate the rectangle to match the smooth angle
                    rect.current_rotation = angle_degrees
                    rect.setRotation(angle_degrees)
                
                target_distance += spacing
            
            current_distance += segment_distance
        
        # Disable batch operation mode
        self.scene.batch_operation = False
    
    def smooth_path(self, path):
        """Smooth the path using a simple moving average"""
        if len(path) < 3:
            return path
        
        smoothed = [path[0]]  # Keep first point
        
        # Apply smoothing to middle points
        for i in range(1, len(path) - 1):
            prev_point = path[i - 1]
            curr_point = path[i]
            next_point = path[i + 1]
            
            # Average the current point with its neighbors
            smooth_x = (prev_point.x() + curr_point.x() + next_point.x()) / 3
            smooth_y = (prev_point.y() + curr_point.y() + next_point.y()) / 3
            
            smoothed.append(QPointF(smooth_x, smooth_y))
        
        smoothed.append(path[-1])  # Keep last point
        return smoothed
    
    def calculate_smooth_angle(self, path, segment_idx, ratio):
        """Calculate a smooth angle by considering neighboring segments"""
        import math
        
        # Get current segment
        p1 = path[segment_idx]
        p2 = path[segment_idx + 1]
        
        # Calculate angle for current segment
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        current_angle = math.atan2(dy, dx)
        
        # If we have neighboring segments, blend the angles
        angles = [current_angle]
        
        # Add previous segment angle if available
        if segment_idx > 0:
            prev_p1 = path[segment_idx - 1]
            prev_p2 = path[segment_idx]
            prev_dx = prev_p2.x() - prev_p1.x()
            prev_dy = prev_p2.y() - prev_p1.y()
            prev_angle = math.atan2(prev_dy, prev_dx)
            angles.append(prev_angle)
        
        # Add next segment angle if available
        if segment_idx < len(path) - 2:
            next_p1 = path[segment_idx + 1]
            next_p2 = path[segment_idx + 2]
            next_dx = next_p2.x() - next_p1.x()
            next_dy = next_p2.y() - next_p1.y()
            next_angle = math.atan2(next_dy, next_dx)
            angles.append(next_angle)
        
        # Handle angle wrapping around -π to π
        # Convert to unit vectors and average them
        avg_x = sum(math.cos(angle) for angle in angles) / len(angles)
        avg_y = sum(math.sin(angle) for angle in angles) / len(angles)
        
        # Convert back to angle
        smooth_angle = math.atan2(avg_y, avg_x)
        
        return math.degrees(smooth_angle)

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
        
        # Add color toggle button
        self.color_btn = QPushButton("Color")
        self.color_btn.clicked.connect(self.toggle_color_mode)
        toolbar_layout.addWidget(self.color_btn)
        
        # Add rectangle size input
        size_label = QLabel("Rectangle Size:")
        toolbar_layout.addWidget(size_label)
        
        self.size_input = QLineEdit("10")
        self.size_input.setMaximumWidth(80)
        self.size_input.setPlaceholderText("Size")
        self.size_input.textChanged.connect(self.update_rectangle_size)
        toolbar_layout.addWidget(self.size_input)
        
        # Add spacing input
        spacing_label = QLabel("Line Spacing:")
        toolbar_layout.addWidget(spacing_label)
        
        self.spacing_input = QLineEdit("1.3")
        self.spacing_input.setMaximumWidth(80)
        self.spacing_input.setPlaceholderText("Spacing")
        self.spacing_input.textChanged.connect(self.update_rectangle_spacing)
        toolbar_layout.addWidget(self.spacing_input)
        
        toolbar_layout.addStretch()
        main_layout.addLayout(toolbar_layout)
        
        # Create and add workspace view
        self.workspace = WorkspaceView()
        main_layout.addWidget(self.workspace)
        
        # Initialize color toggle state
        self.color_mode = False
        
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
    
    def update_rectangle_spacing(self, text):
        """Update the rectangle spacing based on input"""
        try:
            spacing = float(text) if text else 1.5
            # Clamp spacing between 0.1 and 10.0
            spacing = max(0.1, min(10.0, spacing))
            self.workspace.set_rectangle_spacing(spacing)
        except ValueError:
            # If invalid input, keep current spacing
            pass
    
    def clear_all(self):
        # Clear all items except background
        for item in self.workspace.scene.items():
            if item != self.workspace.background_item and not item.type() == 8:  # 8 is QGraphicsTextItem
                self.workspace.scene.removeItem(item)
    
    def toggle_color_mode(self):
        """Toggle between colored and transparent rectangles"""
        self.color_mode = not self.color_mode
        
        # Get all rectangles in the scene
        rectangles = []
        for item in self.workspace.scene.items():
            if isinstance(item, ScalableRectangle):
                rectangles.append(item)
        
        if self.color_mode:
            # Fill all rectangles with their average color
            for rect in rectangles:
                rect.fill_with_average_color()
            self.color_btn.setText("Transparent")
        else:
            # Make all rectangles transparent
            for rect in rectangles:
                rect.set_transparent()
            self.color_btn.setText("Color")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
