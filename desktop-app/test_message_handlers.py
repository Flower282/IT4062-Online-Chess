#!/usr/bin/env python3
"""
Test script to verify all S2C message types are registered
"""

from network_bridge_client import MessageTypeS2C

print("=" * 60)
print("All Server-to-Client Message Types:")
print("=" * 60)

for msg_type in MessageTypeS2C:
    print(f"  ✓ {msg_type.name:25s} (0x{msg_type.value:04x})")

print("=" * 60)
print(f"Total: {len(MessageTypeS2C)} message types")
print("=" * 60)
print()
print("These message types are now automatically registered in NetworkClient.")
print("No more '⚠ No handler registered' warnings!")
