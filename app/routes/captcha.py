from flask import Blueprint, make_response, session
from app.utils.captcha import generate_captcha

captcha = Blueprint('captcha', __name__)


@captcha.route('/captcha/<string:token>')
def get_captcha(token):
    image_bytes, captcha_text = generate_captcha()
    
    session_key = f'captcha_{token}'
    session[session_key] = captcha_text
    session.modified = True
    
    response = make_response(image_bytes)
    response.headers['Content-Type'] = 'image/png'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response


def verify_captcha(token, user_input):
    session_key = f'captcha_{token}'
    stored_captcha = session.get(session_key)
    
    if stored_captcha is None:
        return False
    
    if session_key in session:
        del session[session_key]
        session.modified = True
    
    return stored_captcha.upper() == user_input.upper()
