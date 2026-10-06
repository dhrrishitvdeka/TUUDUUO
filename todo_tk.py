import json
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DATA_FILE = APP_DIR / "todos.json"

BG_BLACK = "#000000"
BG_SURFACE = "#0e0e11"
BG_CARD = "#16161b"
BORDER_COLOR = "#26262e"
TEXT_WHITE = "#f5f5f7"
TEXT_MUTED = "#9898a3"
ACCENT_COLOR = "#f5f5f7"
COLOR_DONE = "#9ed9b8"
COLOR_URGENT = "#ff6b63"

class TuuduuoTk(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TUUDUUO — Minimalist Local PC App")
        self.geometry("900x700")
        self.configure(bg=BG_BLACK)

        self.tasks = []
        self.profile = {"name": "", "onboarded": False}
        self.raw_data = {"calendarMarks": {}}
        self.status_var = tk.StringVar(value=f"Storage: {DATA_FILE.name}")

        self.load_data()
        self.setup_ui()
        self.check_onboarding()
        self.render_tasks()

    def get_greeting(self):
        hour = datetime.now().hour
        day_str = datetime.now().strftime("%A, %b %d")
        if 4 <= hour < 12:
            greet = "Good morning"
            symbol = "✦"
        elif 12 <= hour < 17:
            greet = "Good afternoon"
            symbol = "●"
        elif 17 <= hour < 21:
            greet = "Good evening"
            symbol = "◐"
        else:
            greet = "Good night"
            symbol = "☾"
        name = self.profile.get("name") or "Friend"
        return f"{symbol}  {greet}, {name}  ·  {day_str}"

    def load_data(self):
        if DATA_FILE.exists():
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.tasks = data
                        self.raw_data = {"calendarMarks": {}}
                    elif isinstance(data, dict):
                        self.tasks = data.get("tasks", []) if isinstance(data.get("tasks", []), list) else []
                        self.profile = data.get("profile", self.profile) if isinstance(data.get("profile", {}), dict) else self.profile
                        self.raw_data = data
                    else:
                        self.tasks = []
            except Exception as e:
                print(f"Error loading {DATA_FILE}: {e}")
                try:
                    backup = APP_DIR / f"todos.corrupt.{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    DATA_FILE.rename(backup)
                    print(f"Corrupt file backed up to {backup.name}")
                except Exception:
                    pass

    def save_data(self):
        payload = dict(getattr(self, "raw_data", {}) or {})
        if not isinstance(payload.get("calendarMarks", {}), dict):
            payload["calendarMarks"] = {}
        payload.update({
            "version": 1,
            "lastSaved": datetime.now().isoformat(),
            "activeFile": payload.get("activeFile", "todos.json"),
            "profile": self.profile,
            "tasks": self.tasks
        })
        try:
            import tempfile
            fd, tmp_path = tempfile.mkstemp(dir=str(APP_DIR), prefix="todos.", suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2, ensure_ascii=False)
                os.replace(tmp_path, DATA_FILE)
            finally:
                try:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                except OSError:
                    pass
            self.status_var.set(f"Saved to todos.json at {datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            try:
                self.status_var.set(f"Save error: {e}")
            except Exception:
                print(f"Save error: {e}")

    def check_onboarding(self):
        if not self.profile.get("onboarded") or not self.profile.get("name"):
            name = simpledialog.askstring("Welcome to TUUDUUO", "What should we call you?", parent=self)
            self.profile["name"] = name.strip() if name else "Friend"
            self.profile["onboarded"] = True
            self.save_data()

    def setup_ui(self):
        header = tk.Frame(self, bg=BG_BLACK, pady=12, padx=18)
        header.pack(fill="x")

        self.greet_label = tk.Label(header, text=self.get_greeting(), font=("Segoe UI", 12, "bold"), fg=TEXT_WHITE, bg=BG_BLACK)
        self.greet_label.pack(side="left")

        btn_save = tk.Button(header, text="Save (Ctrl+S)", font=("Segoe UI", 9, "bold"), bg="#1c1c22", fg="#f5f5f7",
                             activebackground="#252940", activeforeground="#ffffff", relief="flat", padx=10, pady=4,
                             cursor="hand2", command=self.save_data)
        btn_save.pack(side="right", padx=4)

        add_frame = tk.Frame(self, bg=BG_SURFACE, padx=14, pady=10)
        add_frame.pack(fill="x", padx=18, pady=(0, 10))

        self.add_entry = tk.Entry(add_frame, font=("Segoe UI", 10), bg="#141419", fg=TEXT_WHITE,
                                  insertbackground=TEXT_WHITE, relief="flat", highlightthickness=1,
                                  highlightbackground=BORDER_COLOR, highlightcolor=ACCENT_COLOR)
        self.add_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))
        self.add_entry.bind("<Return>", lambda e: self.add_task())

        btn_add = tk.Button(add_frame, text="Add Task", font=("Segoe UI", 9, "bold"), bg=ACCENT_COLOR, fg="#ffffff",
                            relief="flat", padx=14, pady=4, cursor="hand2", command=self.add_task)
        btn_add.pack(side="right")

        list_container = tk.Frame(self, bg=BG_BLACK)
        list_container.pack(fill="both", expand=True, padx=18, pady=4)

        self.canvas = tk.Canvas(list_container, bg=BG_BLACK, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(list_container, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg=BG_BLACK)

        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._canvas_win = self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw", width=840)
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self._canvas_win, width=e.width))
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        footer = tk.Label(self, textvariable=self.status_var, font=("Segoe UI", 8), fg=TEXT_MUTED, bg=BG_BLACK, pady=6)
        footer.pack(fill="x")

        self.bind("<Control-s>", lambda e: self.save_data())

    def add_task(self):
        text = self.add_entry.get().strip()
        if not text:
            return
        import random
        clean = text.replace("!urgent", "").replace("!high", "").replace("@today", "").strip() or text
        now = datetime.now()
        new_task = {
            "id": f"tk-{int(now.timestamp() * 1000)}-{random.randint(100, 999)}",
            "title": clean,
            "notes": "",
            "completed": False,
            "priority": "urgent" if "!urgent" in text else ("high" if "!high" in text else "none"),
            "tags": [],
            "dueDate": now.strftime("%Y-%m-%d") if "@today" in text else "",
            "dueTime": "",
            "pinned": False,
            "subtasks": [],
            "pomodoros": 0,
            "createdAt": now.isoformat(),
            "completedAt": None
        }
        self.tasks.insert(0, new_task)
        self.add_entry.delete(0, tk.END)
        self.save_data()
        self.render_tasks()

    def toggle_task(self, task):
        task["completed"] = not task.get("completed", False)
        task["completedAt"] = None if not task["completed"] else datetime.now().isoformat()
        self.save_data()
        self.render_tasks()

    def delete_task(self, task):
        self.tasks = [t for t in self.tasks if t.get("id") != task.get("id")]
        self.save_data()
        self.render_tasks()

    def render_tasks(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        if not self.tasks:
            lbl = tk.Label(self.scroll_frame, text="Clean Slate. No tasks right now.", font=("Segoe UI", 11), fg=TEXT_MUTED, bg=BG_BLACK, pady=40)
            lbl.pack()
            return

        for task in self.tasks:
            is_done = task.get("completed", False)
            card = tk.Frame(self.scroll_frame, bg=BG_CARD, padx=12, pady=8, highlightthickness=1, highlightbackground=BORDER_COLOR)
            card.pack(fill="x", pady=3)

            chk_txt = "✓" if is_done else "○"
            chk_color = COLOR_DONE if is_done else TEXT_MUTED
            chk_btn = tk.Button(card, text=chk_txt, font=("Segoe UI", 10), fg=chk_color, bg=BG_CARD, relief="flat",
                                cursor="hand2", command=lambda t=task: self.toggle_task(t))
            chk_btn.pack(side="left", padx=(0, 10))

            subs = task.get("subtasks", [])
            total_s = len(subs)
            done_s = len([s for s in subs if s.get("completed")])
            meta_parts = []
            if total_s > 0:
                meta_parts.append(f"{done_s}/{total_s} subs")
            if task.get("pomodoros", 0) > 0:
                meta_parts.append(f"{task.get('pomodoros')} pomo")
            suffix = f"  ({ ' · '.join(meta_parts) })" if meta_parts else ""

            title_color = TEXT_MUTED if is_done else TEXT_WHITE
            font_style = ("Segoe UI", 10, "overstrike" if is_done else "normal")
            title_lbl = tk.Label(card, text=task.get("title", "") + suffix, font=font_style, fg=title_color, bg=BG_CARD, anchor="w")
            title_lbl.pack(side="left", fill="x", expand=True)

            del_btn = tk.Button(card, text="✕", font=("Segoe UI", 9), fg=TEXT_MUTED, bg=BG_CARD, relief="flat",
                                cursor="hand2", command=lambda t=task: self.delete_task(t))
            del_btn.pack(side="right")

if __name__ == "__main__":
    app = TuuduuoTk()
    app.mainloop()
