# Hướng dẫn sử dụng tính năng điều chỉnh giao diện quân cờ

## Tổng quan
Desktop app hiện đã hỗ trợ 7 bộ quân cờ khác nhau với hình ảnh PNG chất lượng cao, tương tự như web app.

## Các bộ quân cờ có sẵn

1. **neo** (mặc định) - Phong cách hiện đại, sắc nét
2. **classic** - Kiểu truyền thống, cổ điển
3. **light** - Thiết kế nhẹ nhàng, tối giản
4. **tournament** - Phong cách thi đấu chuyên nghiệp
5. **newspaper** - Kiểu báo in, đen trắng
6. **ocean** - Phong cách biển cả
7. **8bit** - Phong cách retro, pixel art

## Cách sử dụng

### Trong game:
1. Mở game window
2. Tìm dropdown **"🎨 Kiểu quân cờ:"** ở panel bên phải
3. Chọn bộ quân cờ yêu thích từ danh sách
4. Bàn cờ sẽ tự động cập nhật ngay lập tức

### Lập trình:
```python
# Khởi tạo với style cụ thể
board = ChessBoardWidget(orientation='white', piece_style='classic')

# Thay đổi style runtime
board.set_piece_style('tournament')

# Toggle giữa hình ảnh và Unicode (nếu cần)
board.toggle_display_mode()
```

## Cấu trúc thư mục
```
desktop-app/
├── pieces/
│   ├── neo/          # Chứa 12 file PNG (wb, wn, wp, wr, wq, wk, bb, bn, bp, br, bq, bk)
│   ├── classic/
│   ├── light/
│   ├── tournament/
│   ├── newspaper/
│   ├── ocean/
│   └── 8bit/
├── chess_board_widget.py  # Widget quản lý bàn cờ
└── game_window.py         # Cửa sổ game chính
```

## Thay đổi kỹ thuật

### chess_board_widget.py
- Thêm parameter `piece_style` vào constructor
- Thêm thuộc tính `use_images` để toggle giữa hình ảnh/Unicode
- Thêm phương thức `set_piece_image()` để load và hiển thị hình ảnh PNG
- Thêm phương thức `set_piece_style()` để thay đổi bộ quân
- Cập nhật `update_board()` để hỗ trợ cả 2 chế độ hiển thị
- Cập nhật promotion dialog để hiển thị hình ảnh

### game_window.py
- Import thêm `QComboBox`
- Thêm ComboBox chọn bộ quân vào right panel
- Thêm phương thức `on_piece_style_changed()` xử lý sự kiện thay đổi
- Khởi tạo chess board với style mặc định 'neo'

## Tính năng bổ sung

### Fallback mechanism
Nếu không tìm thấy file hình ảnh, hệ thống tự động chuyển sang Unicode characters làm dự phòng.

### Performance
- Hình ảnh được scale về 50x50 pixels để tối ưu hiệu năng
- Sử dụng `SmoothTransformation` để đảm bảo chất lượng

## Ghi chú
- Tất cả hình ảnh được copy từ web app (/front-end/public/chess-themes/pieces/)
- Format file: `[color][piece].png` (ví dụ: wp.png = white pawn, bk.png = black king)
- Không cần cài thêm dependencies mới
