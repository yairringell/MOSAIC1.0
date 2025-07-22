# Studio.py
# Image Design Studio for the MOSAIC project
# A simplified image editing and design workspace

import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QLabel, QFileDialog, QScrollArea,
                             QMessageBox, QSplitter, QLineEdit, QFrame, QSlider,
                             QGraphicsView, QGraphicsScene, QGraphicsPixmapItem)
from PyQt5.QtCore import Qt, QBuffer, QTimer
from PyQt5.QtGui import QPixmap, QFont, QIntValidator
from PIL import Image, ImageQt
import io


class ZoomableImageView(QGraphicsView):
    """Custom graphics view that handles zooming with mouse wheel like tessera"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(self.parent().painter().Antialiasing if self.parent() else 0)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Create scene
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        # Image item
        self.image_item = None
        self.image_studio = None  # Reference to parent studio
    
    def wheelEvent(self, event):
        """Handle mouse wheel events for zooming (same as tessera)"""
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
        
        # Update zoom factor in parent
        if self.image_studio:
            current_transform = self.transform()
            self.image_studio.zoom_factor = current_transform.m11()  # Get scale factor
            
            # Update status bar
            zoom_percent = int(self.image_studio.zoom_factor * 100)
            if self.image_item:
                pixmap = self.image_item.pixmap()
                scaled_width = int(pixmap.width() * self.image_studio.zoom_factor)
                scaled_height = int(pixmap.height() * self.image_studio.zoom_factor)
                self.image_studio.statusBar().showMessage(f"Zoom: {zoom_percent}% | Size: {scaled_width}x{scaled_height}")
    
    def set_image(self, pixmap):
        """Set the image to display"""
        # Clear existing image
        if self.image_item:
            self.scene.removeItem(self.image_item)
        
        # Add new image
        self.image_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.image_item)
        
        # Fit image in view initially
        self.fitInView(self.image_item, Qt.KeepAspectRatio)
        
        # Update zoom factor
        if self.image_studio:
            current_transform = self.transform()
            self.image_studio.zoom_factor = current_transform.m11()

class ImageDesignStudio(QMainWindow):
    """Main design studio window for image editing and design"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MOSAIC Design Studio")
        
        # Current image properties
        self.current_image = None
        self.current_image_path = None
        self.original_image = None  # Store original for contrast adjustments
        self.zoom_factor = 1.0  # Current zoom level
        
        self.init_ui()
        
        # Set initial size and then maximize after a short delay
        self.resize(1400, 900)
        QTimer.singleShot(100, self.showMaximized)
    
    def init_ui(self):
        """Initialize the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Create splitter for resizable sections
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - For future functionality
        self.create_left_panel(splitter)
        
        # Center panel - Image workspace
        self.create_workspace_panel(splitter)
        
        # Set splitter proportions (left panel smaller, workspace larger)
        splitter.setSizes([250, 950])
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create status bar
        self.statusBar().showMessage("Ready - Load an image to begin")
    
    def create_left_panel(self, parent):
        """Create the left panel for future functionality"""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Rescale input field
        self.size_input = QLineEdit()
        self.size_input.setPlaceholderText("Enter size (e.g., 800)")
        self.size_input.setValidator(QIntValidator(1, 9999))  # Only allow positive integers
        left_layout.addWidget(self.size_input)
        
        # Rescale button
        rescale_btn = QPushButton("Rescale Image")
        rescale_btn.clicked.connect(self.rescale_image)
        left_layout.addWidget(rescale_btn)
        
        # 32 colors button
        colors_32_btn = QPushButton("Convert to 32 Colors")
        colors_32_btn.clicked.connect(self.convert_to_32_colors)
        left_layout.addWidget(colors_32_btn)
        
        # Color palette button
        palette_btn = QPushButton("Convert to Palette Colors")
        palette_btn.clicked.connect(self.convert_to_palette_colors)
        left_layout.addWidget(palette_btn)
        
        # Gray button
        gray_btn = QPushButton("Convert to 6 Grays")
        gray_btn.clicked.connect(self.convert_to_grayscale_6)
        left_layout.addWidget(gray_btn)

        # Contrast adjustment
        contrast_label = QLabel("Contrast")
        left_layout.addWidget(contrast_label)
        
        self.contrast_slider = QSlider(Qt.Horizontal)
        self.contrast_slider.setRange(-100, 100)
        self.contrast_slider.setValue(0)
        self.contrast_slider.valueChanged.connect(self.adjust_contrast)
        left_layout.addWidget(self.contrast_slider)
        
        # Temperature adjustment
        temperature_label = QLabel("Temperature")
        left_layout.addWidget(temperature_label)
        
        self.temperature_slider = QSlider(Qt.Horizontal)
        self.temperature_slider.setRange(-100, 100)
        self.temperature_slider.setValue(0)
        self.temperature_slider.valueChanged.connect(self.adjust_temperature)
        left_layout.addWidget(self.temperature_slider)
        
        # Placeholder for future tools
        placeholder_label = QLabel("Future functionality\nwill be added here")
        placeholder_label.setAlignment(Qt.AlignCenter)
        placeholder_label.setStyleSheet("color: #666666; font-style: italic; margin-top: 20px;")
        left_layout.addWidget(placeholder_label)
        
        # Add stretch to push everything to top
        left_layout.addStretch()
        
        parent.addWidget(left_widget)
    
    def create_workspace_panel(self, parent):
        """Create the center workspace panel"""
        workspace_widget = QWidget()
        workspace_layout = QVBoxLayout(workspace_widget)
        
        # Image display area - using QGraphicsView for zoom like tessera
        self.image_view = ZoomableImageView()
        self.image_view.image_studio = self  # Set reference to parent
        
        workspace_layout.addWidget(self.image_view)
        
        parent.addWidget(workspace_widget)
    
    def create_menu_bar(self):
        """Create the menu bar with file dropdown"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        file_menu.addAction('Load Image', self.load_image)
        file_menu.addAction('Save Image', self.save_image)
        file_menu.addSeparator()
        file_menu.addAction('Exit', self.close)
    
    def load_image(self):
        """Load an image into the design studio"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff)"
        )
        
        if file_path:
            self.current_image_path = file_path
            pixmap = QPixmap(file_path)
            
            if not pixmap.isNull():
                self.current_image = pixmap
                self.original_image = pixmap.copy()  # Store original for contrast adjustments
                self.zoom_factor = 1.0  # Reset zoom when loading new image
                self.display_image(pixmap)
                self.statusBar().showMessage(f"Loaded: {os.path.basename(file_path)}")
            else:
                QMessageBox.warning(self, "Error", "Could not load the selected image.")
    
    def display_image(self, pixmap):
        """Display the image in the workspace using QGraphicsView"""
        if pixmap and not pixmap.isNull():
            # Set the image in the graphics view
            self.image_view.set_image(pixmap)
            
            # Update status bar with zoom info
            zoom_percent = int(self.zoom_factor * 100)
            self.statusBar().showMessage(f"Zoom: {zoom_percent}% | Size: {pixmap.width()}x{pixmap.height()}")
    
    def save_image(self):
        """Save the current image"""
        if self.current_image:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp)"
            )
            if file_path:
                if self.current_image.save(file_path):
                    self.statusBar().showMessage(f"Image saved: {os.path.basename(file_path)}")
                else:
                    QMessageBox.warning(self, "Error", "Could not save the image.")
        else:
            QMessageBox.information(self, "Info", "No image loaded to save.")
    
    def rescale_image(self):
        """Rescale the current image based on the input size"""
        if not self.current_image:
            QMessageBox.information(self, "Info", "No image loaded to rescale.")
            return
        
        # Get the size from input
        size_text = self.size_input.text().strip()
        if not size_text:
            QMessageBox.warning(self, "Warning", "Please enter a size value.")
            return
        
        try:
            max_size = int(size_text)
            if max_size <= 0:
                QMessageBox.warning(self, "Warning", "Size must be a positive number.")
                return
        except ValueError:
            QMessageBox.warning(self, "Warning", "Please enter a valid number.")
            return
        
        # Get original dimensions
        original_width = self.current_image.width()
        original_height = self.current_image.height()
        
        # Determine scaling based on the larger dimension
        if original_width >= original_height:
            # Width is larger or equal, scale based on width
            new_width = max_size
            scale_factor = max_size / original_width
            new_height = int(original_height * scale_factor)
        else:
            # Height is larger, scale based on height
            new_height = max_size
            scale_factor = max_size / original_height
            new_width = int(original_width * scale_factor)
        
        # Scale the image
        scaled_pixmap = self.current_image.scaled(
            new_width, new_height, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        
        # Update the current image
        self.current_image = scaled_pixmap
        
        # Display the rescaled image
        self.display_image(scaled_pixmap)
        
        # Update status
        self.statusBar().showMessage(
            f"Image rescaled to {new_width}x{new_height} (max dimension: {max_size}px)"
        )
    
    def adjust_contrast(self):
        """Adjust the contrast of the current image"""
        if not self.original_image:
            return
        
        # Get contrast value from slider (-100 to 100)
        contrast_value = self.contrast_slider.value()
        
        # Convert to a factor (0.0 to 2.0, where 1.0 is no change)
        # -100 = 0.0 (no contrast), 0 = 1.0 (original), 100 = 2.0 (double contrast)
        contrast_factor = (contrast_value + 100) / 100.0
        
        # Apply contrast adjustment
        adjusted_image = self.apply_contrast_to_image(self.original_image, contrast_factor)
        
        # Update current image and display
        self.current_image = adjusted_image
        self.display_image(adjusted_image)
        
        # Update status
        self.statusBar().showMessage(f"Contrast adjusted: {contrast_value}")
    
    def apply_contrast_to_image(self, pixmap, factor):
        """Apply contrast adjustment to a pixmap"""
        # Convert pixmap to QImage for pixel manipulation
        image = pixmap.toImage()
        
        # Apply contrast adjustment to each pixel
        for y in range(image.height()):
            for x in range(image.width()):
                pixel = image.pixel(x, y)
                
                # Extract RGB values
                r = (pixel >> 16) & 0xFF
                g = (pixel >> 8) & 0xFF
                b = pixel & 0xFF
                a = (pixel >> 24) & 0xFF
                
                # Apply contrast (move values away from or towards 128)
                r = max(0, min(255, int(128 + (r - 128) * factor)))
                g = max(0, min(255, int(128 + (g - 128) * factor)))
                b = max(0, min(255, int(128 + (b - 128) * factor)))
                
                # Set the new pixel value
                new_pixel = (a << 24) | (r << 16) | (g << 8) | b
                image.setPixel(x, y, new_pixel)
        
        # Convert back to pixmap
        return QPixmap.fromImage(image)
    
    def adjust_temperature(self):
        """Adjust the color temperature of the current image"""
        if not self.original_image:
            return
        
        # Get temperature value from slider (-100 to 100)
        temperature_value = self.temperature_slider.value()
        
        # Apply temperature adjustment
        adjusted_image = self.apply_temperature_to_image(self.original_image, temperature_value)
        
        # Update current image and display
        self.current_image = adjusted_image
        self.display_image(adjusted_image)
        
        # Update status
        self.statusBar().showMessage(f"Temperature adjusted: {temperature_value}")
    
    def apply_temperature_to_image(self, pixmap, temperature_value):
        """Apply temperature adjustment to a pixmap"""
        # Convert pixmap to QImage for pixel manipulation
        image = pixmap.toImage()
        
        # Calculate temperature adjustments
        # Negative values = cooler (more blue), Positive values = warmer (more red/orange)
        temp_factor = temperature_value / 100.0  # Normalize to -1.0 to 1.0
        
        # Temperature adjustment factors
        if temp_factor > 0:  # Warmer
            red_factor = 1.0 + (temp_factor * 0.3)    # Increase red
            green_factor = 1.0 + (temp_factor * 0.1)  # Slightly increase green
            blue_factor = 1.0 - (temp_factor * 0.2)   # Decrease blue
        else:  # Cooler
            red_factor = 1.0 + (temp_factor * 0.2)    # Decrease red
            green_factor = 1.0 + (temp_factor * 0.1)  # Slightly decrease green
            blue_factor = 1.0 - (temp_factor * 0.3)   # Increase blue
        
        # Apply temperature adjustment to each pixel
        for y in range(image.height()):
            for x in range(image.width()):
                pixel = image.pixel(x, y)
                
                # Extract RGB values
                r = (pixel >> 16) & 0xFF
                g = (pixel >> 8) & 0xFF
                b = pixel & 0xFF
                a = (pixel >> 24) & 0xFF
                
                # Apply temperature adjustments
                r = max(0, min(255, int(r * red_factor)))
                g = max(0, min(255, int(g * green_factor)))
                b = max(0, min(255, int(b * blue_factor)))
                
                # Set the new pixel value
                new_pixel = (a << 24) | (r << 16) | (g << 8) | b
                image.setPixel(x, y, new_pixel)
        
        # Convert back to pixmap
        return QPixmap.fromImage(image)
    
    def convert_to_grayscale_6(self):
        """Convert the current image to 6 shades of gray from black to white"""
        if not self.current_image:
            QMessageBox.information(self, "Info", "No image loaded to convert.")
            return
        
        try:
            # Convert the current image to 6 grayscale levels
            converted_image = self.reduce_to_6_grays(self.current_image)
            
            # Update current image and display
            self.current_image = converted_image
            self.display_image(converted_image)
            
            # Update status
            self.statusBar().showMessage("Image converted to 6 shades of gray")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to convert image: {str(e)}")
            self.statusBar().showMessage("Error during grayscale conversion")
    
    def reduce_to_6_grays(self, pixmap):
        """Reduce the image to 6 shades of gray from black to white"""
        # Define 6 gray levels: black, very dark gray, dark gray, light gray, very light gray, white
        gray_levels = [0, 51, 102, 153, 204, 255]  # Evenly distributed from 0 to 255
        
        # Convert QPixmap to QImage for pixel manipulation
        qimage = pixmap.toImage()
        result_image = qimage.copy()
        
        # Process each pixel
        for y in range(qimage.height()):
            for x in range(qimage.width()):
                pixel = qimage.pixel(x, y)
                
                # Extract RGB values
                r = (pixel >> 16) & 0xFF
                g = (pixel >> 8) & 0xFF
                b = pixel & 0xFF
                a = (pixel >> 24) & 0xFF
                
                # Convert to grayscale using luminance formula
                # Standard formula: 0.299*R + 0.587*G + 0.114*B
                gray_value = int(0.299 * r + 0.587 * g + 0.114 * b)
                
                # Find the closest gray level
                closest_gray = min(gray_levels, key=lambda x: abs(x - gray_value))
                
                # Set the new pixel value (same value for R, G, B to make it gray)
                new_pixel = (a << 24) | (closest_gray << 16) | (closest_gray << 8) | closest_gray
                result_image.setPixel(x, y, new_pixel)
        
        # Convert back to QPixmap
        return QPixmap.fromImage(result_image)
    
    def convert_to_palette_colors(self):
        """Convert the current image to colors from color_palette11.csv"""
        if not self.current_image:
            QMessageBox.information(self, "Info", "No image loaded to convert.")
            return
        
        try:
            # Load colors from CSV file
            palette_colors = self.load_palette_from_csv()
            if not palette_colors:
                QMessageBox.warning(self, "Error", "Could not load color palette from color_palette11.csv")
                return
            
            # Convert the current image to palette colors
            converted_image = self.reduce_colors_to_palette(self.current_image, palette_colors)
            
            # Update current image and display
            self.current_image = converted_image
            self.display_image(converted_image)
            
            # Update status
            self.statusBar().showMessage(f"Image converted to {len(palette_colors)} palette colors")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to convert image: {str(e)}")
            self.statusBar().showMessage("Error during palette color conversion")
    
    def load_palette_from_csv(self):
        """Load color palette from color_palette2.csv file"""
        try:
            csv_path = os.path.join(os.path.dirname(__file__), "color_palette2.csv")
            colors = []
            
            with open(csv_path, 'r') as file:
                # Skip header line
                next(file)
                for line in file:
                    color = line.strip()
                    if color and color.startswith('#'):
                        colors.append(color)
            
            return colors
        except Exception as e:
            print(f"Error loading color palette: {e}")
            return []
    
    def reduce_colors_to_palette(self, pixmap, palette_hex):
        """Reduce the number of colors in an image to the specified palette"""
        # Convert hex colors to RGB tuples
        palette_rgb = []
        for hex_color in palette_hex:
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            palette_rgb.append((r, g, b))
        
        # Convert QPixmap to QImage for pixel manipulation
        qimage = pixmap.toImage()
        result_image = qimage.copy()
        
        # Process each pixel to find closest palette color
        for y in range(qimage.height()):
            for x in range(qimage.width()):
                pixel = qimage.pixel(x, y)
                
                # Extract RGB values
                r = (pixel >> 16) & 0xFF
                g = (pixel >> 8) & 0xFF
                b = pixel & 0xFF
                a = (pixel >> 24) & 0xFF
                
                # Find closest color in palette
                closest_color = self.find_closest_color_rgb((r, g, b), palette_rgb)
                
                # Set the new pixel value
                new_pixel = (a << 24) | (closest_color[0] << 16) | (closest_color[1] << 8) | closest_color[2]
                result_image.setPixel(x, y, new_pixel)
        
        # Convert back to QPixmap
        return QPixmap.fromImage(result_image)
    
    def convert_to_32_colors(self):
        """Convert the current image to 32 colors using a predetermined palette"""
        if not self.current_image:
            QMessageBox.information(self, "Info", "No image loaded to convert.")
            return
        
        try:
            # Convert the current image to 32 colors using predetermined palette
            converted_image = self.reduce_colors_to_32_custom(self.current_image)
            
            # Update current image and display
            self.current_image = converted_image
            self.display_image(converted_image)
            
            # Update status
            self.statusBar().showMessage("Image converted to 32 colors using custom palette")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to convert image: {str(e)}")
            self.statusBar().showMessage("Error during color conversion")
    
    def reduce_colors_to_32_custom(self, pixmap):
        """Reduce the number of colors in an image to 32 using your specific palette"""
        # Load custom color palette from CSV
        palette_hex = self.load_palette_from_csv()
        
        # Fallback to default palette if CSV loading fails
        if not palette_hex:
            palette_hex = [
                "#000000", "#FFFFFF", "#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#00FFFF", "#FF00FF",
                "#C0C0C0", "#808080", "#800000", "#808000", "#008000", "#800080", "#008080", "#000080",
                "#FFA500", "#A52A2A", "#FFC0CB", "#FFD700", "#ADD8E6", "#00008B", "#90EE90", "#006400",
                "#D3D3D3", "#A9A9A9", "#FF7F50", "#FA8072", "#4B0082", "#EE82EE", "#40E0D0", "#F5F5DC"
            ]
        
        # Convert hex colors to RGB tuples
        palette_rgb = []
        for hex_color in palette_hex:
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            palette_rgb.append((r, g, b))
        
        # Convert QPixmap to QImage for pixel manipulation
        qimage = pixmap.toImage()
        result_image = qimage.copy()
        
        # Process each pixel to find closest palette color
        for y in range(qimage.height()):
            for x in range(qimage.width()):
                pixel = qimage.pixel(x, y)
                
                # Extract RGB values
                r = (pixel >> 16) & 0xFF
                g = (pixel >> 8) & 0xFF
                b = pixel & 0xFF
                a = (pixel >> 24) & 0xFF
                
                # Find closest color in palette
                closest_color = self.find_closest_color_rgb((r, g, b), palette_rgb)
                
                # Set the new pixel value
                new_pixel = (a << 24) | (closest_color[0] << 16) | (closest_color[1] << 8) | closest_color[2]
                result_image.setPixel(x, y, new_pixel)
        
        # Convert back to QPixmap
        return QPixmap.fromImage(result_image)
    
    def find_closest_color_rgb(self, target_color, palette_colors):
        """Find the closest color in the palette using Euclidean distance"""
        min_distance = float('inf')
        closest_color = palette_colors[0]
        
        r1, g1, b1 = target_color
        
        for color in palette_colors:
            r2, g2, b2 = color
            # Calculate Euclidean distance in RGB space
            distance = ((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2) ** 0.5
            
            if distance < min_distance:
                min_distance = distance
                closest_color = color
        
        return closest_color
    

def main():
    """Main function for the studio module"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("MOSAIC Design Studio")
    app.setApplicationVersion("1.0")
    
    # Create and show the main window
    studio = ImageDesignStudio()
    studio.show()  # Just show normally, maximizing handled in __init__
    
    # Start the event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
