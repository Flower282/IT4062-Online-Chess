# Makefile for Chess TCP Server
# Compile C server core as shared library for Python integration

CC = gcc
CFLAGS = -Wall -Wextra -O2 -fPIC -std=c11
LDFLAGS = -shared
TARGET = libchess_server.so
SOURCES = server_core.c
HEADERS = protocol.h

# Default target
all: $(TARGET)

# Build shared library
$(TARGET): $(SOURCES) $(HEADERS)
	@echo "Compiling $(TARGET)..."
	$(CC) $(CFLAGS) $(LDFLAGS) -o $(TARGET) $(SOURCES)
	@echo "✓ Build successful: $(TARGET)"
	@echo ""
	@echo "To use with Python:"
	@echo "  python3 network_bridge.py"
	@echo ""

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -f $(TARGET)
	rm -f *.o
	@echo "✓ Clean complete"

# Debug build with symbols
debug: CFLAGS += -g -DDEBUG
debug: $(TARGET)

# Install to system (optional)
install: $(TARGET)
	@echo "Installing $(TARGET) to /usr/local/lib..."
	sudo cp $(TARGET) /usr/local/lib/
	sudo ldconfig
	@echo "✓ Installation complete"

# Uninstall from system
uninstall:
	@echo "Uninstalling $(TARGET)..."
	sudo rm -f /usr/local/lib/$(TARGET)
	sudo ldconfig
	@echo "✓ Uninstall complete"

# Test compilation only (no linking)
test-compile:
	$(CC) $(CFLAGS) -c $(SOURCES)
	@echo "✓ Compilation test passed"

# Show compiler version and flags
info:
	@echo "Compiler: $(CC)"
	@echo "Flags: $(CFLAGS)"
	@echo "Sources: $(SOURCES)"
	@echo "Target: $(TARGET)"

# Help
help:
	@echo "Chess TCP Server - Build System"
	@echo ""
	@echo "Available targets:"
	@echo "  make          - Build the shared library (default)"
	@echo "  make debug    - Build with debug symbols"
	@echo "  make clean    - Remove build artifacts"
	@echo "  make install  - Install library to system"
	@echo "  make uninstall- Remove library from system"
	@echo "  make test-compile - Test compilation only"
	@echo "  make info     - Show build configuration"
	@echo "  make help     - Show this help message"
	@echo ""
	@echo "Example usage:"
	@echo "  make          # Build library"
	@echo "  make clean    # Clean up"
	@echo "  make debug    # Build with debugging"

.PHONY: all clean debug install uninstall test-compile info help
