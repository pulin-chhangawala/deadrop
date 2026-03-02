"""
routes.py - Flask routes for upload and download

Two main endpoints:
  POST /upload  - upload a file, get back a download link
  GET  /d/<id>  - download a file (one-time, then it's deleted)
"""

import os
import uuid
import hashlib
from flask import (Flask, request, jsonify, send_file, render_template,
                   redirect, url_for, flash)
from werkzeug.utils import secure_filename
from io import BytesIO

from .config import Config
from .crypto import encrypt_file, decrypt_file, generate_key
from .models import init_db, create_drop, get_drop, increment_downloads


def create_app():
    app = Flask(__name__,
                template_folder='../templates',
                static_folder='../static')
    app.config.from_object(Config)
    
    # ensure upload directory exists
    os.makedirs(app.config['UPLOAD_DIR'], exist_ok=True)
    
    # init database
    init_db(app.config['DB_PATH'])
    
    # generate or load encryption key
    if app.config['ENCRYPTION_KEY']:
        from .crypto import derive_key
        app.encryption_key = derive_key(app.config['ENCRYPTION_KEY'])
    else:
        # store key in a file so it persists across restarts
        key_path = os.path.join(app.config['UPLOAD_DIR'], '.key')
        if os.path.exists(key_path):
            with open(key_path, 'rb') as f:
                app.encryption_key = f.read()
        else:
            app.encryption_key = generate_key()
            with open(key_path, 'wb') as f:
                f.write(app.encryption_key)
    
    @app.route('/')
    def index():
        return render_template('index.html',
                               max_size_mb=app.config['MAX_FILE_SIZE'] // (1024*1024))
    
    @app.route('/upload', methods=['POST'])
    def upload():
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # read file data
        data = file.read()
        if len(data) > app.config['MAX_FILE_SIZE']:
            return jsonify({'error': f'File too large (max {app.config["MAX_FILE_SIZE"] // (1024*1024)}MB)'}), 413
        
        if len(data) == 0:
            return jsonify({'error': 'Empty file'}), 400
        
        # parse options
        expiry_hours = int(request.form.get('expiry', app.config['DEFAULT_EXPIRY_HOURS']))
        max_downloads = int(request.form.get('max_downloads', app.config['MAX_DOWNLOADS']))
        
        # encrypt
        encrypted = encrypt_file(data, app.encryption_key)
        
        # save encrypted file
        stored_name = f"{uuid.uuid4().hex}.enc"
        filepath = os.path.join(app.config['UPLOAD_DIR'], stored_name)
        with open(filepath, 'wb') as f:
            f.write(encrypted)
        
        # register in database
        key_hash = hashlib.sha256(app.encryption_key).hexdigest()[:16]
        original_name = secure_filename(file.filename)
        
        drop_id = create_drop(
            app.config['DB_PATH'],
            original_name, stored_name, len(data),
            key_hash, expiry_hours, max_downloads
        )
        
        download_url = url_for('download_page', drop_id=drop_id, _external=True)
        
        return jsonify({
            'id': drop_id,
            'url': download_url,
            'expires_in': f'{expiry_hours}h',
            'max_downloads': max_downloads,
            'size': len(data),
        })
    
    @app.route('/d/<drop_id>')
    def download_page(drop_id):
        drop = get_drop(app.config['DB_PATH'], drop_id)
        if not drop:
            return render_template('download.html', error=True, drop_id=drop_id)
        return render_template('download.html', error=False, drop=drop, drop_id=drop_id)
    
    @app.route('/d/<drop_id>/file')
    def download_file(drop_id):
        drop = get_drop(app.config['DB_PATH'], drop_id)
        if not drop:
            return jsonify({'error': 'Drop not found, expired, or already downloaded'}), 404
        
        # read and decrypt
        filepath = os.path.join(app.config['UPLOAD_DIR'], drop['stored_filename'])
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found on disk'}), 404
        
        with open(filepath, 'rb') as f:
            encrypted = f.read()
        
        try:
            decrypted = decrypt_file(encrypted, app.encryption_key)
        except Exception:
            return jsonify({'error': 'Decryption failed'}), 500
        
        # increment download count (may trigger expiry)
        increment_downloads(app.config['DB_PATH'], drop_id)
        
        return send_file(
            BytesIO(decrypted),
            as_attachment=True,
            download_name=drop['original_filename'],
            mimetype='application/octet-stream'
        )
    
    @app.route('/api/health')
    def health():
        return jsonify({'status': 'ok'})
    
    return app
