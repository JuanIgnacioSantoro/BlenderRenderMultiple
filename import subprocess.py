import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

class BlenderBatchGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Blender Batch Renderer")
        self.root.geometry("700x550")

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
        tk.Label(self.root, text="Progreso").pack(anchor="w", padx=10, pady=(10, 0))
        self.progress = ttk.Progressbar(self.root, length=400, mode="determinate")
        self.progress.pack(padx=10, fill="x")

        self.progress_label = tk.Label(self.root, text="0 %")
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

        # Log output
        tk.Label(self.root, text="Log").pack(anchor="w", padx=10)
        self.log = scrolledtext.ScrolledText(self.root, height=8, state="disabled")
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
        if not self.blender_path.get():
            messagebox.showerror("Error", "Seleccioná Blender.exe")
            return
        if not self.blend_files:
            messagebox.showerror("Error", "Agregá al menos un archivo .blend")
            return

        self.progress["value"] = 0
        self.progress["maximum"] = len(self.blend_files)
        self.progress_label.config(text="0 %")

        threading.Thread(target=self.render_batch, daemon=True).start()

    def render_batch(self):
        render_options = [
            "-b",
            "-o", self.output_path.get(),
            "-F", "PNG",
            "-x", "1",
            "-a"
        ]

        total = len(self.blend_files)

        for index, blend in enumerate(self.blend_files, start=1):
            self.log_write(f"▶ Renderizando: {blend}")

            try:
                subprocess.run(
                    [self.blender_path.get(), blend] + render_options,
                    check=True
                )
                self.log_write(f"✔ Finalizado: {blend}")
            except subprocess.CalledProcessError:
                self.log_write(f"✖ Error renderizando: {blend}")

            # Actualizar progreso real
            progress_value = index
            percent = int((progress_value / total) * 100)

            self.root.after(0, self.update_progress, progress_value, percent)

        self.log_write("🎉 Render batch completado")

    def update_progress(self, value, percent):
        self.progress["value"] = value
        self.progress_label.config(text=f"{percent} %")

if __name__ == "__main__":
    root = tk.Tk()
    app = BlenderBatchGUI(root)
    root.mainloop()