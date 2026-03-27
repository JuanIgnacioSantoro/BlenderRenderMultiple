# ============================================================
# 🔷 MÓDULO 0 — IMPORTS Y CONFIGURACIÓN GLOBAL
# ============================================================

import subprocess     # Ejecutar Blender desde Python
import threading      # Ejecutar render sin bloquear la UI
import tkinter as tk  # Interfaz gráfica
from tkinter import filedialog, messagebox, scrolledtext, ttk
import time           # Medición de tiempo (ETA)
import json           # Guardado de configuración
import os             # Manejo de archivos
import re             # Expresiones regulares

CONFIG_FILE = "config.json"


# ============================================================
# 🔷 MÓDULO 1 — CLASE PRINCIPAL DE LA APLICACIÓN
# ============================================================

class BlenderBatchGUI:

    # --------------------------------------------------------
    # 🔹 1.1 Inicialización de la app
    # --------------------------------------------------------
    def __init__(self, root):
        self.root = root
        self.root.title("Blender Batch Renderer PRO")
        self.root.geometry("720x600")

        # Ruta al ejecutable de Blender
        self.blender_path = tk.StringVar()

        # Lista de archivos .blend
        self.blend_files = []

        # Control de ejecución
        self.pause_flag = False
        self.current_process = None

        # Cargar config guardada
        self.load_config()

        # Crear interfaz
        self.create_widgets()


# ============================================================
# 🔷 MÓDULO 2 — CONFIGURACIÓN (JSON)
# ============================================================

    # --------------------------------------------------------
    # 🔹 2.1 Cargar configuración desde archivo
    # --------------------------------------------------------
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    self.blender_path.set(data.get("blender_path", ""))
                    self.blend_files = data.get("blend_files", [])
            except:
                pass

    # --------------------------------------------------------
    # 🔹 2.2 Guardar configuración actual
    # --------------------------------------------------------
    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump({
                "blender_path": self.blender_path.get(),
                "blend_files": self.blend_files
            }, f, indent=4)


# ============================================================
# 🔷 MÓDULO 3 — INTERFAZ GRÁFICA (UI)
# ============================================================

    # --------------------------------------------------------
    # 🔹 3.1 Crear todos los widgets
    # --------------------------------------------------------
    def create_widgets(self):

        # Ruta Blender
        tk.Label(self.root, text="Ruta Blender.exe").pack(anchor="w", padx=10)

        frame = tk.Frame(self.root)
        frame.pack(fill="x", padx=10)

        tk.Entry(frame, textvariable=self.blender_path).pack(side="left", fill="x", expand=True)
        tk.Button(frame, text="Buscar", command=self.select_blender).pack(side="right")

        # Botón agregar archivos
        tk.Button(self.root, text="Agregar .blend", command=self.add_blend_files).pack(anchor="w", padx=10, pady=5)

        # Lista de archivos
        self.listbox = tk.Listbox(self.root)
        self.listbox.pack(fill="both", expand=True, padx=10)

        # Barra de progreso
        self.progress = ttk.Progressbar(self.root, mode="determinate")
        self.progress.pack(fill="x", padx=10, pady=5)

        # Texto progreso + ETA
        self.label = tk.Label(self.root, text="0 % | ETA: --:--")
        self.label.pack(anchor="e", padx=10)

        # Botones control
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=5)

        tk.Button(btn_frame, text="Renderizar", command=self.start_render, bg="green", fg="white").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Pausar", command=self.pause_render, bg="orange").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Reanudar", command=self.resume_render, bg="blue", fg="white").pack(side="left", padx=5)

        # Log
        self.log = scrolledtext.ScrolledText(self.root, height=10, state="disabled")
        self.log.pack(fill="both", padx=10, pady=5)

        self.refresh_listbox()

    # --------------------------------------------------------
    # 🔹 3.2 Actualizar lista visual de archivos
    # --------------------------------------------------------
    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        for f in self.blend_files:
            self.listbox.insert(tk.END, f)


