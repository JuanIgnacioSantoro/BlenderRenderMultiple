# Blender Batch Renderer PRO (FIX FINAL ESCENA)

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
        self.root.geometry("720x650")

        self.blender_path = tk.StringVar()
        self.blend_files = []

        self.pause_flag = False
        self.current_process = None

        self.load_config()
        self.create_widgets()

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

    def log_write(self, text):
        self.root.after(0, self._log_safe, text)

    def _log_safe(self, text):
        self.log.config(state="normal")
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)
        self.log.config(state="disabled")

    # ✅ FIX ESCENA (robusto)
    def get_scene_name(self, blend):
        cmd = [
            self.blender_path.get(),
            blend,
            "-b",
            "--python-expr",
            "import bpy; print('SCENE:'+bpy.data.scenes[0].name)"
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = (result.stdout or b"").decode("utf-8", errors="ignore")

        for line in output.splitlines():
            if line.startswith("SCENE:"):
                return line.replace("SCENE:", "").strip()

        return "Scene"

    def get_frame_range(self, blend):
        cmd = [
            self.blender_path.get(),
            blend,
            "-b",
            "--python-expr",
            "import bpy; s=bpy.data.scenes[0]; print(f'RANGE:{s.frame_start}:{s.frame_end}')"
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = (result.stdout or b"").decode("utf-8", errors="ignore")

        for line in output.splitlines():
            if line.startswith("RANGE:"):
                _, s, e = line.split(":")
                return int(s), int(e)

        return 0, 0

    def get_output_path(self, blend):
        cmd = [
            self.blender_path.get(),
            blend,
            "-b",
            "--python-expr",
            "import bpy, os; s=bpy.data.scenes[0]; print('OUT:' + bpy.path.abspath(s.render.filepath))"
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = (result.stdout or b"").decode("utf-8", errors="ignore")

        for line in output.splitlines():
            if line.startswith("OUT:"):
                path = line.replace("OUT:", "").strip()
                return os.path.dirname(path)

        return os.path.dirname(blend)

    def get_last_frame(self, path):
        if not os.path.exists(path):
            return 0

        nums = []
        for f in os.listdir(path):
            match = re.search(r'(\d+)(?=\.\w+$)', f)
            if match:
                nums.append(int(match.group(1)))

        return max(nums) if nums else 0

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

    def start_render(self):
        if not self.blender_path.get() or not self.blend_files:
            messagebox.showerror("Error", "Faltan datos")
            return

        self.pause_flag = False
        threading.Thread(target=self.render_batch, daemon=True).start()

    def render_batch(self):

        for blend in self.blend_files:

            if self.pause_flag:
                return

            scene = self.get_scene_name(blend)
            s, e = self.get_frame_range(blend)

            if s > e:
                s, e = e, s

            self.log_write(f"Render: {blend}")
            self.log_write(f"Escena: {scene}")
            self.log_write(f"Frames: {s} → {e}")

            self.current_process = subprocess.Popen([
                self.blender_path.get(),
                blend,
                "-b",
                "-S", scene,
                "-x", "1",
                "-s", str(s),
                "-e", str(e),
                "-a"
            ])

            self.current_process.wait()

            self.log_write(f"✔ Terminado: {blend}")

        self.log_write("🎉 COMPLETADO")


if __name__ == "__main__":
    root = tk.Tk()
    app = BlenderBatchGUI(root)
    root.mainloop()
