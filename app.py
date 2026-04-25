import os
import random
import socket
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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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
        guest_count = int(request.form.get('guest_count', 1))
        
        reservation_date = datetime.strptime(reservation_date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        
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
    
    table_id = request.form.get('table_id')
    customer_name = request.form.get('customer_name')
    customer_phone = request.form.get('customer_phone')
    customer_email = request.form.get('customer_email', '')
    guest_count = int(request.form.get('guest_count', 1))
    reservation_date_str = request.form.get('reservation_date')
    start_time_str = request.form.get('start_time')
    end_time_str = request.form.get('end_time')
    notes = request.form.get('notes', '')
    
    reservation_date = datetime.strptime(reservation_date_str, '%Y-%m-%d').date()
    start_time = datetime.strptime(start_time_str, '%H:%M').time()
    end_time = datetime.strptime(end_time_str, '%H:%M').time()
    
    table = Table.query.get(table_id)
    if not table:
        flash('餐桌不存在', 'danger')
        return redirect(url_for('check_availability', restaurant_id=restaurant_id))
    
    if not table.is_available(reservation_date, start_time, end_time):
        flash('该时间段已被预订，请选择其他时间', 'danger')
        return redirect(url_for('check_availability', restaurant_id=restaurant_id))
    
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
        booking_code=Reservation.generate_booking_code()
    )
    
    while Reservation.query.filter_by(booking_code=reservation.booking_code).first():
        reservation.booking_code = Reservation.generate_booking_code()
    
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
        username = request.form.get('username')
        password = request.form.get('password')
        
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
    today_reservations = Reservation.query.filter(
        Reservation.reservation_date == today
    ).order_by(Reservation.start_time).all()
    
    pending_reservations = Reservation.query.filter_by(
        status='pending'
    ).order_by(Reservation.created_at).all()
    
    total_tables = Table.query.filter_by(is_active=True).count()
    total_restaurants = Restaurant.query.count()
    
    return render_template('admin/dashboard.html',
                           today_reservations=today_reservations,
                           pending_reservations=pending_reservations,
                           total_tables=total_tables,
                           total_restaurants=total_restaurants,
                           today=today)

@app.route('/admin/restaurants')
@login_required
def admin_restaurants():
    restaurants = Restaurant.query.all()
    return render_template('admin/restaurants.html', restaurants=restaurants)

@app.route('/admin/restaurant/add', methods=['GET', 'POST'])
@login_required
def add_restaurant():
    if request.method == 'POST':
        name = request.form.get('name')
        address = request.form.get('address', '')
        phone = request.form.get('phone', '')
        description = request.form.get('description', '')
        open_time_str = request.form.get('open_time')
        close_time_str = request.form.get('close_time')
        
        open_time = datetime.strptime(open_time_str, '%H:%M').time()
        close_time = datetime.strptime(close_time_str, '%H:%M').time()
        
        restaurant = Restaurant(
            name=name,
            address=address,
            phone=phone,
            description=description,
            open_time=open_time,
            close_time=close_time
        )
        
        db.session.add(restaurant)
        db.session.commit()
        
        flash('餐厅添加成功', 'success')
        return redirect(url_for('admin_restaurants'))
    
    return render_template('admin/restaurant_form.html', restaurant=None)

