import os
import sys
import time
import json
import uuid
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Master Security Configuration
ADMIN_KEY = os.environ.get("ADMIN_KEY", "Linux X Mrx")
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "Linux X Mrx")
BOT_SECRET = os.environ.get("BOT_SECRET", "mrx_secure_bridge_2026")
BOT_NODE_URL = os.environ.get("BOT_NODE_URL", "").rstrip("/")

DATABASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.json")

AUTH_CONFIG = {
    "ENDPOINT": "https://my-auth-kohl.vercel.app/api/v1/validate-license?allow_plaintext=1",
    "APP_ID": "b8bb56a4-4390-424c-81df-0c4d0760c673",
    "API_SECRET": "19c9925f9ed98553424182d6206e1ac27ae69042a5a409ea66bd3663262c8221"
}

# In-memory runtime state (synced with Bot Node on your PC)
STATE = {
    "ids": [],
    "pending_commands": [],
    "last_heartbeat": 0,
    "bot_status": {
        "online": False,
        "active_bots": {"spam": False, "m9": False, "rom": False},
        "accounts_count": 122,
        "cpu_usage": 0,
        "ram_usage": 0,
        "logs": []
    }
}


# -------------------------------------------------------------------------
# DATABASE PERSISTENCE HELPERS
# -------------------------------------------------------------------------
def load_db():
    if not os.path.exists(DATABASE_FILE):
        return []
    try:
        with open(DATABASE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_db(data):
    try:
        temp = DATABASE_FILE + ".tmp"
        with open(temp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        os.replace(temp, DATABASE_FILE)
    except Exception as e:
        print(f"[DB SAVE ERROR] {e}")


def check_external_auth(key, hwid=""):
    try:
        resp = requests.post(
            AUTH_CONFIG["ENDPOINT"],
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-App-Secret": AUTH_CONFIG["API_SECRET"]
            },
            json={
                "license_key": key,
                "hwid": hwid or "WEB_HWID",
                "app_id": AUTH_CONFIG["APP_ID"],
                "api_secret": AUTH_CONFIG["API_SECRET"]
            },
            timeout=5
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"[AUTH ERROR] {e}")
    return {"valid": False}


def sync_db_to_queue():
    clients = load_db()
    now = time.time()
    queue = []
    seen = set()

    for c in clients:
        if c.get("status") != "active":
            continue
        exp = c.get("exp_timestamp", 0)
        if exp and exp > 0 and now > exp:
            continue
        for t in c.get("targets", []):
            if t.get("status") == "stopped" or t.get("active") is False:
                continue
            uid = str(t.get("uid", "")).strip()
            if uid.isdigit() and uid not in seen:
                seen.add(uid)
                queue.append(t)

    STATE["ids"] = queue


# -------------------------------------------------------------------------
# DASHBOARD UI (Frontend)
# -------------------------------------------------------------------------
@app.route("/", methods=["GET"])
@app.route("/index.html", methods=["GET"])
def serve_index():
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html"),
        os.path.join(os.getcwd(), "index.html"),
        os.path.join(os.getcwd(), "public", "index.html")
    ]
    for p in candidates:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}
    return "<h1>SpammerX Dashboard</h1><p>index.html not found. Place index.html in the same directory.</p>", 404


# -------------------------------------------------------------------------
# BOT NODE SYNC ENDPOINTS
# -------------------------------------------------------------------------
@app.route("/api/bot/sync", methods=["GET"])
def api_bot_sync():
    secret = request.headers.get("X-Bot-Secret") or request.args.get("secret")
    if secret != BOT_SECRET:
        return jsonify({"error": "unauthorized bot node"}), 401

    sync_db_to_queue()
    commands = list(STATE["pending_commands"])
    STATE["pending_commands"].clear()

    return jsonify({
        "status": "ok",
        "targets": STATE["ids"],
        "commands": commands
    })


@app.route("/api/bot/heartbeat", methods=["POST"])
def api_bot_heartbeat():
    secret = request.headers.get("X-Bot-Secret") or request.args.get("secret")
    if secret != BOT_SECRET:
        return jsonify({"error": "unauthorized bot node"}), 401

    data = request.get_json(silent=True) or {}
    STATE["last_heartbeat"] = time.time()
    STATE["bot_status"]["online"] = True
    STATE["bot_status"]["active_bots"] = data.get("active_bots", {"spam": False, "m9": False, "rom": False})
    STATE["bot_status"]["accounts_count"] = data.get("accounts_count", 122)
    STATE["bot_status"]["cpu_usage"] = data.get("cpu_usage", 0)
    STATE["bot_status"]["ram_usage"] = data.get("ram_usage", 0)
    if "logs" in data:
        STATE["bot_status"]["logs"] = data.get("logs")[-30:]

    return jsonify({"status": "heartbeat_acknowledged", "timestamp": time.time()})


