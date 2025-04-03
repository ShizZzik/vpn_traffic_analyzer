from flask import Flask, render_template, jsonify, request
import json
from datetime import datetime
import os
import re  # Для очистки clientId

app = Flask(__name__)
UPLOAD_FOLDER = 'static/avatars'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def format_bytes(bytes):
    if bytes == 0:
        return "0 B"
    units = ["B", "KiB", "MiB", "GiB"]
    i = int(min(len(units) - 1, max(0, (bytes.bit_length() - 1) // 10)))
    return f"{bytes / (1024 ** i):.2f} {units[i]}"

def parse_wg_dump():
    print("Чтение wg_dump.txt")
    try:
        with open("wg_dump.txt", "r") as f:
            lines = f.readlines()
        print(f"Получено строк из wg_dump.txt: {len(lines)}")
    except FileNotFoundError:
        print("Файл wg_dump.txt не найден")
        return {}
    except Exception as e:
        print(f"Ошибка при чтении wg_dump.txt: {e}")
        return {}
    
    peers = {}
    for line in lines:
        parts = line.strip().split()
        if len(parts) < 9:
            print(f"Пропущена строка с недостаточным количеством полей: {line}")
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
        except (IndexError, ValueError) as e:
            print(f"Ошибка парсинга строки '{line}': {e}")
    print(f"Распарсено пиров: {len(peers)}")
    return peers

def load_users():
    print("Загрузка users.json")
    try:
        with open("users.json", "r") as f:
            users = json.load(f)
        print(f"Загружено пользователей из JSON: {len(users)}")
        return users
    except FileNotFoundError:
        print("Файл users.json не найден")
        return []
    except json.JSONDecodeError as e:
        print(f"Ошибка декодирования JSON: {e}")
        return []
    except Exception as e:
        print(f"Неизвестная ошибка при загрузке users.json: {e}")
        return []

def combine_data():
    print("Сопоставление данных")
    wg_data = parse_wg_dump()
    users = load_users()
    combined = []
    
    if not users:
        print("Список пользователей пуст")
        return combined
    
    for user in users:
        try:
            client_id = user["clientId"]
            user_data = user["userData"]
        except KeyError as e:
            print(f"Ошибка в структуре пользователя: {e}")
            continue
        
        wg_info = wg_data.get(client_id, {})
        
        if client_id in wg_data:
            print(f"Найден пир для {user_data.get('clientName', 'Unknown')}")
        else:
            print(f"Пир не найден для {user_data.get('clientName', 'Unknown')} (clientId: {client_id})")
        
        try:
            if wg_info.get("latest_handshake", 0) > 0:
                delta = datetime.now().timestamp() - wg_info["latest_handshake"]
                hours = int(delta // 3600)
                minutes = int((delta % 3600) // 60)
                seconds = int(delta % 60)
                handshake_str = f"{hours}h, {minutes}m, {seconds}s ago"
            else:
                handshake_str = "Нет активности"
            
            combined.append({
                "clientId": client_id,
                "clientName": user_data.get("clientName", "Unknown"),
                "allowedIps": wg_info.get("allowed_ips", user_data.get("allowedIps", "N/A").split('/')[0]),
                "dataReceived": user_data.get("dataReceived", "0 B"),
                "dataSent": user_data.get("dataSent", "0 B"),
                "latestHandshake": handshake_str,
                "transferRx": format_bytes(wg_info.get("transfer_rx", 0)),
                "transferTx": format_bytes(wg_info.get("transfer_tx", 0)),
                "endpoint": wg_info.get("endpoint", "N/A")
            })
        except Exception as e:
            print(f"Ошибка при обработке пользователя {user_data.get('clientName', 'Unknown')}: {e}")
    print(f"Сформировано записей: {len(combined)}")
    return combined

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/traffic")
def traffic_data():
    try:
        data = combine_data()
        return jsonify(data)
    except Exception as e:
        print(f"Ошибка в traffic_data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/user/<client_name>")
def user_page(client_name):
    data = combine_data()
    user = next((u for u in data if u["clientName"] == client_name), None)
    if not user:
        return "Пользователь не найден", 404
    return render_template("user.html", user=user)

@app.route("/upload_avatar/<client_name>", methods=["POST"])
def upload_avatar(client_name):
    if "avatar" not in request.files:
        print(f"Ошибка: файл не выбран для {client_name}")
        return jsonify({"error": "Файл не выбран"}), 400
    file = request.files["avatar"]
    if file.filename == "":
        print(f"Ошибка: пустое имя файла для {client_name}")
        return jsonify({"error": "Файл не выбран"}), 400
    if file:
        data = combine_data()
        user = next((u for u in data if u["clientName"] == client_name), None)
        if not user:
            print(f"Ошибка: пользователь {client_name} не найден")
            return jsonify({"error": "Пользователь не найден"}), 404
        
        # Очищаем clientId от недопустимых символов
        safe_client_id = re.sub(r'[^a-zA-Z0-9_-]', '', user['clientId'])
        filename = f"{safe_client_id}.png"
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        
        print(f"Попытка сохранить аватар для {client_name} как {file_path}")
        try:
            file.save(file_path)
            print(f"Аватар успешно сохранён: {file_path}")
            return jsonify({"message": "Аватар успешно загружен"}), 200
        except Exception as e:
            print(f"Ошибка сохранения файла {file_path}: {e}")
            return jsonify({"error": f"Ошибка сохранения файла: {str(e)}"}), 500
    print(f"Неизвестная ошибка загрузки для {client_name}")
    return jsonify({"error": "Ошибка загрузки"}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
