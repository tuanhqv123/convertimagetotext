import os
import sys
import logging
from dotenv import load_dotenv
load_dotenv()  # Load environment variables

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from flask import Flask, render_template, request, jsonify, current_app
    from werkzeug.utils import secure_filename
    from PIL import Image
    import pytesseract
    import requests
    from io import BytesIO
    import cv2
    import numpy as np
    from flask_cors import CORS
except ImportError as e:
    logger.error(f"Error importing required modules: {e}")
    logger.error("Please install required packages using: pip install -r requirements.txt")
    sys.exit(1)

# Verify Tesseract installation and set path
tesseract_cmd = None
possible_paths = [
    '/opt/homebrew/bin/tesseract',
    '/usr/local/bin/tesseract',
    '/usr/bin/tesseract'
]

for path in possible_paths:
    if os.path.exists(path):
        tesseract_cmd = path
        break

if tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    logger.info(f"Using Tesseract from: {tesseract_cmd}")
else:
    logger.error("Tesseract not found. Please install it first.")
    sys.exit(1)

app = Flask(__name__)
CORS(app)  # Enable CORS
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}

# Đảm bảo thư mục uploads tồn tại
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Debug logging - chỉ log cho API endpoints
@app.before_request
def log_request_info():
    if not request.path.startswith('/static'):
        logger.info('Headers: %s', request.headers)
        logger.info('Body: %s', request.get_data())

@app.after_request
def log_response_info(response):
    if not request.path.startswith('/static'):
        try:
            logger.info('Response: %s', response.get_data())
        except:
            pass
    return response

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def preprocess_image(image):
    try:
        # Convert to numpy array
        img_array = np.array(image)
        
        # Convert to grayscale if needed
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array

        # Tăng kích thước ảnh
        scale_percent = 200  # Tăng gấp đôi kích thước
        width = int(gray.shape[1] * scale_percent / 100)
        height = int(gray.shape[0] * scale_percent / 100)
        gray = cv2.resize(gray, (width, height), interpolation=cv2.INTER_CUBIC)

        # Cải thiện độ tương phản
        gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)
        
        # Làm mịn ảnh
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # Áp dụng ngưỡng Otsu
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return Image.fromarray(binary)
    except Exception as e:
        logger.error(f"Image preprocessing error: {str(e)}")
        return image

def extract_text_from_image(image):
    try:
        # Chuyển sang RGB mode
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Xử lý ảnh
        processed_image = preprocess_image(image)
        
        # Cấu hình Tesseract tối ưu
        custom_config = r'''--oem 1 
            --psm 6 
            -l vie+eng 
            --dpi 300
            -c preserve_interword_spaces=1
            -c tessedit_do_invert=0
            -c textord_heavy_nr=1
            -c textord_min_linesize=3'''

        # Thực hiện OCR
        text = pytesseract.image_to_string(processed_image, config=custom_config)
        
        # Hậu xử lý text
        text = text.strip()
        text = '\n'.join(line.strip() for line in text.splitlines() if line.strip())
        text = text.replace('|', 'I').replace('[]','').replace('{}','')
        
        return text if text else "Không tìm thấy chữ trong ảnh"

    except Exception as e:
        logger.error(f"OCR Error: {str(e)}")
        return f"Lỗi xử lý ảnh: {str(e)}"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/extract', methods=['POST'])
def extract_text():
    try:
        # Handle file upload
        if 'file' in request.files:
            file = request.files['file']
            if not file:
                return jsonify({'error': 'No file uploaded'})
            
            # Process image file
            image = Image.open(file)
            
        # Handle URL input
        elif 'image_url' in request.form:
            url = request.form['image_url']
            if not url:
                return jsonify({'error': 'No URL provided'})
                
            # Download and process image from URL
            response = requests.get(url)
            image = Image.open(BytesIO(response.content))
            
        else:
            return jsonify({'error': 'No image provided'})

        # Extract text from image
        text = extract_text_from_image(image)
        return jsonify({'text': text})

    except Exception as e:
        print(f"Error: {str(e)}")  # For debugging
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    try:
        app.run(debug=True, port=5000)
    except Exception as e:
        print(f"Error starting the application: {str(e)}")
