from flask import Flask, jsonify, request, send_file
from controllers.controller import find_stars, fetch_image_urls, download_image_from_url, start_audio_creation, cancel_audio_processing, IMAGE_URLS, DEFAULT_OUTPUT_FILENAME

app = Flask(__name__)

# Ruta para procesar las imágenes de la web
@app.route('/api/process-image', methods=['GET'])
def process_image():
    # Llamar a la función que obtiene todas las imágenes .png
    fetch_image_urls()
    if IMAGE_URLS:
        response = {
            'status': 'success',
            'images': {i: url for i, url in enumerate(IMAGE_URLS)}  # Asignar índice a cada imagen
        }
        return jsonify(response)
    return jsonify({'status': 'error', 'message': 'No se encontraron imágenes'}), 404

# Ruta para crear audio desde la imagen seleccionada
@app.route('/api/create-audio', methods=['POST'])
def create_audio():
    data = request.json
    index = data.get('index')

    if index is not None and 0 <= index < len(IMAGE_URLS):
        image_url = IMAGE_URLS[index]
        image = download_image_from_url(image_url)
        
        if image:
            coords, _ = find_stars(image)
            max_stars = data.get('maxStars')
            interval = data.get('interval', 350)

            # Llamar la lógica para crear el audio a partir de las coordenadas
            start_audio_creation(coords, image.width, DEFAULT_OUTPUT_FILENAME, max_stars, interval, lambda p: None, lambda s: None)
            return jsonify({'status': 'success', 'message': f'Audio generado para la imagen {index}'})
        else:
            return jsonify({'status': 'error', 'message': 'No se pudo descargar la imagen'}), 400
    return jsonify({'status': 'error', 'message': 'Índice inválido'}), 400

# Ruta para descargar el audio generado
@app.route('/api/download-audio', methods=['GET'])
def download_audio():
    return send_file(DEFAULT_OUTPUT_FILENAME, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
