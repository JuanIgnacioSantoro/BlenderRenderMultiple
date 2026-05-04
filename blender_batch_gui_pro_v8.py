import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import json
import os
import time
import re

CONFIG_FILE = "config.json"


class BlenderBatchGUI:

    def __init__(self, root):
        self.root = root
        self.root.title("Blender Batch Renderer PRO FINAL")
        self.root.geometry("800x700")

        self.blender_path = tk.StringVar()
        self.blend_files = []

        self.current_process = None
        self.cancel_flag = False

        self.load_config()
        self.create_widgets()

    # ================= CONFIG =================

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    self.blender_path.set(data.get("blender_path", ""))
                    self.blend_files = data.get("blend_files", [])
            except:
                pass

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump({
                "blender_path": self.blender_path.get(),
                "blend_files": self.blend_files
            }, f, indent=4)

    # ================= UI =================

    def create_widgets(self):

        tk.Label(self.root, text="Ruta Blender.exe").pack(anchor="w", padx=10)

        frame = tk.Frame(self.root)
        frame.pack(fill="x", padx=10)

        tk.Entry(frame, textvariable=self.blender_path).pack(side="left", fill="x", expand=True)
        tk.Button(frame, text="Buscar", command=self.select_blender).pack(side="right")

        tk.Button(self.root, text="Agregar .blend", command=self.add_blend_files).pack(anchor="w", padx=10)

        self.listbox = tk.Listbox(self.root)
        self.listbox.pack(fill="both", expand=True, padx=10)

        self.progress = ttk.Progressbar(self.root, mode="determinate")
        self.progress.pack(fill="x", padx=10, pady=5)

        self.label = tk.Label(self.root, text="Progreso: 0%")
        self.label.pack(anchor="e", padx=10)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        style = {"width": 12, "height": 2, "bg": "#444", "fg": "white"}

        tk.Button(btn_frame, text="Renderizar", command=self.start_render, **style).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancelar", command=self.cancel_render, **style).pack(side="left", padx=5)

        self.log = scrolledtext.ScrolledText(self.root, height=12)
        self.log.pack(fill="both", padx=10, pady=5)

        self.refresh_listbox()

    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        for f in self.blend_files:
            self.listbox.insert(tk.END, f)

    # ================= EVENTOS =================

    def select_blender(self):
        path = filedialog.askopenfilename(filetypes=[("Blender", "blender.exe")])
        if path:
            self.blender_path.set(path)
            self.save_config()

    def add_blend_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Blender Files", "*.blend")])
        self.blend_files.extend([f for f in files if f not in self.blend_files])
        self.save_config()
        self.refresh_listbox()

    def cancel_render(self):
        self.cancel_flag = True
        if self.current_process:
            self.current_process.terminate()

    # ================= LOG =================

    def log_write(self, text):
        self.root.after(0, lambda: self._log_safe(text))

    def _log_safe(self, text):
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)

    # ================= HELPERS =================

    def get_frame_range(self, blend):
        cmd = [
            self.blender_path.get(), blend, "-b",
            "--python-expr",
            "import bpy; s=bpy.context.scene; print(f'RANGE:{s.frame_start}:{s.frame_end}')"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        for line in result.stdout.splitlines():
            if line.startswith("RANGE:"):
                _, s, e = line.split(":")
                return int(s), int(e)

        return 1, 1

    # ================= RENDER =================

    def start_render(self):
        if not self.blender_path.get() or not self.blend_files:
            messagebox.showerror("Error", "Faltan datos")
            return

        self.cancel_flag = False
        threading.Thread(target=self.render_batch, daemon=True).start()

    def render_batch(self):

        for blend in self.blend_files:

            if self.cancel_flag:
                return

            start, end = self.get_frame_range(blend)
            total = end - start + 1

            self.root.after(0, lambda: self.progress.config(maximum=total, value=0))

            self.log_write(f"🎬 Render: {blend}")
            self.log_write(f"Frames: {start} → {end}")

            process = subprocess.Popen(
                [self.blender_path.get(), blend, "-b", "-a"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True
            )

            self.current_process = process

            for line in iter(process.stdout.readline, ''):

                if self.cancel_flag:
                    process.terminate()
                    return

                line = line.strip()
                self.log_write(line)

                # Detectar frame real
                match = re.search(r"Fra:(\d+)", line)
                if match:
                    current = int(match.group(1))
                    progress = current - start + 1
                    percent = int((progress / total) * 100)

                    self.root.after(0, self.update_progress, progress, total, percent)

            process.wait()
            self.log_write(f"✔ Terminado: {blend}")

        self.log_write("🎉 COMPLETADO")

    def update_progress(self, value, total, percent):
        self.progress["value"] = value
        self.label.config(text=f"{percent}% ({value}/{total})")


if __name__ == "__main__":
    root = tk.Tk()
    app = BlenderBatchGUI(root)
    root.mainloop()