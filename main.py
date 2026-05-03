from flask import Flask, render_template, request, jsonify
from PIL import Image
import io
import base64

app = Flask(__name__)

ASCII_CHARS = '@%#*+=-:. '

def scale_image(image, new_width=100):
    (original_width, original_height) = image.size
    aspect_ratio = original_height / float(original_width)
    new_height = int(aspect_ratio * new_width * 0.55)
    new_image = image.resize((new_width, new_height))
    return new_image

def grayify(image):
    return image.convert('L')

def pixels_to_ascii(image):
    pixels = image.getdata()
    characters = "".join([ASCII_CHARS[pixel // 25] for pixel in pixels])
    return characters

def image_to_ascii(image_data, width=100, invert=False):
    image = Image.open(io.BytesIO(image_data))
    new_image_data = scale_image(image, new_width=width)
    new_image_data = grayify(new_image_data)
    
    if invert:
        new_image_data = new_image_data.point(lambda p: 255 - p)
    
    pixels = pixels_to_ascii(new_image_data)
    len_pixels = len(pixels)
    ascii_image = "\n".join([pixels[index:(index + width)] for index in range(0, len_pixels, width)])
    return ascii_image

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    if 'image' not in request.files:
        return jsonify({'error': '没有上传图片'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    width = int(request.form.get('width', 100))
    invert = request.form.get('invert', 'false').lower() == 'true'
    
    try:
        image_data = file.read()
        ascii_art = image_to_ascii(image_data, width=width, invert=invert)
        return jsonify({'ascii_art': ascii_art})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=2222, debug=True)
