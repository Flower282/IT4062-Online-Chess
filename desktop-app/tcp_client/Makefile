# Makefile for TCP Client C Library

CC = gcc
CFLAGS = -Wall -Wextra -O2 -fPIC
LDFLAGS = -shared

TARGET = libchess_client.so
SOURCES = client_core.c
OBJECTS = $(SOURCES:.c=.o)

.PHONY: all clean

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CC) $(LDFLAGS) -o $@ $^
	@echo "✓ Built $(TARGET)"

%.o: %.c protocol.h
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJECTS) $(TARGET)
	@echo "✓ Cleaned build files"

test: $(TARGET)
	@echo "Testing library..."
	@python3 -c "import ctypes; lib = ctypes.CDLL('./$(TARGET)'); print('✓ Library loaded successfully')"
