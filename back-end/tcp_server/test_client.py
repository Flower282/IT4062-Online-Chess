#!/usr/bin/env python3
"""
Test client for TCP Chess Server
Demonstrates how to connect and communicate with the server
"""

import socket
import struct
import json
import sys
import time
from typing import Tuple, Optional

# Message type constants
MSG_C2S_REGISTER = 0x0001
MSG_C2S_LOGIN = 0x0002
MSG_C2S_FIND_MATCH = 0x0010
MSG_C2S_MAKE_MOVE = 0x0020
MSG_C2S_RESIGN = 0x0021

MSG_S2C_REGISTER_RESULT = 0x1001
MSG_S2C_LOGIN_RESULT = 0x1002
MSG_S2C_MATCH_FOUND = 0x1100
MSG_S2C_GAME_START = 0x1101
MSG_S2C_GAME_STATE_UPDATE = 0x1200


class ChessClient:
    """TCP client for chess server"""
    
    def __init__(self, host='localhost', port=8765):
        self.host = host
        self.port = port
        self.sock = None
        self.connected = False
    
    def connect(self) -> bool:
        """Connect to the server"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.connected = True
            print(f"✓ Connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from server"""
        if self.sock:
            self.sock.close()
            self.sock = None
            self.connected = False
            print("✓ Disconnected")
    
    def send_message(self, message_id: int, data: dict) -> bool:
        """
        Send a message to the server
        
        Args:
            message_id: Message type ID
            data: Dictionary to send as JSON payload
            
        Returns:
            True if sent successfully
        """
        if not self.connected:
            print("✗ Not connected")
            return False
        
        try:
            # Encode payload as JSON
            payload = json.dumps(data).encode('utf-8')
            payload_len = len(payload)
            
            # Pack header (network byte order)
            header = struct.pack('!HI', message_id, payload_len)
            
            # Send header + payload
            self.sock.sendall(header + payload)
            print(f"→ Sent: 0x{message_id:04x} ({len(payload)} bytes)")
            return True
        
        except Exception as e:
            print(f"✗ Send failed: {e}")
            return False
    
    def receive_message(self, timeout: float = 5.0) -> Optional[Tuple[int, dict]]:
        """
        Receive a message from the server
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (message_id, data) or None
        """
        if not self.connected:
            print("✗ Not connected")
            return None
        
        try:
            # Set timeout
            self.sock.settimeout(timeout)
            
            # Receive header (6 bytes)
            header = self._recv_exactly(6)
            if not header:
                return None
            
            # Unpack header
            message_id, payload_len = struct.unpack('!HI', header)
            
            # Receive payload
            payload = self._recv_exactly(payload_len)
            if not payload:
                return None
            
            # Decode JSON
            data = json.loads(payload.decode('utf-8'))
            
            print(f"← Received: 0x{message_id:04x} ({payload_len} bytes)")
            return message_id, data
        
        except socket.timeout:
            print("✗ Receive timeout")
            return None
        except Exception as e:
            print(f"✗ Receive failed: {e}")
            return None
    
    def _recv_exactly(self, num_bytes: int) -> Optional[bytes]:
        """Receive exactly num_bytes from socket"""
        data = b''
        while len(data) < num_bytes:
            chunk = self.sock.recv(num_bytes - len(data))
            if not chunk:
                return None
            data += chunk
        return data
    
    # High-level API methods
    
    def login(self, username: str, password: str) -> bool:
        """Login to server"""
        print(f"\n=== Login: {username} ===")
        if not self.send_message(MSG_C2S_LOGIN, {
            'username': username,
            'password': password
        }):
            return False
        
        result = self.receive_message()
        if result:
            msg_id, data = result
            if msg_id == MSG_S2C_LOGIN_RESULT:
                if data.get('success'):
                    print(f"✓ Login successful: User ID {data.get('user_id')}")
                    return True
                else:
                    print(f"✗ Login failed: {data.get('error', 'Unknown error')}")
            else:
                print(f"✗ Unexpected response: 0x{msg_id:04x}")
        return False
    
    def register(self, username: str, password: str, email: str) -> bool:
        """Register new account"""
        print(f"\n=== Register: {username} ===")
        if not self.send_message(MSG_C2S_REGISTER, {
            'username': username,
            'password': password,
            'email': email
        }):
            return False
        
        result = self.receive_message()
        if result:
            msg_id, data = result
            if msg_id == MSG_S2C_REGISTER_RESULT:
                if data.get('success'):
                    print(f"✓ Registration successful")
                    return True
                else:
                    print(f"✗ Registration failed: {data.get('error', 'Unknown error')}")
            else:
                print(f"✗ Unexpected response: 0x{msg_id:04x}")
        return False
    
    def find_match(self) -> bool:
        """Request matchmaking"""
        print(f"\n=== Find Match ===")
        if not self.send_message(MSG_C2S_FIND_MATCH, {}):
            return False
        
        result = self.receive_message(timeout=30.0)
        if result:
            msg_id, data = result
            if msg_id == MSG_S2C_MATCH_FOUND:
                print(f"✓ Match found!")
                print(f"  Opponent: {data.get('opponent_username')}")
                print(f"  Rating: {data.get('opponent_rating')}")
                print(f"  Game ID: {data.get('game_id')}")
                return True
            else:
                print(f"✗ Unexpected response: 0x{msg_id:04x}")
        return False
    
    def make_move(self, from_square: str, to_square: str, promotion: str = None) -> bool:
        """Make a chess move"""
        print(f"\n=== Make Move: {from_square} -> {to_square} ===")
        move_data = {
            'from': from_square,
            'to': to_square
        }
        if promotion:
            move_data['promotion'] = promotion
        
        if not self.send_message(MSG_C2S_MAKE_MOVE, move_data):
            return False
        
        result = self.receive_message()
        if result:
            msg_id, data = result
            if msg_id == MSG_S2C_GAME_STATE_UPDATE:
                print(f"✓ Move accepted")
                print(f"  FEN: {data.get('fen', 'N/A')}")
                return True
            else:
                print(f"✗ Move rejected or unexpected response: 0x{msg_id:04x}")
        return False


