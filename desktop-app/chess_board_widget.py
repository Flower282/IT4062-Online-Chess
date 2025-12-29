"""
Chess Board Widget - PyQt6
Renders and handles chess board interaction
Replaces the chess board display logic from React
"""

from PyQt6.QtWidgets import QWidget, QGridLayout, QPushButton, QLabel, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor, QPalette
import chess


class ChessBoardWidget(QWidget):
    """
    Interactive chess board widget
    Handles piece rendering and move input
    """
    
    # Signal emitted when user makes a move
    move_made = pyqtSignal(str, str)  # from_square, to_square
    
    def __init__(self, orientation='white', parent=None):
        super().__init__(parent)
        self.board = chess.Board()
        self.orientation = orientation  # 'white' or 'black'
        self.selected_square = None
        self.legal_moves = []
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
                button.setFixedSize(60, 60)
                button.setProperty('square', square)
                button.clicked.connect(lambda checked, sq=square: self.on_square_clicked(sq))
                
                # Set square color
                is_light = (row + col) % 2 == 0
                self.set_square_color(button, is_light, False)
                
                self.squares[square] = button
                self.grid.addWidget(button, row, col)
        
        # Add rank/file labels (optional - can be added later)
        
        self.setLayout(self.grid)
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
        
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border: none;
                font-size: 36px;
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
                # Unicode chess pieces
                piece_symbol = self.get_piece_unicode(piece)
                button.setText(piece_symbol)
            else:
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
            
            # Check if move is legal
            move = chess.Move(chess.parse_square(from_square), 
                            chess.parse_square(to_square))
            
            # Check for promotion
            if move in self.board.legal_moves:
                # Check if pawn promotion
                from_piece = self.board.piece_at(chess.parse_square(from_square))
                if from_piece and from_piece.piece_type == chess.PAWN:
                    to_rank = chess.square_rank(chess.parse_square(to_square))
                    if (from_piece.color == chess.WHITE and to_rank == 7) or \
                       (from_piece.color == chess.BLACK and to_rank == 0):
                        # For now, always promote to queen
                        # TODO: Add promotion dialog
                        move = chess.Move(move.from_square, move.to_square, chess.QUEEN)
                
                # Emit move signal
                self.move_made.emit(from_square, to_square)
            
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
