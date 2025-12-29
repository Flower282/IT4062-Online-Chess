#!/bin/bash
# Build and test script for TCP Chess Server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================================"
echo "TCP Chess Server - Build and Test"
echo "================================================"
echo ""

# Step 1: Build C library
echo -e "${YELLOW}[1/4] Building C library...${NC}"
cd tcp_server

if make clean && make; then
    echo -e "${GREEN}✓ Build successful${NC}"
else
    echo -e "${RED}✗ Build failed${NC}"
    exit 1
fi

echo ""

# Step 2: Verify library exists
echo -e "${YELLOW}[2/4] Verifying library...${NC}"
if [ -f "libchess_server.so" ]; then
    echo -e "${GREEN}✓ Library found: libchess_server.so${NC}"
    echo "  Size: $(du -h libchess_server.so | cut -f1)"
    echo "  Symbols: $(nm -D libchess_server.so | grep -c ' T ')"
else
    echo -e "${RED}✗ Library not found${NC}"
    exit 1
fi

echo ""

# Step 3: Check Python dependencies
echo -e "${YELLOW}[3/4] Checking Python environment...${NC}"
cd ..

python3 -c "import ctypes, json, chess" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Python dependencies OK${NC}"
else
    echo -e "${RED}✗ Missing Python dependencies${NC}"
    echo "Install required packages:"
    echo "  pip install python-chess"
    exit 1
fi

echo ""

# Step 4: Test import
echo -e "${YELLOW}[4/4] Testing Python import...${NC}"
cd tcp_server

python3 -c "from network_bridge import NetworkManager; print('Import successful')" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Python import successful${NC}"
else
    echo -e "${RED}✗ Python import failed${NC}"
    exit 1
fi

cd ..

echo ""
echo "================================================"
echo -e "${GREEN}✓ All checks passed!${NC}"
echo "================================================"
echo ""
echo "Next steps:"
echo "  1. Start the example server:"
echo "     python3 tcp_server/network_bridge.py"
echo ""
echo "  2. Test with client (in another terminal):"
echo "     python3 tcp_server/test_client.py interactive"
echo ""
echo "  3. Or use the full example:"
echo "     python3 server_tcp_example.py"
echo ""
