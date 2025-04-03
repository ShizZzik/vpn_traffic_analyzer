from flask import Flask, render_template, jsonify
import json
from datetime import datetime

app = Flask(__name__)

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
        parts = line.strip().split()  # Разделяем по пробелам, как в твоём примере
        if len(parts) < 9:  # Минимум 9 полей в твоём формате
            print(f"Пропущена строка с недостаточным количеством полей: {line}")
            continue
        try:
            pubkey = parts[1]  # Публичный ключ клиента
            endpoint = parts[3]  # Эндпоинт
            allowed_ips = parts[4]  # Разрешённые IP
            latest_handshake = parts[5]  # Время последнего handshake
            transfer_rx = parts[6]  # Принятые данные
            transfer_tx = parts[7]  # Отправленные данные
            
            peers[pubkey] = {
                "endpoint": endpoint,
                "allowed_ips": allowed_ips,
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
                "clientName": user_data.get("clientName", "Unknown"),
                "allowedIps": user_data.get("allowedIps", ""),
                "dataReceived": user_data.get("dataReceived", "0 B"),
                "dataSent": user_data.get("dataSent", "0 B"),
                "latestHandshake": handshake_str,
                "transferRx": wg_info.get("transfer_rx", 0),
                "transferTx": wg_info.get("transfer_tx", 0),
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

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
