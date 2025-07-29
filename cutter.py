import sys
import csv
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QFileDialog, QGraphicsView, 
                             QGraphicsScene, QGraphicsPixmapItem, QMenuBar, QAction,
                             QGraphicsRectItem, QGraphicsPolygonItem, QGraphicsTextItem)
from PyQt5.QtCore import Qt, QRectF, QPointF, QSize
from PyQt5.QtGui import QColor, QPen, QBrush, QPixmap, QPolygonF

class GridHandle(QGraphicsRectItem):
    """Draggable handle for moving the grid"""
    def __init__(self, parent_view):
        super().__init__(0, 0, 20, 20)  # 20x20 pixel handle
        self.parent_view = parent_view
        
        # Set appearance - red rectangle
        self.setPen(QPen(QColor(255, 0, 0), 1))  # Red border
        self.setBrush(QBrush(QColor(255, 0, 0, 150)))  # Semi-transparent red fill
        
        # Make it movable
        self.setFlag(QGraphicsRectItem.ItemIsMovable, True)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsRectItem.ItemSendsGeometryChanges, True)
        
        # Set Z-value to be in front of grid but behind shapes
        self.setZValue(-0.3)
    
    def itemChange(self, change, value):
        """Handle position changes to move the entire grid"""
        if change == QGraphicsRectItem.ItemPositionChange and self.scene():
            # Calculate the new grid offset
            new_pos = value
            self.parent_view.grid_offset_x = new_pos.x()
            self.parent_view.grid_offset_y = new_pos.y()
            
            # Update grid position
            self.parent_view.update_grid_position()
        
        return super().itemChange(change, value)

class ScalableRectangle(QGraphicsRectItem):
    """Simplified rectangle class for display only"""
    def __init__(self, x, y, width, height, initial_color=None):
        super().__init__(0, 0, width, height)  # Create rect at origin
        self.setPos(x, y)  # Set position
        
        # Set flags to make non-interactive for viewing
        self.setFlag(QGraphicsRectItem.ItemIsMovable, False)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, False)
        
        # Set appearance - black frame with minimal thickness
        self.setPen(QPen(QColor(0, 0, 0), 0))  # Black frame, minimal thickness
        self.setBrush(QBrush(Qt.transparent))  # Start transparent
        
        # Store properties
        self.current_rotation = 0
        self.is_filled = False
        self.fill_color = Qt.transparent
        self.serial_number = 0
        
        # Set rotation center to center of rectangle
        rect_center = self.rect().center()
        self.setTransformOriginPoint(rect_center)
    
    def set_fill_color(self, color):
        """Set fill color"""
        if color and color.isValid():
            self.fill_color = color
            self.is_filled = True
            self.setBrush(QBrush(color))
        else:
            self.is_filled = False
            self.setBrush(QBrush(Qt.transparent))

class ScalableTriangle(QGraphicsPolygonItem):
    """Simplified triangle class for display only"""
    def __init__(self, x, y, size, initial_color=None):
        # Create a 90-degree right triangle
        triangle_points = [
            QPointF(0, 0),
            QPointF(size, 0),
            QPointF(0, size)
        ]
        triangle_polygon = QPolygonF(triangle_points)
        
        super().__init__(triangle_polygon)
        self.setPos(x, y)
        
        # Set flags to make non-interactive for viewing
        self.setFlag(QGraphicsPolygonItem.ItemIsMovable, False)
        self.setFlag(QGraphicsPolygonItem.ItemIsSelectable, False)
        
        # Set appearance - black frame with minimal thickness
        self.setPen(QPen(QColor(0, 0, 0), 0))  # Black frame, minimal thickness
        self.setBrush(QBrush(Qt.transparent))  # Start transparent
        
        # Store properties
        self.current_rotation = 0
        self.is_filled = False
        self.fill_color = Qt.transparent
        self.serial_number = 0
        self.size = size
        
        # Set rotation center to center of triangle
        triangle_center = triangle_polygon.boundingRect().center()
        self.setTransformOriginPoint(triangle_center)
    
    def set_fill_color(self, color):
        """Set fill color"""
        if color and color.isValid():
            self.fill_color = color
            self.is_filled = True
            self.setBrush(QBrush(color))
        else:
            self.is_filled = False
            self.setBrush(QBrush(Qt.transparent))

