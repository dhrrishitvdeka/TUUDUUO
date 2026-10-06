import http.server
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from datetime import datetime
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_FILE = APP_DIR / "todos.json"

def get_free_port(preferred_port=5566):
    for port in range(preferred_port, preferred_port + 50):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    return 0

def list_json_files():
    files = []
    for p in APP_DIR.glob("*.json"):
        try:
            stat = p.stat()
            files.append({
                "name": p.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "is_default": (p.name == "todos.json")
            })
        except Exception:
            pass
    files.sort(key=lambda x: (0 if x["is_default"] else 1, x["modified"]))
    return files

class TodoRequestHandler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP_DIR), **kwargs)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path

        if path == "/api/status":
            self.send_json_response({"status": "ok", "app_dir": str(APP_DIR)})
            return

        if path == "/api/todos":
            query = urllib.parse.parse_qs(url.query)
            filename = query.get("file", ["todos.json"])[0]
            safe_filename = Path(filename).name
            if not safe_filename.endswith(".json"):
                safe_filename += ".json"
            target = APP_DIR / safe_filename

            if target.is_file():
                try:
                    with open(target, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self.send_json_response({"status": "success", "file": safe_filename, "data": data})
                except json.JSONDecodeError:
                    self.send_json_response({"status": "empty", "file": safe_filename, "data": None})
                except Exception:
                    self.send_json_response({"status": "error", "message": "Failed to read file"}, status=500)
            else:
                self.send_json_response({"status": "empty", "file": safe_filename, "data": None})
            return

        if path == "/api/files":
            files = list_json_files()
            self.send_json_response({"status": "success", "files": files})
            return

        if path == "/" or path == "":
            self.path = "/index.html"

        super().do_GET()

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path

        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            content_length = 0
        if content_length > 5 * 1024 * 1024:
            self.send_json_response({"status": "error", "message": "Payload too large"}, status=413)
            return
        body = self.rfile.read(content_length) if content_length > 0 else b""

        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            payload = {}

        if path == "/api/save":
            filename = payload.get("file", "todos.json")
            safe_filename = Path(filename).name
            if not safe_filename.endswith(".json"):
                safe_filename += ".json"
            target = APP_DIR / safe_filename
            todos_data = payload.get("data", [])

            try:
                if isinstance(todos_data, list):
                    task_count = len(todos_data)
                elif isinstance(todos_data, dict) and isinstance(todos_data.get("tasks", []), list):
                    task_count = len(todos_data.get("tasks", []))
                else:
                    self.send_json_response({"status": "error", "message": "Invalid data: 'tasks' must be a list"}, status=400)
                    return
                import tempfile
                fd, tmp_path = tempfile.mkstemp(dir=str(APP_DIR), prefix=safe_filename + ".", suffix=".tmp")
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as f:
                        json.dump(todos_data, f, indent=2, ensure_ascii=False)
                    os.replace(tmp_path, target)
                finally:
                    try:
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)
                    except OSError:
                        pass

                stat = target.stat()
                self.send_json_response({
                    "status": "success",
                    "file": safe_filename,
                    "saved_at": datetime.now().strftime("%H:%M:%S"),
                    "size": stat.st_size,
                    "task_count": task_count
                })
            except Exception as e:
                self.send_json_response({"status": "error", "message": str(e)}, status=500)
            return

        if path == "/api/snapshot":
            todos_data = payload.get("data", [])
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            snapshot_name = f"todos_backup_{timestamp_str}.json"
            target = APP_DIR / snapshot_name

            try:
                import tempfile
                fd, tmp_path = tempfile.mkstemp(dir=str(APP_DIR), prefix="snapshot.", suffix=".tmp")
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as f:
                        json.dump(todos_data, f, indent=2, ensure_ascii=False)
                    os.replace(tmp_path, target)
                finally:
                    try:
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)
                    except OSError:
                        pass
                self.send_json_response({
                    "status": "success",
                    "file": snapshot_name,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            except Exception as e:
                self.send_json_response({"status": "error", "message": str(e)}, status=500)
            return

        self.send_json_response({"status": "error", "message": "Unknown endpoint"}, status=404)

    def list_directory(self, path):
        self.send_error(403, "Directory listing denied")
        return None

    def send_json_response(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass

def launch_app_window(url):
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
    ]
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]

    for p in edge_paths + chrome_paths:
        if os.path.isfile(p):
            try:
                subprocess.Popen([
                    p,
                    f"--app={url}",
                    "--window-size=1180,860",
                    "--window-position=120,80"
                ])
                return True
            except Exception:
                continue

    webbrowser.open(url)
    return False

def main():
    port = get_free_port(5566)
    if not port:
        print("ERROR: no free port available (5566-5615 busy). Close another instance and retry.")
        sys.exit(1)
    server_address = ("127.0.0.1", port)
    httpd = http.server.ThreadingHTTPServer(server_address, TodoRequestHandler)
    url = f"http://127.0.0.1:{port}"

    print("TUUDUUO")
    print(f"  directory  {APP_DIR}")
    print(f"  data       {DEFAULT_DATA_FILE.name}")
    print(f"  server     {url}")
    print("")
    print("  Opening desktop window (Ctrl+C to stop)...\n")

    threading.Thread(target=lambda: (time.sleep(0.3), launch_app_window(url)), daemon=True).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
        httpd.server_close()

if __name__ == "__main__":
    main()