# -------------------------------------------------------------------------
# DASHBOARD API: SYSTEM STATUS
# -------------------------------------------------------------------------
@app.route("/api/status", methods=["GET"])
def api_status():
    now = time.time()
    is_live = (now - STATE["last_heartbeat"]) < 8

    active = STATE["bot_status"]["active_bots"] if is_live else {}
    processes = {
        "spam": {"script": "xSpam.py", "running": bool(active.get("spam")), "pid": "LOCAL" if active.get("spam") else None},
        "m9": {"script": "xM9.py", "running": bool(active.get("m9")), "pid": "LOCAL" if active.get("m9") else None},
        "rom": {"script": "xRom.py", "running": bool(active.get("rom")), "pid": "LOCAL" if active.get("rom") else None},
    }

    sync_db_to_queue()

    return jsonify({
        "node_online": is_live,
        "node_status": "ONLINE" if is_live else "OFFLINE",
        "processes": processes,
        "counts": {
            "spam": STATE["bot_status"]["accounts_count"],
            "m9": 25,
            "rom": STATE["bot_status"]["accounts_count"]
        },
        "ids": len(STATE["ids"]),
        "accont_entries": STATE["bot_status"]["accounts_count"]
    })


@app.route("/api/process/<name>/<action>", methods=["POST"])
def api_process_control(name, action):
    if name not in ["spam", "m9", "rom"] or action not in ["start", "stop", "restart"]:
        return jsonify({"error": "invalid process or action"}), 400

    actual_action = "start" if action in ["start", "restart"] else "stop"
    STATE["pending_commands"].append({"bot": name, "action": actual_action, "timestamp": time.time()})
    STATE["bot_status"]["active_bots"][name] = (actual_action == "start")

    return jsonify({
        "status": action,
        "process": name,
        "script": f"x{name.capitalize()}.py",
        "running": actual_action == "start",
        "pid": "QUEUED"
    })


# -------------------------------------------------------------------------
# CLIENT TARGETS MANAGEMENT (ISOLATED PER ACCOUNT)
# -------------------------------------------------------------------------
@app.route("/api/client/targets", methods=["GET"])
def api_client_targets():
    key = str(request.args.get("key", "")).strip()
    if not key:
        return jsonify({"targets": []})

    if key in ["LINUX-MRX-LIFETIME", "ADMIN-LIFETIME", ADMIN_KEY]:
        sync_db_to_queue()
        return jsonify({"targets": STATE["ids"]})

    clients = load_db()
    for c in clients:
        if c.get("key") == key:
            return jsonify({
                "username": c.get("username", c.get("name", "Client")),
                "targets": c.get("targets", []),
                "expires_at": c.get("expires_at"),
                "status": c.get("status", "active")
            })

    return jsonify({"error": "client not found"}), 404


@app.route("/api/client/targets/add", methods=["POST"])
def api_client_target_add():
    data = request.get_json(silent=True) or {}
    key = str(data.get("key", "")).strip()
    uid = str(data.get("uid", "")).strip()
    mode = str(data.get("mode", "SpmRoom")).strip()
    try:
        loop_minutes = float(data.get("loop", 0) or 0)
    except (TypeError, ValueError):
        loop_minutes = 0.0

    if not uid or not uid.isdigit():
        return jsonify({"error": "UID deve contenere solo numeri"}), 400

    new_target = {
        "uid": uid,
        "mode": mode,
        "loop_minutes": loop_minutes,
        "time": time.time(),
        "status": "active",
        "active": True
    }

    # Master Admin Key
    if key in ["LINUX-MRX-LIFETIME", "ADMIN-LIFETIME", ADMIN_KEY]:
        new_target["created_by"] = "admin"
        STATE["ids"] = [i for i in STATE["ids"] if str(i.get("uid")) != uid]
        STATE["ids"].append(new_target)
        target_bot = "rom" if mode in ["SpmRoom", "Rom", "InvRoom", "JoinRoom"] else "spam"
        STATE["pending_commands"].append({"bot": target_bot, "action": "start", "timestamp": time.time()})
        return jsonify({"status": "added", "target": new_target})

    clients = load_db()
    client = None
    for c in clients:
        if c.get("key") == key:
            client = c
            break

    if not client:
        return jsonify({"error": "Chiave licenza non trovata"}), 404
    if client.get("status") != "active":
        return jsonify({"error": "Licenza sospesa o bloccata"}), 403

    if "targets" not in client or not isinstance(client["targets"], list):
        client["targets"] = []

    client["targets"] = [t for t in client["targets"] if str(t.get("uid")) != uid]
    client["targets"].append(new_target)
    save_db(clients)

    sync_db_to_queue()

    target_bot = "rom" if mode in ["SpmRoom", "Rom", "InvRoom", "JoinRoom"] else "spam"
    STATE["pending_commands"].append({"bot": target_bot, "action": "start", "timestamp": time.time()})

    return jsonify({"status": "added", "target": new_target, "targets_count": len(client["targets"])})


