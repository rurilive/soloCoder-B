import re
import logging
import json
from datetime import datetime
from functools import wraps
from flask import abort, flash, redirect, url_for, request, current_app
from flask_login import current_user, login_required as flask_login_required

PERMISSION_VIEW = 1
PERMISSION_CREATE_SURVEY = 2
PERMISSION_EDIT_SURVEY = 4
PERMISSION_DELETE_SURVEY = 8
PERMISSION_VIEW_STATS = 16
PERMISSION_MANAGE_USERS = 32
PERMISSION_ADMIN = 64

ALL_PERMISSIONS = (
    PERMISSION_VIEW |
    PERMISSION_CREATE_SURVEY |
    PERMISSION_EDIT_SURVEY |
    PERMISSION_DELETE_SURVEY |
    PERMISSION_VIEW_STATS |
    PERMISSION_MANAGE_USERS |
    PERMISSION_ADMIN
)

login_required = flask_login_required

SECURITY_LOGGER = logging.getLogger('security')
SECURITY_LOGGER.setLevel(logging.INFO)

if not SECURITY_LOGGER.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    SECURITY_LOGGER.addHandler(handler)


class SecurityEvent:
    LOGIN_SUCCESS = 'login_success'
    LOGIN_FAILURE = 'login_failure'
    LOGOUT = 'logout'
    REGISTRATION = 'registration'
    REGISTRATION_FAILURE = 'registration_failure'
    SURVEY_CREATE = 'survey_create'
    SURVEY_EDIT = 'survey_edit'
    SURVEY_DELETE = 'survey_delete'
    SURVEY_SUBMIT = 'survey_submit'
    SETTINGS_CHANGE = 'settings_change'
    SUSPICIOUS_ACTIVITY = 'suspicious_activity'
    RATE_LIMIT_EXCEEDED = 'rate_limit_exceeded'
    CSRF_FAILURE = 'csrf_failure'


def log_security_event(event_type, message='', user_id=None, **kwargs):
    try:
        if not current_app.config.get('LOG_SECURITY_EVENTS', True):
            return
        
        log_data = {
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id or (current_user.id if current_user.is_authenticated else None),
            'remote_addr': request.remote_addr,
            'user_agent': request.user_agent.string if request.user_agent else None,
            'path': request.path,
            'method': request.method,
            'message': message,
        }
        log_data.update(kwargs)
        
        log_message = json.dumps(log_data, ensure_ascii=False, default=str)
        
        if event_type in [SecurityEvent.LOGIN_FAILURE, SecurityEvent.SUSPICIOUS_ACTIVITY, 
                          SecurityEvent.RATE_LIMIT_EXCEEDED, SecurityEvent.CSRF_FAILURE]:
            SECURITY_LOGGER.warning(log_message)
        elif event_type in [SecurityEvent.SURVEY_DELETE, SecurityEvent.SETTINGS_CHANGE]:
            SECURITY_LOGGER.warning(log_message)
        else:
            SECURITY_LOGGER.info(log_message)
    except Exception:
        pass


def validate_password_strength(password, min_length=None, require_complexity=None):
    if min_length is None:
        try:
            min_length = current_app.config.get('PASSWORD_MIN_LENGTH', 8)
        except RuntimeError:
            min_length = 8
    
    if require_complexity is None:
        try:
            require_complexity = current_app.config.get('PASSWORD_REQUIRE_COMPLEXITY', True)
        except RuntimeError:
            require_complexity = True
    
    errors = []
    
    if len(password) < min_length:
        errors.append(f'密码长度至少为 {min_length} 个字符')
    
    if require_complexity:
        has_upper = re.search(r'[A-Z]', password) is not None
        has_lower = re.search(r'[a-z]', password) is not None
        has_digit = re.search(r'\d', password) is not None
        has_special = re.search(r'[!@#$%^&*(),.?":{}|<>]', password) is not None
        
        complexity_score = sum([has_upper, has_lower, has_digit, has_special])
        
        if complexity_score < 3:
            errors.append('密码需要满足复杂度要求：至少包含大小写字母、数字、特殊字符中的三种')
    
    return len(errors) == 0, errors


def get_password_strength_message():
    try:
        min_length = current_app.config.get('PASSWORD_MIN_LENGTH', 8)
        require_complexity = current_app.config.get('PASSWORD_REQUIRE_COMPLEXITY', True)
    except RuntimeError:
        min_length = 8
        require_complexity = True
    
    if require_complexity:
        return f'密码长度至少 {min_length} 位，需包含大小写字母、数字、特殊字符中的三种'
    return f'密码长度至少 {min_length} 位'


def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                log_security_event(
                    SecurityEvent.SUSPICIOUS_ACTIVITY,
                    '未认证用户尝试访问需要权限的页面',
                    permission_required=permission
                )
                flash('请先登录', 'warning')
                return redirect(url_for('auth.login'))
            if not current_user.has_permission(permission):
                log_security_event(
                    SecurityEvent.SUSPICIOUS_ACTIVITY,
                    '用户尝试访问无权限的页面',
                    permission_required=permission
                )
                flash('您没有权限访问此页面', 'danger')
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.has_permission(PERMISSION_ADMIN):
            log_security_event(
                SecurityEvent.SUSPICIOUS_ACTIVITY,
                '用户尝试访问管理员页面'
            )
            flash('您没有管理员权限', 'danger')
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def survey_creator_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.has_permission(PERMISSION_CREATE_SURVEY):
            log_security_event(
                SecurityEvent.SUSPICIOUS_ACTIVITY,
                '用户尝试访问问卷创建页面'
            )
            flash('您没有创建问卷的权限', 'danger')
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
