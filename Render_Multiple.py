import subprocess

# Ruta al ejecutable de Blender (ajustá según tu instalación)
BLENDER_PATH = r"F:\SteamLibrary\steamapps\common\Blender\blender.exe"

# Lista de archivos .blend a renderizar en orden
blend_files = [
    r"C:\Test\1.blend",
    r"C:\Test\2.blend",
    r"C:\Test\3.blend"
]

# Opciones de render (podés ajustar formato, carpeta de salida, etc.)
# -b (Carga en segundo plano Background)
# -o (Guarda en ruta perzonalizada remplazando la que contiene el archivo (debe contener una ruta el archivo))
# -F (Elige formato ejemplo PNG)
# -x (Numera los render empezando en 1)
# -a (animación completa)en cambio -f 1 (solo frame 1 o el que sea 25, 50, X)
render_options = ["-b", "-o", "C:/Test/", "-F", "PNG", "-x", "1", "-a"]

for blend in blend_files:
    print(f"Renderizando: {blend}")
    subprocess.run([BLENDER_PATH, blend] + render_options)
    print(f"Finalizado: {blend}")