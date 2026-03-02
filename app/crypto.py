"""
crypto.py - AES-256 file encryption/decryption

Uses AES-256-GCM for authenticated encryption. Each file gets its own
random nonce, so even identical files produce different ciphertexts.
"""

import os
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def derive_key(passphrase: str) -> bytes:
    """Derive a 256-bit key from a passphrase using SHA-256.
    
    In production you'd use PBKDF2 or Argon2, but for a demo project
    this keeps the dependency list small.
    """
    return hashlib.sha256(passphrase.encode()).digest()


def generate_key() -> bytes:
    """Generate a random 256-bit key."""
    return AESGCM.generate_key(bit_length=256)


def encrypt_file(data: bytes, key: bytes) -> bytes:
    """
    Encrypt file data using AES-256-GCM.
    
    Output format: nonce (12 bytes) || ciphertext+tag
    """
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, data, None)
    return nonce + ciphertext


def decrypt_file(encrypted_data: bytes, key: bytes) -> bytes:
    """
    Decrypt file data. Raises an exception if the key is wrong
    or data has been tampered with (that's the 'authenticated' part).
    """
    nonce = encrypted_data[:12]
    ciphertext = encrypted_data[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)
