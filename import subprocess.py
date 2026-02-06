import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import time
import re

FRAME_REGEX = re.compile(r"Fra:(\d+)")

class BlenderBatchGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Blender Batch Renderer PRO")
        self.root.geometry("750x600")

        self.blender_path = tk.StringVar()
        self.output_path = tk.StringVar(value="C:/RenderOutput/")
        self.blend_files = []

        self.create_widgets()

    def create_widgets(self):
        # Blender path
        tk.Label(self.root, text="Ruta Blender.exe").pack(anchor="w", padx=10)
        frame_blender = tk.Frame(self.root)
        frame_blender.pack(fill="x", padx=10)

        tk.Entry(frame_blender, textvariable=self.blender_path).pack(side="left", fill="x", expand=True)
        tk.Button(frame_blender, text="Buscar", command=self.select_blender).pack(side="right")

        # Output path
        tk.Label(self.root, text="Carpeta de salida").pack(anchor="w", padx=10, pady=(10, 0))
        frame_output = tk.Frame(self.root)
        frame_output.pack(fill="x", padx=10)

        tk.Entry(frame_output, textvariable=self.output_path).pack(side="left", fill="x", expand=True)
        tk.Button(frame_output, text="Buscar", command=self.select_output).pack(side="right")

        # Blend files
        tk.Label(self.root, text="Archivos .blend").pack(anchor="w", padx=10, pady=(10, 0))
        tk.Button(self.root, text="Agregar archivos .blend", command=self.add_blend_files).pack(padx=10, anchor="w")

        self.listbox = tk.Listbox(self.root, height=6)
        self.listbox.pack(fill="both", padx=10, pady=5, expand=True)

        # Progress bar
        tk.Label(self.root, text="Progreso por frame").pack(anchor="w", padx=10)
        self.progress = ttk.Progressbar(self.root, mode="determinate")
        self.progress.pack(fill="x", padx=10)

        self.progress_label = tk.Label(self.root, text="0 % | ETA: --:--")
        self.progress_label.pack(anchor="e", padx=10)

        # Start button
        tk.Button(
            self.root,
            text="Iniciar Render",
            command=self.start_render,
            bg="#4CAF50",
            fg="white",
            height=2
        ).pack(pady=10)

        # Log
        tk.Label(self.root, text="Log Blender").pack(anchor="w", padx=10)
        self.log = scrolledtext.ScrolledText(self.root, height=10, state="disabled")
        self.log.pack(fill="both", padx=10, pady=(0, 10), expand=True)

    def select_blender(self):
        path = filedialog.askopenfilename(filetypes=[("Blender", "blender.exe")])
        if path:
            self.blender_path.set(path)

    def select_output(self):
        path = filedialog.askdirectory()
        if path:
            self.output_path.set(path + "/")

    def add_blend_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Blender Files", "*.blend")])
        for f in files:
            if f not in self.blend_files:
                self.blend_files.append(f)
                self.listbox.insert(tk.END, f)

    def log_write(self, text):
        self.log.config(state="normal")
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)
        self.log.config(state="disabled")

    def start_render(self):
        if not self.blender_path.get() or not self.blend_files:
            messagebox.showerror("Error", "Faltan datos")
            return

        threading.Thread(target=self.render_batch, daemon=True).start()

    def get_frame_range(self, blend_file):
        """Detecta frame_start y frame_end usando Blender"""
        cmd = [
            self.blender_path.get(),
            blend_file,
            "-b",
            "--python-expr",
            "import bpy; print(f'FRAME_RANGE:{bpy.context.scene.frame_start}:{bpy.context.scene.frame_end}')"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if line.startswith("FRAME_RANGE"):
                _, start, end = line.split(":")
                return int(start), int(end)

        return 1, 1

    def render_batch(self):
        for blend in self.blend_files:
            self.log_write(f"▶ Analizando frames: {blend}")

            frame_start, frame_end = self.get_frame_range(blend)
            total_frames = frame_end - frame_start + 1

            self.progress["maximum"] = total_frames
            self.progress["value"] = 0

            self.log_write(f"Frames detectados: {frame_start} → {frame_end}")

            cmd = [
                self.blender_path.get(),
                blend,
                "-b",
                "-o", self.output_path.get(),
                "-F", "PNG",
                "-x", "1",
                "-a"
            ]

            start_time = time.time()
            frame_times = []

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            for line in process.stdout:
                self.log_write(line.strip())

                match = FRAME_REGEX.search(line)
                if match:
                    current_frame = int(match.group(1))
                    rendered = current_frame - frame_start + 1

                    now = time.time()
                    frame_times.append(now)
                    if len(frame_times) > 1:
                        avg = (frame_times[-1] - frame_times[0]) / (len(frame_times) - 1)
                        remaining = avg * (total_frames - rendered)
                        eta = time.strftime("%M:%S", time.gmtime(remaining))
                    else:
                        eta = "--:--"

                    percent = int((rendered / total_frames) * 100)

                    self.root.after(
                        0,
                        self.update_progress,
                        rendered,
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