# ============================================================
# 🔷 MÓDULO 0 — IMPORTS Y CONFIG
# ============================================================

import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import json
import os
import re

CONFIG_FILE = "config.json"


# ============================================================
# 🔷 MÓDULO 1 — CLASE PRINCIPAL
# ============================================================

class BlenderBatchGUI:

    # --------------------------------------------------------
    # 🔹 1.1 INIT
    # --------------------------------------------------------
    def __init__(self, root):
        self.root = root
        self.root.title("Blender Batch Renderer PRO")
        self.root.geometry("780x680")

        self.blender_path = tk.StringVar()
        self.blend_files = []

        self.current_process = None
        self.pause_flag = False
        self.cancel_flag = False

        self.load_config()
        self.create_widgets()


# ============================================================
# 🔷 MÓDULO 2 — CONFIG
# ============================================================

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


# ============================================================
# 🔷 MÓDULO 3 — UI
# ============================================================

    def create_widgets(self):

        # -------- Blender Path --------
        tk.Label(self.root, text="Ruta Blender.exe").pack(anchor="w", padx=10)

        frame = tk.Frame(self.root)
        frame.pack(fill="x", padx=10)

        tk.Entry(frame, textvariable=self.blender_path).pack(side="left", fill="x", expand=True)
        tk.Button(frame, text="Buscar", command=self.select_blender).pack(side="right")

        # -------- Archivos --------
        tk.Label(self.root, text="Archivos .blend").pack(anchor="w", padx=10, pady=5)

        list_frame = tk.Frame(self.root)
        list_frame.pack(fill="both", expand=True, padx=10)

        self.listbox = tk.Listbox(list_frame)
        self.listbox.pack(side="left", fill="both", expand=True)

        btn_list = tk.Frame(list_frame)
        btn_list.pack(side="right", fill="y")

        tk.Button(btn_list, text="Agregar", command=self.add_blend_files).pack(fill="x", pady=2)
        tk.Button(btn_list, text="Editar", command=self.edit_selected).pack(fill="x", pady=2)
        tk.Button(btn_list, text="Eliminar", command=self.remove_selected).pack(fill="x", pady=2)

        # -------- Progreso --------
        self.progress = ttk.Progressbar(self.root, mode="determinate")
        self.progress.pack(fill="x", padx=10, pady=5)

        self.label = tk.Label(self.root, text="Frame: 0 / 0")
        self.label.pack(anchor="e", padx=10)

        # -------- Botones --------
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        style = {"width": 12, "height": 2, "bg": "#444", "fg": "white"}

        tk.Button(btn_frame, text="Renderizar", command=self.start_render, **style).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Pausar", command=self.pause_render, **style).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Reanudar", command=self.resume_render, **style).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancelar", command=self.cancel_render, **style).pack(side="left", padx=5)

        # -------- Log --------
        self.log = scrolledtext.ScrolledText(self.root, height=12, state="disabled")
        self.log.pack(fill="both", padx=10, pady=5)

        self.refresh_listbox()


    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        for f in self.blend_files:
            self.listbox.insert(tk.END, f)


# ============================================================
# 🔷 MÓDULO 4 — EVENTOS
# ============================================================

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

    def edit_selected(self):
        index = self.listbox.curselection()
        if not index:
            return

        new_file = filedialog.askopenfilename(filetypes=[("Blender Files", "*.blend")])
        if new_file:
            self.blend_files[index[0]] = new_file
            self.save_config()
            self.refresh_listbox()

    def remove_selected(self):
        index = self.listbox.curselection()
        if not index:
            return

        del self.blend_files[index[0]]
        self.save_config()
        self.refresh_listbox()


# ============================================================
# 🔷 MÓDULO 5 — LOG
# ============================================================

    def log_write(self, text):
        self.root.after(0, self._log_safe, text)

    def _log_safe(self, text):
        self.log.config(state="normal")
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)
        self.log.config(state="disabled")


# ============================================================
# 🔷 MÓDULO 6 — BLENDER HELPERS
# ============================================================

    def get_scene_name(self, blend):
        cmd = [self.blender_path.get(), blend, "-b", "--python-expr",
               "import bpy; print('SCENE:'+bpy.data.scenes[0].name)"]

        result = subprocess.run(cmd, stdout=subprocess.PIPE)
        for line in result.stdout.decode(errors="ignore").splitlines():
            if line.startswith("SCENE:"):
                return line.replace("SCENE:", "")
        return "Scene"

    def get_frame_range(self, blend):
        cmd = [self.blender_path.get(), blend, "-b", "--python-expr",
               "import bpy; s=bpy.data.scenes[0]; print(f'RANGE:{s.frame_start}:{s.frame_end}')"]

        result = subprocess.run(cmd, stdout=subprocess.PIPE)
        for line in result.stdout.decode(errors="ignore").splitlines():
            if line.startswith("RANGE:"):
                _, s, e = line.split(":")
                return int(s), int(e)
        return 0, 0


# ============================================================
# 🔷 MÓDULO 7 — CONTROL
# ============================================================

    def pause_render(self):
        self.pause_flag = True
        if self.current_process:
            self.current_process.terminate()
        self.log_write("⏸ Pausado")

    def resume_render(self):
        if self.pause_flag:
            self.pause_flag = False
            threading.Thread(target=self.render_batch, daemon=True).start()

    def cancel_render(self):
        self.cancel_flag = True
        if self.current_process:
            self.current_process.terminate()
        self.log_write("❌ Cancelado")


# ============================================================
# 🔷 MÓDULO 8 — RENDER + PROGRESO REAL
# ============================================================

    def start_render(self):
        if not self.blender_path.get() or not self.blend_files:
            messagebox.showerror("Error", "Faltan datos")
            return

        self.pause_flag = False
        self.cancel_flag = False

        threading.Thread(target=self.render_batch, daemon=True).start()


    def render_batch(self):

        for blend in self.blend_files:

            if self.cancel_flag:
                return

            scene = self.get_scene_name(blend)
            start, end = self.get_frame_range(blend)

            total = end - start + 1

            self.root.after(0, lambda: self.progress.config(maximum=total, value=0))

            self.log_write(f"🎬 {blend}")
            self.log_write(f"Frames: {start} → {end}")

            cmd = [
                self.blender_path.get(),
                blend,
                "-b",
                "-S", scene,
                "-x", "1",
                "-s", str(start),
                "-e", str(end),
                "-a"
            ]

            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )

            for line in self.current_process.stdout:

                if self.cancel_flag:
                    return

                self.log_write(line.strip())

                match = re.search(r"Fra:(\d+)", line)
                if match:
                    current = int(match.group(1))
                    progress = current - start + 1

                    self.root.after(0, self.update_progress, progress, total)

            self.log_write(f"✔ Terminado: {blend}")

        self.log_write("🎉 COMPLETADO")


    def update_progress(self, value, total):
        self.progress["value"] = value
        self.label.config(text=f"Frame: {value} / {total}")


# ============================================================
# 🔷 MÓDULO 9 — MAIN
# ============================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = BlenderBatchGUI(root)
    root.mainloop()