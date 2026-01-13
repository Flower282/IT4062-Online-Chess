"""
UI Utilities for DPI-aware and responsive design
Cross-platform compatible sizing and styling
"""

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QTimer
from typing import Tuple


class CenteredMessageBox:
    """
    Helper to show QMessageBox centered on parent on Linux.
    
    On Linux (X11/Wayland), QMessageBox geometry is not available until
    after the window manager processes the show() event. Using exec()
    immediately causes the dialog to appear at default position (0,0).
    
    Solution: Use show() instead of exec(), then center after event loop.
    """
    
    @staticmethod
    def show_and_exec(msg_box, parent=None):
        """
        Show message box centered on parent (Linux-compatible).
        
        This is a BLOCKING call that returns the user's choice.
        
        Why this works on Linux:
        1. show() tells window manager to display dialog
        2. QTimer.singleShot(0, ...) schedules centering AFTER WM processes show()
        3. Dialog geometry is now available, so we can calculate center position
        4. exec() is called from within the event loop, after positioning
        
        Args:
            msg_box: QMessageBox instance (already configured)
            parent: Parent widget (if None, uses msg_box.parent())
        
        Returns:
            StandardButton clicked by user
        """
        if parent is None:
            parent = msg_box.parent()
        
        # Show dialog (non-blocking, tells WM to map window)
        msg_box.show()
        
        # Schedule centering after window manager has processed show()
        def center_and_exec():
            if parent and parent.isVisible():
                # Get parent frame geometry (includes window decorations)
                parent_geo = parent.frameGeometry()
                
                # Get dialog frame geometry (now available after show())
                dialog_geo = msg_box.frameGeometry()
                
                # Calculate center position
                x = parent_geo.x() + (parent_geo.width() - dialog_geo.width()) // 2
                y = parent_geo.y() + (parent_geo.height() - dialog_geo.height()) // 2
                
                # Move dialog to center
                msg_box.move(x, y)
            
            # Now exec() to make it blocking and get user response
            # At this point, dialog is already visible and positioned
            msg_box.result_value = msg_box.exec()
        
        # Execute centering after event loop processes show()
        QTimer.singleShot(0, center_and_exec)
        
        # Process events until exec() is called and completed
        # This allows the QTimer callback to run
        QApplication.processEvents()
        
        # Wait for dialog to close and return result
        # The exec() call in center_and_exec() will block here
        while not hasattr(msg_box, 'result_value'):
            QApplication.processEvents()
        
        return msg_box.result_value


class ResponsiveUI:
    """Helper class for DPI-aware and responsive UI calculations"""
    
    @staticmethod
    def get_dpi_scale() -> float:
        """Get DPI scale factor relative to 96 DPI (standard)"""
        screen = QApplication.primaryScreen()
        if screen:
            logical_dpi = screen.logicalDotsPerInch()
            # Standard DPI is 96, calculate scale factor
            return logical_dpi / 96.0
        return 1.0
    
    @staticmethod
    def scale_size(size: int) -> int:
        """Scale a size value based on DPI"""
        return int(size * ResponsiveUI.get_dpi_scale())
    
    @staticmethod
    def scale_font_size(base_size: int) -> int:
        """Scale font size based on DPI"""
        scale = ResponsiveUI.get_dpi_scale()
        # Font scaling should be less aggressive than UI scaling
        font_scale = 1.0 + (scale - 1.0) * 0.7
        return max(8, int(base_size * font_scale))
    
    @staticmethod
    def get_font(family: str = None, size: int = 10, bold: bool = False) -> QFont:
        """
        Get a DPI-aware font
        
        Args:
            family: Font family (will use system default if None)
            size: Base font size in points
            bold: Whether font should be bold
        """
        font = QFont()
        
        if family:
            # Set font family with common fallbacks
            fallbacks = ["Ubuntu", "Segoe UI", "Arial", "Helvetica", "sans-serif"]
            if family not in fallbacks:
                fallbacks.insert(0, family)
            font.setFamilies(fallbacks)
        
        # Set point size (Qt handles DPI scaling automatically for point sizes)
        font.setPointSize(size)
        
        if bold:
            font.setWeight(QFont.Weight.Bold)
        
        return font
    
    @staticmethod
    def get_responsive_window_size(
        preferred_width: int,
        preferred_height: int,
        min_width: int = 800,
        min_height: int = 600,
        max_screen_percent: float = 0.85
    ) -> Tuple[int, int]:
        """
        Calculate responsive window size based on screen size
        
        Args:
            preferred_width: Preferred window width
            preferred_height: Preferred window height
            min_width: Minimum window width
            min_height: Minimum window height
            max_screen_percent: Maximum percentage of screen to use
        
        Returns:
            Tuple of (width, height)
        """
        screen = QApplication.primaryScreen()
        if not screen:
            return (preferred_width, preferred_height)
        
        available = screen.availableGeometry()
        
        # Calculate maximum size based on screen
        max_width = int(available.width() * max_screen_percent)
        max_height = int(available.height() * max_screen_percent)
        
        # Use preferred size, but constrain to screen size
        width = min(preferred_width, max_width)
        height = min(preferred_height, max_height)
        
        # Ensure minimum size
        width = max(width, min_width)
        height = max(height, min_height)
        
        return (width, height)
    
    @staticmethod
    def get_button_stylesheet(
        bg_color: str = "#2196f3",
        text_color: str = "white",
        hover_color: str = "#1976d2",
        disabled_color: str = "#ccc"
    ) -> str:
        """
        Get DPI-aware button stylesheet
        Uses em units and percentages instead of fixed pixels
        """
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: none;
                border-radius: 0.3em;
                padding: 0.5em 1em;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:disabled {{
                background-color: {disabled_color};
                color: #888;
            }}
        """
    
    @staticmethod
    def get_messagebox_stylesheet() -> str:
        """Get cross-platform MessageBox stylesheet - scaled for 960x600 window"""
        return """
            QMessageBox {
                min-width: 18em;
            }
            QLabel {
                min-width: 15em;
                padding: 0.6em;
                font-size: 8pt;
            }
            QPushButton {
                min-width: 4.5em;
                min-height: 1.8em;
                padding: 0.3em 0.75em;
                font-size: 8pt;
            }
        """
    
    @staticmethod
    def center_widget_on_parent(widget, parent):
        """
        Center a widget on its parent window
        DPI-independent positioning
        """
        if not parent or not widget:
            return
        
        # Ensure widget has been sized
        widget.adjustSize()
        
        # Get parent geometry
        parent_geo = parent.geometry()
        widget_geo = widget.geometry()
        
        # Calculate center position
        x = parent_geo.x() + (parent_geo.width() - widget_geo.width()) // 2
        y = parent_geo.y() + (parent_geo.height() - widget_geo.height()) // 2
        
        # Move widget
        widget.move(x, y)