# ============================================================
# 🔷 MÓDULO 4 — EVENTOS DE USUARIO
# ============================================================

    # --------------------------------------------------------
    # 🔹 4.1 Seleccionar Blender.exe
    # --------------------------------------------------------
    def select_blender(self):
        path = filedialog.askopenfilename(filetypes=[("Blender", "blender.exe")])
        if path:
            self.blender_path.set(path)
            self.save_config()

    # --------------------------------------------------------
    # 🔹 4.2 Agregar archivos .blend
    # --------------------------------------------------------
    def add_blend_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Blender Files", "*.blend")])
        for f in files:
            if f not in self.blend_files:
                self.blend_files.append(f)

        self.save_config()
        self.refresh_listbox()


# ============================================================
# 🔷 MÓDULO 5 — SISTEMA DE LOG
# ============================================================

    # --------------------------------------------------------
    # 🔹 5.1 Escribir log de forma segura (thread-safe)
    # --------------------------------------------------------
    def log_write(self, text):
        self.root.after(0, self._log_safe, text)

    # --------------------------------------------------------
    # 🔹 5.2 Escritura real en el widget
    # --------------------------------------------------------
    def _log_safe(self, text):
        self.log.config(state="normal")
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)
        self.log.config(state="disabled")


# ============================================================
# 🔷 MÓDULO 6 — FUNCIONES AUXILIARES (BLENDER + ARCHIVOS)
# ============================================================

    # --------------------------------------------------------
    # 🔹 6.1 Obtener rango de frames desde Blender
    # --------------------------------------------------------
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

    # --------------------------------------------------------
    # 🔹 6.2 Obtener carpeta de salida del render
    # --------------------------------------------------------
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

    # --------------------------------------------------------
    # 🔹 6.3 Detectar último frame renderizado
    # --------------------------------------------------------
    def get_last_frame(self, path):
        if not os.path.exists(path):
            return 0

        nums = []

        for f in os.listdir(path):
            match = re.search(r'(\d+)(?=\.\w+$)', f)
            if match:
                nums.append(int(match.group(1)))

        return max(nums) if nums else 0

    # --------------------------------------------------------
    # 🔹 6.4 Contar archivos válidos (frames renderizados)
    # --------------------------------------------------------
    def count_valid_files(self, path):
        if not os.path.exists(path):
            return 0

        return len([
            f for f in os.listdir(path)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".exr"))
        ])


# ============================================================
# 🔷 MÓDULO 7 — CONTROL DE EJECUCIÓN
# ============================================================

    # --------------------------------------------------------
    # 🔹 7.1 Pausar render
    # --------------------------------------------------------
    def pause_render(self):
        self.pause_flag = True
        if self.current_process:
            self.current_process.terminate()
        self.log_write("⏸ Pausado")

    # --------------------------------------------------------
    # 🔹 7.2 Reanudar render
    # --------------------------------------------------------
    def resume_render(self):
        if not self.pause_flag:
            return

        self.pause_flag = False
        self.log_write("▶ Reanudando...")
        threading.Thread(target=self.render_batch, daemon=True).start()


# ============================================================
# 🔷 MÓDULO 8 — MOTOR DE RENDER
# ============================================================

    # --------------------------------------------------------
    # 🔹 8.1 Iniciar render
    # --------------------------------------------------------
    def start_render(self):
        if not self.blender_path.get() or not self.blend_files:
            messagebox.showerror("Error", "Faltan datos")
            return

        self.pause_flag = False
        threading.Thread(target=self.render_batch, daemon=True).start()

    # --------------------------------------------------------
    # 🔹 8.2 Lógica completa de render batch
    # --------------------------------------------------------
    def render_batch(self):

        total_frames = 0
        trabajos = []

        # Calcular total de frames
        for blend in self.blend_files:
            s, e = self.get_frame_range(blend)
            total = e - s + 1
            out = self.get_output_path(blend)

            trabajos.append((blend, s, total, out))
            total_frames += total

        self.root.after(0, lambda: self.progress.config(maximum=total_frames, value=0))

        rendered_global = 0
        frame_times = []

        # Procesar cada archivo
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

                    # Calcular ETA
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

    # --------------------------------------------------------
    # 🔹 8.3 Actualizar barra de progreso
    # --------------------------------------------------------
    def update_progress(self, value, percent, eta):
        self.progress["value"] = value
        self.label.config(text=f"{percent} % | ETA: {eta}")


# ============================================================
# 🔷 MÓDULO 9 — ENTRY POINT
# ============================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = BlenderBatchGUI(root)
    root.mainloop()