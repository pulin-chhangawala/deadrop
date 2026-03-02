"""
integrity.py - File integrity verification

SHA-256 checksums for uploaded files. Stored alongside the encrypted
file so the recipient can verify the download wasn't corrupted or
tampered with during transit.

This is defense in depth since AES-GCM already provides integrity via
the authentication tag, but an explicit checksum gives the user
a human-readable way to verify.
"""

import hashlib


def compute_checksum(data, algorithm='sha256'):
    """Compute checksum of raw data."""
    h = hashlib.new(algorithm)
    h.update(data)
    return h.hexdigest()


def compute_file_checksum(filepath, algorithm='sha256', chunk_size=8192):
    """Compute checksum of a file (streaming, memory-efficient)."""
    h = hashlib.new(algorithm)
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def verify_checksum(data, expected, algorithm='sha256'):
    """Verify data matches expected checksum."""
    actual = compute_checksum(data, algorithm)
    return actual == expected