def test_basic_flow():
    """Test basic login and matchmaking flow"""
    client = ChessClient()
    
    if not client.connect():
        return
    
    try:
        # Test login
        if client.login('testuser', 'password123'):
            # Test matchmaking
            client.find_match()
        
        # Keep connection open briefly
        time.sleep(1)
    
    finally:
        client.disconnect()


def test_register():
    """Test registration"""
    client = ChessClient()
    
    if not client.connect():
        return
    
    try:
        client.register('newuser', 'pass123', 'new@example.com')
    
    finally:
        client.disconnect()


def interactive_mode():
    """Interactive testing mode"""
    client = ChessClient()
    
    if not client.connect():
        return
    
    print("\n=== Interactive Mode ===")
    print("Commands:")
    print("  login <username> <password>")
    print("  register <username> <password> <email>")
    print("  find_match")
    print("  move <from> <to> [promotion]")
    print("  quit")
    print()
    
    try:
        while True:
            try:
                cmd = input("> ").strip().split()
                if not cmd:
                    continue
                
                if cmd[0] == 'quit':
                    break
                
                elif cmd[0] == 'login' and len(cmd) >= 3:
                    client.login(cmd[1], cmd[2])
                
                elif cmd[0] == 'register' and len(cmd) >= 4:
                    client.register(cmd[1], cmd[2], cmd[3])
                
                elif cmd[0] == 'find_match':
                    client.find_match()
                
                elif cmd[0] == 'move' and len(cmd) >= 3:
                    promotion = cmd[3] if len(cmd) > 3 else None
                    client.make_move(cmd[1], cmd[2], promotion)
                
                else:
                    print("Invalid command")
            
            except KeyboardInterrupt:
                print("\nInterrupted")
                break
    
    finally:
        client.disconnect()


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 test_client.py test      # Run basic test")
        print("  python3 test_client.py register  # Test registration")
        print("  python3 test_client.py interactive # Interactive mode")
        return
    
    mode = sys.argv[1]
    
    if mode == 'test':
        test_basic_flow()
    elif mode == 'register':
        test_register()
    elif mode == 'interactive':
        interactive_mode()
    else:
        print(f"Unknown mode: {mode}")


if __name__ == '__main__':
    main()
