import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QGraphicsScene, 
                           QGraphicsView, QVBoxLayout, QWidget, QMenuBar, 
                           QMenu, QAction, QFileDialog, QHBoxLayout, QPushButton,
                           QGraphicsRectItem, QGraphicsPixmapItem, QLineEdit, QLabel,
                           QGraphicsLineItem, QGraphicsPathItem, QSlider)
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
        self.original_background_pixmap = None  # Store original background
        self.edge_background_pixmap = None  # Store edge detection background
        self.edge_mode = False  # Track if edge mode is active
        self.edge_strength = 50  # Default edge detection strength (0-100)
        
        # Performance optimization flag
        self.scene.batch_operation = False
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
        
        # Store the original scaled pixmap
        self.original_background_pixmap = scaled_pixmap
        
        # Generate edge detection version
        self.edge_background_pixmap = self.create_edge_detection(scaled_pixmap)
        
        # Add the appropriate background (original or edge based on current mode)
        current_pixmap = self.edge_background_pixmap if self.edge_mode else self.original_background_pixmap
        self.background_item = QGraphicsPixmapItem(current_pixmap)
        self.background_item.setZValue(-1)  # Put it behind everything
        self.scene.addItem(self.background_item)
        
        # Update scene rect to fit the scaled image
        self.scene.setSceneRect(QRectF(scaled_pixmap.rect()))
    
    def create_edge_detection(self, pixmap):
        """Create an edge detection version of the pixmap using OpenCV Canny edge detection"""
        # Convert QPixmap to OpenCV format
        image = pixmap.toImage()
        width = image.width()
        height = image.height()
        
        # Convert QImage to numpy array
        ptr = image.bits()
        ptr.setsize(image.byteCount())
        arr = np.array(ptr).reshape(height, width, 4)  # RGBA format
        
        # Convert RGBA to BGR for OpenCV (ignore alpha channel)
        bgr_image = cv2.cvtColor(arr[:, :, :3], cv2.COLOR_RGB2BGR)
        
        # Convert to grayscale
        gray = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Calculate thresholds based on edge strength (0-100)
        # Convert strength to appropriate threshold values
        base_threshold = self.edge_strength * 2  # Scale 0-100 to 0-200
        low_threshold = max(10, base_threshold - 50)  # Minimum 10, typically 50 less than high
        high_threshold = min(250, base_threshold + 50)  # Maximum 250, typically 50 more than low
        
        # Apply Canny edge detection with adjustable thresholds
        edges = cv2.Canny(blurred, low_threshold, high_threshold)
        
        # Convert back to QPixmap
        # Create a white background
        edge_image = QPixmap(width, height)
        edge_image.fill(Qt.white)
        
        # Create painter for the edge image
        painter = QPainter(edge_image)
        
        # Draw the edges on the white background
        for y in range(height):
            for x in range(width):
                if edges[y, x] > 0:  # If it's an edge pixel
                    painter.setPen(QColor(0, 0, 0))  # Black edges
                    painter.drawPoint(x, y)
        
        painter.end()
        return edge_image
    
    def toggle_edge_mode(self):
        """Toggle between original background and edge detection"""
        if not self.original_background_pixmap:
            return  # No background image loaded
        
        self.edge_mode = not self.edge_mode
        
        # Remove current background
        if self.background_item:
            self.scene.removeItem(self.background_item)
        
        # Add the appropriate background
        current_pixmap = self.edge_background_pixmap if self.edge_mode else self.original_background_pixmap
        self.background_item = QGraphicsPixmapItem(current_pixmap)
        self.background_item.setZValue(-1)  # Put it behind everything
        self.scene.addItem(self.background_item)
        
        return self.edge_mode
    
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
    
    def set_parallel_mode(self, enabled):
        """Enable or disable parallel line mode"""
        self.parallel_mode = enabled
    
    def set_edge_strength(self, strength):
        """Set the edge detection strength (0-100) and regenerate edge detection if needed"""
        self.edge_strength = max(0, min(100, strength))  # Clamp between 0 and 100
        
        # If we have an original background and edge mode is active, regenerate edge detection
        if self.original_background_pixmap and self.edge_mode:
            self.edge_background_pixmap = self.create_edge_detection(self.original_background_pixmap)
            
            # Update the current background display
            if self.background_item:
                self.scene.removeItem(self.background_item)
            
            self.background_item = QGraphicsPixmapItem(self.edge_background_pixmap)
            self.background_item.setZValue(-1)  # Put it behind everything
            self.scene.addItem(self.background_item)
    
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
            
            # If parallel mode is enabled, create parallel paths
            if self.parallel_mode:
                self.create_parallel_paths()
            
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
        
        # Only create rectangles on the main line if parallel mode is NOT enabled
        if not self.parallel_mode:
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
        import math
        
        # Get the current position
        p1 = path[segment_idx]
        p2 = path[segment_idx + 1]
        current_x = p1.x() + ratio * (p2.x() - p1.x())
        current_y = p1.y() + ratio * (p2.y() - p1.y())
        
        # Simple approach: use a small window around the current position
        # Look at points immediately before and after
        
        # Find the best points for direction calculation
        # Look for points that are approximately 1-2 rectangle sizes away
        target_distance = self.rectangle_size * 1.5
        
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
            
            # Normalize angle to respect the -89 to +89 degree boundaries
            # If angle is outside this range, flip it by 180 degrees to keep it within bounds
            if angle_degrees > 89:
                angle_degrees -= 180
            elif angle_degrees < -89:
                angle_degrees += 180
            
            # Ensure we're still within bounds after adjustment
            angle_degrees = max(-89, min(89, angle_degrees))
            
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
            else:
                # Additional lines: use larger spacing to prevent overlap
                spacing_multiplier = 1.5  # Increase spacing for lines 4+
                parallel_distance = base_parallel_distance * (3.6 + (line_index - 3) * spacing_multiplier)
            
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
        
        # Add parallel mode button
        self.parallel_btn = QPushButton("Parallel")
        self.parallel_btn.setCheckable(True)
        self.parallel_btn.setChecked(False)
        self.parallel_btn.clicked.connect(self.toggle_parallel_mode)
        toolbar_layout.addWidget(self.parallel_btn)
        
        # Add edge detection button
        self.edge_btn = QPushButton("Edge")
        self.edge_btn.setCheckable(True)
        self.edge_btn.setChecked(False)
        self.edge_btn.clicked.connect(self.toggle_edge_mode)
        toolbar_layout.addWidget(self.edge_btn)
        
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
        
        # Add parallel distance input
        parallel_distance_label = QLabel("Parallel Distance:")
        toolbar_layout.addWidget(parallel_distance_label)
        
        self.parallel_distance_input = QLineEdit("0.7")
        self.parallel_distance_input.setMaximumWidth(80)
        self.parallel_distance_input.setPlaceholderText("Distance")
        self.parallel_distance_input.textChanged.connect(self.update_parallel_distance)
        toolbar_layout.addWidget(self.parallel_distance_input)
        
        # Add parallel lines count input
        parallel_lines_label = QLabel("Parallel Lines:")
        toolbar_layout.addWidget(parallel_lines_label)
        
        self.parallel_lines_input = QLineEdit("1")
        self.parallel_lines_input.setMaximumWidth(80)
        self.parallel_lines_input.setPlaceholderText("Lines")
        self.parallel_lines_input.textChanged.connect(self.update_parallel_lines_count)
        toolbar_layout.addWidget(self.parallel_lines_input)
        
        # Add second line spacing input
        second_line_spacing_label = QLabel("2nd Line Spacing:")
        toolbar_layout.addWidget(second_line_spacing_label)
        
        self.second_line_spacing_input = QLineEdit("1.5")
        self.second_line_spacing_input.setMaximumWidth(80)
        self.second_line_spacing_input.setPlaceholderText("Spacing")
        self.second_line_spacing_input.textChanged.connect(self.update_second_line_spacing)
        toolbar_layout.addWidget(self.second_line_spacing_input)
        
        # Add third line spacing input
        third_line_spacing_label = QLabel("3rd Line Spacing:")
        toolbar_layout.addWidget(third_line_spacing_label)
        
        self.third_line_spacing_input = QLineEdit("1.7")
        self.third_line_spacing_input.setMaximumWidth(80)
        self.third_line_spacing_input.setPlaceholderText("Spacing")
        self.third_line_spacing_input.textChanged.connect(self.update_third_line_spacing)
        toolbar_layout.addWidget(self.third_line_spacing_input)
        
        # Add edge strength slider
        edge_strength_label = QLabel("Edge Strength:")
        toolbar_layout.addWidget(edge_strength_label)
        
        self.edge_strength_slider = QSlider(Qt.Horizontal)
        self.edge_strength_slider.setMinimum(0)
        self.edge_strength_slider.setMaximum(100)
        self.edge_strength_slider.setValue(50)  # Default strength
        self.edge_strength_slider.setMaximumWidth(100)
        self.edge_strength_slider.valueChanged.connect(self.update_edge_strength)
        toolbar_layout.addWidget(self.edge_strength_slider)
        
        # Add edge strength value label
        self.edge_strength_value_label = QLabel("50")
        self.edge_strength_value_label.setMinimumWidth(25)
        toolbar_layout.addWidget(self.edge_strength_value_label)
        
        toolbar_layout.addStretch()
        main_layout.addLayout(toolbar_layout)
        
        # Create main content area with left taskbar, workspace, and right taskbar
        content_layout = QHBoxLayout()
        
        # Create and add workspace view first
        self.workspace = WorkspaceView()
        
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
        
        # Create menu bar
        self.create_menu_bar()
        
        # Add initial instructions
        self.add_instructions()
    
    def toggle_parallel_mode(self):
        """Toggle parallel line mode"""
        self.workspace.set_parallel_mode(self.parallel_btn.isChecked())
        # Update both buttons
        if self.parallel_btn.isChecked():
            self.parallel_btn.setText("Parallel: ON")
            self.right_parallel_btn.setChecked(True)
            self.right_parallel_btn.setText("Parallel Mode: ON")
        else:
            self.parallel_btn.setText("Parallel")
            self.right_parallel_btn.setChecked(False)
            self.right_parallel_btn.setText("Parallel Mode: OFF")
    
    def create_left_taskbar(self):
        """Create the left taskbar with tools and controls"""
        self.left_taskbar = QWidget()
        self.left_taskbar.setFixedWidth(200)
        self.left_taskbar.setStyleSheet("background-color: #f0f0f0; border-right: 1px solid #ccc;")
        
        taskbar_layout = QVBoxLayout(self.left_taskbar)
        taskbar_layout.setSpacing(10)
        taskbar_layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title_label = QLabel("Tools")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        taskbar_layout.addWidget(title_label)
        
        # Separator
        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #ccc;")
        taskbar_layout.addWidget(line)
        
        # Drawing Mode Section
        drawing_section = QLabel("Drawing Mode")
        drawing_section.setStyleSheet("font-size: 12px; font-weight: bold; color: #555; margin-top: 10px;")
        taskbar_layout.addWidget(drawing_section)
        
        # Drawing mode toggle button
        self.drawing_btn = QPushButton("Drawing: OFF")
        self.drawing_btn.setCheckable(True)
        self.drawing_btn.setChecked(False)
        self.drawing_btn.clicked.connect(self.toggle_drawing_mode)
        self.drawing_btn.setStyleSheet("QPushButton { text-align: left; padding: 5px; }")
        taskbar_layout.addWidget(self.drawing_btn)
        
        # Rectangle Tools Section
        rect_section = QLabel("Rectangle Tools")
        rect_section.setStyleSheet("font-size: 12px; font-weight: bold; color: #555; margin-top: 15px;")
        taskbar_layout.addWidget(rect_section)
        
        # Quick rectangle buttons
        rect_btn = QPushButton("Add Rectangle (T)")
        rect_btn.clicked.connect(self.add_rectangle)
        rect_btn.setStyleSheet("QPushButton { text-align: left; padding: 5px; }")
        taskbar_layout.addWidget(rect_btn)
        
        half_rect_btn = QPushButton("Half Width (P)")
        half_rect_btn.clicked.connect(self.add_half_width_rectangle)
        half_rect_btn.setStyleSheet("QPushButton { text-align: left; padding: 5px; }")
        taskbar_layout.addWidget(half_rect_btn)
        
        small_rect_btn = QPushButton("Half Size (O)")
        small_rect_btn.clicked.connect(self.add_small_rectangle)
        small_rect_btn.setStyleSheet("QPushButton { text-align: left; padding: 5px; }")
        taskbar_layout.addWidget(small_rect_btn)
        
        # Navigation Section
        nav_section = QLabel("Navigation")
        nav_section.setStyleSheet("font-size: 12px; font-weight: bold; color: #555; margin-top: 15px;")
        taskbar_layout.addWidget(nav_section)
        
        # Navigation info
        nav_info = QLabel("Arrow Keys: Pan\nMouse Wheel: Zoom")
        nav_info.setStyleSheet("font-size: 10px; color: #666; margin-bottom: 5px;")
        taskbar_layout.addWidget(nav_info)
        
        # Actions Section
        actions_section = QLabel("Actions")
        actions_section.setStyleSheet("font-size: 12px; font-weight: bold; color: #555; margin-top: 15px;")
        taskbar_layout.addWidget(actions_section)
        
        # Action buttons
        fill_btn = QPushButton("Fill Selected (C)")
        fill_btn.clicked.connect(self.fill_selected_rectangles)
        fill_btn.setStyleSheet("QPushButton { text-align: left; padding: 5px; }")
        taskbar_layout.addWidget(fill_btn)
        
        rotate_ccw_btn = QPushButton("Rotate CCW (R)")
        rotate_ccw_btn.clicked.connect(lambda: self.workspace.rotate_selected_rectangles(False))
        rotate_ccw_btn.setStyleSheet("QPushButton { text-align: left; padding: 5px; }")
        taskbar_layout.addWidget(rotate_ccw_btn)
        
        rotate_cw_btn = QPushButton("Rotate CW (Y)")
        rotate_cw_btn.clicked.connect(lambda: self.workspace.rotate_selected_rectangles(True))
        rotate_cw_btn.setStyleSheet("QPushButton { text-align: left; padding: 5px; }")
        taskbar_layout.addWidget(rotate_cw_btn)
        
        delete_btn = QPushButton("Delete (Del)")
        delete_btn.clicked.connect(self.workspace.delete_selected_rectangles)
        delete_btn.setStyleSheet("QPushButton { text-align: left; padding: 5px; }")
        taskbar_layout.addWidget(delete_btn)
        
        # Add stretch to push everything to the top
        taskbar_layout.addStretch()
        
        # Status Section at bottom
        status_section = QLabel("Status")
        status_section.setStyleSheet("font-size: 12px; font-weight: bold; color: #555; margin-top: 15px;")
        taskbar_layout.addWidget(status_section)
        
        # Status info
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-size: 10px; color: #666; margin-bottom: 10px;")
        taskbar_layout.addWidget(self.status_label)
    
    def create_right_taskbar(self):
        """Create the right taskbar with additional controls and information"""
        self.right_taskbar = QWidget()
        self.right_taskbar.setFixedWidth(200)
        self.right_taskbar.setStyleSheet("background-color: #f0f0f0; border-left: 1px solid #ccc;")
        
        taskbar_layout = QVBoxLayout(self.right_taskbar)
        taskbar_layout.setSpacing(10)
        taskbar_layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title_label = QLabel("Settings")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        taskbar_layout.addWidget(title_label)
        
        # Separator
        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #ccc;")
        taskbar_layout.addWidget(line)
        
        # Parallel Settings Section
        parallel_section = QLabel("Parallel Settings")
        parallel_section.setStyleSheet("font-size: 12px; font-weight: bold; color: #555; margin-top: 10px;")
        taskbar_layout.addWidget(parallel_section)
        
        # Parallel mode toggle
        self.right_parallel_btn = QPushButton("Parallel Mode: OFF")
        self.right_parallel_btn.setCheckable(True)
        self.right_parallel_btn.setChecked(False)
        self.right_parallel_btn.clicked.connect(self.toggle_parallel_mode_right)
        self.right_parallel_btn.setStyleSheet("QPushButton { text-align: left; padding: 5px; }")
        taskbar_layout.addWidget(self.right_parallel_btn)
        
        # Parallel lines count
        lines_count_label = QLabel("Lines Count:")
        lines_count_label.setStyleSheet("font-size: 10px; color: #666;")
        taskbar_layout.addWidget(lines_count_label)
        
        self.right_parallel_lines_input = QLineEdit("1")
        self.right_parallel_lines_input.setMaximumWidth(180)
        self.right_parallel_lines_input.setPlaceholderText("Number of parallel lines")
        self.right_parallel_lines_input.textChanged.connect(self.update_parallel_lines_count)
        taskbar_layout.addWidget(self.right_parallel_lines_input)
        
        # Parallel distance
        distance_label = QLabel("Parallel Distance:")
        distance_label.setStyleSheet("font-size: 10px; color: #666;")
        taskbar_layout.addWidget(distance_label)
        
        self.right_parallel_distance_input = QLineEdit("0.7")
        self.right_parallel_distance_input.setMaximumWidth(180)
        self.right_parallel_distance_input.setPlaceholderText("Distance multiplier")
        self.right_parallel_distance_input.textChanged.connect(self.update_parallel_distance)
        taskbar_layout.addWidget(self.right_parallel_distance_input)
        
        # Line Spacing Section
        spacing_section = QLabel("Line Spacing")
        spacing_section.setStyleSheet("font-size: 12px; font-weight: bold; color: #555; margin-top: 15px;")
        taskbar_layout.addWidget(spacing_section)
        
        # 2nd line spacing
        second_line_label = QLabel("2nd Line Spacing:")
        second_line_label.setStyleSheet("font-size: 10px; color: #666;")
        taskbar_layout.addWidget(second_line_label)
        
        self.right_second_line_input = QLineEdit("1.5")
        self.right_second_line_input.setMaximumWidth(180)
        self.right_second_line_input.setPlaceholderText("Second line spacing multiplier")
        self.right_second_line_input.textChanged.connect(self.update_second_line_spacing)
        taskbar_layout.addWidget(self.right_second_line_input)
        
        # 3rd line spacing
        third_line_label = QLabel("3rd Line Spacing:")
        third_line_label.setStyleSheet("font-size: 10px; color: #666;")
        taskbar_layout.addWidget(third_line_label)
        
        self.right_third_line_input = QLineEdit("1.7")
        self.right_third_line_input.setMaximumWidth(180)
        self.right_third_line_input.setPlaceholderText("Third line spacing multiplier")
        self.right_third_line_input.textChanged.connect(self.update_third_line_spacing)
        taskbar_layout.addWidget(self.right_third_line_input)
        
        # Rectangle Settings Section
        rect_settings_section = QLabel("Rectangle Settings")
        rect_settings_section.setStyleSheet("font-size: 12px; font-weight: bold; color: #555; margin-top: 15px;")
        taskbar_layout.addWidget(rect_settings_section)
        
        # Rectangle size
        size_label = QLabel("Rectangle Size:")
        size_label.setStyleSheet("font-size: 10px; color: #666;")
        taskbar_layout.addWidget(size_label)
        
        self.right_size_input = QLineEdit("10")
        self.right_size_input.setMaximumWidth(180)
        self.right_size_input.setPlaceholderText("Rectangle size in pixels")
        self.right_size_input.textChanged.connect(self.update_rectangle_size)
        taskbar_layout.addWidget(self.right_size_input)
        
        # Line spacing
        line_spacing_label = QLabel("Line Spacing:")
        line_spacing_label.setStyleSheet("font-size: 10px; color: #666;")
        taskbar_layout.addWidget(line_spacing_label)
        
        self.right_spacing_input = QLineEdit("1.3")
        self.right_spacing_input.setMaximumWidth(180)
        self.right_spacing_input.setPlaceholderText("Spacing between rectangles")
        self.right_spacing_input.textChanged.connect(self.update_rectangle_spacing)
        taskbar_layout.addWidget(self.right_spacing_input)
        
        # Edge Detection Section
        edge_section = QLabel("Edge Detection")
        edge_section.setStyleSheet("font-size: 12px; font-weight: bold; color: #555; margin-top: 15px;")
        taskbar_layout.addWidget(edge_section)
        
        # Edge mode toggle
        self.right_edge_btn = QPushButton("Edge Mode: OFF")
        self.right_edge_btn.setCheckable(True)
        self.right_edge_btn.setChecked(False)
        self.right_edge_btn.clicked.connect(self.toggle_edge_mode_right)
        self.right_edge_btn.setStyleSheet("QPushButton { text-align: left; padding: 5px; }")
        taskbar_layout.addWidget(self.right_edge_btn)
        
        # Edge strength
        edge_strength_label = QLabel("Edge Strength:")
        edge_strength_label.setStyleSheet("font-size: 10px; color: #666;")
        taskbar_layout.addWidget(edge_strength_label)
        
        self.right_edge_strength_slider = QSlider(Qt.Horizontal)
        self.right_edge_strength_slider.setMinimum(0)
        self.right_edge_strength_slider.setMaximum(100)
        self.right_edge_strength_slider.setValue(50)
        self.right_edge_strength_slider.setMaximumWidth(180)
        self.right_edge_strength_slider.valueChanged.connect(self.update_edge_strength)
        taskbar_layout.addWidget(self.right_edge_strength_slider)
        
        # Edge strength value
        self.right_edge_strength_value_label = QLabel("50")
        self.right_edge_strength_value_label.setStyleSheet("font-size: 10px; color: #666; text-align: center;")
        taskbar_layout.addWidget(self.right_edge_strength_value_label)
        
        # Add stretch to push everything to the top
        taskbar_layout.addStretch()
        
        # Info Section at bottom
        info_section = QLabel("Information")
        info_section.setStyleSheet("font-size: 12px; font-weight: bold; color: #555; margin-top: 15px;")
        taskbar_layout.addWidget(info_section)
        
        # Info text
        info_text = QLabel("Press D to toggle drawing mode.\nPress T to add rectangle.\nPress C to fill selected.")
        info_text.setStyleSheet("font-size: 9px; color: #666; margin-bottom: 10px;")
        info_text.setWordWrap(True)
        taskbar_layout.addWidget(info_text)
    
    def toggle_parallel_mode_right(self):
        """Toggle parallel mode from right taskbar"""
        self.workspace.set_parallel_mode(self.right_parallel_btn.isChecked())
        # Update both buttons
        if self.right_parallel_btn.isChecked():
            self.right_parallel_btn.setText("Parallel Mode: ON")
            self.parallel_btn.setChecked(True)
            self.parallel_btn.setText("Parallel: ON")
        else:
            self.right_parallel_btn.setText("Parallel Mode: OFF")
            self.parallel_btn.setChecked(False)
            self.parallel_btn.setText("Parallel")
    
    def toggle_edge_mode_right(self):
        """Toggle edge mode from right taskbar"""
        edge_mode = self.workspace.toggle_edge_mode()
        # Update both buttons
        if edge_mode:
            self.right_edge_btn.setText("Edge Mode: ON")
            self.edge_btn.setChecked(True)
            self.edge_btn.setText("Edge: ON")
        else:
            self.right_edge_btn.setText("Edge Mode: OFF")
            self.edge_btn.setChecked(False)
            self.edge_btn.setText("Edge")
    
    def toggle_edge_mode(self):
        """Toggle edge detection mode"""
        edge_mode = self.workspace.toggle_edge_mode()
        # Update both buttons
        if edge_mode:
            self.edge_btn.setText("Edge: ON")
            self.right_edge_btn.setChecked(True)
            self.right_edge_btn.setText("Edge Mode: ON")
        else:
            self.edge_btn.setText("Edge")
            self.right_edge_btn.setChecked(False)
            self.right_edge_btn.setText("Edge Mode: OFF")
    
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
            # Sync both inputs
            self.size_input.setText(str(size))
            self.right_size_input.setText(str(size))
        except ValueError:
            # If invalid input, keep current size
            pass
    
    def update_rectangle_spacing(self, text):
        """Update the rectangle spacing based on input"""
        try:
            spacing = float(text) if text else 1.3
            # Clamp spacing between 0.1 and 10.0
            spacing = max(0.1, min(10.0, spacing))
            self.workspace.set_rectangle_spacing(spacing)
            # Sync both inputs
            self.spacing_input.setText(str(spacing))
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
            # Sync both inputs
            self.parallel_distance_input.setText(str(distance))
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
            # Sync both inputs
            self.parallel_lines_input.setText(str(count))
            self.right_parallel_lines_input.setText(str(count))
        except ValueError:
            # If invalid input, keep current count
            pass
    
    def update_second_line_spacing(self, text):
        """Update the second line spacing multiplier based on input"""
        try:
            spacing = float(text) if text else 1.5
            # Clamp spacing between 1.0 and 3.0
            spacing = max(1.0, min(3.0, spacing))
            self.workspace.set_second_line_spacing(spacing)
            # Sync both inputs
            self.second_line_spacing_input.setText(str(spacing))
            self.right_second_line_input.setText(str(spacing))
        except ValueError:
            # If invalid input, keep current spacing
            pass
    
    def update_third_line_spacing(self, text):
        """Update the third line spacing multiplier based on input"""
        try:
            spacing = float(text) if text else 1.7
            # Clamp spacing between 1.0 and 3.0
            spacing = max(1.0, min(3.0, spacing))
            self.workspace.set_third_line_spacing(spacing)
            # Sync both inputs
            self.third_line_spacing_input.setText(str(spacing))
            self.right_third_line_input.setText(str(spacing))
        except ValueError:
            # If invalid input, keep current spacing
            pass
    
    def update_edge_strength(self, value):
        """Update the edge detection strength based on slider value"""
        self.edge_strength_value_label.setText(str(value))
        self.right_edge_strength_value_label.setText(str(value))
        # Sync both sliders
        self.edge_strength_slider.setValue(value)
        self.right_edge_strength_slider.setValue(value)
        self.workspace.set_edge_strength(value)
    
    def toggle_drawing_mode(self):
        """Toggle drawing mode from the taskbar"""
        self.workspace.drawing_mode = self.drawing_btn.isChecked()
        if self.workspace.drawing_mode:
            self.workspace.setDragMode(QGraphicsView.NoDrag)
            self.workspace.setCursor(self.workspace.drawing_cursor)
            self.drawing_btn.setText("Drawing: ON")
            self.status_label.setText("Drawing mode active")
        else:
            self.workspace.setDragMode(QGraphicsView.RubberBandDrag)
            self.workspace.setCursor(Qt.ArrowCursor)
            self.drawing_btn.setText("Drawing: OFF")
            self.status_label.setText("Ready")
    
    def add_half_width_rectangle(self):
        """Add rectangle with half width"""
        center = self.workspace.mapToScene(self.workspace.rect().center())
        half_width = self.workspace.rectangle_size / 2
        self.workspace.add_rectangle(center.x() - half_width/2, center.y() - self.workspace.rectangle_size/2, 
                                   half_width, self.workspace.rectangle_size)
        self.status_label.setText("Added half-width rectangle")
    
    def add_small_rectangle(self):
        """Add rectangle with half size"""
        center = self.workspace.mapToScene(self.workspace.rect().center())
        half_size = self.workspace.rectangle_size / 2
        self.workspace.add_rectangle(center.x() - half_size/2, center.y() - half_size/2, 
                                   half_size, half_size)
        self.status_label.setText("Added small rectangle")
    
    def fill_selected_rectangles(self):
        """Fill selected rectangles with average color"""
        self.workspace.fill_selected_rectangles()
        self.status_label.setText("Filled selected rectangles")
    
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
