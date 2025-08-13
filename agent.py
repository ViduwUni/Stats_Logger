import psutil
import datetime
import time
import platform
import socket
import getpass
import os
import threading
import base64
from io import BytesIO
from tempfile import NamedTemporaryFile
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, errors
from pync import Notifier
from pystray import Icon, MenuItem, Menu
from PIL import Image
import shutil
import sqlite3

# ------------------------------
# Load environment variables
load_dotenv()

# ------------------------------
# Base64 icon placeholder
ICON_BASE64 = """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"""

def load_icon_from_base64():
    icon_bytes = base64.b64decode(ICON_BASE64)
    return Image.open(BytesIO(icon_bytes))

def save_icon_temp_file():
    icon_image = load_icon_from_base64()
    temp_file = NamedTemporaryFile(delete=False, suffix=".png")
    icon_image.save(temp_file.name)
    return temp_file.name

# ------------------------------
# Configuration
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")
COLLECTION_INTERVAL = int(os.getenv("COLLECTION_INTERVAL", 60))

# ------------------------------
# Global variables
running = True
ICON_PATH = save_icon_temp_file()

# ------------------------------
# MongoDB connection with exponential backoff
def get_mongo_collection():
    wait_time = 5
    while True:
        try:
            client = MongoClient(MONGO_URI, tls=True, serverSelectionTimeoutMS=5000)
            db = client[DB_NAME]
            username = getpass.getuser()
            collection_name = f"{COLLECTION_NAME}_{username}"
            collection = db[collection_name]
            collection.create_index([("timestamp", ASCENDING)], expireAfterSeconds=86400)
            print("MongoDB connected successfully.")
            return client, collection
        except errors.ServerSelectionTimeoutError:
            print(f"MongoDB connection failed. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
            wait_time = min(wait_time * 2, 300)

client, collection = get_mongo_collection()

# ------------------------------
# System monitoring functions
def get_active_status():
    # macOS placeholder; assume active
    return True

def get_chrome_history(limit=5):
    # macOS Chrome history is in ~/Library/Application Support/Google/Chrome/Default/History
    history = []
    path = os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/History")
    temp_path = path + "_temp"
    try:
        shutil.copy2(path, temp_path)
        conn = sqlite3.connect(temp_path)
        cursor = conn.cursor()
        cursor.execute("SELECT url, title, last_visit_time FROM urls ORDER BY last_visit_time DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        for url, title, t in rows:
            history.append({"url": url, "title": title})
        conn.close()
        os.remove(temp_path)
    except Exception:
        pass
    return history

def get_system_stats():
    uname = platform.uname()
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    net_io = psutil.net_io_counters()
    return {
        "pc_name": socket.gethostname(),
        "username": getpass.getuser(),
        "os": f"{uname.system} {uname.release}",
        "cpu_model": uname.processor or "Unknown",
        "cpu_cores": psutil.cpu_count(logical=False),
        "cpu_threads": psutil.cpu_count(logical=True),
        "cpu_usage_percent": psutil.cpu_percent(interval=1),
        "ram_total_GB": round(mem.total / (1024 ** 3), 2),
        "ram_usage_percent": mem.percent,
        "disk_total_GB": round(disk.total / (1024 ** 3), 2),
        "disk_usage_percent": disk.percent,
        "network_sent_MB": round(net_io.bytes_sent / (1024 * 1024), 2),
        "network_recv_MB": round(net_io.bytes_recv / (1024 * 1024), 2),
        "active": get_active_status(),
        "recent_sites": get_chrome_history(),
        "timestamp": datetime.datetime.utcnow()
    }

# ------------------------------
# MongoDB insert with exponential backoff
def send_to_mongodb(data):
    wait_time = 5
    while True:
        try:
            collection.insert_one(data)
            print(f"[{datetime.datetime.now()}] Logged data for {data['pc_name']}")
            break
        except Exception as e:
            print(f"[{datetime.datetime.now()}] MongoDB insert failed: {e}. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
            wait_time = min(wait_time * 2, 300)

# ------------------------------
# Tray menu actions
def stop(icon, item):
    global running
    running = False
    icon.stop()
    Notifier.notify("System Monitor Agent stopped.")

def show_mongo_status(icon, item):
    try:
        client.admin.command('ping')
        status = "MongoDB is connected ✅"
    except Exception:
        status = "MongoDB is disconnected ❌"
    Notifier.notify(status)

# ------------------------------
# Monitoring loop
def monitor_loop():
    global running
    Notifier.notify("System Monitor Agent has started collecting system stats.")
    while running:
        stats = get_system_stats()
        send_to_mongodb(stats)
        for _ in range(COLLECTION_INTERVAL):
            if not running:
                break
            time.sleep(1)
    Notifier.notify("System Monitor Agent has stopped.")

# ------------------------------
# Start tray icon
icon = Icon("System Monitor Agent")
icon.icon = load_icon_from_base64()
icon.title = "System Monitor Agent"
icon.menu = Menu(
    MenuItem("Show MongoDB Status", show_mongo_status),
    MenuItem("Exit", stop)
)

threading.Thread(target=monitor_loop, daemon=True).start()
icon.run()

# ------------------------------
# Clean up temp icon file
if os.path.exists(ICON_PATH):
    os.remove(ICON_PATH)
