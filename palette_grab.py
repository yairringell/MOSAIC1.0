# palette_grab.py
# MOSAIC project - Interactive pixel color picker
# Click on image pixels to capture hex colors and build a palette

import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QLabel, QFileDialog, QScrollArea,
                             QMessageBox, QFrame, QListWidget, QListWidgetItem, QSplitter)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPixmap, QColor, QPainter, QFont, QPen, QBrush
from PIL import Image
import csv


class ClickableImageLabel(QLabel):
    """Custom QLabel that can detect mouse clicks and return pixel colors"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.original_pixmap = None
        self.scaled_pixmap = None
        self.pil_image = None
        self.scale_factor = 1.0
        
        # Set up the label
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("border: 2px solid #cccccc; background-color: #f0f0f0;")
        self.setText("Click 'Load Image' to begin")
        self.setMinimumSize(400, 300)
    
    def set_image(self, image_path):
        """Load and display an image"""
        try:
            # Load with PIL for pixel access
            self.pil_image = Image.open(image_path)
            if self.pil_image.mode != 'RGB':
                self.pil_image = self.pil_image.convert('RGB')
            
            # Load with Qt for display
            self.original_pixmap = QPixmap(image_path)
            self.update_display()
            
            return True
        except Exception as e:
            print(f"Error loading image: {e}")
            return False
    
    def update_display(self):
        """Update the displayed image, scaling it to fit the label"""
        if self.original_pixmap:
            # Scale pixmap to fit label while maintaining aspect ratio
            label_size = self.size()
            self.scaled_pixmap = self.original_pixmap.scaled(
                label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            
            # Calculate scale factor for coordinate conversion
            original_size = self.original_pixmap.size()
            scaled_size = self.scaled_pixmap.size()
            self.scale_factor = min(
                scaled_size.width() / original_size.width(),
                scaled_size.height() / original_size.height()
            )
            
            self.setPixmap(self.scaled_pixmap)
    
    def resizeEvent(self, event):
        """Handle resize events to update image display"""
        super().resizeEvent(event)
        if self.original_pixmap:
            self.update_display()
    
    def mousePressEvent(self, event):
        """Handle mouse clicks to get pixel colors"""
        if self.pil_image is None or self.scaled_pixmap is None:
            return
        
        # Get click position
        click_pos = event.pos()
        
        # Calculate the position of the image within the label
        label_size = self.size()
        pixmap_size = self.scaled_pixmap.size()
        
        # Calculate offsets to center the image
        x_offset = (label_size.width() - pixmap_size.width()) // 2
        y_offset = (label_size.height() - pixmap_size.height()) // 2
        
        # Convert click position to image coordinates
        image_x = click_pos.x() - x_offset
        image_y = click_pos.y() - y_offset
        
        # Check if click is within the image bounds
        if (0 <= image_x < pixmap_size.width() and 0 <= image_y < pixmap_size.height()):
            # Convert to original image coordinates
            original_x = int(image_x / self.scale_factor)
            original_y = int(image_y / self.scale_factor)
            
            # Ensure coordinates are within bounds
            original_x = max(0, min(original_x, self.pil_image.width - 1))
            original_y = max(0, min(original_y, self.pil_image.height - 1))
            
            # Get pixel color
            pixel_color = self.pil_image.getpixel((original_x, original_y))
            hex_color = f"#{pixel_color[0]:02x}{pixel_color[1]:02x}{pixel_color[2]:02x}"
            
            # Add to palette
            if self.parent_window:
                self.parent_window.add_color_to_palette(hex_color)


class ColorListItem(QWidget):
    """Custom widget for displaying color and hex value in the list"""
    
    def __init__(self, hex_color, parent=None):
        super().__init__(parent)
        self.hex_color = hex_color
        
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Color swatch
        color_swatch = QLabel()
        color_swatch.setFixedSize(30, 30)
        color_swatch.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #333;")
        layout.addWidget(color_swatch)
        
        # Hex value label
        hex_label = QLabel(hex_color.upper())
        hex_label.setFont(QFont("Courier", 10))
        hex_label.setStyleSheet("padding: 5px;")
        layout.addWidget(hex_label)
        
        # Add stretch to push everything to the left
        layout.addStretch()
        
        # Delete button
        delete_btn = QPushButton("×")
        delete_btn.setFixedSize(25, 25)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #cc0000;
            }
        """)
        delete_btn.clicked.connect(lambda: self.remove_color(hex_color))
        layout.addWidget(delete_btn)
    
    def remove_color(self, hex_color):
        """Remove this color from the palette"""
        # Find the main window (PaletteGrabber instance)
        main_window = self.parent()
        while main_window and not hasattr(main_window, 'remove_color_from_palette'):
            main_window = main_window.parent()
        
        if main_window:
            main_window.remove_color_from_palette(hex_color)


