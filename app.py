import os
import random
import socket
import re
import json
from functools import wraps
from datetime import datetime, date, time, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from models import db, User, Restaurant, Table, Reservation

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurant.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'
login_manager.login_message = '请先登录'

BOOKING_CODE_PATTERN = re.compile(r'^[A-Z]{2}\d{6}$')
DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')
TIME_PATTERN = re.compile(r'^\d{2}:\d{2}$')

def is_valid_booking_code(code):
    if not code:
        return False
    return bool(BOOKING_CODE_PATTERN.match(code))

def is_valid_date(date_str):
    if not date_str or not DATE_PATTERN.match(date_str):
        return False
    try:
        datetime.strptime(date_str, '%Y-%m-%d').date()
        return True
    except ValueError:
        return False

def is_valid_time(time_str):
    if not time_str or not TIME_PATTERN.match(time_str):
        return False
    try:
        datetime.strptime(time_str, '%H:%M').time()
        return True
    except ValueError:
        return False

def safe_parse_int(value, default=0, min_val=None, max_val=None):
    try:
        num = int(value)
        if min_val is not None and num < min_val:
            return default
        if max_val is not None and num > max_val:
            return default
        return num
    except (TypeError, ValueError):
        return default

def safe_parse_recommendations(data_str):
    if not data_str:
        return None
    try:
        if data_str.startswith('{'):
            return json.loads(data_str)
        else:
            return None
    except json.JSONDecodeError:
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(safe_parse_int(user_id, default=0))

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('您没有权限执行此操作', 'danger')
            return redirect(url_for('admin_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def store_manager_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin and not current_user.is_store_manager:
            flash('您没有权限执行此操作', 'danger')
            return redirect(url_for('admin_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def can_manage_restaurant(restaurant_id):
    if current_user.is_admin:
        return True
    if current_user.is_store_manager:
        return current_user.manages_restaurant(restaurant_id)
    return False

def get_available_tables(restaurant_id, reservation_date, start_time, end_time, guest_count=None):
    restaurant = Restaurant.query.get(restaurant_id)
    if not restaurant:
        return []
    
    tables = Table.query.filter_by(restaurant_id=restaurant_id, is_active=True).all()
    
    if guest_count:
        tables = [t for t in tables if t.capacity >= guest_count]
    
    available_tables = []
    for table in tables:
        if table.is_available(reservation_date, start_time, end_time):
            available_tables.append(table)
    
    return available_tables

def get_time_slots(restaurant_id, reservation_date):
    restaurant = Restaurant.query.get(restaurant_id)
    if not restaurant:
        return []
    
    slots = []
    current_time = restaurant.open_time
    close_time = restaurant.close_time
    
    while current_time < close_time:
        slots.append(current_time)
        current_dt = datetime.combine(date.today(), current_time)
        next_dt = current_dt + timedelta(hours=1)
        current_time = next_dt.time()
    
    return slots

@app.route('/')
def index():
    restaurants = Restaurant.query.all()
    return render_template('index.html', restaurants=restaurants, today=date.today())

@app.route('/restaurant/<int:restaurant_id>')
def restaurant_detail(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    return render_template('restaurant_detail.html', restaurant=restaurant, today=date.today())

@app.route('/restaurant/<int:restaurant_id>/availability', methods=['GET', 'POST'])
def check_availability(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    
    if request.method == 'POST':
        reservation_date_str = request.form.get('reservation_date')
        start_time_str = request.form.get('start_time')
        guest_count_raw = request.form.get('guest_count', '1')
        
        errors = []
        
        if not reservation_date_str or not is_valid_date(reservation_date_str):
            errors.append('请选择有效的日期')
        
        if not start_time_str or not is_valid_time(start_time_str):
            errors.append('请选择有效的时间')
        
        guest_count = safe_parse_int(guest_count_raw, default=1, min_val=1, max_val=20)
        if guest_count < 1:
            errors.append('用餐人数至少为1人')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return redirect(url_for('check_availability', restaurant_id=restaurant_id))
        
        try:
            reservation_date = datetime.strptime(reservation_date_str, '%Y-%m-%d').date()
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
        except ValueError:
            flash('日期或时间格式错误', 'danger')
            return redirect(url_for('check_availability', restaurant_id=restaurant_id))
        
        end_dt = datetime.combine(reservation_date, start_time) + timedelta(hours=2)
        end_time = end_dt.time()
        
        available_tables = get_available_tables(
            restaurant_id, 
            reservation_date, 
            start_time, 
            end_time,
            guest_count
        )
        
        return render_template('availability.html', 
                               restaurant=restaurant,
                               reservation_date=reservation_date,
                               start_time=start_time,
                               end_time=end_time,
                               guest_count=guest_count,
                               available_tables=available_tables)
    
    time_slots = get_time_slots(restaurant_id, date.today())
    return render_template('check_availability.html', 
                           restaurant=restaurant, 
                           time_slots=time_slots,
                           today=date.today())

@app.route('/restaurant/<int:restaurant_id>/reserve', methods=['POST'])
def make_reservation(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    
    table_id_raw = request.form.get('table_id')
    customer_name = request.form.get('customer_name', '').strip()
    customer_phone = request.form.get('customer_phone', '').strip()
    customer_email = request.form.get('customer_email', '').strip()
    guest_count_raw = request.form.get('guest_count', '1')
    reservation_date_str = request.form.get('reservation_date')
    start_time_str = request.form.get('start_time')
    end_time_str = request.form.get('end_time')
    notes = request.form.get('notes', '').strip()
    
    errors = []
    
    table_id = safe_parse_int(table_id_raw, default=0, min_val=1)
    if table_id < 1:
        errors.append('请选择有效的餐桌')
    
    if not customer_name or len(customer_name) < 1 or len(customer_name) > 100:
        errors.append('请输入有效的姓名（1-100字符）')
    
    if not customer_phone or len(customer_phone) < 5 or len(customer_phone) > 20:
        errors.append('请输入有效的联系电话（5-20字符）')
    
    guest_count = safe_parse_int(guest_count_raw, default=0, min_val=1, max_val=20)
    if guest_count < 1:
        errors.append('用餐人数至少为1人')
    
    if not reservation_date_str or not is_valid_date(reservation_date_str):
        errors.append('请选择有效的日期')
    
    if not start_time_str or not is_valid_time(start_time_str):
        errors.append('请选择有效的开始时间')
    
    if not end_time_str or not is_valid_time(end_time_str):
        errors.append('请选择有效的结束时间')
    
    if customer_email and '@' not in customer_email:
        errors.append('电子邮箱格式无效')
    
    if len(notes) > 500:
        errors.append('备注不能超过500字符')
    
    if errors:
        for error in errors:
            flash(error, 'danger')
        return redirect(url_for('check_availability', restaurant_id=restaurant_id))
    
    try:
        reservation_date = datetime.strptime(reservation_date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
    except ValueError:
        flash('日期或时间格式错误', 'danger')
        return redirect(url_for('check_availability', restaurant_id=restaurant_id))
    
    table = Table.query.get(table_id)
    if not table or table.restaurant_id != restaurant_id:
        flash('餐桌不存在', 'danger')
        return redirect(url_for('check_availability', restaurant_id=restaurant_id))
    
    if not table.is_active:
        flash('该餐桌已停用', 'danger')
        return redirect(url_for('check_availability', restaurant_id=restaurant_id))
    
    if guest_count > table.capacity:
        flash('用餐人数超过餐桌容量', 'danger')
        return redirect(url_for('check_availability', restaurant_id=restaurant_id))
    
    if not table.is_available(reservation_date, start_time, end_time):
        flash('该时间段已被预订，请选择其他时间', 'danger')
        return redirect(url_for('check_availability', restaurant_id=restaurant_id))
    
    booking_code = Reservation.generate_booking_code()
    while Reservation.query.filter_by(booking_code=booking_code).first():
        booking_code = Reservation.generate_booking_code()
    
    reservation = Reservation(
        table_id=table_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_email=customer_email,
        guest_count=guest_count,
        reservation_date=reservation_date,
        start_time=start_time,
        end_time=end_time,
        notes=notes,
        status='pending',
        booking_code=booking_code
    )
    
    db.session.add(reservation)
    db.session.commit()
    
    flash('预订成功！我们将尽快与您确认。', 'success')
    return render_template('reservation_success.html', 
                           reservation=reservation, 
                           restaurant=restaurant)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or len(username) < 1 or len(username) > 80:
            flash('请输入有效的用户名', 'danger')
            return redirect(url_for('admin_login'))
        
        if not password or len(password) < 1:
            flash('请输入密码', 'danger')
            return redirect(url_for('admin_login'))
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('登录成功', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('用户名或密码错误', 'danger')
    
    return render_template('admin/login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    flash('已退出登录', 'info')
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin_dashboard():
    today = date.today()
    
    if current_user.is_admin:
        today_reservations = Reservation.query.filter(
            Reservation.reservation_date == today
        ).order_by(Reservation.start_time).all()
        
        pending_reservations = Reservation.query.filter_by(
            status='pending'
        ).order_by(Reservation.created_at).all()
        
        total_tables = Table.query.filter_by(is_active=True).count()
        total_restaurants = Restaurant.query.count()
    else:
        managed_restaurants = current_user.get_managed_restaurants()
        managed_restaurant_ids = [r.id for r in managed_restaurants]
        
        today_reservations = Reservation.query.join(Table).filter(
            Reservation.reservation_date == today,
            Table.restaurant_id.in_(managed_restaurant_ids)
        ).order_by(Reservation.start_time).all()
        
        pending_reservations = Reservation.query.join(Table).filter(
            Reservation.status == 'pending',
            Table.restaurant_id.in_(managed_restaurant_ids)
        ).order_by(Reservation.created_at).all()
        
        total_tables = Table.query.filter(
            Table.is_active == True,
            Table.restaurant_id.in_(managed_restaurant_ids)
        ).count()
        total_restaurants = len(managed_restaurants)
    
    return render_template('admin/dashboard.html',
                           today_reservations=today_reservations,
                           pending_reservations=pending_reservations,
                           total_tables=total_tables,
                           total_restaurants=total_restaurants,
                           today=today)

@app.route('/admin/restaurants')
@login_required
def admin_restaurants():
    if current_user.is_admin:
        restaurants = Restaurant.query.all()
    else:
        restaurants = current_user.get_managed_restaurants()
    return render_template('admin/restaurants.html', restaurants=restaurants)

@app.route('/admin/restaurant/add', methods=['GET', 'POST'])
@admin_required
def add_restaurant():
    store_managers = User.query.filter_by(is_store_manager=True).all()
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        address = request.form.get('address', '').strip()
        phone = request.form.get('phone', '').strip()
        description = request.form.get('description', '').strip()
        open_time_str = request.form.get('open_time')
        close_time_str = request.form.get('close_time')
        store_manager_id_raw = request.form.get('store_manager_id')
        
        errors = []
        
        if not name or len(name) < 1 or len(name) > 100:
            errors.append('餐厅名称必须在1-100字符之间')
        
        if not open_time_str or not is_valid_time(open_time_str):
            errors.append('请输入有效的开门时间')
        
        if not close_time_str or not is_valid_time(close_time_str):
            errors.append('请输入有效的关门时间')
        
        if phone and len(phone) > 20:
            errors.append('电话不能超过20字符')
        
        if address and len(address) > 200:
            errors.append('地址不能超过200字符')
        
        if description and len(description) > 1000:
            errors.append('描述不能超过1000字符')
        
        store_manager_id = safe_parse_int(store_manager_id_raw, default=None)
        if store_manager_id is not None:
            store_manager = User.query.get(store_manager_id)
            if not store_manager or not store_manager.is_store_manager:
                errors.append('请选择有效的店长')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return redirect(url_for('add_restaurant'))
        
        try:
            open_time = datetime.strptime(open_time_str, '%H:%M').time()
            close_time = datetime.strptime(close_time_str, '%H:%M').time()
        except ValueError:
            flash('时间格式错误', 'danger')
            return redirect(url_for('add_restaurant'))
        
        restaurant = Restaurant(
            name=name,
            address=address,
            phone=phone,
            description=description,
            open_time=open_time,
            close_time=close_time,
            store_manager_id=store_manager_id
        )
        
        db.session.add(restaurant)
        db.session.commit()
        
        flash('餐厅添加成功', 'success')
        return redirect(url_for('admin_restaurants'))
    
    return render_template('admin/restaurant_form.html', restaurant=None, store_managers=store_managers)

@app.route('/admin/restaurant/<int:restaurant_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    
    if not can_manage_restaurant(restaurant_id):
        flash('您没有权限管理此餐厅', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    store_managers = User.query.filter_by(is_store_manager=True).all() if current_user.is_admin else []
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        address = request.form.get('address', '').strip()
        phone = request.form.get('phone', '').strip()
        description = request.form.get('description', '').strip()
        open_time_str = request.form.get('open_time')
        close_time_str = request.form.get('close_time')
        
        errors = []
        
        if not name or len(name) < 1 or len(name) > 100:
            errors.append('餐厅名称必须在1-100字符之间')
        
        if not open_time_str or not is_valid_time(open_time_str):
            errors.append('请输入有效的开门时间')
        
        if not close_time_str or not is_valid_time(close_time_str):
            errors.append('请输入有效的关门时间')
        
        if phone and len(phone) > 20:
            errors.append('电话不能超过20字符')
        
        if address and len(address) > 200:
            errors.append('地址不能超过200字符')
        
        if description and len(description) > 1000:
            errors.append('描述不能超过1000字符')
        
        if current_user.is_admin:
            store_manager_id_raw = request.form.get('store_manager_id')
            store_manager_id = safe_parse_int(store_manager_id_raw, default=None)
            if store_manager_id is not None:
                store_manager = User.query.get(store_manager_id)
                if not store_manager or not store_manager.is_store_manager:
                    errors.append('请选择有效的店长')
        else:
            store_manager_id = restaurant.store_manager_id
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return redirect(url_for('edit_restaurant', restaurant_id=restaurant_id))
        
        try:
            open_time = datetime.strptime(open_time_str, '%H:%M').time()
            close_time = datetime.strptime(close_time_str, '%H:%M').time()
        except ValueError:
            flash('时间格式错误', 'danger')
            return redirect(url_for('edit_restaurant', restaurant_id=restaurant_id))
        
        restaurant.name = name
        restaurant.address = address
        restaurant.phone = phone
        restaurant.description = description
        restaurant.open_time = open_time
        restaurant.close_time = close_time
        
        if current_user.is_admin:
            restaurant.store_manager_id = store_manager_id
        
        db.session.commit()
        flash('餐厅信息已更新', 'success')
        return redirect(url_for('admin_restaurants'))
    
    return render_template('admin/restaurant_form.html', restaurant=restaurant, store_managers=store_managers)

@app.route('/admin/restaurant/<int:restaurant_id>/delete', methods=['POST'])
@admin_required
def delete_restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    
    db.session.delete(restaurant)
    db.session.commit()
    
    flash('餐厅已删除', 'success')
    return redirect(url_for('admin_restaurants'))

@app.route('/admin/tables')
@login_required
def admin_tables():
    restaurant_id = request.args.get('restaurant_id', type=int)
    
    if current_user.is_admin:
        restaurants = Restaurant.query.all()
    else:
        restaurants = current_user.get_managed_restaurants()
    
    managed_restaurant_ids = [r.id for r in restaurants]
    
    if restaurant_id:
        if not current_user.is_admin and restaurant_id not in managed_restaurant_ids:
            flash('您没有权限查看此餐厅的餐桌', 'danger')
            return redirect(url_for('admin_tables'))
        
        tables = Table.query.filter_by(restaurant_id=restaurant_id).all()
        restaurant = Restaurant.query.get(restaurant_id)
    else:
        if current_user.is_admin:
            tables = Table.query.all()
        else:
            tables = Table.query.filter(Table.restaurant_id.in_(managed_restaurant_ids)).all()
        restaurant = None
    
    return render_template('admin/tables.html', 
                           tables=tables, 
                           restaurants=restaurants, 
                           selected_restaurant=restaurant)

@app.route('/admin/table/add', methods=['GET', 'POST'])
@login_required
def add_table():
    if current_user.is_admin:
        restaurants = Restaurant.query.all()
    else:
        restaurants = current_user.get_managed_restaurants()
    
    if not restaurants:
        flash('没有可管理的餐厅', 'danger')
        return redirect(url_for('admin_tables'))
    
    if request.method == 'POST':
        restaurant_id_raw = request.form.get('restaurant_id')
        table_number_raw = request.form.get('table_number')
        capacity_raw = request.form.get('capacity')
        
        errors = []
        
        restaurant_id = safe_parse_int(restaurant_id_raw, default=0, min_val=1)
        if restaurant_id < 1:
            errors.append('请选择有效的餐厅')
        
        if not current_user.is_admin:
            managed_ids = [r.id for r in restaurants]
            if restaurant_id not in managed_ids:
                errors.append('您没有权限管理此餐厅')
        
        table_number = safe_parse_int(table_number_raw, default=0, min_val=1)
        if table_number < 1:
            errors.append('桌号必须大于0')
        
        capacity = safe_parse_int(capacity_raw, default=0, min_val=1, max_val=50)
        if capacity < 1:
            errors.append('容量必须大于0')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return redirect(url_for('add_table'))
        
        restaurant = Restaurant.query.get(restaurant_id)
        if not restaurant:
            flash('餐厅不存在', 'danger')
            return redirect(url_for('add_table'))
        
        existing = Table.query.filter_by(
            restaurant_id=restaurant_id, 
            table_number=table_number
        ).first()
        
        if existing:
            flash('该桌号已存在', 'danger')
            return redirect(url_for('add_table'))
        
        table = Table(
            restaurant_id=restaurant_id,
            table_number=table_number,
            capacity=capacity
        )
        
        db.session.add(table)
        db.session.commit()
        
        flash('餐桌添加成功', 'success')
        return redirect(url_for('admin_tables', restaurant_id=restaurant_id))
    
    return render_template('admin/table_form.html', table=None, restaurants=restaurants)

@app.route('/admin/table/<int:table_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_table(table_id):
    table = Table.query.get_or_404(table_id)
    
    if not can_manage_restaurant(table.restaurant_id):
        flash('您没有权限管理此餐桌', 'danger')
        return redirect(url_for('admin_tables'))
    
    if current_user.is_admin:
        restaurants = Restaurant.query.all()
    else:
        restaurants = current_user.get_managed_restaurants()
    
    if request.method == 'POST':
        table_number_raw = request.form.get('table_number')
        capacity_raw = request.form.get('capacity')
        is_active = request.form.get('is_active') == 'on'
        
        errors = []
        
        table_number = safe_parse_int(table_number_raw, default=0, min_val=1)
        if table_number < 1:
            errors.append('桌号必须大于0')
        
        capacity = safe_parse_int(capacity_raw, default=0, min_val=1, max_val=50)
        if capacity < 1:
            errors.append('容量必须大于0')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return redirect(url_for('edit_table', table_id=table_id))
        
        if table_number != table.table_number:
            existing = Table.query.filter_by(
                restaurant_id=table.restaurant_id, 
                table_number=table_number
            ).first()
            if existing:
                flash('该桌号已存在', 'danger')
                return redirect(url_for('edit_table', table_id=table_id))
        
        table.table_number = table_number
        table.capacity = capacity
        table.is_active = is_active
        
        db.session.commit()
        flash('餐桌信息已更新', 'success')
        return redirect(url_for('admin_tables', restaurant_id=table.restaurant_id))
    
    return render_template('admin/table_form.html', table=table, restaurants=restaurants)

@app.route('/admin/table/<int:table_id>/delete', methods=['POST'])
@login_required
def delete_table(table_id):
    table = Table.query.get_or_404(table_id)
    
    if not can_manage_restaurant(table.restaurant_id):
        flash('您没有权限管理此餐桌', 'danger')
        return redirect(url_for('admin_tables'))
    
    restaurant_id = table.restaurant_id
    
    db.session.delete(table)
    db.session.commit()
    
    flash('餐桌已删除', 'success')
    return redirect(url_for('admin_tables', restaurant_id=restaurant_id))

@app.route('/admin/reservations')
@login_required
def admin_reservations():
    status = request.args.get('status')
    restaurant_id = request.args.get('restaurant_id', type=int)
    date_str = request.args.get('date')
    
    if current_user.is_admin:
        restaurants = Restaurant.query.all()
    else:
        restaurants = current_user.get_managed_restaurants()
    
    managed_restaurant_ids = [r.id for r in restaurants]
    
    query = Reservation.query.join(Table)
    
    if not current_user.is_admin:
        query = query.filter(Table.restaurant_id.in_(managed_restaurant_ids))
    
    if status:
        query = query.filter(Reservation.status == status)
    if restaurant_id:
        if not current_user.is_admin and restaurant_id not in managed_restaurant_ids:
            flash('您没有权限查看此餐厅的预订', 'danger')
            return redirect(url_for('admin_reservations'))
        query = query.filter(Table.restaurant_id == restaurant_id)
    if date_str:
        try:
            reservation_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            query = query.filter(Reservation.reservation_date == reservation_date)
        except ValueError:
            pass
    
    reservations = query.order_by(
        Reservation.reservation_date.desc(),
        Reservation.start_time.desc()
    ).all()
    
    return render_template('admin/reservations.html',
                           reservations=reservations,
                           restaurants=restaurants,
                           today=date.today())

@app.route('/admin/reservation/<int:reservation_id>/status', methods=['POST'])
@login_required
def update_reservation_status(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    
    if not can_manage_restaurant(reservation.table.restaurant_id):
        flash('您没有权限管理此预订', 'danger')
        return redirect(url_for('admin_reservations'))
    
    new_status = request.form.get('status')
    reject_reason = request.form.get('reject_reason', '')
    
    valid_statuses = ['pending', 'confirmed', 'cancelled', 'completed', 'rejected']
    
    if new_status in valid_statuses:
        reservation.status = new_status
        
        if new_status == 'rejected':
            reservation.reject_reason = reject_reason
            recommendations = generate_recommendations(reservation)
            reservation.recommendation_suggestions = json.dumps(recommendations)
        
        db.session.commit()
        flash(f'预订状态已更新为 {reservation.status_display}', 'success')
    else:
        flash('无效的状态', 'danger')
    
    return redirect(url_for('admin_reservations'))

def generate_recommendations(reservation):
    recommendations = {
        'alternative_times': [],
        'alternative_tables': [],
        'alternative_dates': [],
        'reservation_id': reservation.id,
        'restaurant_id': reservation.table.restaurant_id,
        'guest_count': reservation.guest_count
    }
    
    restaurant = reservation.table.restaurant
    original_date = reservation.reservation_date
    original_start = reservation.start_time
    original_end = reservation.end_time
    original_guest_count = reservation.guest_count
    
    time_slots = get_time_slots(restaurant.id, original_date)
    for slot in time_slots:
        if slot == original_start:
            continue
        end_dt = datetime.combine(original_date, slot) + timedelta(hours=2)
        end_time = end_dt.time()
        
        available_tables = get_available_tables(
            restaurant.id,
            original_date,
            slot,
            end_time,
            original_guest_count
        )
        
        if available_tables:
            first_table = available_tables[0]
            recommendations['alternative_times'].append({
                'time': slot.strftime('%H:%M'),
                'end_time': end_time.strftime('%H:%M'),
                'tables_available': len(available_tables),
                'table_id': first_table.id,
                'table_number': first_table.table_number,
                'date': original_date.isoformat()
            })
    
    for days_offset in range(1, 8):
        alt_date = original_date + timedelta(days=days_offset)
        alt_end = (datetime.combine(alt_date, original_start) + timedelta(hours=2)).time()
        
        available_tables = get_available_tables(
            restaurant.id,
            alt_date,
            original_start,
            alt_end,
            original_guest_count
        )
        
        if available_tables:
            first_table = available_tables[0]
            recommendations['alternative_dates'].append({
                'date': alt_date.isoformat(),
                'weekday': ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][alt_date.weekday()],
                'tables_available': len(available_tables),
                'table_id': first_table.id,
                'table_number': first_table.table_number,
                'start_time': original_start.strftime('%H:%M'),
                'end_time': alt_end.strftime('%H:%M')
            })
    
    all_tables = Table.query.filter_by(
        restaurant_id=restaurant.id,
        is_active=True
    ).all()
    
    suitable_tables = [t for t in all_tables if t.capacity >= original_guest_count]
    
    for table in suitable_tables:
        if table.id == reservation.table_id:
            continue
        if table.is_available(original_date, original_start, original_end):
            recommendations['alternative_tables'].append({
                'table_id': table.id,
                'table_number': table.table_number,
                'capacity': table.capacity,
                'date': original_date.isoformat(),
                'start_time': original_start.strftime('%H:%M'),
                'end_time': original_end.strftime('%H:%M')
            })
    
    return recommendations

@app.route('/reservation/query', methods=['GET', 'POST'])
def query_reservation():
    reservation = None
    error = None
    recommendations = None
    
    if request.method == 'POST':
        booking_code = request.form.get('booking_code', '').upper().strip()
        customer_phone = request.form.get('customer_phone', '').strip()
        
        if not booking_code:
            error = '请输入预订凭据'
        elif not is_valid_booking_code(booking_code):
            error = '预订凭据格式错误，应为2个大写字母加6个数字（如：AB123456）'
        else:
            try:
                reservation = Reservation.query.filter_by(booking_code=booking_code).first()
                
                if not reservation:
                    error = '未找到该预订，请检查预订凭据是否正确'
                elif customer_phone and reservation.customer_phone != customer_phone:
                    error = '联系电话与预订信息不匹配'
                else:
                    if reservation.status == 'rejected' and reservation.recommendation_suggestions:
                        recommendations = safe_parse_recommendations(reservation.recommendation_suggestions)
            except Exception as e:
                app.logger.error(f"查询预订时出错: {str(e)}")
                error = '查询出错，请稍后重试或联系管理员'
    
    return render_template('query_reservation.html',
                           reservation=reservation,
                           error=error,
                           recommendations=recommendations)

@app.route('/reservation/<int:reservation_id>/quick_rebook', methods=['POST'])
def quick_rebook(reservation_id):
    original_reservation = Reservation.query.get_or_404(reservation_id)
    
    if original_reservation.status != 'rejected':
        flash('只有被拒绝的预订才能快速重新预订', 'danger')
        return redirect(url_for('query_reservation'))
    
    table_id = safe_parse_int(request.form.get('table_id'), default=0, min_val=1)
    reservation_date_str = request.form.get('reservation_date')
    start_time_str = request.form.get('start_time')
    end_time_str = request.form.get('end_time')
    
    errors = []
    
    if table_id < 1:
        errors.append('请选择有效的餐桌')
    
    if not reservation_date_str or not is_valid_date(reservation_date_str):
        errors.append('请选择有效的日期')
    
    if not start_time_str or not is_valid_time(start_time_str):
        errors.append('请选择有效的开始时间')
    
    if not end_time_str or not is_valid_time(end_time_str):
        errors.append('请选择有效的结束时间')
    
    if errors:
        for error in errors:
            flash(error, 'danger')
        return redirect(url_for('query_reservation'))
    
    try:
        reservation_date = datetime.strptime(reservation_date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
    except ValueError:
        flash('日期或时间格式错误', 'danger')
        return redirect(url_for('query_reservation'))
    
    table = Table.query.get(table_id)
    restaurant = Restaurant.query.get(original_reservation.table.restaurant_id)
    
    if not table or table.restaurant_id != restaurant.id:
        flash('餐桌不存在', 'danger')
        return redirect(url_for('query_reservation'))
    
    if not table.is_active:
        flash('该餐桌已停用', 'danger')
        return redirect(url_for('query_reservation'))
    
    if original_reservation.guest_count > table.capacity:
        flash('用餐人数超过餐桌容量', 'danger')
        return redirect(url_for('query_reservation'))
    
    if not table.is_available(reservation_date, start_time, end_time):
        flash('该时间段已被预订，请选择其他时间', 'danger')
        return redirect(url_for('query_reservation'))
    
    original_booking_code = original_reservation.booking_code
    
    old_booking_code = Reservation.generate_booking_code()
    while Reservation.query.filter_by(booking_code=old_booking_code).first():
        old_booking_code = Reservation.generate_booking_code()
    
    original_reservation.booking_code = old_booking_code
    original_reservation.original_booking_code = original_booking_code
    
    new_reservation = Reservation(
        table_id=table_id,
        customer_name=original_reservation.customer_name,
        customer_phone=original_reservation.customer_phone,
        customer_email=original_reservation.customer_email,
        guest_count=original_reservation.guest_count,
        reservation_date=reservation_date,
        start_time=start_time,
        end_time=end_time,
        notes=original_reservation.notes,
        status='pending',
        booking_code=original_booking_code
    )
    
    db.session.add(new_reservation)
    db.session.commit()
    
    flash('重新预订成功！您可以使用原预订凭据查询状态。', 'success')
    return render_template('reservation_success.html', 
                           reservation=new_reservation, 
                           restaurant=restaurant)

@app.route('/admin/calendar')
@login_required
def admin_calendar():
    return render_template('admin/calendar.html')

@app.route('/admin/calendar/data')
@login_required
def calendar_data():
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    
    if not start_str or not end_str or not is_valid_date(start_str) or not is_valid_date(end_str):
        today = date.today()
        start_date = today - timedelta(days=30)
        end_date = today + timedelta(days=30)
    else:
        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
        except ValueError:
            today = date.today()
            start_date = today - timedelta(days=30)
            end_date = today + timedelta(days=30)
    
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    
    query = Reservation.query.filter(
        Reservation.reservation_date >= start_date,
        Reservation.reservation_date <= end_date
    )
    
    if not current_user.is_admin:
        managed_restaurants = current_user.get_managed_restaurants()
        managed_restaurant_ids = [r.id for r in managed_restaurants]
        query = query.join(Table).filter(Table.restaurant_id.in_(managed_restaurant_ids))
    
    reservations = query.all()
    
    events = []
    for res in reservations:
        start_dt = datetime.combine(res.reservation_date, res.start_time)
        end_dt = datetime.combine(res.reservation_date, res.end_time)
        
        color_map = {
            'pending': '#ffc107',
            'confirmed': '#28a745',
            'cancelled': '#dc3545',
            'completed': '#6c757d',
            'rejected': '#dc3545'
        }
        
        events.append({
            'id': res.id,
            'title': f'[{res.booking_code}] {res.customer_name} - {res.table.table_number}号桌 ({res.guest_count}人)',
            'start': start_dt.isoformat(),
            'end': end_dt.isoformat(),
            'backgroundColor': color_map.get(res.status, '#6c757d'),
            'borderColor': color_map.get(res.status, '#6c757d'),
            'extendedProps': {
                'status': res.status,
                'status_display': res.status_display,
                'booking_code': res.booking_code,
                'table_number': res.table.table_number,
                'guest_count': res.guest_count,
                'phone': res.customer_phone,
                'notes': res.notes
            }
        })
    
    return jsonify(events)

@app.route('/admin/store_managers')
@admin_required
def admin_store_managers():
    store_managers = User.query.filter_by(is_store_manager=True).order_by(User.created_at.desc()).all()
    return render_template('admin/store_managers.html', store_managers=store_managers)

@app.route('/admin/store_manager/add', methods=['GET', 'POST'])
@admin_required
def add_store_manager():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        errors = []
        
        if not username or len(username) < 1 or len(username) > 80:
            errors.append('用户名必须在1-80字符之间')
        
        if not password or len(password) < 6:
            errors.append('密码至少6个字符')
        
        existing = User.query.filter_by(username=username).first()
        if existing:
            errors.append('用户名已存在')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return redirect(url_for('add_store_manager'))
        
        store_manager = User(
            username=username,
            is_store_manager=True
        )
        store_manager.set_password(password)
        
        db.session.add(store_manager)
        db.session.commit()
        
        flash('店长添加成功', 'success')
        return redirect(url_for('admin_store_managers'))
    
    return render_template('admin/store_manager_form.html', store_manager=None)

@app.route('/admin/store_manager/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_store_manager(user_id):
    store_manager = User.query.get_or_404(user_id)
    
    if not store_manager.is_store_manager:
        flash('该用户不是店长', 'danger')
        return redirect(url_for('admin_store_managers'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        errors = []
        
        if not username or len(username) < 1 or len(username) > 80:
            errors.append('用户名必须在1-80字符之间')
        
        if password and len(password) < 6:
            errors.append('密码至少6个字符')
        
        existing = User.query.filter_by(username=username).first()
        if existing and existing.id != store_manager.id:
            errors.append('用户名已存在')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return redirect(url_for('edit_store_manager', user_id=user_id))
        
        store_manager.username = username
        if password:
            store_manager.set_password(password)
        
        db.session.commit()
        flash('店长信息已更新', 'success')
        return redirect(url_for('admin_store_managers'))
    
    managed_restaurants = store_manager.get_managed_restaurants()
    return render_template('admin/store_manager_form.html', store_manager=store_manager, managed_restaurants=managed_restaurants)

@app.route('/admin/store_manager/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_store_manager(user_id):
    store_manager = User.query.get_or_404(user_id)
    
    if not store_manager.is_store_manager:
        flash('该用户不是店长', 'danger')
        return redirect(url_for('admin_store_managers'))
    
    managed_restaurants = store_manager.get_managed_restaurants()
    if managed_restaurants:
        flash('该店长还有管理的餐厅，请先解除餐厅管理关系', 'danger')
        return redirect(url_for('edit_store_manager', user_id=user_id))
    
    db.session.delete(store_manager)
    db.session.commit()
    
    flash('店长已删除', 'success')
    return redirect(url_for('admin_store_managers'))

def init_db():
    with app.app_context():
        db.create_all()
        
        migrate_database()
        
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                is_admin=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
        
        restaurant = Restaurant.query.filter_by(name='示例餐厅').first()
        if not restaurant:
            restaurant = Restaurant(
                name='示例餐厅',
                address='示例地址123号',
                phone='12345678900',
                description='这是一家示例餐厅',
                open_time=datetime.strptime('10:00', '%H:%M').time(),
                close_time=datetime.strptime('22:00', '%H:%M').time()
            )
            db.session.add(restaurant)
            db.session.commit()
            
            tables_data = [
                (1, 2), (2, 2), (3, 4), (4, 4),
                (5, 6), (6, 6), (7, 8), (8, 10)
            ]
            
            for table_num, capacity in tables_data:
                table = Table(
                    restaurant_id=restaurant.id,
                    table_number=table_num,
                    capacity=capacity
                )
                db.session.add(table)
        
        db.session.commit()
        print('数据库初始化完成')
        print('管理员账号: admin / admin123')

def migrate_database():
    try:
        from sqlalchemy import inspect, text
        
        inspector = inspect(db.engine)
        
        if 'user' in inspector.get_table_names():
            columns = [c['name'] for c in inspector.get_columns('user')]
            
            with db.engine.connect() as conn:
                if 'is_store_manager' not in columns:
                    try:
                        conn.execute(text('ALTER TABLE user ADD COLUMN is_store_manager BOOLEAN DEFAULT 0'))
                        conn.commit()
                        print('已添加字段: user.is_store_manager')
                    except Exception as e:
                        print(f'添加 is_store_manager 字段时出错: {e}')
        
        if 'restaurant' in inspector.get_table_names():
            columns = [c['name'] for c in inspector.get_columns('restaurant')]
            
            with db.engine.connect() as conn:
                if 'store_manager_id' not in columns:
                    try:
                        conn.execute(text('ALTER TABLE restaurant ADD COLUMN store_manager_id INTEGER'))
                        conn.execute(text('CREATE INDEX IF NOT EXISTS idx_restaurant_store_manager ON restaurant(store_manager_id)'))
                        conn.commit()
                        print('已添加字段: restaurant.store_manager_id')
                    except Exception as e:
                        print(f'添加 store_manager_id 字段时出错: {e}')
        
        if 'reservation' in inspector.get_table_names():
            columns = [c['name'] for c in inspector.get_columns('reservation')]
            
            with db.engine.connect() as conn:
                if 'booking_code' not in columns:
                    try:
                        conn.execute(text('ALTER TABLE reservation ADD COLUMN booking_code VARCHAR(12)'))
                        conn.commit()
                        print('已添加字段: booking_code')
                    except Exception as e:
                        print(f'添加 booking_code 字段时出错: {e}')
                
                if 'original_booking_code' not in columns:
                    try:
                        conn.execute(text('ALTER TABLE reservation ADD COLUMN original_booking_code VARCHAR(12)'))
                        conn.commit()
                        print('已添加字段: original_booking_code')
                    except Exception as e:
                        print(f'添加 original_booking_code 字段时出错: {e}')
                
                if 'reject_reason' not in columns:
                    try:
                        conn.execute(text('ALTER TABLE reservation ADD COLUMN reject_reason TEXT'))
                        conn.commit()
                        print('已添加字段: reject_reason')
                    except Exception as e:
                        print(f'添加 reject_reason 字段时出错: {e}')
                
                if 'recommendation_suggestions' not in columns:
                    try:
                        conn.execute(text('ALTER TABLE reservation ADD COLUMN recommendation_suggestions TEXT'))
                        conn.commit()
                        print('已添加字段: recommendation_suggestions')
                    except Exception as e:
                        print(f'添加 recommendation_suggestions 字段时出错: {e}')
                
                try:
                    result = conn.execute(text('SELECT id FROM reservation WHERE booking_code IS NULL OR booking_code = ""'))
                    rows = result.fetchall()
                    for row in rows:
                        booking_code = Reservation.generate_booking_code()
                        while conn.execute(text('SELECT id FROM reservation WHERE booking_code = :code'), {'code': booking_code}).fetchone():
                            booking_code = Reservation.generate_booking_code()
                        conn.execute(
                            text('UPDATE reservation SET booking_code = :code WHERE id = :id'),
                            {'code': booking_code, 'id': row[0]}
                        )
                    conn.commit()
                    if rows:
                        print(f'已为 {len(rows)} 条旧预订记录生成预订凭据')
                except Exception as e:
                    print(f'更新旧预订记录时出错: {e}')
                    
    except Exception as e:
        print(f'数据库迁移出错: {e}')

def find_free_port():
    port = random.randint(10000, 50000)
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', port))
                return port
            except OSError:
                port = random.randint(10000, 50000)

if __name__ == '__main__':
    init_db()
    port = 2222
    print(f'服务器运行在 http://localhost:{port}')
    print(f'管理后台: http://localhost:{port}/admin')
    app.run(host='0.0.0.0', port=port, debug=True)
