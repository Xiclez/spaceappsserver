from tkinter import Tk, filedialog, Canvas, Label, Button, Frame, Entry, IntVar, Checkbutton, Scrollbar
from tkinter import ttk
from PIL import Image, ImageTk
import numpy as np
from pydub import AudioSegment
import os
import cv2
import webbrowser
import threading
import sys

# Function to get the correct resource path, useful for bundling with PyInstaller
def resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller bundled app. """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Updated paths to use resource_path
AUDIO_FOLDER = resource_path(r"C:/POLARIS/piano")
DEFAULT_OUTPUT_FILENAME = "audio_coordenadas_estelares.mp3"

# Rutas de imagen predefinidas
PREDEFINED_IMAGES = [
    {"name": "Imagen 1", "path": resource_path(r"C:/POLARIS/photos/Imagen 1.jpg")},
    {"name": "Imagen 2", "path": resource_path(r"C:/POLARIS/photos/Imagen 2.jpeg")},
    {"name": "Imagen 3", "path": resource_path(r"C:/POLARIS/photos/Imagen 3.png")},
    {"name": "Imagen 4", "path": resource_path(r"C:/POLARIS/photos/Imagen 4.jpg")},
    {"name": "Imagen 5", "path": resource_path(r"C:/POLARIS/photos/Imagen 5.jpg")},
    {"name": "Imagen 6", "path": resource_path(r"C:/POLARIS/photos/Imagen 6.jpg")},
]

cancel_processing = False  # Indicador para cancelar el procesamiento

# (rest of your code remains unchanged)

# Example of using the resource_path for audio and image files
# ...



def map_to_scale(value, old_min, old_max, new_min, new_max):
    if old_max == old_min:
        return (new_min + new_max) / 2  # Valor por defecto en el medio del nuevo rango
    return new_min + (value - old_min) * (new_max - new_min) / (old_max - old_min)

def find_stars(image):
    min_area = 3  # Umbral mínimo de área para retener una estrella

    image_array = np.array(image.convert('RGB'))
    gray_image = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)

    _, thresholded = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresholded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    star_coords_filtered = []
    for contour in contours:
        if cv2.contourArea(contour) >= min_area:
            M = cv2.moments(contour)
            if M['m00'] != 0:
                cX = int(M['m10'] / M['m00'])
                cY = int(M['m01'] / M['m00'])
                star_coords_filtered.append((cY, cX))
                
                cv2.circle(image_array, (cX, cY), radius=2, color=(255, 0, 0), thickness=-1)

    star_detection_progress['value'] = 100
    return [{'x': int(x), 'y': int(y)} for y, x in star_coords_filtered], image_array

def create_audio_from_coordinates(coords, image_width, output_filename, max_stars, interval_between_starts):
    global cancel_processing
    if not coords:
        print("No se encontraron coordenadas.")
        return

    coords.sort(key=lambda coord: coord['x'])

    if max_stars is not None and len(coords) > max_stars:
        coords = coords[:max_stars]

    y_values = [coord['y'] for coord in coords]
    original_min_y = min(y_values)
    original_max_y = max(y_values)

    total_duration = (len(coords) - 1) * interval_between_starts + 1000  # Extra 1000ms para seguridad

    min_audio_duration = 10000  # 10 segundos en milisegundos

    if total_duration < min_audio_duration:
        total_duration = min_audio_duration

    base_audio = AudioSegment.silent(duration=total_duration)

    current_time = 0
    total_coords = len(coords)
    processed_coords = 0

    for coord in coords:
        if cancel_processing:
            print("Procesamiento de audio cancelado.")
            audio_processing_progress['value'] = 0
            return
        
        processed_coords += 1
        progress = (processed_coords / total_coords) * 100
        audio_processing_progress['value'] = progress
        root.update_idletasks()

        x = coord['x']
        y = coord['y']

        try:
            y_mapped = map_to_scale(y, original_min_y, original_max_y, 25, 75)
            x_mapped = map_to_scale(x, 0, image_width, 0, total_duration)
        except ValueError as e:
            print(f"Error al mapear x={x} o y={y}: {e}")
            continue

        if 25 <= y_mapped <= 75:
            file_name = os.path.join(AUDIO_FOLDER, f"{int(y_mapped)}.mp3")
            
            try:
                sound = AudioSegment.from_mp3(file_name)
                sound_duration = len(sound)  # Duración del archivo de sonido
                end_time = current_time + sound_duration

                if end_time > len(base_audio):
                    extra_duration = end_time - len(base_audio)
                    base_audio = base_audio + AudioSegment.silent(duration=extra_duration)

                print(f"Superponiendo {file_name} en la posición {current_time / 1000} segundos.")
                base_audio = base_audio.overlay(sound, position=int(current_time))
                current_time += interval_between_starts  # Mover current_time al inicio de la siguiente nota
            except FileNotFoundError:
                print(f"Archivo {file_name} no encontrado.")
    
    if base_audio.duration_seconds > 0:
        base_audio.export(output_filename, format="mp3")
        print(f"Audio guardado como: {output_filename}")
        audio_saved_label.config(bg="green", text="¡Audio guardado exitosamente!")
        open_audio_button.config(state="normal")
    else:
        print("No se generó audio.")
    
    audio_processing_progress['value'] = 100

def process_image(file_path=None):
    if not file_path:
        file_path = filedialog.askopenfilename(filetypes=[("Archivos de imagen", "*.png;*.jpg;*.jpeg;*.bmp")])
    if file_path:
        open_audio_button.config(state="disabled")
        audio_saved_label.config(bg="white", text="")

        image = Image.open(file_path)
        
        aspect_ratio = image.width / image.height
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        
        if aspect_ratio > 1:
            new_width = canvas_width
            new_height = int(new_width / aspect_ratio)
        else:
            new_height = canvas_height
            new_width = int(new_height * aspect_ratio)
        
        image = image.resize((new_width, new_height))
        image_width = image.size[0]
        image_height = image.size[1]
        
        tk_image = ImageTk.PhotoImage(image)
        canvas.config(scrollregion=canvas.bbox("all"))
        canvas.create_image(0, 0, anchor="nw", image=tk_image)
        canvas.image = tk_image

        star_detection_progress['value'] = 0
        audio_processing_progress['value'] = 0
        root.update_idletasks()
        
        coords, image_array = find_stars(image)
        
        image_with_dots = Image.fromarray(image_array)
        tk_image_with_dots = ImageTk.PhotoImage(image_with_dots)
        
        canvas.create_image(0, 0, anchor="nw", image=tk_image_with_dots)
        canvas.image = tk_image_with_dots

        global output_filename
        output_filename = DEFAULT_OUTPUT_FILENAME
        
        max_stars = None
        if limit_var.get():
            try:
                max_stars = int(limit_entry.get())
            except ValueError:
                print("Valor de límite no válido. Usando sin límite.")

        try:
            interval_between_starts = int(interval_entry.get())
        except ValueError:
            print("Valor de intervalo no válido. Usando el valor predeterminado de 350ms.")
            interval_between_starts = 350
        
        global cancel_processing
        cancel_processing = False
        threading.Thread(target=create_audio_from_coordinates, args=(coords, image_width, output_filename, max_stars, interval_between_starts)).start()

def open_predefined_image(image_path):
    process_image(image_path)

def open_audio_file():
    if os.path.isfile(DEFAULT_OUTPUT_FILENAME):
        webbrowser.open(f'file:///{os.path.abspath(DEFAULT_OUTPUT_FILENAME)}')
    else:
        print("El archivo de audio no existe.")

def cancel_audio_processing():
    global cancel_processing
    cancel_processing = True
    print("Cancelando procesamiento de audio...")
    
def open_flickr_album():
    webbrowser.open("https://www.flickr.com/photos/nasawebbtelescope/albums/")

root = Tk()
root.title("Reconocimiento de Coordenadas Estelares")
root.state('zoomed')

top_frame = Frame(root, padx=10, pady=10)
top_frame.pack(side="top", fill="x")

canvas_frame = Frame(root, padx=10, pady=10)
canvas_frame.pack(side="bottom", fill="both", expand=True)

canvas = Canvas(canvas_frame, bg="white")
canvas.pack(side="left", fill="both", expand=True)

scroll_y = Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
scroll_y.pack(side="right", fill="y")
scroll_x = Scrollbar(canvas_frame, orient="horizontal", command=canvas.xview)
scroll_x.pack(side="bottom", fill="x")

canvas.config(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

top_controls_frame = Frame(top_frame, padx=10, pady=10)
top_controls_frame.pack(side="top", fill="x")

file_frame = Frame(top_controls_frame, pady=5)
file_frame.pack(side="top", fill="x")

cancel_button = Button(file_frame, text="Cancelar", command=cancel_audio_processing, height=2, width=15, fg="white", bg="red")
cancel_button.pack(side="top", padx=5, pady=5)

limit_frame = Frame(top_controls_frame, pady=5)
limit_frame.pack(side="top", fill="x")

limit_var = IntVar()
limit_check = Checkbutton(limit_frame, text="Limitar Estrellas", variable=limit_var)
limit_check.pack(side="left")
limit_entry = Entry(limit_frame, width=10)
limit_entry.pack(side="left")

interval_frame = Frame(top_controls_frame, pady=5)
interval_frame.pack(side="top", fill="x")

Label(interval_frame, text="Intervalo entre notas (ms):").pack(side="left")
interval_entry = Entry(interval_frame, width=10)
interval_entry.pack(side="left")
interval_entry.insert(0, "350")

audio_saved_label = Label(top_controls_frame, text="", width=20, height=2)
audio_saved_label.pack(side="top")

star_detection_progress = ttk.Progressbar(top_controls_frame, orient="horizontal", length=300, mode="determinate")
star_detection_progress.pack(side="top", pady=0)

audio_processing_progress = ttk.Progressbar(top_controls_frame, orient="horizontal", length=300, mode="determinate")
audio_processing_progress.pack(side="top", pady=5)

open_audio_button = Button(top_controls_frame, text="Abrir Archivo de Audio", state="disabled", command=open_audio_file)
open_audio_button.pack(side="top", padx=5, pady=5)

link_frame = Frame(top_controls_frame, pady=5)
link_frame.pack(side="top", fill="x")

Label(link_frame, text="Encuentra y descarga más imágenes aquí:").pack(side="left", padx=5)
link_button = Button(link_frame, text="Haz clic aquí", command=open_flickr_album, fg="blue", cursor="hand2")
link_button.pack(side="left", padx=5)

upload_frame = Frame(top_controls_frame, pady=5)
upload_frame.pack(side="top", fill="x")

Label(upload_frame, text="Sube tu propia imagen aquí:").pack(side="left", padx=5)
Button(upload_frame, text="Subir Imagen", command=process_image, fg="blue", cursor="hand2").pack(side="left", padx=42, pady=5)

# Añadir sección de imágenes predefinidas
predefined_frame = Frame(top_controls_frame, pady=5)
predefined_frame.pack(side="top", fill="x")

Label(predefined_frame, text="Imágenes Precargadas:").pack(side="left")
for img in PREDEFINED_IMAGES:
    Button(predefined_frame, text=img['name'], command=lambda img_path=img['path']: open_predefined_image(img_path)).pack(side="left", padx=5)

root.mainloop()
