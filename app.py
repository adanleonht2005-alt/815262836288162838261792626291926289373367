from flask import Flask, request, jsonify
from flask_cors import CORS
import time

app = Flask(__name__)
CORS(app)

latest = {"id": 0, "code": ""}
inject_state = {"pending": False, "connected": False, "last_ping": 0}

@app.route('/upload', methods=['POST'])
def upload():
    data = request.get_json()
    if data.get('token') != "Larp67":
        return jsonify({"error": "bad token"}), 403
    latest["id"] = int(time.time() * 1000)
    latest["code"] = data.get('script', '')
    return jsonify({"status": "ok", "id": latest["id"]})

@app.route('/latest', methods=['GET'])
def get_latest():
    return jsonify(latest)

@app.route('/inject', methods=['POST'])
def inject():
    data = request.get_json()
    if data.get('token') != "Larp67":
        return jsonify({"error": "bad token"}), 403
    inject_state["pending"] = True
    inject_state["connected"] = False
    return jsonify({"status": "ok"})

@app.route('/inject-check', methods=['GET'])
def inject_check():
    # Delta llama aquí. Si hay un ping pendiente, lo confirma y lo marca conectado.
    if inject_state["pending"]:
        inject_state["pending"] = False
        inject_state["connected"] = True
        inject_state["last_ping"] = time.time()
        return jsonify({"pending": True})
    return jsonify({"pending": False})

@app.route('/inject-status', methods=['GET'])
def inject_status():
    # La web llama aquí para saber si Delta ya confirmó
    # Considera "conectado" si el último ping fue hace menos de 10s
    if inject_state["connected"] and (time.time() - inject_state["last_ping"]) < 10:
        return jsonify({"connected": True})
    return jsonify({"connected": False})

@app.route('/')
def home():
    return "ExSer relay activo"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
