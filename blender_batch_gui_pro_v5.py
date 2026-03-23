import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import time
import json
import os
import re

CONFIG_FILE = "config.json"

class BlenderBatchGUI:

    def __init__(self, root):
        self.root = root
        self.root.title("Blender Batch Renderer PRO")
        self.root.geometry("720x600")

        self.blender_path = tk.StringVar()
        self.blend_files = []

        self.pause_flag = False
        self.current_process = None

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

        tk.Button(self.root, text="Agregar .blend", command=self.add_blend_files).pack(anchor="w", padx=10, pady=5)

        self.listbox = tk.Listbox(self.root)
        self.listbox.pack(fill="both", expand=True, padx=10)

        self.progress = ttk.Progressbar(self.root, mode="determinate")
        self.progress.pack(fill="x", padx=10, pady=5)

        self.label = tk.Label(self.root, text="0 % | ETA: --:--")
        self.label.pack(anchor="e", padx=10)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=5)

        tk.Button(btn_frame, text="Renderizar", command=self.start_render, bg="green", fg="white").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Pausar", command=self.pause_render, bg="orange").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Reanudar", command=self.resume_render, bg="blue", fg="white").pack(side="left", padx=5)

        self.log = scrolledtext.ScrolledText(self.root, height=10, state="disabled")
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
        for f in files:
            if f not in self.blend_files:
                self.blend_files.append(f)

        self.save_config()
        self.refresh_listbox()

    # ================= LOG =================

    def log_write(self, text):
        self.root.after(0, self._log_safe, text)

    def _log_safe(self, text):
        self.log.config(state="normal")
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)
        self.log.config(state="disabled")

    # ================= HELPERS =================

    def get_frame_range(self, blend):
        cmd = [
            self.blender_path.get(),
            blend,
            "-b",
            "--python-expr",
            "import bpy; print(f'RANGE:{bpy.context.scene.frame_start}:{bpy.context.scene.frame_end}')"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        for line in result.stdout.splitlines():
            if line.startswith("RANGE:"):
                _, s, e = line.split(":")
                return int(s), int(e)

        return 1, 1

    def get_output_path(self, blend):
        cmd = [
            self.blender_path.get(),
            blend,
            "-b",
            "--python-expr",
            "import bpy, os; print('OUT:' + bpy.path.abspath(bpy.context.scene.render.filepath))"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        for line in result.stdout.splitlines():
            if line.startswith("OUT:"):
                path = line.replace("OUT:", "").strip()
                return os.path.dirname(path)

        return os.path.dirname(blend)

    def get_last_frame(self, path):
        if not os.path.exists(path):
            return 0

        files = os.listdir(path)
        nums = []

        for f in files:
            match = re.search(r'(\d+)(?=\.\w+$)', f)
            if match:
                nums.append(int(match.group(1)))

        return max(nums) if nums else 0

    def count_valid_files(self, path):
        if not os.path.exists(path):
            return 0

        return len([
            f for f in os.listdir(path)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".exr"))
        ])

    # ================= CONTROL =================

    def pause_render(self):
        self.pause_flag = True
        if self.current_process:
            self.current_process.terminate()
        self.log_write("⏸ Pausado")

    def resume_render(self):
        if not self.pause_flag:
            return

        self.pause_flag = False
        self.log_write("▶ Reanudando...")
        threading.Thread(target=self.render_batch, daemon=True).start()

    # ================= RENDER =================

    def start_render(self):
        if not self.blender_path.get() or not self.blend_files:
            messagebox.showerror("Error", "Faltan datos")
            return

        self.pause_flag = False
        threading.Thread(target=self.render_batch, daemon=True).start()

    def render_batch(self):

        total_frames = 0
        trabajos = []

        for blend in self.blend_files:
            s, e = self.get_frame_range(blend)
            total = e - s + 1
            out = self.get_output_path(blend)

            trabajos.append((blend, s, total, out))
            total_frames += total

        self.root.after(0, lambda: self.progress.config(maximum=total_frames, value=0))

        rendered_global = 0
        frame_times = []

        for blend, frame_start, total, out in trabajos:

            if self.pause_flag:
                return

            last_frame = self.get_last_frame(out)
            start_frame = last_frame + 1

            self.log_write(f"Render: {blend}")
            self.log_write(f"Reanuda desde frame {start_frame}")

            self.current_process = subprocess.Popen([
                self.blender_path.get(),
                blend,
                "-b",
                "-x", "1",
                "-s", str(start_frame),
                "-a"
            ])

            last_count = self.count_valid_files(out)

            while self.current_process.poll() is None:

                if self.pause_flag:
                    return

                current_count = self.count_valid_files(out)

                if current_count > last_count:
                    diff = current_count - last_count
                    rendered_global += diff

                    now = time.time()
                    frame_times.append(now)

                    if len(frame_times) > 1:
                        avg = (frame_times[-1] - frame_times[0]) / (len(frame_times) - 1)
                        remaining = avg * (total_frames - rendered_global)
                        eta = time.strftime("%M:%S", time.gmtime(remaining))
                    else:
                        eta = "--:--"

                    percent = int((rendered_global / total_frames) * 100)

                    self.root.after(0, self.update_progress, rendered_global, percent, eta)

                    last_count = current_count

                time.sleep(0.3)

            self.log_write(f"✔ Terminado: {blend}")

        self.log_write("🎉 COMPLETADO")

    def update_progress(self, value, percent, eta):
        self.progress["value"] = value
        self.label.config(text=f"{percent} % | ETA: {eta}")


if __name__ == "__main__":
    root = tk.Tk()
    app = BlenderBatchGUI(root)
    root.mainloop()