@app.route('/admin/restaurant/<int:restaurant_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    
    if request.method == 'POST':
        restaurant.name = request.form.get('name')
        restaurant.address = request.form.get('address', '')
        restaurant.phone = request.form.get('phone', '')
        restaurant.description = request.form.get('description', '')
        
        open_time_str = request.form.get('open_time')
        close_time_str = request.form.get('close_time')
        
        restaurant.open_time = datetime.strptime(open_time_str, '%H:%M').time()
        restaurant.close_time = datetime.strptime(close_time_str, '%H:%M').time()
        
        db.session.commit()
        flash('餐厅信息已更新', 'success')
        return redirect(url_for('admin_restaurants'))
    
    return render_template('admin/restaurant_form.html', restaurant=restaurant)

@app.route('/admin/restaurant/<int:restaurant_id>/delete', methods=['POST'])
@login_required
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
    
    if restaurant_id:
        tables = Table.query.filter_by(restaurant_id=restaurant_id).all()
        restaurant = Restaurant.query.get(restaurant_id)
    else:
        tables = Table.query.all()
        restaurant = None
    
    restaurants = Restaurant.query.all()
    return render_template('admin/tables.html', 
                           tables=tables, 
                           restaurants=restaurants, 
                           selected_restaurant=restaurant)

@app.route('/admin/table/add', methods=['GET', 'POST'])
@login_required
def add_table():
    if request.method == 'POST':
        restaurant_id = request.form.get('restaurant_id', type=int)
        table_number = request.form.get('table_number', type=int)
        capacity = request.form.get('capacity', type=int)
        
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
    
    restaurants = Restaurant.query.all()
    return render_template('admin/table_form.html', table=None, restaurants=restaurants)

@app.route('/admin/table/<int:table_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_table(table_id):
    table = Table.query.get_or_404(table_id)
    
    if request.method == 'POST':
        table.table_number = request.form.get('table_number', type=int)
        table.capacity = request.form.get('capacity', type=int)
        table.is_active = request.form.get('is_active') == 'on'
        
        db.session.commit()
        flash('餐桌信息已更新', 'success')
        return redirect(url_for('admin_tables', restaurant_id=table.restaurant_id))
    
    restaurants = Restaurant.query.all()
    return render_template('admin/table_form.html', table=table, restaurants=restaurants)

@app.route('/admin/table/<int:table_id>/delete', methods=['POST'])
@login_required
def delete_table(table_id):
    table = Table.query.get_or_404(table_id)
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
    
    query = Reservation.query.join(Table)
    
    if status:
        query = query.filter(Reservation.status == status)
    if restaurant_id:
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
    
    restaurants = Restaurant.query.all()
    return render_template('admin/reservations.html',
                           reservations=reservations,
                           restaurants=restaurants,
                           today=date.today())

@app.route('/admin/reservation/<int:reservation_id>/status', methods=['POST'])
@login_required
def update_reservation_status(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    new_status = request.form.get('status')
    reject_reason = request.form.get('reject_reason', '')
    
    valid_statuses = ['pending', 'confirmed', 'cancelled', 'completed', 'rejected']
    
    if new_status in valid_statuses:
        reservation.status = new_status
        
        if new_status == 'rejected':
            reservation.reject_reason = reject_reason
            recommendations = generate_recommendations(reservation)
            reservation.recommendation_suggestions = str(recommendations)
        
        db.session.commit()
        flash(f'预订状态已更新为 {reservation.status_display}', 'success')
    else:
        flash('无效的状态', 'danger')
    
    return redirect(url_for('admin_reservations'))

def generate_recommendations(reservation):
    recommendations = {
        'alternative_times': [],
        'alternative_tables': [],
        'alternative_dates': []
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
            recommendations['alternative_times'].append({
                'time': slot.strftime('%H:%M'),
                'end_time': end_time.strftime('%H:%M'),
                'tables_available': len(available_tables)
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
            recommendations['alternative_dates'].append({
                'date': alt_date.isoformat(),
                'weekday': ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][alt_date.weekday()],
                'tables_available': len(available_tables)
            })
    
    all_tables = Table.query.filter_by(
        restaurant_id=restaurant.id,
        is_active=True
    ).all()
    
    for table in all_tables:
        if table.id == reservation.table_id:
            continue
        if table.is_available(original_date, original_start, original_end):
            recommendations['alternative_tables'].append({
                'table_number': table.table_number,
                'capacity': table.capacity
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
        else:
            reservation = Reservation.query.filter_by(booking_code=booking_code).first()
            
            if not reservation:
                error = '未找到该预订，请检查预订凭据是否正确'
            elif customer_phone and reservation.customer_phone != customer_phone:
                error = '联系电话与预订信息不匹配'
            else:
                if reservation.status == 'rejected' and reservation.recommendation_suggestions:
                    try:
                        recommendations = eval(reservation.recommendation_suggestions)
                    except:
                        recommendations = None
    
    return render_template('query_reservation.html',
                           reservation=reservation,
                           error=error,
                           recommendations=recommendations)

@app.route('/admin/calendar')
@login_required
def admin_calendar():
    return render_template('admin/calendar.html')

@app.route('/admin/calendar/data')
@login_required
def calendar_data():
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    
    start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
    
    reservations = Reservation.query.filter(
        Reservation.reservation_date >= start_date,
        Reservation.reservation_date <= end_date
    ).all()
    
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
            'title': f'{res.customer_name} - {res.table.table_number}号桌 ({res.guest_count}人)',
            'start': start_dt.isoformat(),
            'end': end_dt.isoformat(),
            'backgroundColor': color_map.get(res.status, '#6c757d'),
            'borderColor': color_map.get(res.status, '#6c757d'),
            'extendedProps': {
                'status': res.status,
                'status_display': res.status_display,
                'table_number': res.table.table_number,
                'guest_count': res.guest_count,
                'phone': res.customer_phone,
                'notes': res.notes
            }
        })
    
    return jsonify(events)

def init_db():
    with app.app_context():
        db.create_all()
        
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
    port = find_free_port()
    print(f'服务器运行在 http://localhost:{port}')
    print(f'管理后台: http://localhost:{port}/admin')
    app.run(host='0.0.0.0', port=port, debug=True)