class CutterView(QGraphicsView):
    """Graphics view with zoom capabilities"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create scene
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        # Set up zooming parameters - copied from tessera1_2.py
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        
        # Enable drag mode for panning
        self.setDragMode(QGraphicsView.RubberBandDrag)
        
        # Set scene rect to match tessera1_2.py positioning
        self.scene.setSceneRect(QRectF(0, 0, 2000, 1100))
        
        # Enable mouse tracking
        self.setMouseTracking(True)
        
        # Background
        self.background_item = None
        
        # Grid items for 6x6 grid of 250x250 boxes
        self.grid_items = []
        self.grid_labels = []  # Store grid labels separately
        self.cut_lines = []  # Store cut lines
        self.grid_visible = False
        self.grid_handle = None
        self.grid_offset_x = 0
        self.grid_offset_y = 0
        
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming towards cursor position"""
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
        """Set background image"""
        if self.background_item:
            self.scene.removeItem(self.background_item)
        
        self.background_item = QGraphicsPixmapItem(pixmap)
        self.background_item.setZValue(-1)  # Put background behind everything
        self.scene.addItem(self.background_item)
        
        # Center the view on the background
        self.centerOn(self.background_item)
    
    def add_shape(self, shape):
        """Add a shape to the scene"""
        self.scene.addItem(shape)
    
    def clear_shapes(self):
        """Clear all shapes"""
        # Remove all items except background, grid, grid labels, cut lines, and grid handle
        for item in self.scene.items():
            if (item != self.background_item and 
                item not in self.grid_items and 
                item not in self.grid_labels and
                item not in self.cut_lines and
                item != self.grid_handle):
                self.scene.removeItem(item)
    
    def create_grid(self):
        """Create a 6x6 grid with boxes of 250x250 pixels each"""
        if self.grid_visible:
            return  # Grid already visible
        
        # Clear any existing grid
        self.clear_grid()
        
        # Grid parameters - 6x6 boxes of 250x250 pixels
        box_size = 250
        grid_cols = 6
        grid_rows = 6
        
        # Starting position (top-left of grid) with offset
        start_x = 0 + self.grid_offset_x
        start_y = 0 + self.grid_offset_y
        
        # Create vertical lines (7 lines to make 6 columns)
        for i in range(grid_cols + 1):
            x = start_x + (i * box_size)
            line_item = self.scene.addLine(
                x, start_y, 
                x, start_y + (grid_rows * box_size),
                QPen(QColor(0, 0, 255), 0)  # Blue pen with minimal thickness
            )
            line_item.setZValue(-0.5)  # Put grid behind shapes but in front of background
            self.grid_items.append(line_item)
        
        # Create horizontal lines (7 lines to make 6 rows)
        for i in range(grid_rows + 1):
            y = start_y + (i * box_size)
            line_item = self.scene.addLine(
                start_x, y,
                start_x + (grid_cols * box_size), y,
                QPen(QColor(0, 0, 255), 0)  # Blue pen with minimal thickness
            )
            line_item.setZValue(-0.5)  # Put grid behind shapes but in front of background
            self.grid_items.append(line_item)
        
        # Create the draggable handle at the top-left corner
        self.grid_handle = GridHandle(self)
        self.grid_handle.setPos(start_x, start_y)
        self.scene.addItem(self.grid_handle)
        
        # Create labels for vertical lines (A, B, C... on top)
        for i in range(grid_cols + 1):
            x = start_x + (i * box_size)
            label_text = chr(ord('A') + i)  # A, B, C, D, E, F, G
            label_item = QGraphicsTextItem(label_text)
            label_item.setPos(x - 10, start_y - 25)  # Position above the grid
            label_item.setDefaultTextColor(QColor(0, 0, 255))  # Blue color to match grid
            label_item.setZValue(-0.4)  # In front of grid lines but behind shapes
            self.scene.addItem(label_item)
            self.grid_labels.append(label_item)
        
        # Create labels for horizontal lines (1, 2, 3... on left)
        for i in range(grid_rows + 1):
            y = start_y + (i * box_size)
            label_text = str(i + 1)  # 1, 2, 3, 4, 5, 6, 7
            label_item = QGraphicsTextItem(label_text)
            label_item.setPos(start_x - 25, y - 10)  # Position to the left of the grid
            label_item.setDefaultTextColor(QColor(0, 0, 255))  # Blue color to match grid
            label_item.setZValue(-0.4)  # In front of grid lines but behind shapes
            self.scene.addItem(label_item)
            self.grid_labels.append(label_item)
        
        self.grid_visible = True
    
    def update_grid_position(self):
        """Update the position of all grid lines and labels based on the handle position"""
        if not self.grid_visible or not self.grid_items:
            return
        
        # Remove existing grid lines
        for item in self.grid_items:
            self.scene.removeItem(item)
        self.grid_items.clear()
        
        # Remove existing labels
        for item in self.grid_labels:
            self.scene.removeItem(item)
        self.grid_labels.clear()
        
        # Grid parameters
        box_size = 250
        grid_cols = 6
        grid_rows = 6
        
        # Starting position with current offset
        start_x = 0 + self.grid_offset_x
        start_y = 0 + self.grid_offset_y
        
        # Recreate vertical lines
        for i in range(grid_cols + 1):
            x = start_x + (i * box_size)
            line_item = self.scene.addLine(
                x, start_y, 
                x, start_y + (grid_rows * box_size),
                QPen(QColor(0, 0, 255), 0)
            )
            line_item.setZValue(-0.5)
            self.grid_items.append(line_item)
        
        # Recreate horizontal lines
        for i in range(grid_rows + 1):
            y = start_y + (i * box_size)
            line_item = self.scene.addLine(
                start_x, y,
                start_x + (grid_cols * box_size), y,
                QPen(QColor(0, 0, 255), 0)
            )
            line_item.setZValue(-0.5)
            self.grid_items.append(line_item)
        
        # Recreate labels for vertical lines (A, B, C... on top)
        for i in range(grid_cols + 1):
            x = start_x + (i * box_size)
            label_text = chr(ord('A') + i)  # A, B, C, D, E, F, G
            label_item = QGraphicsTextItem(label_text)
            label_item.setPos(x - 10, start_y - 25)  # Position above the grid
            label_item.setDefaultTextColor(QColor(0, 0, 255))  # Blue color to match grid
            label_item.setZValue(-0.4)  # In front of grid lines but behind shapes
            self.scene.addItem(label_item)
            self.grid_labels.append(label_item)
        
        # Recreate labels for horizontal lines (1, 2, 3... on left)
        for i in range(grid_rows + 1):
            y = start_y + (i * box_size)
            label_text = str(i + 1)  # 1, 2, 3, 4, 5, 6, 7
            label_item = QGraphicsTextItem(label_text)
            label_item.setPos(start_x - 25, y - 10)  # Position to the left of the grid
            label_item.setDefaultTextColor(QColor(0, 0, 255))  # Blue color to match grid
            label_item.setZValue(-0.4)  # In front of grid lines but behind shapes
            self.scene.addItem(label_item)
            self.grid_labels.append(label_item)
    
    def clear_grid(self):
        """Remove the grid, labels, and handle"""
        for item in self.grid_items:
            self.scene.removeItem(item)
        self.grid_items.clear()
        
        for item in self.grid_labels:
            self.scene.removeItem(item)
        self.grid_labels.clear()
        
        if self.grid_handle:
            self.scene.removeItem(self.grid_handle)
            self.grid_handle = None
        
        self.grid_visible = False

    def fill_A1_and_A2_boxes(self):
        """Fill all boxes that contain shapes with different colors and color the overlapping shapes"""
        if not self.grid_visible:
            return  # No grid to reference
        
        # Calculate box positions and size
        box_size = 250
        grid_cols = 6
        grid_rows = 6
        
        # Define colors for each box (36 different colors for 6x6 grid)
        box_colors = [
            QColor(255, 0, 0),      # Red
            QColor(0, 255, 0),      # Green  
            QColor(0, 0, 255),      # Blue
            QColor(255, 255, 0),    # Yellow
            QColor(255, 0, 255),    # Magenta
            QColor(0, 255, 255),    # Cyan
            QColor(255, 128, 0),    # Orange
            QColor(128, 255, 0),    # Lime
            QColor(0, 255, 128),    # Spring Green
            QColor(0, 128, 255),    # Sky Blue
            QColor(128, 0, 255),    # Purple
            QColor(255, 0, 128),    # Pink
            QColor(192, 192, 192),  # Silver
            QColor(128, 128, 128),  # Gray
            QColor(128, 0, 0),      # Maroon
            QColor(0, 128, 0),      # Dark Green
            QColor(0, 0, 128),      # Navy
            QColor(128, 128, 0),    # Olive
            QColor(128, 0, 128),    # Purple Dark
            QColor(0, 128, 128),    # Teal
            QColor(255, 192, 203),  # Light Pink
            QColor(255, 165, 0),    # Orange Red
            QColor(255, 215, 0),    # Gold
            QColor(173, 216, 230),  # Light Blue
            QColor(144, 238, 144),  # Light Green
            QColor(221, 160, 221),  # Plum
            QColor(255, 182, 193),  # Light Pink
            QColor(255, 218, 185),  # Peach
            QColor(240, 230, 140),  # Khaki
            QColor(230, 230, 250),  # Lavender
            QColor(250, 128, 114),  # Salmon
            QColor(255, 160, 122),  # Light Salmon
            QColor(176, 196, 222),  # Light Steel Blue
            QColor(205, 92, 92),    # Indian Red
            QColor(255, 105, 180),  # Hot Pink
            QColor(64, 224, 208)    # Turquoise
        ]
        
        # Find which boxes contain shapes and collect box information
        boxes_with_shapes = []
        
        for row in range(grid_rows):
            for col in range(grid_cols):
                # Calculate box position
                box_x = self.grid_offset_x + (col * box_size)
                box_y = self.grid_offset_y + (row * box_size)
                box_rect = QRectF(box_x, box_y, box_size, box_size)
                
                # Check if any shapes overlap with this box
                has_shapes = False
                for item in self.scene.items():
                    if (item != self.background_item and 
                        item not in self.grid_items and 
                        item not in self.grid_labels and
                        item not in self.cut_lines and
                        item != self.grid_handle and
                        (isinstance(item, ScalableRectangle) or isinstance(item, ScalableTriangle))):
                        
                        shape_rect = item.sceneBoundingRect()
                        if box_rect.intersects(shape_rect):
                            has_shapes = True
                            break
                
                if has_shapes:
                    # Calculate box index for color selection based on grid position
                    # This ensures each box always gets the same color regardless of order
                    box_index = row * grid_cols + col  # A1=0, B1=1, C1=2, A2=6, etc.
                    color = box_colors[box_index % len(box_colors)]
                    
                    boxes_with_shapes.append({
                        'rect': box_rect,
                        'color': color,
                        'x': box_x,
                        'y': box_y,
                        'row': row,
                        'col': col,
                        'box_index': box_index  # Store for consistent identification
                    })
        
        # Create colored rectangles for boxes that contain shapes
        for box_info in boxes_with_shapes:
            colored_rect = QGraphicsRectItem(box_info['x'], box_info['y'], box_size, box_size)
            colored_rect.setPen(QPen(Qt.transparent))  # No border
            colored_rect.setBrush(QBrush(box_info['color']))  # Box color
            colored_rect.setZValue(-0.3)
            self.scene.addItem(colored_rect)
            self.cut_lines.append(colored_rect)
        
        # Color shapes based on which box they primarily belong to
        for item in self.scene.items():
            # Only check actual shapes (rectangles and triangles)
            if (item != self.background_item and 
                item not in self.grid_items and 
                item not in self.grid_labels and
                item not in self.cut_lines and
                item != self.grid_handle and
                (isinstance(item, ScalableRectangle) or isinstance(item, ScalableTriangle))):
                
                # Get the shape's bounding rectangle in scene coordinates
                shape_rect = item.sceneBoundingRect()
                
                # Find which box has the largest overlap with this shape
                max_overlap_area = 0
                best_box_color = None
                
                for box_info in boxes_with_shapes:
                    if box_info['rect'].intersects(shape_rect):
                        intersection_rect = box_info['rect'].intersected(shape_rect)
                        overlap_area = intersection_rect.width() * intersection_rect.height()
                        
                        if overlap_area > max_overlap_area:
                            max_overlap_area = overlap_area
                            best_box_color = box_info['color']
                
                # Color the shape based on overlap
                if best_box_color and max_overlap_area > 0:
                    total_shape_area = shape_rect.width() * shape_rect.height()
                    area_ratio = max_overlap_area / total_shape_area if total_shape_area > 0 else 0
                    
                    if area_ratio > 0.25:  # More than 25% of shape is in the dominant box (lowered threshold)
                        # Fill with the box color
                        item.setBrush(QBrush(best_box_color))  # Box color
                        item.setPen(QPen(best_box_color, 0))  # Matching frame
                    else:  # Less than 25% of shape is in any box
                        # Fill with white
                        item.setBrush(QBrush(QColor(255, 255, 255)))  # Solid white
                        item.setPen(QPen(QColor(0, 0, 0), 0))  # Black frame
    
    def clear_cut_lines(self):
        """Remove all cut lines and filled boxes, and reset shape colors"""
        for cut_item in self.cut_lines:
            self.scene.removeItem(cut_item)
        self.cut_lines.clear()
        
        # Reset all shape colors back to transparent
        for item in self.scene.items():
            if (item != self.background_item and 
                item not in self.grid_items and 
                item not in self.grid_labels and
                item != self.grid_handle and
                (isinstance(item, ScalableRectangle) or isinstance(item, ScalableTriangle))):
                # Reset to transparent fill and black frame
                item.setBrush(QBrush(Qt.transparent))
                item.setPen(QPen(QColor(0, 0, 0), 0))  # Reset to black frame

