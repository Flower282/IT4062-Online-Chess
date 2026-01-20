"""
Chess Board Widget - PyQt6
Renders and handles chess board interaction
Replaces the chess board display logic from React
"""

from PyQt6.QtWidgets import (QWidget, QGridLayout, QPushButton, QLabel, 
                            QSizePolicy, QDialog, QVBoxLayout, QHBoxLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor, QPalette, QPixmap, QIcon
import chess
import os


class ChessBoardWidget(QWidget):
    """
    Interactive chess board widget
    Handles piece rendering and move input
    """
    
    # Signal emitted when user makes a move
    move_made = pyqtSignal(str, str, str)  # from_square, to_square, promotion (optional, '' if none)
    
    def __init__(self, orientation='white', piece_style='neo', parent=None):
        super().__init__(parent)
        self.board = chess.Board()
        self.orientation = orientation  # 'white' or 'black'
        self.selected_square = None
        self.legal_moves = []
        self.piece_style = piece_style  # Style of pieces (neo, classic, etc.)
        self.use_images = True  # Use images instead of Unicode
        self.init_ui()
    
    def init_ui(self):
        """Initialize chess board UI"""
        # Grid layout for 8x8 board
        self.grid = QGridLayout()
        self.grid.setSpacing(0)
        self.grid.setContentsMargins(0, 0, 0, 0)
        
        # Create 64 square buttons
        self.squares = {}
        
        for row in range(8):
            for col in range(8):
                # Calculate square index based on orientation
                if self.orientation == 'white':
                    square_idx = (7 - row) * 8 + col
                else:
                    square_idx = row * 8 + (7 - col)
                
                square = chess.SQUARE_NAMES[square_idx]
                
                # Create button for square
                button = QPushButton()
                # Use size policy instead of fixed size for dynamic scaling
                button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                button.setMinimumSize(30, 30)  # Reduced minimum for smaller window (960x600)
                button.setProperty('square', square)
                button.clicked.connect(lambda checked, sq=square: self.on_square_clicked(sq))
                
                # Set square color
                is_light = (row + col) % 2 == 0
                self.set_square_color(button, is_light, False)
                
                self.squares[square] = button
                self.grid.addWidget(button, row, col)
        
        # Add rank/file labels (optional - can be added later)
        
        self.setLayout(self.grid)
        # Set size policy for the widget itself
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.update_board()
    
    def set_square_color(self, button, is_light, is_selected=False, is_legal=False):
        """Set square background color"""
        if is_selected:
            color = "#ffeb3b"  # Yellow for selected
        elif is_legal:
            color = "#4caf50" if is_light else "#388e3c"  # Green for legal moves
        elif is_light:
            color = "#f0d9b5"  # Light square
        else:
            color = "#b58863"  # Dark square
        
        # Set font using QFont to avoid stylesheet issues
        font = QFont()
        font.setPointSize(36)
        button.setFont(font)
        
        # Simplified stylesheet without font-size
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border: none;
            }}
            QPushButton:hover {{
                border: 2px solid #333;
            }}
        """)
    
    def update_board(self):
        """Update all pieces on board"""
        for square_name, button in self.squares.items():
            square_idx = chess.parse_square(square_name)
            piece = self.board.piece_at(square_idx)
            
            if piece:
                if self.use_images:
                    # Use PNG images
                    self.set_piece_image(button, piece)
                else:
                    # Unicode chess pieces
                    piece_symbol = self.get_piece_unicode(piece)
                    button.setText(piece_symbol)
            else:
                button.setIcon(QIcon())  # Clear icon
                button.setText("")
            
            # Update square colors
            row = chess.square_rank(square_idx)
            col = chess.square_file(square_idx)
            is_light = (row + col) % 2 == 0
            
            is_selected = (square_name == self.selected_square)
            is_legal = square_name in [chess.square_name(move.to_square) 
                                      for move in self.legal_moves]
            
            self.set_square_color(button, is_light, is_selected, is_legal)
    
    def get_piece_unicode(self, piece):
        """Get Unicode character for chess piece"""
        symbols = {
            'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔',
            'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚'
        }
        return symbols.get(piece.symbol(), '')
    
    def set_piece_image(self, button, piece):
        """Set piece image on button - dynamically scale based on button size"""
        # Map piece to file name
        color_prefix = 'w' if piece.color == chess.WHITE else 'b'
        piece_type = piece.symbol().lower()
        filename = f"{color_prefix}{piece_type}.png"
        
        # Get the directory of this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(current_dir, 'pieces', self.piece_style, filename)
        
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            # Scale based on button size (use 80% of button size for padding)
            button_size = min(button.width(), button.height())
            icon_size = max(int(button_size * 0.8), 30)  # At least 30px
            scaled_pixmap = pixmap.scaled(icon_size, icon_size, 
                                         Qt.AspectRatioMode.KeepAspectRatio, 
                                         Qt.TransformationMode.SmoothTransformation)
            button.setIcon(QIcon(scaled_pixmap))
            button.setIconSize(QSize(icon_size, icon_size))
            button.setText("")  # Clear text when using icon
        else:
            # Fallback to Unicode if image not found
            button.setIcon(QIcon())
            button.setText(self.get_piece_unicode(piece))
    
    def set_piece_style(self, style):
        """Change piece style (neo, classic, light, etc.)"""
        available_styles = ['neo', 'classic', 'light', 'tournament', 'newspaper', 'ocean', '8bit']
        if style in available_styles:
            self.piece_style = style
            self.update_board()
    
    def toggle_display_mode(self):
        """Toggle between images and Unicode"""
        self.use_images = not self.use_images
        self.update_board()
    
    def resizeEvent(self, event):
        """Handle widget resize - update piece images to match new size"""
        super().resizeEvent(event)
        # Update board to rescale piece images
        self.update_board()
    
    def sizeHint(self):
        """Provide preferred size for the chess board"""
        # Suggest a square size for 960x600 window (480x480)
        return QSize(480, 480)
    
    def on_square_clicked(self, square):
        """Handle square click"""
        square_idx = chess.parse_square(square)
        piece = self.board.piece_at(square_idx)
        
        if self.selected_square is None:
            # First click - select piece
            if piece and piece.color == self.board.turn:
                self.selected_square = square
                self.legal_moves = [move for move in self.board.legal_moves 
                                   if move.from_square == square_idx]
                self.update_board()
        else:
            # Second click - try to move
            from_square = self.selected_square
            to_square = square
            
            from_square_idx = chess.parse_square(from_square)
            to_square_idx = chess.parse_square(to_square)
            from_piece = self.board.piece_at(from_square_idx)
            
            promotion_piece = ''
            move = None
            
            # Check if pawn promotion is needed
            if from_piece and from_piece.piece_type == chess.PAWN:
                to_rank = chess.square_rank(to_square_idx)
                if (from_piece.color == chess.WHITE and to_rank == 7) or \
                   (from_piece.color == chess.BLACK and to_rank == 0):
                    print(f"👑 Pawn promotion detected: {from_square} -> {to_square}")
                    print(f"   From piece: {from_piece}, color: {from_piece.color}, to_rank: {to_rank}")
                    # Show promotion dialog
                    promotion_piece = self.show_promotion_dialog(from_piece.color)
                    print(f"   Chosen piece: '{promotion_piece}'")
                    if not promotion_piece:  # User cancelled
                        print(f"   ✗ User cancelled promotion")
                        self.selected_square = None
                        self.legal_moves = []
                        self.update_board()
                        return
                    
                    # Create move with promotion
                    # Map 'q' -> QUEEN, 'r' -> ROOK, 'b' -> BISHOP, 'n' -> KNIGHT
                    promotion_map = {
                        'q': chess.QUEEN,
                        'r': chess.ROOK,
                        'b': chess.BISHOP,
                        'n': chess.KNIGHT
                    }
                    promotion_type = promotion_map.get(promotion_piece.lower(), chess.QUEEN)
                    print(f"   Creating promotion move with piece type: {promotion_type}")
                    move = chess.Move(from_square_idx, to_square_idx, promotion=promotion_type)
                else:
                    # Pawn move but not to promotion rank
                    move = chess.Move(from_square_idx, to_square_idx)
            else:
                # Normal move without promotion (not a pawn or different piece)
                move = chess.Move(from_square_idx, to_square_idx)
            
            # Check if move is legal
            if move and move in self.board.legal_moves:
                print(f"✓ Move is legal: {move.uci()}")
                # Emit move signal with promotion piece
                self.move_made.emit(from_square, to_square, promotion_piece)
            else:
                if move:
                    print(f"✗ Move not legal: {move.uci()}")
                else:
                    print(f"✗ No move created")
                print(f"   Legal moves from {from_square}: {[m.uci() for m in self.legal_moves]}")
            
            # Clear selection
            self.selected_square = None
            self.legal_moves = []
            self.update_board()
    
    def set_board(self, fen):
        """Set board from FEN string"""
        self.board = chess.Board(fen)
        self.selected_square = None
        self.legal_moves = []
        self.update_board()
    
    def get_fen(self):
        """Get current FEN"""
        return self.board.fen()
    
    def set_orientation(self, color):
        """Change board orientation"""
        self.orientation = color
        # Recreate board with new orientation
        # Clear and rebuild grid
        for i in reversed(range(self.grid.count())): 
            self.grid.itemAt(i).widget().setParent(None)
        
        self.init_ui()
    
    def show_promotion_dialog(self, color):
        """Show dialog to select promotion piece"""
        print(f"   Opening promotion dialog for color: {color}")
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Pawn Promotion")
        dialog.setModal(True)
        dialog.setMinimumWidth(500)
        dialog.setMinimumHeight(250)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel("Choose piece to promote to:")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        # No stylesheet for title to avoid potential issues
        layout.addWidget(title)
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        
        # Promotion options
        pieces = [
            ('Queen', '♕' if color == chess.WHITE else '♛', 'q'),
            ('Rook', '♖' if color == chess.WHITE else '♜', 'r'),
            ('Bishop', '♗' if color == chess.WHITE else '♝', 'b'),
            ('Knight', '♘' if color == chess.WHITE else '♞', 'n')
        ]
        
        selected_piece = ['q']  # Default to queen
        
        for name, symbol, piece_code in pieces:
            btn = QPushButton()
            btn.setFixedSize(100, 100)
            btn.setToolTip(name)  # Thêm tooltip
            
            # Set piece image or Unicode
            if self.use_images:
                color_prefix = 'w' if color == chess.WHITE else 'b'
                filename = f"{color_prefix}{piece_code}.png"
                current_dir = os.path.dirname(os.path.abspath(__file__))
                image_path = os.path.join(current_dir, 'pieces', self.piece_style, filename)
                
                if os.path.exists(image_path):
                    pixmap = QPixmap(image_path)
                    scaled_pixmap = pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, 
                                                 Qt.TransformationMode.SmoothTransformation)
                    btn.setIcon(QIcon(scaled_pixmap))
                    btn.setIconSize(QSize(80, 80))
                else:
                    btn.setText(symbol)
                    btn_font = QFont()
                    btn_font.setPointSize(42)
                    btn.setFont(btn_font)
            else:
                btn.setText(symbol)
                btn_font = QFont()
                btn_font.setPointSize(42)
                btn.setFont(btn_font)
            
            # Use QPalette instead of stylesheet to avoid "Unknown property" issues
            palette = btn.palette()
            palette.setColor(QPalette.ColorRole.Button, QColor("#4CAF50"))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor("white"))
            btn.setPalette(palette)
            btn.setAutoFillBackground(True)
            
            # Minimal stylesheet for border only
            btn.setStyleSheet("QPushButton { border: 2px solid #388E3C; }")
            btn.clicked.connect(lambda checked, p=piece_code: (
                selected_piece.__setitem__(0, p),
                dialog.accept()
            ))
            buttons_layout.addWidget(btn)
        
        layout.addLayout(buttons_layout)
        dialog.setLayout(layout)
        
        print("   Showing promotion dialog...")
        # Show dialog
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            print(f"   Dialog accepted, selected piece: {selected_piece[0]}")
            return selected_piece[0]
        
        print("   Dialog cancelled, defaulting to queen")
        return 'q'  # Default to queen if dialog closed