@app.route("/api/client/targets/delete", methods=["POST"])
def api_client_target_delete():
    data = request.get_json(silent=True) or {}
    key = str(data.get("key", "")).strip()
    uid = str(data.get("uid", "")).strip()

    if key in ["LINUX-MRX-LIFETIME", "ADMIN-LIFETIME", ADMIN_KEY]:
        STATE["ids"] = [i for i in STATE["ids"] if str(i.get("uid")) != uid]
        return jsonify({"status": "deleted", "uid": uid})

    clients = load_db()
    for c in clients:
        if c.get("key") == key:
            c["targets"] = [t for t in c.get("targets", []) if str(t.get("uid")) != uid]
            save_db(clients)
            break

    sync_db_to_queue()
    return jsonify({"status": "deleted", "uid": uid})


@app.route("/api/client/targets/toggle", methods=["POST"])
def api_client_target_toggle():
    data = request.get_json(silent=True) or {}
    key = str(data.get("key", "")).strip()
    uid = str(data.get("uid", "")).strip()
    action = str(data.get("action", "")).strip().lower()

    new_status = "stopped" if action == "stop" else "active"

    if key in ["LINUX-MRX-LIFETIME", "ADMIN-LIFETIME", ADMIN_KEY]:
        for i in STATE["ids"]:
            if str(i.get("uid")) == uid:
                if not action:
                    new_status = "active" if i.get("status") == "stopped" else "stopped"
                i["status"] = new_status
                i["active"] = (new_status == "active")
                break
        return jsonify({"status": "updated", "target_status": new_status, "uid": uid})

    clients = load_db()
    for c in clients:
        if c.get("key") == key:
            for t in c.get("targets", []):
                if str(t.get("uid")) == uid:
                    if not action:
                        new_status = "active" if t.get("status") == "stopped" else "stopped"
                    t["status"] = new_status
                    t["active"] = (new_status == "active")
                    break
            save_db(clients)
            break

    sync_db_to_queue()
    return jsonify({"status": "updated", "target_status": new_status, "uid": uid})


# -------------------------------------------------------------------------
# AUTH & LICENSE VERIFICATION (3-FACTOR + EXTERNAL AUTH AUTO-REGISTRATION)
# -------------------------------------------------------------------------
@app.route("/api/verify-client", methods=["POST"])
def api_verify_client():
    data = request.get_json(silent=True) or {}
    key = str(data.get("key", "")).strip()
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()
    hwid = str(data.get("hwid", "")).strip()

    # 1. Master Admin Login
    if key in ["LINUX-MRX-LIFETIME", "ADMIN-LIFETIME", ADMIN_KEY] or (username.lower() == "linux x mrx" and password == "Linux X Mrx"):
        return jsonify({
            "valid": True,
            "status": "valid",
            "role": "admin",
            "username": "Linux X Mrx (Admin)",
            "key": key or ADMIN_KEY,
            "license_type": "Lifetime",
            "expires_at": "Lifetime",
            "bot_developer": "Linux X Mrx"
        })

    # 2. Local Database Verification
    clients = load_db()
    now = time.time()
    for c in clients:
        key_matches = bool(key and c.get("key") == key)
        user_matches = bool(username and (c.get("username", "").lower() == username.lower() or c.get("name", "").lower() == username.lower()))

        if key_matches or user_matches:
            if c.get("password") and password and c.get("password") != password:
                return jsonify({"valid": False, "status": "invalid", "message": "Password errata per questo account."}), 401

            if c.get("status") == "banned" or c.get("active") is False:
                return jsonify({"valid": False, "status": "banned", "message": "Licenza sospesa dall'amministratore."}), 403

            exp = c.get("exp_timestamp", 0)
            if c.get("type") != "lifetime" and exp and now > exp:
                return jsonify({"valid": False, "status": "expired", "message": "Licenza scaduta."}), 403

            return jsonify({
                "valid": True,
                "status": "valid",
                "role": "client",
                "key": c.get("key"),
                "license_type": str(c.get("type", "monthly")).capitalize(),
                "expires_at": c.get("expires_at", "30 Giorni"),
                "username": c.get("username", c.get("name", "Client"))
            })

    # 3. External Auth Fallback & Auto-Registration
    if key:
        auth_data = check_external_auth(key, hwid)
        if auth_data.get("valid"):
            exp_days = 30
            exp_timestamp = now + (exp_days * 86400)
            new_client = {
                "id": f"cli_{int(now)}_{len(clients)+1}",
                "key": key,
                "username": username or "Client",
                "name": username or "Client",
                "password": password or "123456",
                "type": "monthly",
                "expires_at": time.strftime("%Y-%m-%d %H:%M", time.localtime(exp_timestamp)),
                "exp_timestamp": exp_timestamp,
                "hwid": hwid,
                "status": "active",
                "active": True,
                "created_at": time.strftime("%Y-%m-%d %H:%M", time.localtime(now)),
                "targets": []
            }
            clients.append(new_client)
            save_db(clients)

            return jsonify({
                "valid": True,
                "status": "valid",
                "role": "client",
                "key": key,
                "license_type": "Monthly",
                "expires_at": new_client["expires_at"],
                "username": new_client["username"]
            })
        else:
            err_msg = auth_data.get("message") or "Chiave licenza non valida su Auth."
            return jsonify({"valid": False, "status": "invalid", "message": f"Auth: {err_msg}"}), 401

    return jsonify({"valid": False, "status": "invalid", "message": "Credenziali (Username / Password / Key) non valide."}), 401


