import os
import numpy as np
from PIL import Image
from pydub import AudioSegment
import requests
from io import BytesIO
import cv2
import threading

# Definir la constante para el nombre del archivo de audio generado
DEFAULT_OUTPUT_FILENAME = "audio_coordenadas_estelares.mp3"
AUDIO_FOLDER = "../output"

# Definir la lista de URLs de imágenes
IMAGE_URLS = [
    "https://stsci-opo.org/STScI-01J7BVGEPR6BTSCGHRG8MM8GDJ.jpg",
    "https://stsci-opo.org/STScI-01J5E84FQE409A25RG9KCSSCRS.png",
    "https://stsci-opo.org/STScI-01J09ECGMXDT8TCQH19HQN9FZ2.jpg",
    "https://stsci-opo.org/STScI-01J06XZZCGVD7HBM57Y0D0PQ12.jpg",
    "https://stsci-opo.org/STScI-01J06ZFWJRYEWWC7DX59QVCKTC.jpg",
    "https://stsci-opo.org/STScI-01J0PA3WF4913VD555ZXMRXGA6.jpg",
    "https://stsci-opo.org/STScI-01J0709DWCQ62K2TWJ6RNRH9BY.jpg",
    "https://stsci-opo.org/STScI-01J070EA2WHYN4C1HNWW4JGAMD.jpg",
    "https://stsci-opo.org/STScI-01HYGF8985BWJWGT9DZ7WM9F62.png",
    "https://stsci-opo.org/STScI-01HYGK7ZHMKHSFAFS4X3T2883J.png",
    "https://stsci-opo.org/STScI-01HYGKZ738T2BKTF6426GC5TKE.png",
    "https://stsci-opo.org/STScI-01J04A5Z6KRTGC8K9B5R7SYK77.jpg",
    "https://stsci-opo.org/STScI-01HZME8S3F7D5TG8VSC61Y3QJY.png",
    "https://stsci-opo.org/STScI-01HZ0846ZKA69JAA217MPJZ9RV.png",
    "https://stsci-opo.org/STScI-01HTFYYGRMK3C2PRJ7GMHRQAMA.jpg",
    "https://stsci-opo.org/STScI-01HV4BFQCW7RZHQM563V9H1BVM.png",
    "https://stsci-opo.org/STScI-01HWDBWWT0SYNXXSETE5VD21QJ.jpg",
    "https://stsci-opo.org/STScI-01HRD3C2D0VJFYXXZTGPDPG49E.png",
    "https://stsci-opo.org/STScI-01HRD50Q449N2A4YQ9RN6EZKCX.png",
    "https://webbtelescope.org/files/live/sites/webb/files/home/resource-gallery/_images/wt-image-resources.jpg?t=tn1600"
]

def fetch_image_urls():
    """
    Devuelve la lista de URLs de las imágenes ya predefinidas.
    """
    if not IMAGE_URLS:
        print("No se encontraron URLs de imágenes.")
    return IMAGE_URLS


def download_image_from_url(url):
    """
    Descarga una imagen desde una URL y la carga en un objeto PIL Image.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Verificar que la petición fue exitosa
        img = Image.open(BytesIO(response.content))
        return img
    except requests.exceptions.RequestException as e:
        print(f"Error al descargar la imagen: {e}")
        return None


def find_stars(image):
    """
    Detecta las estrellas en la imagen, retornando las coordenadas de las mismas.
    """
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
    
    return [{'x': int(x), 'y': int(y)} for y, x in star_coords_filtered], image_array

def create_audio_from_coordinates(coords, image_width, output_filename, max_stars, interval_between_starts, update_progress, finish_callback):
    """
    Genera un archivo de audio a partir de las coordenadas de estrellas detectadas.
    """
    global cancel_processing
    if not coords:
        print("No se encontraron coordenadas.")
        return

    coords.sort(key=lambda coord: coord['x'])  # Ordenar coordenadas por el eje X

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
            update_progress(0)
            return
        
        processed_coords += 1
        progress = (processed_coords / total_coords) * 100
        update_progress(progress)

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
                sound_duration = len(sound)
                end_time = current_time + sound_duration

                if end_time > len(base_audio):
                    extra_duration = end_time - len(base_audio)
                    base_audio = base_audio + AudioSegment.silent(duration=extra_duration)

                print(f"Superponiendo {file_name} en la posición {current_time / 1000} segundos.")
                base_audio = base_audio.overlay(sound, position=int(current_time))
                current_time += interval_between_starts
            except FileNotFoundError:
                print(f"Archivo {file_name} no encontrado.")
    
    if base_audio.duration_seconds > 0:
        base_audio.export(output_filename, format="mp3")
        print(f"Audio guardado como: {output_filename}")
        finish_callback(True)
    else:
        print("No se generó audio.")
        finish_callback(False)
    
    update_progress(100)

def start_audio_creation(coords, image_width, output_filename, max_stars, interval_between_starts, update_progress, finish_callback):
    """
    Inicia la creación del archivo de audio en un nuevo hilo.
    """
    global cancel_processing
    cancel_processing = False
    threading.Thread(target=create_audio_from_coordinates, args=(
        coords, image_width, output_filename, max_stars, interval_between_starts, update_progress, finish_callback
    )).start()

def cancel_audio_processing():
    """
    Cancela el proceso de creación de audio.
    """
    global cancel_processing
    cancel_processing = True

def map_to_scale(value, old_min, old_max, new_min, new_max):
    """
    Mapea un valor de un rango antiguo a uno nuevo.
    """
    if old_max == old_min:
        return (new_min + new_max) / 2  # Valor por defecto en el medio del nuevo rango
    return new_min + (value - old_min) * (new_max - new_min) / (old_max - new_min)
