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
ICON_BASE64 = os.getenv("ICON")

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
