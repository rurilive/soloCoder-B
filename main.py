from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from PIL import Image
import io
import base64
from functools import wraps
from user_manager import user_manager

app = Flask(__name__)
app.secret_key = 'solo_coder_secret_key_2024'

ASCII_CHARS = '@%#*+=-:. '


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return jsonify({'error': '请先登录', 'login_required': True}), 401
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return jsonify({'error': '请先登录', 'login_required': True}), 401
        user = user_manager.get_user(session['username'])
        if not user or not user.get('is_admin', False):
            return jsonify({'error': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return decorated_function

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
    if 'username' in session:
        return render_template('index.html')
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or request.form
    username = data.get('username', '')
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'success': False, 'error': '用户名和密码不能为空'})
    
    if user_manager.verify_password(username, password):
        session['username'] = username
        user = user_manager.get_user(username)
        return jsonify({
            'success': True,
            'username': username,
            'is_admin': user.get('is_admin', False),
            'usage_count': user.get('usage_count', 0),
            'usage_limit': user.get('usage_limit', 0)
        })
    
    return jsonify({'success': False, 'error': '用户名或密码错误'})


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


@app.route('/api/user/info')
@login_required
def user_info():
    user = user_manager.get_user(session['username'])
    return jsonify({
        'username': session['username'],
        'is_admin': user.get('is_admin', False),
        'usage_count': user.get('usage_count', 0),
        'usage_limit': user.get('usage_limit', 0)
    })


@app.route('/api/users')
@admin_required
def get_users():
    users = user_manager.get_all_users()
    result = []
    for username, user_data in users.items():
        result.append({
            'username': username,
            'is_admin': user_data.get('is_admin', False),
            'usage_count': user_data.get('usage_count', 0),
            'usage_limit': user_data.get('usage_limit', 0)
        })
    return jsonify({'success': True, 'users': result})


@app.route('/api/users', methods=['POST'])
@admin_required
def create_user():
    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')
    is_admin = data.get('is_admin', False)
    usage_limit = data.get('usage_limit', 10)
    
    if not username or not password:
        return jsonify({'success': False, 'error': '用户名和密码不能为空'})
    
    if user_manager.create_user(username, password, is_admin, usage_limit):
        return jsonify({'success': True, 'message': '用户创建成功'})
    
    return jsonify({'success': False, 'error': '用户名已存在'})


@app.route('/api/users/<username>', methods=['PUT'])
@admin_required
def update_user(username):
    data = request.get_json()
    password = data.get('password')
    usage_limit = data.get('usage_limit')
    is_admin = data.get('is_admin')
    
    if user_manager.update_user(username, password, usage_limit, is_admin):
        return jsonify({'success': True, 'message': '用户更新成功'})
    
    return jsonify({'success': False, 'error': '用户不存在'})


@app.route('/api/users/<username>', methods=['DELETE'])
@admin_required
def delete_user(username):
    if username == session.get('username'):
        return jsonify({'success': False, 'error': '不能删除自己'})
    
    if user_manager.delete_user(username):
        return jsonify({'success': True, 'message': '用户删除成功'})
    
    return jsonify({'success': False, 'error': '用户不存在或无法删除'})


@app.route('/convert', methods=['POST'])
@login_required
def convert():
    if not user_manager.check_usage_limit(session['username']):
        user = user_manager.get_user(session['username'])
        return jsonify({
            'error': f'使用次数已达上限 (已使用 {user.get("usage_count", 0)} 次)',
            'usage_exceeded': True
        }), 403
    
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
        
        user_manager.increment_usage(session['username'])
        user = user_manager.get_user(session['username'])
        
        return jsonify({
            'ascii_art': ascii_art,
            'usage_count': user.get('usage_count', 0),
            'usage_limit': user.get('usage_limit', 0)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin')
@admin_required
def admin_page():
    return render_template('admin.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=2223, debug=True)
