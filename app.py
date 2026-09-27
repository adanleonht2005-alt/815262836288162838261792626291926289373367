import time
import secrets
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("exser")

# ============================================
# CONFIG
# ============================================
KEY = "Larp67"
SESSION_TTL = 1800
RATE_LIMIT = 10
RATE_WINDOW = 60

ALLOWED_ORIGINS = [
    "https://ex-ser-larped.vercel.app",
    "https://adanleonht2005-alt.github.io",
    "http://localhost:3000",
    "http://localhost:5000"
]

# ============================================
# STATE
# ============================================
latest = {"id": 0, "code": ""}
inject_state = {"pending": False, "connected": False, "last_ping": 0}
sessions = {}
rate_log = {}
blocked = {}

# ============================================
# HELPERS
# ============================================
def get_cid(): return request.headers.get("X-Client-ID", "")
def get_tok(): return request.headers.get("X-Session", "")

def is_rate_limited(cid):
    now = time.time()
    if cid in blocked and now < blocked[cid]:
        return True
    h = rate_log.get(cid, [])
    h = [t for t in h if now - t < RATE_WINDOW]
    rate_log[cid] = h
    if len(h) >= RATE_LIMIT:
        blocked[cid] = now + 300
        log.warning(f"BLOCKED: {cid}")
        return True
    rate_log[cid].append(now)
    return False

def validate_session():
    cid = get_cid()
    tok = get_tok()
    if not cid or not tok:
        return None
    s = sessions.get(tok)
    if not s or s["client_id"] != cid:
        return None
    if time.time() - s["created"] > SESSION_TTL:
        del sessions[tok]
        return None
    s["last_seen"] = time.time()
    return s

def clean_old():
    now = time.time()
    for tok in list(sessions.keys()):
        if now - sessions[tok]["created"] > SESSION_TTL:
            del sessions[tok]
    for cid in list(blocked.keys()):
        if now > blocked[cid]:
            del blocked[cid]

# ============================================
# MIDDLEWARE
# ============================================
@app.before_request
def check_origin():
    exempt_paths = [
        '/api/v2/latest',
        '/api/v2/ping-check'
    ]
    if request.path in exempt_paths:
        return None
    if request.method == "POST":
        origin = request.headers.get("Origin", "")
        if origin and origin not in ALLOWED_ORIGINS:
            log.warning(f"Blocked origin: {origin}")
            return jsonify({"error": "forbidden origin"}), 403

# ============================================
# ROUTES
# ============================================
@app.route('/')
def home():
    return "ok"

@app.route('/api/v2/session', methods=['POST'])
def create_session():
    clean_old()
    cid = get_cid()
    if not cid:
        return jsonify({"error": "no client"}), 400
    if is_rate_limited(cid):
        return jsonify({"error": "rate limited"}), 429

    data = request.get_json() or {}
    if data.get("t") != KEY:
        log.warning(f"Failed login: {cid}")
        return jsonify({"error": "bad key"}), 403

    token = secrets.token_urlsafe(32)
    sessions[token] = {
        "client_id": cid,
        "created": time.time(),
        "last_seen": time.time()
    }
    log.info(f"LOGIN OK: {cid} -> {token[:8]}...")
    return jsonify({"status": "ok", "token": token})

@app.route('/api/v2/x', methods=['POST'])
def upload():
    s = validate_session()
    if not s:
        return jsonify({"error": "unauthorized"}), 401
    cid = s["client_id"]
    if is_rate_limited(cid):
        return jsonify({"error": "rate limited"}), 429

    data = request.get_json() or {}
    code = data.get("s", "")
    if not code:
        return jsonify({"error": "empty"}), 400

    latest["id"] = int(time.time() * 1000)
    latest["code"] = code
    log.info(f"UPLOAD: {cid} ({len(code)} bytes)")
    return jsonify({"status": "ok", "id": latest["id"]})

@app.route('/api/v2/y', methods=['POST'])
def inject():
    s = validate_session()
    if not s:
        return jsonify({"error": "unauthorized"}), 401
    cid = s["client_id"]
    if is_rate_limited(cid):
        return jsonify({"error": "rate limited"}), 429

    inject_state["pending"] = True
    inject_state["connected"] = False
    log.info(f"INJECT: {cid}")
    return jsonify({"status": "ok"})

@app.route('/api/v2/z', methods=['GET'])
def state():
    s = validate_session()
    if not s:
        return jsonify({"error": "unauthorized"}), 401

    if inject_state["connected"] and (time.time() - inject_state["last_ping"]) < 60:
        return jsonify({"connected": True})
    return jsonify({"connected": False})

@app.route('/api/v2/latest', methods=['GET'])
def get_latest():
    return jsonify(latest)

@app.route('/api/v2/ping-check', methods=['GET'])
def ping_check():
    if inject_state["pending"]:
        inject_state["pending"] = False
        inject_state["connected"] = True
        inject_state["last_ping"] = time.time()
        return jsonify({"pending": True})
    return jsonify({"pending": False})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