class PaletteGrabber(QMainWindow):
    """Main window for interactive pixel color picking"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MOSAIC Palette Grabber - Click to Pick Colors")
        self.setGeometry(100, 100, 1000, 700)
        
        # Color palette storage
        self.color_palette = []
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout with splitter
        main_layout = QHBoxLayout(central_widget)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Image display
        self.create_image_panel(splitter)
        
        # Right panel - Color palette
        self.create_palette_panel(splitter)
        
        # Set splitter proportions (image larger, palette smaller)
        splitter.setSizes([700, 300])
        
        # Status bar
        self.statusBar().showMessage("Load an image and click on pixels to capture their colors")
    
    def create_image_panel(self, parent):
        """Create the left panel with image display and controls"""
        image_widget = QWidget()
        image_layout = QVBoxLayout(image_widget)
        
        # Top controls
        controls_layout = QHBoxLayout()
        
        load_btn = QPushButton("Load Image")
        load_btn.clicked.connect(self.load_image)
        load_btn.setStyleSheet("QPushButton { padding: 8px 16px; font-weight: bold; }")
        controls_layout.addWidget(load_btn)
        
        self.image_info_label = QLabel("No image loaded")
        self.image_info_label.setStyleSheet("color: #666; font-style: italic; margin-left: 10px;")
        controls_layout.addWidget(self.image_info_label)
        
        controls_layout.addStretch()
        
        image_layout.addLayout(controls_layout)
        
        # Image display area
        self.image_label = ClickableImageLabel(self)
        image_layout.addWidget(self.image_label)
        
        parent.addWidget(image_widget)
    
    def create_palette_panel(self, parent):
        """Create the right panel with color palette"""
        palette_widget = QWidget()
        palette_layout = QVBoxLayout(palette_widget)
        
        # Title
        title_label = QLabel("Color Palette")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("padding: 10px; background-color: #e0e0e0; border-radius: 5px;")
        palette_layout.addWidget(title_label)
        
        # Instructions
        instructions = QLabel("Click on image pixels to add colors to your palette")
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #666; font-size: 10px; padding: 5px; font-style: italic;")
        instructions.setAlignment(Qt.AlignCenter)
        palette_layout.addWidget(instructions)
        
        # Color list
        self.color_list = QListWidget()
        self.color_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ccc;
                border-radius: 5px;
                background-color: white;
            }
            QListWidget::item {
                border-bottom: 1px solid #eee;
                padding: 2px;
            }
        """)
        palette_layout.addWidget(self.color_list)
        
        # Bottom controls
        bottom_layout = QHBoxLayout()
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear_palette)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff6666;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #ff4444;
            }
        """)
        bottom_layout.addWidget(clear_btn)
        
        save_btn = QPushButton("Save to CSV")
        save_btn.clicked.connect(self.save_palette_to_csv)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        bottom_layout.addWidget(save_btn)
        
        palette_layout.addLayout(bottom_layout)
        
        # Color count label
        self.count_label = QLabel("Colors: 0")
        self.count_label.setAlignment(Qt.AlignCenter)
        self.count_label.setStyleSheet("color: #666; font-size: 10px; padding: 5px;")
        palette_layout.addWidget(self.count_label)
        
        parent.addWidget(palette_widget)
    
    def load_image(self):
        """Load an image file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff)"
        )
        
        if file_path:
            if self.image_label.set_image(file_path):
                filename = os.path.basename(file_path)
                self.image_info_label.setText(f"Loaded: {filename}")
                self.image_info_label.setStyleSheet("color: #000;")
                self.statusBar().showMessage(f"Image loaded: {filename} - Click on pixels to capture colors")
            else:
                QMessageBox.warning(self, "Error", "Failed to load image")
    
    def add_color_to_palette(self, hex_color):
        """Add a color to the palette list"""
        # Check if color already exists
        if hex_color.upper() not in [color.upper() for color in self.color_palette]:
            self.color_palette.append(hex_color.upper())
            
            # Create list item
            item = QListWidgetItem()
            color_widget = ColorListItem(hex_color.upper(), self.color_list)
            item.setSizeHint(color_widget.sizeHint())
            
            self.color_list.addItem(item)
            self.color_list.setItemWidget(item, color_widget)
            
            # Scroll to new item
            self.color_list.scrollToBottom()
            
            # Update count
            self.update_color_count()
            
            self.statusBar().showMessage(f"Added color: {hex_color.upper()}")
    
    def remove_color_from_palette(self, hex_color):
        """Remove a color from the palette"""
        try:
            # Find and remove from palette list
            self.color_palette.remove(hex_color.upper())
            
            # Find and remove from list widget
            for i in range(self.color_list.count()):
                item = self.color_list.item(i)
                widget = self.color_list.itemWidget(item)
                if widget and widget.hex_color.upper() == hex_color.upper():
                    self.color_list.takeItem(i)
                    break
            
            self.update_color_count()
            self.statusBar().showMessage(f"Removed color: {hex_color}")
            
        except ValueError:
            pass  # Color not in list
    
    def clear_palette(self):
        """Clear all colors from the palette"""
        if self.color_palette:
            reply = QMessageBox.question(
                self, "Clear Palette", 
                f"Are you sure you want to remove all {len(self.color_palette)} colors?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.color_palette.clear()
                self.color_list.clear()
                self.update_color_count()
                self.statusBar().showMessage("Palette cleared")
    
    def update_color_count(self):
        """Update the color count display"""
        count = len(self.color_palette)
        self.count_label.setText(f"Colors: {count}")
    
    def save_palette_to_csv(self):
        """Save the color palette to a CSV file"""
        if not self.color_palette:
            QMessageBox.warning(self, "No Colors", "Add some colors to your palette first!")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Color Palette", "color_palette.csv", "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['Color'])  # Header
                    for color in self.color_palette:
                        writer.writerow([color])
                
                filename = os.path.basename(file_path)
                QMessageBox.information(
                    self, "Saved", 
                    f"Palette with {len(self.color_palette)} colors saved to {filename}"
                )
                self.statusBar().showMessage(f"Palette saved to: {filename}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save palette: {str(e)}")


def main():
    """Main function to run the palette grabber"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("MOSAIC Palette Grabber")
    app.setApplicationVersion("1.0")
    
    # Create and show the main window
    palette_grabber = PaletteGrabber()
    palette_grabber.show()
    
    # Start the event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()