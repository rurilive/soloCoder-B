from flask import Flask, request, g
from app.config import config
from app.extensions import init_extensions, login_manager, db, limiter
from flask_wtf.csrf import CSRFError


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    init_extensions(app)
    
    from app.models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    @app.before_request
    def before_request_handler():
        g.start_time = None
    
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = app.config.get('SECURITY_CONTENT_TYPE_OPTIONS', 'nosniff')
        response.headers['X-Frame-Options'] = app.config.get('SECURITY_FRAME_OPTIONS', 'SAMEORIGIN')
        response.headers['X-XSS-Protection'] = app.config.get('SECURITY_XSS_PROTECTION', '1; mode=block')
        
        referrer_policy = app.config.get('SECURITY_REFERRER_POLICY', 'strict-origin-when-cross-origin')
        response.headers['Referrer-Policy'] = referrer_policy
        
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        return response
    
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        from app.utils.security import log_security_event, SecurityEvent
        log_security_event(
            SecurityEvent.CSRF_FAILURE,
            f'CSRF 验证失败: {str(e)}',
            endpoint=request.endpoint
        )
        from flask import flash, redirect, url_for
        flash('表单已过期，请重试', 'danger')
        return redirect(request.referrer or url_for('main.index'))
    
    @app.errorhandler(429)
    def handle_rate_limit_exceeded(e):
        from app.utils.security import log_security_event, SecurityEvent
        from flask import request, jsonify, render_template, make_response
        
        log_security_event(
            SecurityEvent.RATE_LIMIT_EXCEEDED,
            f'请求频率超限: {e.description}',
            endpoint=request.endpoint
        )
        
        if request.is_json or request.path.startswith('/api/'):
            response = jsonify({
                'success': False,
                'error': '请求过于频繁，请稍后再试'
            })
            response.status_code = 429
            return response
        
        from flask import flash, redirect, url_for
        flash('请求过于频繁，请稍后再试', 'danger')
        response = make_response(redirect(request.referrer or url_for('main.index')))
        response.status_code = 429
        return response
    
    from app.routes.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)
    
    from app.routes.main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    from app.routes.survey import survey as survey_blueprint
    app.register_blueprint(survey_blueprint)
    
    from app.routes.editor import editor as editor_blueprint
    app.register_blueprint(editor_blueprint)
    
    from app.routes.response import response as response_blueprint
    app.register_blueprint(response_blueprint)
    
    from app.routes.captcha import captcha as captcha_blueprint
    app.register_blueprint(captcha_blueprint)
    
    from app.routes.stats import stats as stats_blueprint
    app.register_blueprint(stats_blueprint)
    
    return app
