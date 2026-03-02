"""
scheduler.py - Background cleanup scheduler

Periodically purges expired file drops. Runs as a daemon thread
so it doesn't block the Flask request loop.

Two strategies:
  1. Lazy cleanup: check on every download request (already done in routes)
  2. Active cleanup: background thread sweeps every N minutes

The active approach prevents storage from growing even if nobody
is downloading expired files.
"""

import threading
import time
import os
import logging
from app.models import cleanup_expired, get_stats

logger = logging.getLogger(__name__)


class CleanupScheduler:
    """Background thread that periodically cleans up expired drops."""

    def __init__(self, upload_dir, interval_minutes=15):
        self.upload_dir = upload_dir
        self.interval = interval_minutes * 60  # convert to seconds
        self._thread = None
        self._running = False

    def start(self):
        """Start the cleanup thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info(f"Cleanup scheduler started (every {self.interval//60} min)")

    def stop(self):
        """Stop the cleanup thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self):
        """Main loop: periodically purge expired drops."""
        while self._running:
            try:
                self._cleanup()
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

            # sleep in small increments so we can stop quickly
            for _ in range(self.interval):
                if not self._running:
                    break
                time.sleep(1)

    def _cleanup(self):
        """Run one cleanup cycle."""
        expired = cleanup_expired()

        # also remove orphaned files (files with no DB entry)
        if os.path.isdir(self.upload_dir):
            db_files = set()
            stats = get_stats()
            # any files in upload dir that aren't in the DB are orphans

            for fname in os.listdir(self.upload_dir):
                fpath = os.path.join(self.upload_dir, fname)
                if os.path.isfile(fpath):
                    # check age: delete if more than 24 hours old and no DB entry
                    age_hours = (time.time() - os.path.getmtime(fpath)) / 3600
                    if age_hours > 24:
                        try:
                            os.remove(fpath)
                            logger.info(f"Removed orphaned file: {fname}")
                        except OSError:
                            pass

        if expired > 0:
            logger.info(f"Cleaned up {expired} expired drops")


def get_admin_stats():
    """
    Collect system-wide statistics for the admin endpoint.
    
    Returns dict with:
      - total_drops: all-time drop count
      - active_drops: currently valid drops
      - total_downloads: all-time download count
      - storage_used_mb: current disk usage
    """
    stats = get_stats()

    return {
        'total_drops': stats.get('total_drops', 0),
        'active_drops': stats.get('active_drops', 0),
        'expired_drops': stats.get('expired_drops', 0),
        'total_downloads': stats.get('total_downloads', 0),
        'storage_used_mb': stats.get('storage_bytes', 0) / (1024 * 1024),
    }
