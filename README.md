<p align="center">
  <img src="docs/banner.png" alt="deadrop banner" width="800"/>
</p>

<h1 align="center">deadrop</h1>

<p align="center">
  <strong>Self-hosted encrypted file sharing. Upload. Download once. Gone.</strong><br/>
  <em>AES-256-GCM encryption, one-time download links, automatic expiry</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/backend-Flask-blue?style=flat-square" alt="Flask"/>
  <img src="https://img.shields.io/badge/encryption-AES--256--GCM-brightgreen?style=flat-square" alt="AES"/>
  <img src="https://img.shields.io/badge/storage-ephemeral-red?style=flat-square" alt="Ephemeral"/>
  <img src="https://img.shields.io/badge/deploy-Docker-2496ED?style=flat-square" alt="Docker"/>
</p>

---

## What is this?

Upload a file → get a one-time download link → recipient downloads → link is burned and the file is deleted from the server. No accounts, no tracking, no file lingering on someone's cloud forever.

The idea came from needing to send files to people without wanting them to live on Google Drive forever. There are services like Firefox Send (RIP) and Wormhole, but I wanted something I could self-host and understand completely.

## Quick Start

### Docker (recommended)
```bash
docker compose up --build
# → http://localhost:5000
```

### Without Docker
```bash
pip install -r requirements.txt
python run.py
```

---

## How It Works

```
You                          Server                        Recipient
 │                             │                              │
 │  ┌──────────┐               │                              │
 │  │ file.pdf │──── upload ──▶│                              │
 │  └──────────┘               │                              │
 │                             │  ┌─────────────────┐         │
 │                             │  │ AES-256-GCM     │         │
 │                             │  │ encrypt + store  │         │
 │                             │  └────────┬────────┘         │
 │                             │           │                  │
 │  ◀──── link: /d/a3f8b2c1 ──│           │                  │
 │                             │           │                  │
 │         share link ────────────────────────────────────▶   │
 │                             │           │                  │
 │                             │  ◀── GET /d/a3f8b2c1 ───────│
 │                             │           │                  │
 │                             │  ┌────────▼────────┐         │
 │                             │  │ decrypt + stream │         │
 │                             │  │ delete file      │         │
 │                             │  │ burn link        │──────▶  │ file.pdf
 │                             │  └─────────────────┘         │
```

1. **Upload**: File sent via XHR with drag-and-drop progress tracking
2. **Encrypt**: Server encrypts with **AES-256-GCM** (authenticated encryption) + unique 12-byte nonce
3. **Store**: Only ciphertext touches disk. Plaintext is never written
4. **Link**: Short random ID returned (e.g., `/d/a3f8b2c1`)
5. **Download**: Decrypt on-the-fly, stream to browser
6. **Burn**: Link invalidated, encrypted file deleted from disk

---

## Security Model

### What It Does

| Protection | How |
|-----------|-----|
| **Encryption at rest** | AES-256-GCM: plaintext never touches disk |
| **Authenticated encryption** | GCM tag detects any ciphertext tampering |
| **Unique nonces** | Each file gets a random 12-byte nonce, so identical files produce different ciphertexts |
| **One-time download** | Link burned after first download |
| **Auto-expiry** | Files deleted after configurable timer (default: 24h), even if never downloaded |
| **Rate limiting** | Per-IP upload throttling to prevent abuse |
| **Integrity verification** | SHA-256 checksum stored with each file, verified on download |

### What It Doesn't Do

> **⚠️ Threat model transparency**

- **Not E2E encrypted**: the server sees plaintext during upload/download (encryption protects against disk theft, not a compromised server)
- **No authentication**: anyone with the link can download
- **Server holds the key**: by design, for server-side encryption. For E2E, you'd need client-side encryption (like Firefox Send did)

---

## Admin Dashboard

```bash
# view server stats
curl http://localhost:5000/api/stats
{
  "active_drops": 12,
  "total_uploads": 847,
  "total_downloads": 623,
  "storage_used_mb": 156.3,
  "expired_cleaned": 234
}

# purge all expired
curl -X POST http://localhost:5000/api/admin/purge
```

### Background Cleanup

The scheduler automatically runs every hour to purge expired files:
- Files past their expiry timer → deleted
- Files that exceeded max downloads → deleted
- Orphaned ciphertext (no database record) → deleted

---

## Configuration

All configurable via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | random | Flask session key |
| `UPLOAD_DIR` | `/tmp/deadrop_uploads` | Encrypted file storage |
| `DB_PATH` | `deadrop.db` | SQLite database path |
| `MAX_FILE_SIZE` | `52428800` | Max upload (50MB) |
| `DEFAULT_EXPIRY` | `24` | Expiry in hours |
| `MAX_DOWNLOADS` | `1` | Downloads per link |
| `ENCRYPTION_KEY` | auto-generated | Passphrase for key derivation |

---

## API

```bash
# upload a file
curl -X POST -F "file=@secret.pdf" -F "expiry=6" http://localhost:5000/upload
# → {"id": "a3f8b2c1", "url": "http://localhost:5000/d/a3f8b2c1", "expires_at": "..."}

# download (one-time)
curl -O -J http://localhost:5000/d/a3f8b2c1/file
# → file downloaded, link burned

# try again
curl http://localhost:5000/d/a3f8b2c1/file
# → 410 Gone

# health check
curl http://localhost:5000/api/health
# → {"status": "ok", "uptime": 3600}
```

---

## Architecture

```
app/
├── __init__.py    App factory, Flask setup
├── config.py      Environment-based configuration
├── crypto.py      AES-256-GCM encrypt/decrypt, key derivation
├── models.py      SQLite: file metadata, expiry tracking
├── routes.py      Flask routes: upload, download, health
├── ratelimit.py   Per-IP upload throttling
├── integrity.py   SHA-256 checksum verification
├── admin.py       Stats endpoint, purge API
└── scheduler.py   Background cleanup (expired file removal)

templates/
├── index.html     Upload page (drag-and-drop, progress bar)
└── download.html  Download page (with expiry countdown)

static/
├── style.css      Dark monospace theme
└── app.js         Drag-drop handler, XHR upload, clipboard copy
```

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask + SQLite + `cryptography` (Python) |
| Frontend | Vanilla JS + CSS (no frameworks) |
| Encryption | AES-256-GCM via `cryptography.fernet` |
| Database | SQLite (metadata, expiry tracking) |
| Deployment | Docker + gunicorn |

---

<p align="center">
  <sub>Your files are not my business. Upload, download, gone.</sub>
</p>
