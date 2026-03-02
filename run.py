"""
run.py - Entry point for the deadrop application

Usage:
    python run.py                      # development mode
    gunicorn --bind 0.0.0.0:5000 run:app  # production
"""

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
