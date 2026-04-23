from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录以访问此页面。'


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app) if hasattr(config[config_name], 'init_app') else None

    db.init_app(app)
    login_manager.init_app(app)

    from .blueprints.main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .blueprints.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .blueprints.problems import problems as problems_blueprint
    app.register_blueprint(problems_blueprint, url_prefix='/problems')

    from .blueprints.daily import daily as daily_blueprint
    app.register_blueprint(daily_blueprint, url_prefix='/daily')

    from .blueprints.admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin')

    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return User.query.get(int(user_id))

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    return app
