import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import time
import re
import json
import os

CONFIG_FILE = "config.json"

FRAME_REGEX_1 = re.compile(r"Fra:(\d+)")
FRAME_REGEX_2 = re.compile(r"Rendering\s+(\d+)\s*/\s*(\d+)")

class BlenderBatchGUI:

    def __init__(self, root):
        self.root = root
        self.root.title("Blender Batch Renderer PRO")
        self.root.geometry("750x600")

        self.blender_path = tk.StringVar()
        self.output_path = tk.StringVar(value="C:/RenderOutput/")
        self.blend_files = []

        self.load_config()
        self.create_widgets()

    # ================= CONFIG =================

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    self.blender_path.set(data.get("blender_path", ""))
                    self.output_path.set(data.get("output_path", "C:/RenderOutput/"))
            except:
                pass

    def save_config(self):
        data = {
            "blender_path": self.blender_path.get(),
            "output_path": self.output_path.get()
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=4)

    # ================= UI =================

    def create_widgets(self):
        tk.Label(self.root, text="Ruta Blender.exe").pack(anchor="w", padx=10)
        frame_blender = tk.Frame(self.root)
        frame_blender.pack(fill="x", padx=10)

        tk.Entry(frame_blender, textvariable=self.blender_path).pack(side="left", fill="x", expand=True)
        tk.Button(frame_blender, text="Buscar", command=self.select_blender).pack(side="right")

        tk.Label(self.root, text="Carpeta de salida (no usada si se respeta .blend)").pack(anchor="w", padx=10, pady=(10, 0))
        frame_output = tk.Frame(self.root)
        frame_output.pack(fill="x", padx=10)

        tk.Entry(frame_output, textvariable=self.output_path).pack(side="left", fill="x", expand=True)
        tk.Button(frame_output, text="Buscar", command=self.select_output).pack(side="right")

        tk.Label(self.root, text="Archivos .blend").pack(anchor="w", padx=10, pady=(10, 0))
        tk.Button(self.root, text="Agregar archivos .blend", command=self.add_blend_files).pack(padx=10, anchor="w")

        self.listbox = tk.Listbox(self.root, height=6)
        self.listbox.pack(fill="both", padx=10, pady=5, expand=True)

        tk.Label(self.root, text="Progreso GLOBAL").pack(anchor="w", padx=10)
        self.progress = ttk.Progressbar(self.root, mode="determinate")
        self.progress.pack(fill="x", padx=10)

        self.progress_label = tk.Label(self.root, text="0 % | ETA: --:--")
        self.progress_label.pack(anchor="e", padx=10)

        tk.Button(
            self.root,
            text="Iniciar Render",
            command=self.start_render,
            bg="#4CAF50",
            fg="white",
            height=2
        ).pack(pady=10)

        tk.Label(self.root, text="Log Blender").pack(anchor="w", padx=10)
        self.log = scrolledtext.ScrolledText(self.root, height=10, state="disabled")
        self.log.pack(fill="both", padx=10, pady=(0, 10), expand=True)

    # ================= EVENTOS =================

    def select_blender(self):
        path = filedialog.askopenfilename(filetypes=[("Blender", "blender.exe")])
        if path:
            self.blender_path.set(path)
            self.save_config()

    def select_output(self):
        path = filedialog.askdirectory()
        if path:
            self.output_path.set(path + "/")
            self.save_config()

    def add_blend_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Blender Files", "*.blend")])
        for f in files:
            if f not in self.blend_files:
                self.blend_files.append(f)
                self.listbox.insert(tk.END, f)

    # ================= LOG =================

    def log_write(self, text):
        self.root.after(0, self._log_write_safe, text)

    def _log_write_safe(self, text):
        self.log.config(state="normal")
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)
        self.log.config(state="disabled")

    # ================= RENDER =================

    def start_render(self):
        if not self.blender_path.get() or not self.blend_files:
            messagebox.showerror("Error", "Faltan datos")
            return

        threading.Thread(target=self.render_batch, daemon=True).start()

    def get_frame_range(self, blend_file):
        cmd = [
            self.blender_path.get(),
            blend_file,
            "-b",
            "--python-expr",
            "import bpy; print(f'FRAME_RANGE:{bpy.context.scene.frame_start}:{bpy.context.scene.frame_end}')"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        for line in result.stdout.splitlines():
            if line.startswith("FRAME_RANGE"):
                _, start, end = line.split(":")
                return int(start), int(end)

        return 1, 1

    def render_batch(self):

        # 🔥 PRE-CÁLCULO GLOBAL
        total_global_frames = 0
        frame_ranges = []

        for blend in self.blend_files:
            frame_start, frame_end = self.get_frame_range(blend)
            total = frame_end - frame_start + 1

            frame_ranges.append((blend, frame_start, frame_end, total))
            total_global_frames += total

        self.root.after(0, lambda: self.progress.config(maximum=total_global_frames, value=0))

        global_rendered = 0
        global_times = []

        # 🔥 LOOP PRINCIPAL
        for blend, frame_start, frame_end, total_frames in frame_ranges:
            self.log_write(f"🎬 Render actual: {blend}")

            cmd = [
                self.blender_path.get(),
                blend,
                "-b",
                "--log-level", "1",
                "-x", "1",
                "-a"
            ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace"
            )

            last_rendered_local = 0

            for line in process.stdout:
                if not line:
                    continue

                line = line.strip()
                self.log_write(line)

                rendered = None

                match1 = FRAME_REGEX_1.search(line)
                if match1:
                    current_frame = int(match1.group(1))
                    rendered = current_frame - frame_start + 1

                match2 = FRAME_REGEX_2.search(line)
                if match2:
                    current_frame = int(match2.group(1))
                    rendered = current_frame

                if rendered is not None:
                    delta = rendered - last_rendered_local
                    if delta > 0:
                        global_rendered += delta
                        last_rendered_local = rendered

                    now = time.time()
                    global_times.append(now)

                    if len(global_times) > 1:
                        avg = (global_times[-1] - global_times[0]) / (len(global_times) - 1)
                        remaining = avg * (total_global_frames - global_rendered)
                        eta = time.strftime("%M:%S", time.gmtime(remaining))
                    else:
                        eta = "--:--"

                    percent = int((global_rendered / total_global_frames) * 100)

                    self.root.after(
                        0,
                        self.update_progress,
                        global_rendered,
                        percent,
                        eta
                    )

            process.wait()
            self.log_write(f"✔ Render terminado: {blend}")

        self.log_write("🎉 TODOS LOS RENDERS COMPLETADOS")

    def update_progress(self, value, percent, eta):
        self.progress["value"] = value
        self.progress_label.config(text=f"{percent} % | ETA: {eta}")


if __name__ == "__main__":
    root = tk.Tk()
    app = BlenderBatchGUI(root)
    root.mainloop()