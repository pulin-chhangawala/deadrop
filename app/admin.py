"""
admin.py - Admin API endpoints

Protected endpoints for monitoring the service. In production you'd
add token-based auth, but for a demo project this is sufficient.

Endpoints:
    GET /api/stats   - System-wide statistics
    POST /api/purge  - Force cleanup of expired drops
"""

from flask import Blueprint, jsonify, request
from app.models import cleanup_expired, get_stats
from app.scheduler import get_admin_stats

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/api/stats')
def api_stats():
    """Return system-wide statistics."""
    stats = get_admin_stats()
    return jsonify(stats)


@admin_bp.route('/api/health')
def api_health():
    """Simple health check."""
    return jsonify({
        'status': 'ok',
        'service': 'deadrop',
    })


@admin_bp.route('/api/purge', methods=['POST'])
def api_purge():
    """Force cleanup of expired drops."""
    count = cleanup_expired()
    return jsonify({
        'purged': count,
        'message': f'{count} expired drops removed',
    })
