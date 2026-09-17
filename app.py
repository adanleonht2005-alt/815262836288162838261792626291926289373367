from flask import Flask, request, jsonify
from flask_cors import CORS
import time

app = Flask(__name__)
CORS(app)

latest = {"id": 0, "code": ""}

@app.route('/upload', methods=['POST'])
def upload():
    data = request.get_json()
    if data.get('token') != "Rc7 is back":
        return jsonify({"error": "bad token"}), 403
    
    latest["id"] = int(time.time() * 1000)
    latest["code"] = data.get('script', '')
    return jsonify({"status": "ok", "id": latest["id"]})

@app.route('/latest', methods=['GET'])
def get_latest():
    return jsonify(latest)

@app.route('/')
def home():
    return "RC7 relay activo"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
