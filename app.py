from flask import Flask, render_template, jsonify, request, send_from_directory, abort, redirect, url_for, session, flash
import json
from datetime import datetime
import os
import re

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Замените на свой секретный ключ
UPLOAD_FOLDER = 'static/avatars'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Настройки авторизации
USERNAME = "admin"
PASSWORD = "password123"  # Замените на свои логин и пароль

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def requires_auth(f):
    def decorated(*args, **kwargs):
        if "logged_in" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

def format_bytes(bytes):
    if bytes == 0:
        return "0 B"
    units = ["B", "KiB", "MiB", "GiB"]
    i = int(min(len(units) - 1, max(0, (bytes.bit_length() - 1) // 10)))
    return f"{bytes / (1024 ** i):.2f} {units[i]}"

def parse_wg_dump():
    try:
        with open("wg_dump.txt", "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return {}
    
    peers = {}
    for line in lines:
        parts = line.strip().split()
        if len(parts) < 9:
            continue
        try:
            pubkey = parts[1]
            endpoint = parts[3]
            allowed_ips = parts[4]
            latest_handshake = parts[5]
            transfer_rx = parts[6]
            transfer_tx = parts[7]
            
            peers[pubkey] = {
                "endpoint": endpoint,
                "allowed_ips": allowed_ips.split('/')[0],
                "latest_handshake": int(latest_handshake) if latest_handshake != "0" else 0,
                "transfer_rx": int(transfer_rx),
                "transfer_tx": int(transfer_tx)
            }
        except (IndexError, ValueError):
            pass
    return peers

def load_users():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f, indent=2)

def combine_data():
    wg_data = parse_wg_dump()
    users = load_users()
    combined = []
    
    for user in users:
        try:
            client_id = user["clientId"]
            user_data = user["userData"]
            wg_info = wg_data.get(client_id, {})
            
            safe_client_id = re.sub(r'[^a-zA-Z0-9_-]', '', client_id)
            
            combined.append({
                "clientId": client_id,
                "safeClientId": safe_client_id,
                "clientName": user_data.get("clientName", "Unknown"),
                "allowedIps": wg_info.get("allowed_ips", user_data.get("allowedIps", "N/A").split('/')[0]),
                "dataReceived": user_data.get("dataReceived", "0 B"),
                "dataSent": user_data.get("dataSent", "0 B"),
                "latestHandshakeTimestamp": wg_info.get("latest_handshake", 0),
                "transferRx": format_bytes(wg_info.get("transfer_rx", 0)),
                "transferTx": format_bytes(wg_info.get("transfer_tx", 0)),
                "endpoint": wg_info.get("endpoint", "N/A")
            })
        except KeyError:
            continue
    return combined

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == USERNAME and password == PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        else:
            flash("Неверный логин или пароль")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))

@app.route("/")
@requires_auth
def index():
    return render_template("index.html")

@app.route("/api/traffic")
@requires_auth
def traffic_data():
    try:
        data = combine_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/user/<client_name>")
@requires_auth
def user_page(client_name):
    data = combine_data()
    user = next((u for u in data if u["clientName"] == client_name), None)
    if not user:
        return "Пользователь не найден", 404
    return render_template("user.html", user=user)

@app.route("/upload_avatar/<client_name>", methods=["POST"])
@requires_auth
def upload_avatar(client_name):
    if "avatar" not in request.files:
        return jsonify({"error": "Файл не выбран"}), 400
    file = request.files["avatar"]
    if file.filename == "":
        return jsonify({"error": "Файл не выбран"}), 400
    if file:
        data = combine_data()
        user = next((u for u in data if u["clientName"] == client_name), None)
        if not user:
            return jsonify({"error": "Пользователь не найден"}), 404
        
        filename = f"{user['safeClientId']}.png"
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)
        return jsonify({"message": "Аватар успешно загружен"}), 200
    return jsonify({"error": "Ошибка загрузки"}), 500

@app.route("/update_client_name/<client_name>", methods=["POST"])
@requires_auth
def update_client_name(client_name):
    new_name = request.json.get("clientName")
    if not new_name:
        return jsonify({"error": "Новое имя не указано"}), 400
    
    users = load_users()
    for user in users:
        if user["userData"].get("clientName") == client_name:
            user["userData"]["clientName"] = new_name
            save_users(users)
            return jsonify({"message": "Имя успешно обновлено", "newName": new_name}), 200
    return jsonify({"error": "Пользователь не найден"}), 404

@app.route('/static/<path:path>')
def send_static(path):
    response = send_from_directory('static', path)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