# -------------------------------------------------------------------------
# ADMIN CLIENT MANAGEMENT
# -------------------------------------------------------------------------
@app.route("/api/admin/clients", methods=["GET"])
def api_admin_clients():
    return jsonify({"clients": load_db()})


@app.route("/api/admin/clients/create", methods=["POST"])
def api_admin_clients_create():
    data = request.get_json(silent=True) or {}
    key = str(data.get("key", "")).strip()
    name = str(data.get("username", data.get("name", "Client"))).strip()
    password = str(data.get("password", "")).strip()
    days = int(data.get("days", 30))
    lic_type = str(data.get("type", "monthly")).lower()

    if not password:
        password = uuid.uuid4().hex[:8]
    if not key:
        key = f"LXMRX-{lic_type[:3].upper()}-{uuid.uuid4().hex[:8].upper()}"

    now = time.time()
    exp_timestamp = now + (days * 86400) if lic_type != "lifetime" else 0
    expires_at = time.strftime("%Y-%m-%d %H:%M", time.localtime(exp_timestamp)) if exp_timestamp else "Lifetime"

    record = {
        "id": f"cli_{int(now)}",
        "key": key,
        "username": name,
        "name": name,
        "password": password,
        "type": lic_type,
        "created_at": time.strftime("%Y-%m-%d %H:%M", time.localtime(now)),
        "expires_at": expires_at,
        "exp_timestamp": exp_timestamp,
        "status": "active",
        "active": True,
        "hwid": None,
        "targets": []
    }

    clients = load_db()
    clients = [c for c in clients if c.get("key") != key]
    clients.append(record)
    save_db(clients)

    return jsonify({"status": "created", "client": record})


@app.route("/api/admin/clients/toggle", methods=["POST"])
def api_admin_clients_toggle():
    data = request.get_json(silent=True) or {}
    key = str(data.get("key", "")).strip()
    clients = load_db()
    for c in clients:
        if c.get("key") == key:
            c["status"] = "banned" if c.get("status") == "active" else "active"
            c["active"] = (c["status"] == "active")
            save_db(clients)
            sync_db_to_queue()
            return jsonify({"status": "toggled", "client_status": c["status"]})
    return jsonify({"error": "client not found"}), 404


@app.route("/api/admin/clients/delete", methods=["POST"])
def api_admin_clients_delete():
    data = request.get_json(silent=True) or {}
    key = str(data.get("key", "")).strip()
    clients = load_db()
    clients = [c for c in clients if c.get("key") != key]
    save_db(clients)
    sync_db_to_queue()
    return jsonify({"status": "deleted", "key": key})


@app.route("/api/admin/clients/reset_hwid", methods=["POST"])
def api_admin_clients_reset_hwid():
    data = request.get_json(silent=True) or {}
    key = str(data.get("key", "")).strip()
    clients = load_db()
    for c in clients:
        if c.get("key") == key:
            c["hwid"] = None
            save_db(clients)
            return jsonify({"status": "reset", "key": key})
    return jsonify({"error": "client not found"}), 404


if __name__ == "__main__":
    if not os.path.exists(DATABASE_FILE):
        save_db([])
    port = int(os.environ.get("PORT", 5986))
    print(f"[*] SpammerX Dashboard Server starting on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
