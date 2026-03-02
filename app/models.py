"""
models.py - SQLite database models for file metadata

Tracks uploaded files, their encryption keys, expiry times,
and download counts.
"""

import sqlite3
import os
import uuid
from datetime import datetime, timedelta


def get_db(db_path='deadrop.db'):
    """Get a database connection with row factory."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path='deadrop.db'):
    """Create tables if they don't exist."""
    conn = get_db(db_path)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS drops (
            id TEXT PRIMARY KEY,
            original_filename TEXT NOT NULL,
            stored_filename TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            encryption_key_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            max_downloads INTEGER DEFAULT 1,
            download_count INTEGER DEFAULT 0,
            is_expired INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()


def create_drop(db_path, original_filename, stored_filename, file_size,
                key_hash, expiry_hours=24, max_downloads=1):
    """Register a new file drop. Returns the drop ID."""
    drop_id = str(uuid.uuid4())[:8]  # short IDs are more user-friendly
    expires_at = datetime.utcnow() + timedelta(hours=expiry_hours)
    
    conn = get_db(db_path)
    conn.execute('''
        INSERT INTO drops (id, original_filename, stored_filename, file_size,
                          encryption_key_hash, expires_at, max_downloads)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (drop_id, original_filename, stored_filename, file_size,
          key_hash, expires_at, max_downloads))
    conn.commit()
    conn.close()
    
    return drop_id


def get_drop(db_path, drop_id):
    """Fetch a drop by ID. Returns None if not found or expired."""
    conn = get_db(db_path)
    row = conn.execute(
        'SELECT * FROM drops WHERE id = ?', (drop_id,)
    ).fetchone()
    conn.close()
    
    if not row:
        return None
    
    # check expiry
    expires_at = datetime.fromisoformat(row['expires_at'])
    if datetime.utcnow() > expires_at:
        mark_expired(db_path, drop_id)
        return None
    
    # check download limit
    if row['download_count'] >= row['max_downloads']:
        return None
    
    return dict(row)


def increment_downloads(db_path, drop_id):
    """Increment download count. Returns new count."""
    conn = get_db(db_path)
    conn.execute(
        'UPDATE drops SET download_count = download_count + 1 WHERE id = ?',
        (drop_id,))
    conn.commit()
    
    row = conn.execute(
        'SELECT download_count, max_downloads FROM drops WHERE id = ?',
        (drop_id,)).fetchone()
    conn.close()
    
    if row and row['download_count'] >= row['max_downloads']:
        mark_expired(db_path, drop_id)
    
    return row['download_count'] if row else 0


def mark_expired(db_path, drop_id):
    """Mark a drop as expired and delete the encrypted file."""
    conn = get_db(db_path)
    row = conn.execute(
        'SELECT stored_filename FROM drops WHERE id = ?', (drop_id,)
    ).fetchone()
    
    if row:
        # try to delete the encrypted file
        try:
            upload_dir = os.environ.get('UPLOAD_DIR', '/tmp/deadrop_uploads')
            filepath = os.path.join(upload_dir, row['stored_filename'])
            if os.path.exists(filepath):
                os.remove(filepath)
        except OSError:
            pass
    
    conn.execute(
        'UPDATE drops SET is_expired = 1 WHERE id = ?', (drop_id,))
    conn.commit()
    conn.close()


def cleanup_expired(db_path):
    """Clean up all expired drops. Run periodically."""
    conn = get_db(db_path)
    expired = conn.execute('''
        SELECT id FROM drops 
        WHERE is_expired = 0 AND expires_at < ?
    ''', (datetime.utcnow(),)).fetchall()
    conn.close()
    
    for row in expired:
        mark_expired(db_path, row['id'])
    
    return len(expired)