class CutterWindow(QMainWindow):
    """Main window for the cutter application"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cutter - Shape Viewer")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create layout
        layout = QVBoxLayout(central_widget)
        
        # Create minimal toolbar
        toolbar_layout = QHBoxLayout()
        
        import_btn = QPushButton("Import Array")
        import_btn.clicked.connect(self.import_array_from_csv)
        toolbar_layout.addWidget(import_btn)
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_all)
        toolbar_layout.addWidget(clear_btn)
        
        grid_btn = QPushButton("Grid 250")
        grid_btn.clicked.connect(self.toggle_grid)
        toolbar_layout.addWidget(grid_btn)
        
        cut_btn = QPushButton("Cut")
        cut_btn.clicked.connect(self.perform_cut)
        toolbar_layout.addWidget(cut_btn)
        
        save_boxes_btn = QPushButton("Save Boxes")
        save_boxes_btn.clicked.connect(self.save_a1_box)
        toolbar_layout.addWidget(save_boxes_btn)
        
        small_array_btn = QPushButton("Small Array")
        small_array_btn.clicked.connect(self.create_small_array)
        toolbar_layout.addWidget(small_array_btn)
        
        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)
        
        # Create graphics view
        self.cutter_view = CutterView(self)
        layout.addWidget(self.cutter_view)
        
        # Create menu bar
        self.create_menu_bar()
    
    def create_menu_bar(self):
        """Create minimal menu bar"""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("File")
        
        import_action = QAction("Import Array", self)
        import_action.triggered.connect(self.import_array_from_csv)
        file_menu.addAction(import_action)
        
        load_bg_action = QAction("Load Background Image", self)
        load_bg_action.triggered.connect(self.load_background)
        file_menu.addAction(load_bg_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
    
    def load_background(self):
        """Load background image"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Background Image", "", 
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
        )
        if file_path:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                self.cutter_view.set_background_image(pixmap)
    
    def clear_all(self):
        """Clear all shapes and cut lines"""
        self.cutter_view.clear_shapes()
        self.cutter_view.clear_cut_lines()
    
    def perform_cut(self):
        """Perform cut operation - fill all boxes that contain shapes with different colors"""
        self.cutter_view.fill_A1_and_A2_boxes()
    
    def save_a1_box(self):
        """Save the A1 box area with 20-pixel margin as a high-quality image"""
        if not self.cutter_view.grid_visible:
            print("Error: Grid must be visible to save A1 box")
            return
        
        try:
            # A1 box parameters (top-left box: row=0, col=0)
            box_size = 250
            margin = 20
            
            # Calculate A1 box position
            a1_x = self.cutter_view.grid_offset_x
            a1_y = self.cutter_view.grid_offset_y
            
            # Define the capture area with margin
            capture_x = a1_x - margin
            capture_y = a1_y - margin
            capture_width = box_size + (2 * margin)
            capture_height = box_size + (2 * margin)
            
            # Create high-quality pixmap at native resolution
            pixmap = QPixmap(capture_width, capture_height)
            pixmap.fill(Qt.white)  # White background
            
            # Create QPainter for high-quality rendering
            from PyQt5.QtGui import QPainter
            painter = QPainter(pixmap)
            
            # Enable high-quality rendering
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.TextAntialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            
            # Define the source rectangle (scene coordinates)
            source_rect = QRectF(capture_x, capture_y, capture_width, capture_height)
            
            # Define the target rectangle (pixmap coordinates)
            target_rect = QRectF(0, 0, capture_width, capture_height)
            
            # Render the scene area to the pixmap
            self.cutter_view.scene.render(painter, target_rect, source_rect)
            painter.end()
            
            # Get save file path - Default to TIFF for maximum quality
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save A1 Box Area", "A1_box_area.tiff", 
                "TIFF Files (*.tiff);;BMP Files (*.bmp);;PNG Files (*.png);;JPEG Files (*.jpg);;All Files (*)"
            )
            
            if file_path:
                # Determine format from file extension
                if file_path.lower().endswith(('.jpg', '.jpeg')):
                    format_type = "JPEG"
                    # Save with high quality for JPEG
                    success = pixmap.save(file_path, format_type, 95)  # 95% quality
                elif file_path.lower().endswith('.bmp'):
                    format_type = "BMP"
                    success = pixmap.save(file_path, format_type)
                elif file_path.lower().endswith(('.tiff', '.tif')):
                    format_type = "TIFF"
                    success = pixmap.save(file_path, format_type)
                else:
                    format_type = "PNG"
                    success = pixmap.save(file_path, format_type)
                
                if success:
                    print(f"A1 box area saved successfully: {file_path}")
                    print(f"Image dimensions: {capture_width}x{capture_height} pixels")
                    print(f"Box area: A1 with {margin}px margin on all sides")
                else:
                    print(f"Error: Failed to save A1 box area to {file_path}")
            
        except Exception as e:
            print(f"Error saving A1 box area: {e}")
    
    def create_small_array(self):
        """Color all shape frames black and create arrays for all boxes that contain shapes, using each box's top-left corner as (0,0)"""
        if not self.cutter_view.grid_visible:
            print("Error: Grid must be visible to create small array")
            return
        
        try:
            # First, color all shape frames black
            for item in self.cutter_view.scene.items():
                if (item != self.cutter_view.background_item and 
                    item not in self.cutter_view.grid_items and 
                    item not in self.cutter_view.grid_labels and
                    item not in self.cutter_view.cut_lines and
                    item != self.cutter_view.grid_handle and
                    (isinstance(item, ScalableRectangle) or isinstance(item, ScalableTriangle))):
                    # Set frame to black
                    item.setPen(QPen(QColor(0, 0, 0), 1))  # Black frame with 1 pixel thickness
            
            box_size = 250
            grid_cols = 6
            grid_rows = 6
            
            # Define colors for each box (same as in fill_A1_and_A2_boxes)
            box_colors = [
                QColor(255, 0, 0),      # Red
                QColor(0, 255, 0),      # Green  
                QColor(0, 0, 255),      # Blue
                QColor(255, 255, 0),    # Yellow
                QColor(255, 0, 255),    # Magenta
                QColor(0, 255, 255),    # Cyan
                QColor(255, 128, 0),    # Orange
                QColor(128, 255, 0),    # Lime
                QColor(0, 255, 128),    # Spring Green
                QColor(0, 128, 255),    # Sky Blue
                QColor(128, 0, 255),    # Purple
                QColor(255, 0, 128),    # Pink
                QColor(192, 192, 192),  # Silver
                QColor(128, 128, 128),  # Gray
                QColor(128, 0, 0),      # Maroon
                QColor(0, 128, 0),      # Dark Green
                QColor(0, 0, 128),      # Navy
                QColor(128, 128, 0),    # Olive
                QColor(128, 0, 128),    # Purple Dark
                QColor(0, 128, 128),    # Teal
                QColor(255, 192, 203),  # Light Pink
                QColor(255, 165, 0),    # Orange Red
                QColor(255, 215, 0),    # Gold
                QColor(173, 216, 230),  # Light Blue
                QColor(144, 238, 144),  # Light Green
                QColor(221, 160, 221),  # Plum
                QColor(255, 182, 193),  # Light Pink
                QColor(255, 218, 185),  # Peach
                QColor(240, 230, 140),  # Khaki
                QColor(230, 230, 250),  # Lavender
                QColor(250, 128, 114),  # Salmon
                QColor(255, 160, 122),  # Light Salmon
                QColor(176, 196, 222),  # Light Steel Blue
                QColor(205, 92, 92),    # Indian Red
                QColor(255, 105, 180),  # Hot Pink
                QColor(64, 224, 208)    # Turquoise
            ]
            
            # Dictionary to store shapes for each box
            box_shapes = {}
            
            # Process all grid boxes
            for row in range(grid_rows):
                for col in range(grid_cols):
                    # Calculate box position
                    box_x = self.cutter_view.grid_offset_x + (col * box_size)
                    box_y = self.cutter_view.grid_offset_y + (row * box_size)
                    box_rect = QRectF(box_x, box_y, box_size, box_size)
                    
                    # Calculate box index and color
                    box_index = row * grid_cols + col
                    box_color = box_colors[box_index % len(box_colors)]
                    
                    # Box name (A1, B1, C1, A2, B2, etc.)
                    box_name = chr(ord('A') + col) + str(row + 1)
                    
                    # Find shapes in this box
                    shapes_in_box = []
                    
                    for item in self.cutter_view.scene.items():
                        if (item != self.cutter_view.background_item and 
                            item not in self.cutter_view.grid_items and 
                            item not in self.cutter_view.grid_labels and
                            item not in self.cutter_view.cut_lines and
                            item != self.cutter_view.grid_handle and
                            (isinstance(item, ScalableRectangle) or isinstance(item, ScalableTriangle))):
                            
                            shape_rect = item.sceneBoundingRect()
                            shape_brush = item.brush()
                            
                            # Check if shape overlaps with this box and has the box's color
                            if box_rect.intersects(shape_rect) and shape_brush.color() == box_color:
                                # Calculate relative position from this box's top-left corner
                                relative_x = item.pos().x() - box_x
                                relative_y = item.pos().y() - box_y
                                
                                if isinstance(item, ScalableRectangle):
                                    shape_data = {
                                        'type': 'Rectangle',
                                        'x': relative_x,
                                        'y': relative_y,
                                        'width': item.rect().width(),
                                        'height': item.rect().height(),
                                        'rotation': item.rotation(),
                                        'serial_number': getattr(item, 'serial_number', 0),
                                        'fill_color': f"#{box_color.red():02X}{box_color.green():02X}{box_color.blue():02X}"
                                    }
                                else:  # ScalableTriangle
                                    shape_data = {
                                        'type': 'Triangle',
                                        'x': relative_x,
                                        'y': relative_y,
                                        'size': getattr(item, 'size', 50),
                                        'rotation': item.rotation(),
                                        'serial_number': getattr(item, 'serial_number', 0),
                                        'fill_color': f"#{box_color.red():02X}{box_color.green():02X}{box_color.blue():02X}"
                                    }
                                shapes_in_box.append(shape_data)
                    
                    # Store shapes if any found
                    if shapes_in_box:
                        box_shapes[box_name] = {
                            'shapes': shapes_in_box,
                            'color': f"#{box_color.red():02X}{box_color.green():02X}{box_color.blue():02X}",
                            'box_index': box_index
                        }
            
            # Create box_array folder and save all box arrays
            if box_shapes:
                # Get save directory
                save_dir = QFileDialog.getExistingDirectory(
                    self, "Select Directory to Save Box Arrays"
                )
                
                if save_dir:
                    # Create box_array folder
                    box_array_folder = os.path.join(save_dir, "box_array")
                    os.makedirs(box_array_folder, exist_ok=True)
                    
                    def save_box_array(box_name, box_data):
                        """Helper function to save a box array"""
                        shapes = box_data['shapes']
                        fill_color_hex = box_data['color']
                        
                        if not shapes:
                            return 0
                        
                        file_path = os.path.join(box_array_folder, f"{box_name}_array.csv")
                        
                        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                            writer = csv.writer(csvfile)
                            
                            # Write header
                            writer.writerow([
                                'Serial Number', 'Shape Type', 'X', 'Y', 'Width', 'Height', 
                                'Rotation', 'Frame Color', 'Fill Color', 'Is Filled'
                            ])
                            
                            # Write shape data
                            for shape in shapes:
                                if shape['type'] == 'Rectangle':
                                    writer.writerow([
                                        shape['serial_number'],
                                        'Rectangle',
                                        shape['x'],
                                        shape['y'],
                                        shape['width'],
                                        shape['height'],
                                        shape['rotation'],
                                        '#000000',  # Black frame
                                        fill_color_hex,
                                        'True'
                                    ])
                                else:  # Triangle
                                    writer.writerow([
                                        shape['serial_number'],
                                        'Triangle',
                                        shape['x'],
                                        shape['y'],
                                        shape['size'],
                                        shape['size'],  # Height same as width for triangles
                                        shape['rotation'],
                                        '#000000',  # Black frame
                                        fill_color_hex,
                                        'True'
                                    ])
                        
                        return len(shapes)
                    
                    # Save arrays for all boxes with shapes
                    total_boxes = 0
                    total_shapes = 0
                    
                    for box_name in sorted(box_shapes.keys()):
                        box_data = box_shapes[box_name]
                        shape_count = save_box_array(box_name, box_data)
                        total_boxes += 1
                        total_shapes += shape_count
                        
                        # Print individual box info
                        rectangles = sum(1 for s in box_data['shapes'] if s['type'] == 'Rectangle')
                        triangles = sum(1 for s in box_data['shapes'] if s['type'] == 'Triangle')
                        print(f"{box_name}: {shape_count} shapes ({rectangles} rectangles, {triangles} triangles)")
                    
                    print(f"\nBox arrays saved successfully to: {box_array_folder}")
                    print(f"Total: {total_boxes} boxes processed with {total_shapes} shapes")
                    print("Each array uses its box's top-left corner as (0,0)")
                    
                    if total_shapes == 0:
                        print("No shapes found in any boxes with their respective colors")
                        print("Make sure to run 'Cut' first to color the shapes")
            else:
                print("No shapes found in any boxes with their respective colors")
                print("Make sure to run 'Cut' first to color the shapes")
            
        except Exception as e:
            print(f"Error creating small array: {e}")
    
    def toggle_grid(self):
        """Toggle the 250x250 grid on/off"""
        if self.cutter_view.grid_visible:
            self.cutter_view.clear_grid()
        else:
            self.cutter_view.create_grid()
    
    def import_array_from_csv(self):
        """Import shape data from CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Array from CSV", "", 
            "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            try:
                shapes_created = 0
                self.cutter_view.clear_shapes()
                
                with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
                    reader = csv.reader(csvfile)
                    
                    # Skip header row
                    header = next(reader, None)
                    if not header:
                        print("Error: Empty CSV file")
                        return
                    
                    # Process each row
                    for row_num, row in enumerate(reader, start=2):
                        try:
                            if len(row) < 10:
                                print(f"Warning: Row {row_num} has insufficient data, skipping")
                                continue
                            
                            # Parse CSV data
                            serial_number = int(row[0]) if row[0] else 0
                            shape_type = row[1]
                            x = float(row[2])
                            y = float(row[3])
                            width = float(row[4])
                            height = float(row[5])
                            rotation = float(row[6]) if row[6] else 0
                            frame_color = row[7] if row[7] else "#8B4513"
                            fill_color = row[8] if row[8] else ""
                            is_filled = row[9].lower() in ('true', '1', 'yes') if row[9] else False
                            
                            # Create shape
                            if shape_type == "Triangle":
                                shape = ScalableTriangle(x, y, width)
                            else:
                                shape = ScalableRectangle(x, y, width, height)
                            
                            shape.serial_number = serial_number
                            
                            # Set rotation if specified
                            if rotation != 0:
                                shape.current_rotation = rotation
                                shape.setRotation(rotation)
                            
                            # Always keep shapes transparent with black frame - ignore saved colors
                            # This ensures all shapes are displayed as transparent regardless of CSV data
                            
                            self.cutter_view.add_shape(shape)
                            shapes_created += 1
                            
                        except (ValueError, IndexError) as e:
                            print(f"Warning: Error parsing row {row_num}: {e}, skipping")
                            continue
                
                print(f"Successfully imported {shapes_created} shapes from: {file_path}")
                
                # Center view on imported shapes if any were created
                if shapes_created > 0:
                    self.center_on_content()
                
            except Exception as e:
                print(f"Error importing CSV file: {e}")
    
    def center_on_content(self):
        """Center the view on all shapes"""
        # Get bounding rectangle of all items (excluding background)
        items_rect = None
        for item in self.cutter_view.scene.items():
            if item != self.cutter_view.background_item:
                if items_rect is None:
                    items_rect = item.sceneBoundingRect()
                else:
                    items_rect = items_rect.united(item.sceneBoundingRect())
        
        if items_rect is not None:
            # Add some padding
            padding = 50
            items_rect.adjust(-padding, -padding, padding, padding)
            self.cutter_view.fitInView(items_rect, Qt.KeepAspectRatio)
            # Don't zoom too much - limit the scale
            current_scale = self.cutter_view.transform().m11()
            if current_scale > 2.0:  # If zoomed in too much, zoom out a bit
                self.cutter_view.scale(0.5, 0.5)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CutterWindow()
    window.show()
    sys.exit(app.exec_())
