import sys
import math
from PyQt5.QtWidgets import (QApplication, QMainWindow, QGraphicsScene, 
                           QGraphicsView, QVBoxLayout, QWidget, QMenuBar, 
                           QMenu, QAction, QFileDialog, QHBoxLayout, QPushButton,
                           QGraphicsRectItem, QGraphicsPixmapItem, QLineEdit, QLabel,
                           QGraphicsLineItem, QGraphicsPathItem, QSlider, QGridLayout)
from PyQt5.QtCore import Qt, QRectF, QPointF, QTimer
from PyQt5.QtGui import QBrush, QPen, QColor, QPixmap, QPainter, QTransform, QPainterPath, QCursor

class ScalableRectangle(QGraphicsRectItem):
    # Class variable to track rectangle creation order
    _next_serial_number = 1
    
    def __init__(self, x, y, width, height, initial_color=None):
        super().__init__(x, y, width, height)
        self.setFlag(QGraphicsRectItem.ItemIsMovable, True)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsRectItem.ItemSendsGeometryChanges, True)
        
        # Set appearance
        self.setPen(QPen(QColor(139, 69, 19), 0.5))  # Brown frame (saddle brown)
        
        # Enable mouse tracking for selection
        self.setAcceptHoverEvents(True)
        self.current_rotation = 0  # Track current rotation angle
        self.is_filled = False  # Track if rectangle is filled with average color
        self.fill_color = Qt.transparent  # Store the fill color
        
        # Set initial color if provided - only for frame/border
        if initial_color and initial_color != Qt.transparent:
            self.setPen(QPen(initial_color, 0.5))  # Apply color to frame with thinnest width
        else:
            self.setPen(QPen(QColor(139, 69, 19), 0.5))  # Default brown frame with thinnest width
        
        self.setBrush(QBrush(Qt.transparent))  # Always transparent fill
        
        # Assign serial number and increment for next rectangle
        self.serial_number = ScalableRectangle._next_serial_number
        ScalableRectangle._next_serial_number += 1
        
        # Set rotation center to the center of the rectangle
        # The transform origin should be relative to the rectangle's bounds
        rect_center = self.rect().center()
        self.setTransformOriginPoint(rect_center)
        
    def boundingRect(self):
        # Use standard bounding rect
        return super().boundingRect()
    
    def paint(self, painter, option, widget):
        # Determine if we should check for overlaps (avoid during batch operations or zooming)
        should_check_overlaps = not ((hasattr(self.scene(), 'batch_operation') and self.scene().batch_operation) or \
                                   (hasattr(self.scene(), 'is_zooming') and self.scene().is_zooming))
        
        # Check for overlaps if allowed, otherwise use cached state
        if should_check_overlaps:
            overlapping = self.check_for_overlaps()
            # Cache the overlap state for use during zoom
            self._cached_overlapping = overlapping
        else:
            # Use cached overlap state if available, otherwise assume no overlap
            overlapping = getattr(self, '_cached_overlapping', False)
        
        if overlapping:
            # Change appearance for overlapping rectangles
            painter.setPen(QPen(Qt.red, 0.5))  # Thinnest possible red frame
            painter.setBrush(QBrush(QColor(255, 0, 0, 100)))  # Semi-transparent red fill
        else:
            # Normal appearance - use the rectangle's pen and transparent brush
            painter.setPen(self.pen())
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
        self.setRotation(self.current_rotation)
    
    def rotate_counter_clockwise(self):
        # Rotate 1 degree counter-clockwise
        self.current_rotation -= 1
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
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
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
        self.original_background_pixmap = None  # Store original background
        
        # Performance optimization flag
        self.scene.batch_operation = False
        self.scene.is_zooming = False  # Flag to prevent overlap checking during zoom
        #jj
        # Drawing mode variables
        self.drawing_mode = False
        self.drawing_path = []
        self.current_path_item = None
        self.is_drawing = False
        self.rectangle_spacing = 1.3  # Default spacing multiplier
        self.parallel_mode = False  # Parallel line mode
        self.parallel_distance_multiplier = 0.7  # Distance multiplier for parallel lines
        self.parallel_lines_count = 1  # Number of parallel lines on each side
        self.second_line_spacing = 1.5  # Spacing multiplier for second parallel line
        self.third_line_spacing = 1.7  # Spacing multiplier for third parallel line
        self.fourth_line_spacing = 1.8  # Spacing multiplier for fourth parallel line
        self.fifth_line_spacing = 1.85  # Spacing multiplier for fifth parallel line
        
        # Edge mode variables - separate from parallel mode
        self.edge_distance_multiplier = 0.6  # Distance multiplier for edge mode side lines
        self.edge_lines_count = 2  # Number of side lines on each side in edge mode
        self.edge_first_line_spacing = 1.5  # Spacing multiplier for first edge side line
        self.edge_second_line_spacing = 1.8  # Spacing multiplier for second edge side line
        self.edge_third_line_spacing = 2.0  # Spacing multiplier for third edge side line
        self.edge_fourth_line_spacing = 2.0  # Spacing multiplier for fourth edge side line
        self.edge_fifth_line_spacing = 2.0  # Spacing multiplier for fifth edge side line
        
        # Circle mode variables
        self.circle_mode = False  # Circle drawing mode
        self.circle_radius = 7  # Number of rectangles in circle radius
        
        # Half rectangle mode
        self.half_rectangle_mode = False  # Half rectangle mode
        
        # Erase mode variables
        self.erase_mode = False  # Erase mode
        self.is_erasing = False  # Track if currently erasing with drag
        self.erased_rectangles = []  # Track rectangles erased in current operation
        
        # Edge mode variables
        self.edge_mode = False  # Edge mode for drawing central half rectangles with regular rectangles on sides
        
        # Enable keyboard events
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Create custom drawing cursor
        self.drawing_cursor = self.create_drawing_cursor()
        
        # Create circle cursor for circle mode
        self.circle_cursor = self.create_circle_cursor()
        
        # Create erase cursor for erase mode
        self.erase_cursor = self.create_erase_cursor()
        
        # Set initial cursor
        self.setCursor(Qt.ArrowCursor)
        
    def create_drawing_cursor(self):
        """Create a 3x3 black square cursor"""
        # Create a 3x3 pixmap
        pixmap = QPixmap(3, 3)
        pixmap.fill(QColor(0, 0, 0))  # Fill with black
        
        # Create cursor with the pixmap, hotspot at center (1, 1)
        cursor = QCursor(pixmap, 1, 1)
        return cursor
    
    def create_circle_cursor(self):
        """Create a small circle cursor for circle mode"""
        # Create a 15x15 pixmap for the circle cursor
        size = 15
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)  # Transparent background
        
        # Create painter to draw the circle
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw a small circle outline
        pen = QPen(QColor(139, 69, 19), 2)  # Brown color, 2px width
        painter.setPen(pen)
        painter.setBrush(QBrush(Qt.transparent))
        
        # Draw circle with some margin from edges
        margin = 2
        painter.drawEllipse(margin, margin, size - 2*margin, size - 2*margin)
        
        painter.end()
        
        # Create cursor with the circle pixmap, hotspot at center
        cursor = QCursor(pixmap, size//2, size//2)
        return cursor
    
    def create_erase_cursor(self):
        """Create a small green frame cursor for erase mode"""
        # Create a 15x15 pixmap for the erase cursor
        size = 15
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)  # Transparent background
        
        # Create painter to draw the frame
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw a small green frame outline
        pen = QPen(QColor(0, 255, 0), 2)  # Green color, 2px width
        painter.setPen(pen)
        painter.setBrush(QBrush(Qt.transparent))
        
        # Draw rectangle frame with some margin from edges
        margin = 2
        painter.drawRect(margin, margin, size - 2*margin, size - 2*margin)
        
        painter.end()
        
        # Create cursor with the frame pixmap, hotspot at center
        cursor = QCursor(pixmap, size//2, size//2)
        return cursor
        
    def wheelEvent(self, event):
        # Set zoom flag to prevent overlap checking during zoom
        self.scene.is_zooming = True
        
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
        
        # Clear zoom flag after a short delay to allow all paint events to complete
        QTimer.singleShot(100, lambda: setattr(self.scene, 'is_zooming', False))
    
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
        
        # Store the original scaled pixmap
        self.original_background_pixmap = scaled_pixmap
        
        # Add the background
        self.background_item = QGraphicsPixmapItem(scaled_pixmap)
        self.background_item.setZValue(-1)  # Put it behind everything
        self.scene.addItem(self.background_item)
        
        # Update scene rect to fit the scaled image
        self.scene.setSceneRect(QRectF(scaled_pixmap.rect()))
    
    def add_rectangle(self, x, y, width=100, height=100, color=None):
        rect = ScalableRectangle(x, y, width, height, color)
        self.scene.addItem(rect)
        
        # Track for undo if main window exists and not in batch operation
        if self.main_window and not (hasattr(self.scene, 'batch_operation') and self.scene.batch_operation):
            self.main_window.add_to_undo_stack('add_rectangles', [rect])
        
        return rect
    
    def remove_overlapping_rectangles(self):
        """Remove overlapping rectangles, keeping the older one (lower serial number) - using existing overlap detection"""
        rectangles = []
        for item in self.scene.items():
            if isinstance(item, ScalableRectangle):
                rectangles.append(item)
        
        if len(rectangles) < 2:
            return 0  # No overlaps possible with less than 2 rectangles
        
        rectangles_to_remove = []
        
        # Use existing check_for_overlaps method for each rectangle
        for rect in rectangles:
            if rect in rectangles_to_remove:
                continue
                
            # Use the existing optimized overlap detection
            if rect.check_for_overlaps():
                # Find which specific rectangles this one overlaps with
                search_rect = rect.sceneBoundingRect().adjusted(-50, -50, 50, 50)
                nearby_items = self.scene.items(search_rect)
                
                for item in nearby_items:
                    if (isinstance(item, ScalableRectangle) and 
                        item != rect and 
                        item not in rectangles_to_remove and
                        rect.collidesWithItem(item)):
                        
                        # Remove the one with the higher serial number (created later)
                        if rect.serial_number > item.serial_number:
                            rectangles_to_remove.append(rect)
                            break  # No need to check this rectangle further
                        else:
                            rectangles_to_remove.append(item)
        
        # Remove the overlapping rectangles
        for rect in rectangles_to_remove:
            self.scene.removeItem(rect)
        
        # Force update of remaining rectangles to clear red coloring
        for rect in rectangles:
            if rect not in rectangles_to_remove:
                rect.update()
        
        return len(rectangles_to_remove)
    
    def create_circle_of_rectangles(self, center_pos):
        """Create a circle of rectangles around a center position with a central rectangle at 45 degrees"""
        # Get selected color
        color = self.main_window.selected_color if self.main_window else None
        
        # Create central rectangle at 45 degrees
        center_rect = self.add_rectangle(
            center_pos.x() - self.rectangle_size/2,
            center_pos.y() - self.rectangle_size/2,
            self.rectangle_size,
            self.rectangle_size,
            color
        )
        center_rect.current_rotation = 45
        center_rect.setRotation(45)
        
        # Calculate the diagonal size of rectangle (when rotated, this is the maximum span)
        diagonal_size = self.rectangle_size * math.sqrt(2)
        
        # Create circles of rectangles around the center
        for radius in range(1, self.circle_radius + 1):
            # Calculate radius distance - minimal spacing to prevent overlap
            # Use diagonal size plus minimal gap to prevent touching
            minimal_gap = self.rectangle_size * 0.02  # Increase gap slightly to prevent overlap
            
            # Make outer circles progressively smaller and closer but avoid overlap
            if radius == 1:
                # First circle: normal spacing
                radius_distance = radius * (diagonal_size + minimal_gap)
            elif radius == 2:
                # Second circle: make it smaller (more compressed)
                compression_factor = 0.75  # More aggressive compression for second circle only
                base_distance = radius * (diagonal_size + minimal_gap)
                compressed_distance = base_distance * compression_factor
                
                # Ensure minimum distance from first circle
                prev_radius_distance = diagonal_size + minimal_gap  # First circle distance
                min_safe_distance = prev_radius_distance + diagonal_size + minimal_gap
                radius_distance = max(compressed_distance, min_safe_distance)
            else:
                # Third circle and beyond: use NORMAL spacing (no compression)
                radius_distance = radius * (diagonal_size + minimal_gap)
                
                # Ensure minimum distance from previous circle
                if radius == 3:
                    # Previous circle was the compressed second circle - calculate its actual distance
                    second_circle_base = 2 * (diagonal_size + minimal_gap)
                    second_circle_compressed = second_circle_base * 0.75
                    second_circle_safe = (diagonal_size + minimal_gap) + diagonal_size + minimal_gap
                    prev_radius_distance = max(second_circle_compressed, second_circle_safe)
                else:
                    # For radius 4+, previous circle used normal spacing
                    prev_radius_distance = (radius - 1) * (diagonal_size + minimal_gap)
                
                min_safe_distance = prev_radius_distance + diagonal_size + minimal_gap
                radius_distance = max(radius_distance, min_safe_distance)
            
            # Calculate the circumference at this radius
            circumference = 2 * math.pi * radius_distance
            
            # Calculate number of rectangles needed to fit around the circle
            # Use diagonal size plus minimal gap for tight packing
            space_per_rectangle = diagonal_size + minimal_gap
            num_rectangles = max(4, int(circumference / space_per_rectangle))
            
            # Create rectangles evenly spaced around the circle
            for i in range(num_rectangles):
                angle = (2 * math.pi * i) / num_rectangles
                
                # Calculate position on circle
                rect_x = center_pos.x() + radius_distance * math.cos(angle) - self.rectangle_size/2
                rect_y = center_pos.y() + radius_distance * math.sin(angle) - self.rectangle_size/2
                
                # Get selected color
                color = self.main_window.selected_color if self.main_window else None
                
                # Create rectangle
                rect = self.add_rectangle(rect_x, rect_y, self.rectangle_size, self.rectangle_size, color)
                
                # Rotate rectangle to point towards center (tangent to circle)
                angle_degrees = math.degrees(angle) + 90  # +90 to make it tangent
                
                rect.current_rotation = angle_degrees
                rect.setRotation(angle_degrees)
        
        # Check if auto overlap removal is enabled
        if self.main_window and hasattr(self.main_window, 'auto_overlap_checkbox') and self.main_window.auto_overlap_checkbox.isChecked():
            removed_count = self.remove_overlapping_rectangles()
            if removed_count > 0 and hasattr(self.main_window, 'status_label'):
                self.main_window.status_label.setText(f"Circle created - Auto-removed {removed_count} overlapping rectangles")
    

    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_T:
            # Add rectangle at center of current view when 'T' is pressed
            center = self.mapToScene(self.rect().center())
            rect_x = center.x() - self.rectangle_size/2
            rect_y = center.y() - self.rectangle_size/2
            color = self.main_window.selected_color if self.main_window else None
            
            if self.half_rectangle_mode:
                # Add half-width rectangle
                half_width = self.rectangle_size / 2
                rect_x = center.x() - half_width/2
                self.add_rectangle(rect_x, rect_y, half_width, self.rectangle_size, color)
            else:
                # Add full rectangle
                self.add_rectangle(rect_x, rect_y, self.rectangle_size, self.rectangle_size, color)
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
            rect_x = center.x() - half_width/2
            rect_y = center.y() - self.rectangle_size/2
            color = self.main_window.selected_color if self.main_window else None
            
            self.add_rectangle(rect_x, rect_y, half_width, self.rectangle_size, color)
        elif event.key() == Qt.Key_O:
            # Add rectangle with half the size when 'O' is pressed
            center = self.mapToScene(self.rect().center())
            half_size = self.rectangle_size / 2
            rect_x = center.x() - half_size/2
            rect_y = center.y() - half_size/2
            color = self.main_window.selected_color if self.main_window else None
            
            self.add_rectangle(rect_x, rect_y, half_size, half_size, color)
        elif event.key() == Qt.Key_D:
            # Toggle drawing mode
            self.drawing_mode = not self.drawing_mode
            if self.drawing_mode:
                self.setDragMode(QGraphicsView.NoDrag)
                # Use circle cursor if circle mode is on, otherwise use drawing cursor
                if self.circle_mode:
                    self.setCursor(self.circle_cursor)
                else:
                    self.setCursor(self.drawing_cursor)
            else:
                self.setDragMode(QGraphicsView.RubberBandDrag)
                # Use circle cursor if circle mode is on, otherwise use default cursor
                if self.circle_mode:
                    self.setCursor(self.circle_cursor)
                else:
                    self.setCursor(Qt.ArrowCursor)
        else:
            super().keyPressEvent(event)
    
    def set_rectangle_size(self, size):
        """Set the size for new rectangles"""
        self.rectangle_size = size
    
    def set_rectangle_spacing(self, spacing):
        """Set the spacing multiplier for rectangles along drawn lines"""
        self.rectangle_spacing = spacing
    
    def set_parallel_distance(self, distance):
        """Set the distance multiplier for parallel lines"""
        self.parallel_distance_multiplier = distance
    
    def set_parallel_lines_count(self, count):
        """Set the number of parallel lines on each side"""
        self.parallel_lines_count = count
    
    def set_second_line_spacing(self, spacing):
        """Set the spacing multiplier for the second parallel line"""
        self.second_line_spacing = spacing
    
    def set_third_line_spacing(self, spacing):
        """Set the spacing multiplier for the third parallel line"""
        self.third_line_spacing = spacing
    
    def set_fourth_line_spacing(self, spacing):
        """Set the spacing multiplier for the fourth parallel line"""
        self.fourth_line_spacing = spacing
    
    def set_fifth_line_spacing(self, spacing):
        """Set the spacing multiplier for the fifth parallel line"""
        self.fifth_line_spacing = spacing
    
    def set_edge_distance(self, distance):
        """Set the distance multiplier for edge mode side lines"""
        self.edge_distance_multiplier = distance
    
    def set_edge_lines_count(self, count):
        """Set the number of side lines on each side in edge mode"""
        self.edge_lines_count = count
    
    def set_edge_first_line_spacing(self, spacing):
        """Set the spacing multiplier for the first edge side line"""
        self.edge_first_line_spacing = spacing
    
    def set_edge_second_line_spacing(self, spacing):
        """Set the spacing multiplier for the second edge side line"""
        self.edge_second_line_spacing = spacing
    
    def set_edge_third_line_spacing(self, spacing):
        """Set the spacing multiplier for the third edge side line"""
        self.edge_third_line_spacing = spacing
    
    def set_edge_fourth_line_spacing(self, spacing):
        """Set the spacing multiplier for the fourth edge side line"""
        self.edge_fourth_line_spacing = spacing
    
    def set_edge_fifth_line_spacing(self, spacing):
        """Set the spacing multiplier for the fifth edge side line"""
        self.edge_fifth_line_spacing = spacing
    
    def set_parallel_mode(self, enabled):
        """Enable or disable parallel line mode"""
        self.parallel_mode = enabled
    
    def set_circle_mode(self, enabled):
        """Enable or disable circle drawing mode"""
        self.circle_mode = enabled
        
        # Update cursor based on circle mode
        if self.circle_mode:
            self.setCursor(self.circle_cursor)
        else:
            # Reset to appropriate cursor based on current mode
            if self.drawing_mode:
                self.setCursor(self.drawing_cursor)
            else:
                self.setCursor(Qt.ArrowCursor)
    
    def set_half_rectangle_mode(self, enabled):
        """Enable or disable half rectangle mode"""
        self.half_rectangle_mode = enabled
    
    def set_erase_mode(self, enabled):
        """Enable or disable erase mode"""
        self.erase_mode = enabled
        
        # Update cursor based on erase mode
        if self.erase_mode:
            self.setCursor(self.erase_cursor)
        else:
            # Reset to appropriate cursor based on current mode
            if self.circle_mode:
                self.setCursor(self.circle_cursor)
            elif self.drawing_mode:
                self.setCursor(self.drawing_cursor)
            else:
                self.setCursor(Qt.ArrowCursor)
    
    def set_edge_mode(self, enabled):
        """Enable or disable edge mode"""
        self.edge_mode = enabled
        
        # Edge mode uses the same cursor as drawing mode
        if self.edge_mode:
            self.setCursor(self.drawing_cursor)
        else:
            # Reset to appropriate cursor based on current mode
            if self.erase_mode:
                self.setCursor(self.erase_cursor)
            elif self.circle_mode:
                self.setCursor(self.circle_cursor)
            elif self.drawing_mode:
                self.setCursor(self.drawing_cursor)
            else:
                self.setCursor(Qt.ArrowCursor)
    
    def erase_rectangles_at_position(self, pos):
        """Erase any rectangles at the given position"""
        # Get the scene position
        scene_pos = self.mapToScene(pos)
        
        # Find rectangles at this position
        items_at_pos = self.scene.items(scene_pos)
        rectangles_to_remove = []
        
        for item in items_at_pos:
            if isinstance(item, ScalableRectangle):
                rectangles_to_remove.append(item)
        
        # Remove the rectangles
        for rect in rectangles_to_remove:
            self.scene.removeItem(rect)
        
        return rectangles_to_remove
    

    
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
        if self.erase_mode and event.button() == Qt.LeftButton:
            # Start erasing on left click
            self.is_erasing = True
            self.erased_rectangles = []  # Track erased rectangles for undo
            erased = self.erase_rectangles_at_position(event.pos())
            self.erased_rectangles.extend(erased)
        elif self.circle_mode and event.button() == Qt.LeftButton:
            # Track rectangles before creating circle
            rectangles_before = [item for item in self.scene.items() if isinstance(item, ScalableRectangle)]
            
            # Create a circle of rectangles at the click position
            click_pos = self.mapToScene(event.pos())
            self.create_circle_of_rectangles(click_pos)
            
            # Track new rectangles for undo
            rectangles_after = [item for item in self.scene.items() if isinstance(item, ScalableRectangle)]
            new_rectangles = [rect for rect in rectangles_after if rect not in rectangles_before]
            
            if new_rectangles and self.main_window:
                self.main_window.add_to_undo_stack('add_rectangles', new_rectangles)
        elif (self.drawing_mode or self.edge_mode) and event.button() == Qt.LeftButton:
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
        if self.erase_mode and self.is_erasing:
            # Continue erasing while dragging
            erased = self.erase_rectangles_at_position(event.pos())
            self.erased_rectangles.extend(erased)
        elif (self.drawing_mode or self.edge_mode) and self.is_drawing and self.current_path_item:
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
        if self.erase_mode and event.button() == Qt.LeftButton and self.is_erasing:
            # Stop erasing and add to undo stack
            self.is_erasing = False
            if self.erased_rectangles and self.main_window:
                self.main_window.add_to_undo_stack('erase_rectangles', self.erased_rectangles)
            self.erased_rectangles = []
        elif (self.drawing_mode or self.edge_mode) and event.button() == Qt.LeftButton and self.is_drawing:
            # Finish drawing and create rectangles along the path
            self.is_drawing = False
            
            # Remove the temporary path visual
            if self.current_path_item:
                self.scene.removeItem(self.current_path_item)
                self.current_path_item = None
            
            # Track rectangles before creating them
            rectangles_before = [item for item in self.scene.items() if isinstance(item, ScalableRectangle)]
            
            # Create rectangles along the drawn path
            self.create_rectangles_along_path()
            
            # If parallel mode is enabled, create parallel paths
            if self.parallel_mode:
                self.create_parallel_paths()
            
            # Track new rectangles for undo
            rectangles_after = [item for item in self.scene.items() if isinstance(item, ScalableRectangle)]
            new_rectangles = [rect for rect in rectangles_after if rect not in rectangles_before]
            
            if new_rectangles and self.main_window:
                self.main_window.add_to_undo_stack('add_rectangles', new_rectangles)
            
            # Check if auto overlap removal is enabled
            if self.main_window and hasattr(self.main_window, 'auto_overlap_checkbox') and self.main_window.auto_overlap_checkbox.isChecked():
                removed_count = self.remove_overlapping_rectangles()
                if removed_count > 0 and hasattr(self.main_window, 'status_label'):
                    self.main_window.status_label.setText(f"Auto-removed {removed_count} overlapping rectangles")
            
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
        
        # Smooth the path by averaging neighboring points
        self.smoothed_path = self.smooth_path(self.drawing_path)
        
        if self.edge_mode:
            # Edge mode: create central half rectangles and regular rectangles on sides
            self.create_edge_rectangles_along_path(self.smoothed_path)
        elif not self.parallel_mode:
            # Only create rectangles on the main line if parallel mode is NOT enabled
            # Use half rectangles if half rectangle mode is enabled
            if self.half_rectangle_mode:
                self.create_half_rectangles_along_path(self.smoothed_path)
            else:
                self.create_rectangles_along_specific_path(self.smoothed_path)
        
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
        """Calculate a smooth angle using immediate local direction"""
        
        # Get the current position
        p1 = path[segment_idx]
        p2 = path[segment_idx + 1]
        current_x = p1.x() + ratio * (p2.x() - p1.x())
        current_y = p1.y() + ratio * (p2.y() - p1.y())
        
        # Simple approach: use a small window around the current position
        # Look at points immediately before and after
        
        # Find the best points for direction calculation
        # Look for points that are approximately 1-2 rectangle sizes away
        target_distance = self.rectangle_size * 1.5;
        
        # Search backwards from current position
        back_point = None
        for i in range(segment_idx, -1, -1):
            if i == segment_idx:
                # For current segment, check if we should use previous point or current position
                if ratio > 0.5:
                    test_point = QPointF(current_x, current_y)
                else:
                    test_point = path[i]
            else:
                test_point = path[i]
            
            dx = test_point.x() - current_x
            dy = test_point.y() - current_y
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance >= target_distance * 0.8:  # Found a good back point
                back_point = test_point
                break
        
        # Search forwards from current position
        forward_point = None
        for i in range(segment_idx, len(path)):
            if i == segment_idx:
                # For current segment, check if we should use next point or current position
                if ratio < 0.5:
                    test_point = QPointF(current_x, current_y)
                else:
                    test_point = path[i + 1] if i + 1 < len(path) else path[i]
            else:
                test_point = path[i]
            
            dx = test_point.x() - current_x
            dy = test_point.y() - current_y
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance >= target_distance * 0.8:  # Found a good forward point
                forward_point = test_point
                break
        
        # Calculate direction vector
        if back_point and forward_point:
            # Use the two reference points
            direction_x = forward_point.x() - back_point.x()
            direction_y = forward_point.y() - back_point.y()
        elif forward_point:
            # Only forward point available
            direction_x = forward_point.x() - current_x
            direction_y = forward_point.y() - current_y
        elif back_point:
            # Only back point available
            direction_x = current_x - back_point.x()
            direction_y = current_y - back_point.y()
        else:
            # Fallback to current segment
            direction_x = p2.x() - p1.x()
            direction_y = p2.y() - p1.y()
        
        # Calculate angle
        if direction_x != 0 or direction_y != 0:
            angle_radians = math.atan2(direction_y, direction_x)
            angle_degrees = math.degrees(angle_radians)
            
            return angle_degrees
        
        return 0
    
    def create_parallel_paths(self):
        """Create parallel paths on both sides of the drawn line"""
        if not hasattr(self, 'smoothed_path') or len(self.smoothed_path) < 2:
            return
        
        # Use the configurable parallel distance multiplier from the text input
        base_parallel_distance = self.rectangle_size * self.parallel_distance_multiplier
        
        # First, create a resampled version of the smoothed path with consistent point spacing
        # This ensures parallel lines have the same point density as the main line
        resampled_path = self.resample_path_by_distance(self.smoothed_path)
        
        # Create multiple parallel paths on each side
        for line_index in range(1, self.parallel_lines_count + 1):
            # Calculate distance for this line with better spacing
            # Keep first line close, increase spacing for second line, then larger spacing for additional lines
            if line_index == 1:
                # First line: use original spacing
                parallel_distance = base_parallel_distance * line_index
            elif line_index == 2:
                # Second line: use configurable spacing multiplier
                parallel_distance = base_parallel_distance * line_index * self.second_line_spacing
            elif line_index == 3:
                # Third line: use configurable spacing multiplier
                parallel_distance = base_parallel_distance * line_index * self.third_line_spacing
            elif line_index == 4:
                # Fourth line: use configurable spacing multiplier
                parallel_distance = base_parallel_distance * line_index * self.fourth_line_spacing
            elif line_index == 5:
                # Fifth line: use configurable spacing multiplier
                parallel_distance = base_parallel_distance * line_index * self.fifth_line_spacing
            else:
                # Additional lines (6+): use larger spacing to prevent overlap
                spacing_multiplier = 1.5  # Increase spacing for lines 6+
                parallel_distance = base_parallel_distance * (6.0 + (line_index - 5) * spacing_multiplier)
            
            # Create parallel paths by offsetting each point of the resampled path
            left_path = []
            right_path = []
            
            # For each point in the resampled path, calculate the perpendicular offset
            for i in range(len(resampled_path)):
                current_point = resampled_path[i]
                
                # Calculate the direction at this point
                if i == 0:
                    # First point: use direction to next point
                    next_point = resampled_path[i + 1]
                    direction_x = next_point.x() - current_point.x()
                    direction_y = next_point.y() - current_point.y()
                elif i == len(resampled_path) - 1:
                    # Last point: use direction from previous point
                    prev_point = resampled_path[i - 1]
                    direction_x = current_point.x() - prev_point.x()
                    direction_y = current_point.y() - prev_point.y()
                else:
                    # Middle points: use average direction of neighboring segments
                    prev_point = resampled_path[i - 1]
                    next_point = resampled_path[i + 1]
                    
                    # Direction from previous to current
                    dir1_x = current_point.x() - prev_point.x()
                    dir1_y = current_point.y() - prev_point.y()
                    
                    # Direction from current to next
                    dir2_x = next_point.x() - current_point.x()
                    dir2_y = next_point.y() - current_point.y()
                    
                    # Average the two directions for smoother curves
                    direction_x = (dir1_x + dir2_x) / 2
                    direction_y = (dir1_y + dir2_y) / 2
                
                # Normalize the direction vector
                length = (direction_x * direction_x + direction_y * direction_y) ** 0.5
                if length > 0:
                    unit_x = direction_x / length
                    unit_y = direction_y / length
                    
                    # Calculate perpendicular vector (90 degrees rotated)
                    perp_x = -unit_y
                    perp_y = unit_x
                    
                    # Calculate parallel points
                    left_point = QPointF(
                        current_point.x() + perp_x * parallel_distance,
                        current_point.y() + perp_y * parallel_distance
                    )
                    right_point = QPointF(
                        current_point.x() - perp_x * parallel_distance,
                        current_point.y() - perp_y * parallel_distance
                    )
                    
                    left_path.append(left_point)
                    right_path.append(right_point)
            
            # Create rectangles along the parallel paths using the same algorithm as main line
            if left_path:
                self.create_rectangles_along_specific_path(left_path)
                
            if right_path:
                self.create_rectangles_along_specific_path(right_path)
    
    def resample_path_by_distance(self, path):
        """Resample a path to have consistent point spacing based on rectangle spacing"""
        if len(path) < 2:
            return path
        
        # Calculate the target spacing between points
        target_spacing = self.rectangle_size * self.rectangle_spacing
        
        # Create a new path with consistent spacing
        resampled = [path[0]]  # Always include the first point
        
        # Calculate total path length and segments
        path_segments = []
        total_distance = 0
        
        for i in range(len(path) - 1):
            p1 = path[i]
            p2 = path[i + 1]
            distance = ((p2.x() - p1.x()) ** 2 + (p2.y() - p1.y()) ** 2) ** 0.5
            path_segments.append((p1, p2, distance))
            total_distance += distance
        
        # Sample points at regular intervals
        current_distance = 0
        target_distance = target_spacing
        
        for p1, p2, segment_distance in path_segments:
            while target_distance <= current_distance + segment_distance:
                # Calculate position along this segment
                if segment_distance > 0:
                    ratio = (target_distance - current_distance) / segment_distance
                    x = p1.x() + ratio * (p2.x() - p1.x())
                    y = p1.y() + ratio * (p2.y() - p1.y())
                    resampled.append(QPointF(x, y))
                
                target_distance += target_spacing
            
            current_distance += segment_distance
        
        # Always include the last point if it's not too close to the last resampled point
        if len(resampled) > 0:
            last_point = path[-1]
            last_resampled = resampled[-1]
            distance_to_last = ((last_point.x() - last_resampled.x()) ** 2 + 
                               (last_point.y() - last_resampled.y()) ** 2) ** 0.5
            if distance_to_last > target_spacing * 0.5:  # If it's far enough away
                resampled.append(last_point)
        
        return resampled
    
    def create_rectangles_along_specific_path(self, path):
        """Create rectangles along a specific path (used for parallel lines)"""
        if len(path) < 2:
            return
        
        # Calculate spacing between rectangles based on rectangle size
        spacing = self.rectangle_size * self.rectangle_spacing
        
        # Sample points along the path at regular intervals
        total_distance = 0
        path_segments = []
        
        # Calculate distances between consecutive points
        for i in range(len(path) - 1):
            p1 = path[i]
            p2 = path[i + 1]
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
                    
                    # Calculate smooth angle using the parallel path
                    angle_degrees = self.calculate_smooth_angle(path, segment_idx, ratio)
                    
                    # Get selected color
                    color = self.main_window.selected_color if self.main_window else None
                    
                    # Create rectangle at this position
                    rect_x = x - self.rectangle_size/2
                    rect_y = y - self.rectangle_size/2
                    rect = self.add_rectangle(rect_x, rect_y, self.rectangle_size, self.rectangle_size, color)
                    
                    # Rotate the rectangle to match the smooth angle
                    rect.current_rotation = angle_degrees
                    rect.setRotation(angle_degrees)
                
                target_distance += spacing
            
            current_distance += segment_distance
    
    def create_half_rectangles_along_path(self, path):
        """Create half-width rectangles along a specific path (only for single line drawing)"""
        if len(path) < 2:
            return
        
        # Calculate spacing between rectangles based on rectangle size
        spacing = self.rectangle_size * self.rectangle_spacing
        
        # Sample points along the path at regular intervals
        total_distance = 0
        path_segments = []
        
        # Calculate distances between consecutive points
        for i in range(len(path) - 1):
            p1 = path[i]
            p2 = path[i + 1]
            distance = ((p2.x() - p1.x()) ** 2 + (p2.y() - p1.y()) ** 2) ** 0.5
            path_segments.append((p1, p2, distance))
            total_distance += distance
        
        # Place half rectangles at regular intervals
        current_distance = 0
        target_distance = 0
        
        for segment_idx, (p1, p2, segment_distance) in enumerate(path_segments):
            while target_distance <= current_distance + segment_distance:
                # Calculate position along this segment
                if segment_distance > 0:
                    ratio = (target_distance - current_distance) / segment_distance
                    x = p1.x() + ratio * (p2.x() - p1.x())
                    y = p1.y() + ratio * (p2.y() - p1.y())
                    
                    # Calculate smooth angle using the path
                    angle_degrees = self.calculate_smooth_angle(path, segment_idx, ratio)
                    
                    # Get selected color
                    color = self.main_window.selected_color if self.main_window else None
                    
                    # Create half-width rectangle at this position
                    # For half rectangle mode, we want the long side along the line
                    # So we create with full width and half height, with no additional rotation
                    half_height = self.rectangle_size / 2
                    rect_x = x - self.rectangle_size/2
                    rect_y = y - half_height/2
                    rect = self.add_rectangle(rect_x, rect_y, self.rectangle_size, half_height, color)
                    
                    # Rotate the rectangle to match the smooth angle (no additional offset)
                    # This makes the long side align with the drawn line
                    rect.current_rotation = angle_degrees
                    rect.setRotation(angle_degrees)
                
                target_distance += spacing
            
            current_distance += segment_distance

    def create_edge_rectangles_along_path(self, path):
        """Create edge rectangles: central half rectangles with multiple regular rectangles on both sides using dedicated edge variables"""
        if len(path) < 2:
            return
        
        # Calculate spacing between rectangles based on rectangle size
        spacing = self.rectangle_size * self.rectangle_spacing
        
        # Calculate base side distance using edge-specific distance multiplier
        base_edge_distance = self.rectangle_size * self.edge_distance_multiplier
        
        # First, create a resampled version of the path with consistent point spacing
        resampled_path = self.resample_path_by_distance(path)
        
        # Create center half rectangles along the main path
        self.create_half_rectangles_along_path(resampled_path)
        
        # Create multiple side paths using edge-specific variables
        # Calculate cumulative distances to prevent overlaps
        edge_line_distances = []
        
        for line_index in range(1, self.edge_lines_count + 1):
            if line_index == 1:
                # First edge line: use edge-specific first line spacing
                edge_distance = base_edge_distance * self.edge_first_line_spacing
            elif line_index == 2:
                # Second edge line: use cumulative spacing
                prev_distance = edge_line_distances[0]  # First line distance
                spacing_addition = base_edge_distance * self.edge_second_line_spacing
                edge_distance = prev_distance + spacing_addition
            elif line_index == 3:
                # Third edge line: use cumulative spacing
                prev_distance = edge_line_distances[1]  # Second line distance
                spacing_addition = base_edge_distance * self.edge_third_line_spacing
                edge_distance = prev_distance + spacing_addition
            elif line_index == 4:
                # Fourth edge line: use cumulative spacing
                prev_distance = edge_line_distances[2]  # Third line distance
                spacing_addition = base_edge_distance * self.edge_fourth_line_spacing
                edge_distance = prev_distance + spacing_addition
            elif line_index == 5:
                # Fifth edge line: use cumulative spacing
                prev_distance = edge_line_distances[3]  # Fourth line distance
                spacing_addition = base_edge_distance * self.edge_fifth_line_spacing
                edge_distance = prev_distance + spacing_addition
            else:
                # Additional edge lines (6+): use consistent spacing
                prev_distance = edge_line_distances[line_index - 2]  # Previous line distance
                spacing_addition = base_edge_distance * 1.5  # Default spacing for additional lines
                edge_distance = prev_distance + spacing_addition
            
            # Store this distance for next iteration
            edge_line_distances.append(edge_distance)
            
            # Create parallel paths by offsetting each point of the resampled path
            left_edge_path = []
            right_edge_path = []
            
            # For each point in the resampled path, calculate the perpendicular offset
            for i in range(len(resampled_path)):
                current_point = resampled_path[i]
                
                # Calculate the direction at this point
                if i == 0:
                    # First point: use direction to next point
                    next_point = resampled_path[i + 1]
                    direction_x = next_point.x() - current_point.x()
                    direction_y = next_point.y() - current_point.y()
                elif i == len(resampled_path) - 1:
                    # Last point: use direction from previous point
                    prev_point = resampled_path[i - 1]
                    direction_x = current_point.x() - prev_point.x()
                    direction_y = current_point.y() - prev_point.y()
                else:
                    # Middle points: use average direction of neighboring segments
                    prev_point = resampled_path[i - 1]
                    next_point = resampled_path[i + 1]
                    
                    # Direction from previous to current
                    dir1_x = current_point.x() - prev_point.x()
                    dir1_y = current_point.y() - prev_point.y()
                    
                    # Direction from current to next
                    dir2_x = next_point.x() - current_point.x()
                    dir2_y = next_point.y() - current_point.y()
                    
                    # Average the two directions for smoother curves
                    direction_x = (dir1_x + dir2_x) / 2
                    direction_y = (dir1_y + dir2_y) / 2
                
                # Normalize the direction vector
                length = (direction_x * direction_x + direction_y * direction_y) ** 0.5
                if length > 0:
                    unit_x = direction_x / length
                    unit_y = direction_y / length
                    
                    # Calculate perpendicular vector (90 degrees rotated)
                    perp_x = -unit_y
                    perp_y = unit_x
                    
                    # Calculate edge parallel points
                    left_edge_point = QPointF(
                        current_point.x() + perp_x * edge_distance,
                        current_point.y() + perp_y * edge_distance
                    )
                    right_edge_point = QPointF(
                        current_point.x() - perp_x * edge_distance,
                        current_point.y() - perp_y * edge_distance
                    )
                    
                    left_edge_path.append(left_edge_point)
                    right_edge_path.append(right_edge_point)
            
            # Create rectangles along the edge paths using the same algorithm as main line
            if left_edge_path:
                self.create_rectangles_along_specific_path(left_edge_path)
                
            if right_edge_path:
                self.create_rectangles_along_specific_path(right_edge_path)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tessera - Interactive Workspace")
        self.setGeometry(100, 100, 2000, 1100)
        self.showMaximized()  # Start in full screen mode
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create toolbar
        toolbar_layout = QHBoxLayout()
        
        load_bg_btn = QPushButton("Load Background")
        load_bg_btn.clicked.connect(self.load_background)
        toolbar_layout.addWidget(load_bg_btn)
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear_all)
        toolbar_layout.addWidget(clear_btn)
        
        # Add undo button
        self.undo_btn = QPushButton("Undo")
        self.undo_btn.clicked.connect(self.undo_last_action)
        toolbar_layout.addWidget(self.undo_btn)
        
        # Add color toggle button
        self.color_btn = QPushButton("Color")
        self.color_btn.clicked.connect(self.toggle_color_mode)
        toolbar_layout.addWidget(self.color_btn)
        
        # Add overlap removal button
        self.overlap_btn = QPushButton("Overlap")
        self.overlap_btn.clicked.connect(self.remove_overlapping_rectangles)
        toolbar_layout.addWidget(self.overlap_btn)
        
        toolbar_layout.addStretch()
        main_layout.addLayout(toolbar_layout)
        
        # Create main content area with left taskbar, workspace, and right taskbar
        content_layout = QHBoxLayout()
        
        # Create and add workspace view first
        self.workspace = WorkspaceView(self)
        
        # Create left taskbar (now that workspace exists)
        self.create_left_taskbar()
        content_layout.addWidget(self.left_taskbar)
        
        # Add workspace to layout
        content_layout.addWidget(self.workspace)
        
        # Create right taskbar
        self.create_right_taskbar()
        content_layout.addWidget(self.right_taskbar)
        
        # Add content layout to main layout
        main_widget = QWidget()
        main_widget.setLayout(content_layout)
        main_layout.addWidget(main_widget)
        
        # Initialize color toggle state
        self.color_mode = False
        
        # Initialize selected color
        self.selected_color = QColor(0, 0, 0)  # Default black
        
        # Initialize undo stack
        self.undo_stack = []
        
        # Create menu bar
        self.create_menu_bar()
        
        # Add initial instructions
        self.add_instructions()
    
    def toggle_parallel_mode_right(self):
        """Toggle parallel mode from right taskbar"""
        self.workspace.set_parallel_mode(self.right_parallel_btn.isChecked())
        # Update button text
        if self.right_parallel_btn.isChecked():
            self.right_parallel_btn.setText("Parallel Mode: ON")
        else:
            self.right_parallel_btn.setText("Parallel Mode: OFF")
    
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
        rect_x = center.x() - size/2
        rect_y = center.y() - size/2
        
        self.workspace.add_rectangle(rect_x, rect_y, size, size, self.selected_color)
    
    def update_rectangle_size(self):
        """Update the rectangle size based on input"""
        text = self.right_size_input.text().strip()
        
        # If empty, set to default
        if text == "":
            self.right_size_input.setText("10")
            self.workspace.set_rectangle_size(10)
            return
        
        try:
            size = int(text)
            # Clamp size between 10 and 500
            size = max(10, min(500, size))
            self.workspace.set_rectangle_size(size)
            # Update the field with the clamped value
            self.right_size_input.setText(str(size))
        except ValueError:
            # If invalid input, reset to current size
            current_size = self.workspace.rectangle_size
            self.right_size_input.setText(str(current_size))
    
    def update_rectangle_spacing(self, text):
        """Update the rectangle spacing based on input"""
        try:
            spacing = float(text) if text else 1.3
            # Clamp spacing between 0.1 and 10.0
            spacing = max(0.1, min(10.0, spacing))
            self.workspace.set_rectangle_spacing(spacing)
            # Sync right input only
            self.right_spacing_input.setText(str(spacing))
        except ValueError:
            # If invalid input, keep current spacing
            pass
    
    def update_parallel_distance(self, text):
        """Update the parallel distance based on input"""
        try:
            distance = float(text) if text else 0.7
            # Clamp distance between 0.5 and 10.0
            distance = max(0.5, min(10.0, distance))
            self.workspace.set_parallel_distance(distance)
            # Sync right input only
            self.right_parallel_distance_input.setText(str(distance))
        except ValueError:
            # If invalid input, keep current distance
            pass
    
    def update_parallel_lines_count(self, text):
        """Update the parallel lines count based on input"""
        try:
            count = int(text) if text else 1
            # Clamp count between 1 and 10
            count = max(1, min(10, count))
            self.workspace.set_parallel_lines_count(count)
            # Sync right input only
            self.right_parallel_lines_input.setText(str(count))
        except ValueError:
            # If invalid input, keep current count
            pass
    
    def update_circle_count(self, text):
        """Update the circle count based on input"""
        try:
            count = int(text) if text else 7
            # Clamp count between 1 and 20
            count = max(1, min(20, count))
            self.workspace.circle_radius = count
            # Sync right input only
            self.right_circle_count_input.setText(str(count))
        except ValueError:
            # If invalid input, keep current count
            pass
    
    def update_edge_distance(self, text):
        """Update the edge distance based on input"""
        try:
            distance = float(text) if text else 0.8
            # Clamp distance between 0.1 and 10.0
            distance = max(0.1, min(10.0, distance))
            self.workspace.set_edge_distance(distance)
            self.edge_distance_input.setText(str(distance))
        except ValueError:
            # If invalid input, keep current distance
            pass
    
    def update_edge_lines_count(self, text):
        """Update the edge lines count based on input"""
        try:
            count = int(text) if text else 2
            # Clamp count between 1 and 10
            count = max(1, min(10, count))
            self.workspace.set_edge_lines_count(count)
            self.edge_lines_input.setText(str(count))
        except ValueError:
            # If invalid input, keep current count
            pass
    
    def toggle_drawing_mode(self):
        """Toggle drawing mode from the taskbar"""
        self.workspace.drawing_mode = self.drawing_btn.isChecked()
        if self.workspace.drawing_mode:
            # Turn off erase mode when drawing mode is enabled
            if self.erase_btn.isChecked():
                self.erase_btn.setChecked(False)
                self.toggle_erase_mode()
            # Turn off edge mode when drawing mode is enabled
            if self.edge_btn.isChecked():
                self.edge_btn.setChecked(False)
                self.toggle_edge_mode()
            
            self.workspace.setDragMode(QGraphicsView.NoDrag)
            # Use circle cursor if circle mode is on, otherwise use drawing cursor
            if self.workspace.circle_mode:
                self.workspace.setCursor(self.workspace.circle_cursor)
            else:
                self.workspace.setCursor(self.workspace.drawing_cursor)
            self.drawing_btn.setText("Drawing: ON")
            self.status_label.setText("Drawing mode active")
        else:
            self.workspace.setDragMode(QGraphicsView.RubberBandDrag)
            # Use circle cursor if circle mode is on, otherwise use default cursor
            if self.workspace.circle_mode:
                self.workspace.setCursor(self.workspace.circle_cursor)
            else:
                self.workspace.setCursor(Qt.ArrowCursor)
            self.drawing_btn.setText("Drawing: OFF")
            self.status_label.setText("Ready")
    
    def add_half_width_rectangle(self):
        """Add rectangle with half width"""
        center = self.workspace.mapToScene(self.workspace.rect().center())
        half_width = self.workspace.rectangle_size / 2
        rect_x = center.x() - half_width/2
        rect_y = center.y() - self.workspace.rectangle_size/2
        
        self.workspace.add_rectangle(rect_x, rect_y, half_width, self.workspace.rectangle_size, self.selected_color)
        self.status_label.setText("Added half-width rectangle")
    
    def add_small_rectangle(self):
        """Add rectangle with half size"""
        center = self.workspace.mapToScene(self.workspace.rect().center())
        half_size = self.workspace.rectangle_size / 2
        rect_x = center.x() - half_size/2
        rect_y = center.y() - half_size/2
        
        self.workspace.add_rectangle(rect_x, rect_y, half_size, half_size, self.selected_color)
        self.status_label.setText("Added small rectangle")
    
    def fill_selected_rectangles(self):
        """Fill selected rectangles with average color"""
        self.workspace.fill_selected_rectangles()
        self.status_label.setText("Filled selected rectangles")
    
    def clear_all(self):
        # Get all rectangles before clearing
        rectangles_to_clear = []
        for item in self.workspace.scene.items():
            if isinstance(item, ScalableRectangle):
                rectangles_to_clear.append(item)
        
        # Add to undo stack before clearing
        if rectangles_to_clear:
            self.add_to_undo_stack('clear_all', rectangles_to_clear)
        
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
    
    def remove_overlapping_rectangles(self):
        """Remove overlapping rectangles, keeping the older ones"""
        removed_count = self.workspace.remove_overlapping_rectangles()
        if removed_count > 0:
            self.status_label.setText(f"Removed {removed_count} overlapping rectangles")
        else:
            self.status_label.setText("No overlapping rectangles found")
    
    def undo_last_action(self):
        """Undo the last action"""
        if self.undo_stack:
            last_action = self.undo_stack.pop()
            if last_action['type'] == 'add_rectangles':
                # Remove the rectangles that were added
                for rect in last_action['rectangles']:
                    if rect.scene():  # Check if rectangle is still in scene
                        self.workspace.scene.removeItem(rect)
                self.status_label.setText(f"Undid: removed {len(last_action['rectangles'])} rectangles")
            elif last_action['type'] == 'clear_all':
                # Restore all the rectangles that were cleared
                for rect in last_action['rectangles']:
                    self.workspace.scene.addItem(rect)
                self.status_label.setText(f"Undid: restored {len(last_action['rectangles'])} rectangles")
            elif last_action['type'] == 'erase_rectangles':
                # Restore the rectangles that were erased
                for rect in last_action['rectangles']:
                    self.workspace.scene.addItem(rect)
                self.status_label.setText(f"Undid: restored {len(last_action['rectangles'])} erased rectangles")
        else:
            self.status_label.setText("Nothing to undo")
    
    def add_to_undo_stack(self, action_type, rectangles):
        """Add an action to the undo stack"""
        # Keep only the last 10 actions to prevent memory issues
        if len(self.undo_stack) >= 10:
            self.undo_stack.pop(0)
        
        self.undo_stack.append({
            'type': action_type,
            'rectangles': rectangles.copy() if isinstance(rectangles, list) else [rectangles]
        })
    
    def create_left_taskbar(self):
        """Create the left taskbar with drawing tools"""
        from PyQt5.QtWidgets import QFrame
        
        # Create left taskbar frame
        self.left_taskbar = QFrame()
        self.left_taskbar.setFrameStyle(QFrame.StyledPanel)
        self.left_taskbar.setMaximumWidth(200)
        self.left_taskbar.setMinimumWidth(200)
        
        # Create layout for left taskbar
        left_layout = QVBoxLayout(self.left_taskbar)
        
        # Add rectangle tools section
        rect_tools_label = QLabel("Rectangle Tools")
        rect_tools_label.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px 0px;")
        left_layout.addWidget(rect_tools_label)
        
        # Add rectangle buttons
        add_rect_btn = QPushButton("Add Rectangle (T)")
        add_rect_btn.clicked.connect(self.add_rectangle)
        left_layout.addWidget(add_rect_btn)
        
        half_width_btn = QPushButton("Half Width (P)")
        half_width_btn.clicked.connect(self.add_half_width_rectangle)
        left_layout.addWidget(half_width_btn)
        
        small_rect_btn = QPushButton("Small Rectangle (O)")
        small_rect_btn.clicked.connect(self.add_small_rectangle)
        left_layout.addWidget(small_rect_btn)
        
        # Add rectangle actions section
        actions_label = QLabel("Rectangle Actions")
        actions_label.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px 0px;")
        left_layout.addWidget(actions_label)
        
        fill_btn = QPushButton("Fill Selected (C)")
        fill_btn.clicked.connect(self.fill_selected_rectangles)
        left_layout.addWidget(fill_btn)
        
        # Add status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-size: 12px; color: gray; margin: 10px 0px;")
        left_layout.addWidget(self.status_label)
        
        # Add stretch to push everything to the top
        left_layout.addStretch()
    
    def create_right_taskbar(self):
        """Create the right taskbar with settings and controls"""
        from PyQt5.QtWidgets import QFrame
        
        # Create right taskbar frame
        self.right_taskbar = QFrame()
        self.right_taskbar.setFrameStyle(QFrame.StyledPanel)
        self.right_taskbar.setMaximumWidth(250)
        self.right_taskbar.setMinimumWidth(250)
        
        # Create layout for right taskbar
        right_layout = QVBoxLayout(self.right_taskbar)
        
        # Basic Settings Section
        basic_settings_label = QLabel("Basic Settings")
        basic_settings_label.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px 0px;")
        right_layout.addWidget(basic_settings_label)
        
        # Add drawing mode toggle
        self.drawing_btn = QPushButton("Drawing: OFF")
        self.drawing_btn.setCheckable(True)
        self.drawing_btn.setChecked(False)
        self.drawing_btn.clicked.connect(self.toggle_drawing_mode)
        right_layout.addWidget(self.drawing_btn)
        
        # Add half rectangle mode toggle
        self.half_rect_btn = QPushButton("Half Rectangle: OFF")
        self.half_rect_btn.setCheckable(True)
        self.half_rect_btn.setChecked(False)
        self.half_rect_btn.clicked.connect(self.toggle_half_rectangle_mode)
        right_layout.addWidget(self.half_rect_btn)
        
        # Rectangle size input
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Rectangle Size:"))
        self.right_size_input = QLineEdit("10")
        self.right_size_input.setMaximumWidth(80)
        self.right_size_input.setPlaceholderText("Size")
        self.right_size_input.editingFinished.connect(self.update_rectangle_size)
        size_layout.addWidget(self.right_size_input)
        right_layout.addLayout(size_layout)
        
        # Auto-cleanup checkbox
        self.auto_overlap_checkbox = QPushButton("Auto Remove Overlaps: OFF")
        self.auto_overlap_checkbox.setCheckable(True)
        self.auto_overlap_checkbox.setChecked(False)
        self.auto_overlap_checkbox.clicked.connect(self.toggle_auto_overlap)
        right_layout.addWidget(self.auto_overlap_checkbox)
        
        # Circle mode toggle
        self.circle_btn = QPushButton("Circle Mode: OFF")
        self.circle_btn.setCheckable(True)
        self.circle_btn.setChecked(False)
        self.circle_btn.clicked.connect(self.toggle_circle_mode)
        right_layout.addWidget(self.circle_btn)
        
        # Circle count input
        circle_count_layout = QHBoxLayout()
        circle_count_layout.addWidget(QLabel("Circle Count:"))
        self.right_circle_count_input = QLineEdit("7")
        self.right_circle_count_input.setMaximumWidth(80)
        self.right_circle_count_input.setPlaceholderText("Count")
        self.right_circle_count_input.textChanged.connect(self.update_circle_count)
        circle_count_layout.addWidget(self.right_circle_count_input)
        right_layout.addLayout(circle_count_layout)
        
        # Erase mode toggle
        self.erase_btn = QPushButton("Erase Mode: OFF")
        self.erase_btn.setCheckable(True)
        self.erase_btn.setChecked(False)
        self.erase_btn.clicked.connect(self.toggle_erase_mode)
        right_layout.addWidget(self.erase_btn)
        
        # Edge mode toggle
        self.edge_btn = QPushButton("Edge Mode: OFF")
        self.edge_btn.setCheckable(True)
        self.edge_btn.setChecked(False)
        self.edge_btn.clicked.connect(self.toggle_edge_mode)
        right_layout.addWidget(self.edge_btn)
        
        # Edge Settings Section
        edge_section_label = QLabel("Edge Settings")
        edge_section_label.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px 0px;")
        right_layout.addWidget(edge_section_label)
        
        # Edge distance input
        edge_distance_layout = QHBoxLayout()
        edge_distance_layout.addWidget(QLabel("Edge Distance:"))
        self.edge_distance_input = QLineEdit("0.8")
        self.edge_distance_input.setMaximumWidth(80)
        self.edge_distance_input.setPlaceholderText("Distance")
        self.edge_distance_input.textChanged.connect(self.update_edge_distance)
        edge_distance_layout.addWidget(self.edge_distance_input)
        right_layout.addLayout(edge_distance_layout)
        
        # Edge lines count input
        edge_lines_layout = QHBoxLayout()
        edge_lines_layout.addWidget(QLabel("Edge Lines:"))
        self.edge_lines_input = QLineEdit("2")
        self.edge_lines_input.setMaximumWidth(80)
        self.edge_lines_input.setPlaceholderText("Count")
        self.edge_lines_input.textChanged.connect(self.update_edge_lines_count)
        edge_lines_layout.addWidget(self.edge_lines_input)
        right_layout.addLayout(edge_lines_layout)
        
        # Parallel Settings Section
        parallel_section_label = QLabel("Parallel Settings")
        parallel_section_label.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px 0px;")
        right_layout.addWidget(parallel_section_label)
        
        # Parallel mode toggle
        self.right_parallel_btn = QPushButton("Parallel Mode: OFF")
        self.right_parallel_btn.setCheckable(True)
        self.right_parallel_btn.setChecked(False)
        self.right_parallel_btn.clicked.connect(self.toggle_parallel_mode_right)
        right_layout.addWidget(self.right_parallel_btn)
        
        # Parallel distance input
        parallel_distance_layout = QHBoxLayout()
        parallel_distance_layout.addWidget(QLabel("Parallel Distance:"))
        self.right_parallel_distance_input = QLineEdit("0.7")
        self.right_parallel_distance_input.setMaximumWidth(80)
        self.right_parallel_distance_input.setPlaceholderText("Distance")
        self.right_parallel_distance_input.textChanged.connect(self.update_parallel_distance)
        parallel_distance_layout.addWidget(self.right_parallel_distance_input)
        right_layout.addLayout(parallel_distance_layout)
        
        # Parallel lines count input
        parallel_lines_layout = QHBoxLayout()
        parallel_lines_layout.addWidget(QLabel("Parallel Lines:"))
        self.right_parallel_lines_input = QLineEdit("1")
        self.right_parallel_lines_input.setMaximumWidth(80)
        self.right_parallel_lines_input.setPlaceholderText("Count")
        self.right_parallel_lines_input.textChanged.connect(self.update_parallel_lines_count)
        parallel_lines_layout.addWidget(self.right_parallel_lines_input)
        right_layout.addLayout(parallel_lines_layout)
        
        # Rectangle spacing input
        spacing_layout = QHBoxLayout()
        spacing_layout.addWidget(QLabel("Line Spacing:"))
        self.right_spacing_input = QLineEdit("1.3")
        self.right_spacing_input.setMaximumWidth(80)
        self.right_spacing_input.setPlaceholderText("Spacing")
        self.right_spacing_input.textChanged.connect(self.update_rectangle_spacing)
        spacing_layout.addWidget(self.right_spacing_input)
        right_layout.addLayout(spacing_layout)
        
        # Color Palette Section
        palette_label = QLabel("Color Palette")
        palette_label.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px 0px;")
        right_layout.addWidget(palette_label)
        
        # Create selected color display
        selected_color_layout = QHBoxLayout()
        selected_color_layout.addWidget(QLabel("Selected Color:"))
        self.selected_color_display = QLabel()
        self.selected_color_display.setFixedSize(30, 20)
        self.selected_color_display.setStyleSheet("border: 1px solid black; background-color: #000000;")
        selected_color_layout.addWidget(self.selected_color_display)
        selected_color_layout.addStretch()
        right_layout.addLayout(selected_color_layout)
        
        # Create color palette grid
        self.create_color_palette(right_layout)
        
        # Add stretch to push everything to the top
        right_layout.addStretch()

    def toggle_auto_overlap(self):
        """Toggle auto overlap removal mode"""
        if self.auto_overlap_checkbox.isChecked():
            self.auto_overlap_checkbox.setText("Auto Remove Overlaps: ON")
        else:
            self.auto_overlap_checkbox.setText("Auto Remove Overlaps: OFF")
    
    def toggle_circle_mode(self):
        """Toggle circle mode"""
        self.workspace.set_circle_mode(self.circle_btn.isChecked())
        if self.circle_btn.isChecked():
            # Turn off erase mode when circle mode is enabled
            if self.erase_btn.isChecked():
                self.erase_btn.setChecked(False)
                self.toggle_erase_mode()
            # Turn off edge mode when circle mode is enabled
            if self.edge_btn.isChecked():
                self.edge_btn.setChecked(False)
                self.toggle_edge_mode()
            self.circle_btn.setText("Circle Mode: ON")
        else:
            self.circle_btn.setText("Circle Mode: OFF")
    
    def toggle_erase_mode(self):
        """Toggle erase mode"""
        self.workspace.set_erase_mode(self.erase_btn.isChecked())
        if self.erase_btn.isChecked():
            self.erase_btn.setText("Erase Mode: ON")
            # Turn off other modes when erase mode is enabled
            if self.drawing_btn.isChecked():
                self.drawing_btn.setChecked(False)
                self.toggle_drawing_mode()
            if self.circle_btn.isChecked():
                self.circle_btn.setChecked(False)
                self.toggle_circle_mode()
            if self.edge_btn.isChecked():
                self.edge_btn.setChecked(False)
                self.toggle_edge_mode()
        else:
            self.erase_btn.setText("Erase Mode: OFF")
    
    def toggle_edge_mode(self):
        """Toggle edge mode"""
        self.workspace.set_edge_mode(self.edge_btn.isChecked())
        if self.edge_btn.isChecked():
            self.edge_btn.setText("Edge Mode: ON")
            # Turn off other modes when edge mode is enabled
            if self.drawing_btn.isChecked():
                self.drawing_btn.setChecked(False)
                self.toggle_drawing_mode()
            if self.circle_btn.isChecked():
                self.circle_btn.setChecked(False)
                self.toggle_circle_mode()
            if self.erase_btn.isChecked():
                self.erase_btn.setChecked(False)
                self.toggle_erase_mode()
        else:
            self.edge_btn.setText("Edge Mode: OFF")
    
    def toggle_half_rectangle_mode(self):
        """Toggle half rectangle mode"""
        self.workspace.set_half_rectangle_mode(self.half_rect_btn.isChecked())
        if self.half_rect_btn.isChecked():
            self.half_rect_btn.setText("Half Rectangle: ON")
        else:
            self.half_rect_btn.setText("Half Rectangle: OFF")
    
    def create_color_palette(self, layout):
        """Create a 16-color palette grid"""
        # Define 16 colors arranged in a visually appealing way
        colors = [
            # Row 1: Reds and Pinks
            "#FF0000",  # red
            "#FFC0CB",  # pink
            "#FFA500",  # orange
            "#FFFF00",  # yellow
            
            # Row 2: Greens
            "#008000",  # green
            "#90EE90",  # light green
            "#8B4513",  # brown
            "#DEB887",  # light brown (burlywood)
            
            # Row 3: Blues and Purples
            "#0000FF",  # blue
            "#ADD8E6",  # light blue
            "#800080",  # purple
            "#F5F5DC",  # off white (beige)
            
            # Row 4: Neutrals
            "#000000",  # black
            "#808080",  # grey
            "#D3D3D3",  # light grey
            "#FFFFFF"   # white
        ]
        
        # Create grid layout for colors
        palette_grid = QGridLayout()
        palette_grid.setSpacing(0)
        palette_grid.setContentsMargins(0, 0, 0, 0)
        palette_grid.setVerticalSpacing(0)
        palette_grid.setHorizontalSpacing(0)
        
        # Create color buttons in 4x4 grid
        for i, color_hex in enumerate(colors):
            row = i // 4
            col = i % 4
            
            color_btn = QPushButton()
            color_btn.setFixedSize(25, 25)
            color_btn.setStyleSheet(f"background-color: {color_hex}; border: none; margin: 0px; padding: 0px;")
            color_btn.clicked.connect(lambda checked, c=color_hex: self.select_color(c))
            
            palette_grid.addWidget(color_btn, row, col)
        
        # Set row and column stretches to 0 to prevent expansion
        for i in range(4):
            palette_grid.setRowStretch(i, 0)
            palette_grid.setColumnStretch(i, 0)
        
        # Create widget to hold the grid
        palette_widget = QWidget()
        palette_widget.setLayout(palette_grid)
        palette_widget.setContentsMargins(0, 0, 0, 0)
        palette_widget.setStyleSheet("QWidget { margin: 0px; padding: 0px; }")
        palette_widget.setFixedSize(100, 100)  # Fixed size: 4 columns × 25px = 100px, 4 rows × 25px = 100px
        
        # Add the palette to the layout
        layout.addWidget(palette_widget)
    
    def select_color(self, color_hex):
        """Select a color from the palette"""
        self.selected_color = QColor(color_hex)
        self.selected_color_display.setStyleSheet(f"border: 1px solid black; background-color: {color_hex};")

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())