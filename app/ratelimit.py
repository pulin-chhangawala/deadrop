"""
ratelimit.py - Token bucket rate limiter

Limits upload frequency per IP address to prevent abuse.
Uses a simple in-memory token bucket, no Redis needed.

Each IP gets a bucket that fills at a constant rate and
drains with each request. When the bucket is empty, requests
are rejected with 429 Too Many Requests.
"""

import time
import threading
from functools import wraps
from flask import request, jsonify


class TokenBucket:
    """Thread-safe token bucket rate limiter."""

    def __init__(self, rate=10, capacity=20):
        """
        Args:
            rate: Tokens added per second
            capacity: Maximum tokens in bucket
        """
        self.rate = rate
        self.capacity = capacity
        self.buckets = {}   # ip -> (tokens, last_time)
        self.lock = threading.Lock()

    def _get_tokens(self, ip):
        """Get current token count for an IP, refilling as needed."""
        now = time.time()

        with self.lock:
            if ip not in self.buckets:
                self.buckets[ip] = (self.capacity, now)
                return self.capacity

            tokens, last_time = self.buckets[ip]
            elapsed = now - last_time

            # refill tokens based on elapsed time
            tokens = min(self.capacity, tokens + elapsed * self.rate)
            self.buckets[ip] = (tokens, now)
            return tokens

    def consume(self, ip, cost=1):
        """
        Try to consume tokens. Returns True if allowed, False if rate limited.
        """
        now = time.time()

        with self.lock:
            if ip not in self.buckets:
                self.buckets[ip] = (self.capacity - cost, now)
                return True

            tokens, last_time = self.buckets[ip]
            elapsed = now - last_time
            tokens = min(self.capacity, tokens + elapsed * self.rate)

            if tokens >= cost:
                self.buckets[ip] = (tokens - cost, now)
                return True
            else:
                self.buckets[ip] = (tokens, now)
                return False

    def cleanup(self, max_age=3600):
        """Remove stale entries (call periodically)."""
        now = time.time()
        with self.lock:
            stale = [ip for ip, (_, t) in self.buckets.items()
                     if now - t > max_age]
            for ip in stale:
                del self.buckets[ip]


# global rate limiter instance
upload_limiter = TokenBucket(rate=0.5, capacity=5)   # 1 upload per 2 seconds, burst of 5
download_limiter = TokenBucket(rate=2, capacity=10)   # 2 downloads per second, burst of 10


def rate_limit(limiter, cost=1):
    """Flask decorator to apply rate limiting."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            ip = request.remote_addr or '127.0.0.1'
            if not limiter.consume(ip, cost):
                return jsonify({
                    'error': 'Rate limit exceeded. Please wait.',
                    'retry_after': int(cost / limiter.rate) + 1
                }), 429
            return f(*args, **kwargs)
        return wrapped
    return decorator
