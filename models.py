from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import random
import string

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    description = db.Column(db.Text)
    open_time = db.Column(db.Time, nullable=False)
    close_time = db.Column(db.Time, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tables = db.relationship('Table', backref='restaurant', lazy=True, cascade='all, delete-orphan')

class Table(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    table_number = db.Column(db.Integer, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reservations = db.relationship('Reservation', backref='table', lazy=True)

    def is_available(self, date, start_time, end_time):
        for reservation in self.reservations:
            if reservation.status in ['confirmed', 'pending']:
                if reservation.reservation_date == date:
                    if not (end_time <= reservation.start_time or start_time >= reservation.end_time):
                        return False
        return True

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('table.id'), nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    customer_email = db.Column(db.String(100))
    guest_count = db.Column(db.Integer, nullable=False)
    reservation_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default='pending')
    notes = db.Column(db.Text)
    booking_code = db.Column(db.String(12), unique=True, nullable=False)
    reject_reason = db.Column(db.Text)
    recommendation_suggestions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_COMPLETED = 'completed'
    STATUS_REJECTED = 'rejected'

    @staticmethod
    def generate_booking_code():
        letters = string.ascii_uppercase
        digits = string.digits
        part1 = ''.join(random.choices(letters, k=2))
        part2 = ''.join(random.choices(digits, k=6))
        return f"{part1}{part2}"

    @property
    def status_display(self):
        status_map = {
            'pending': '待确认',
            'confirmed': '已确认',
            'cancelled': '已取消',
            'completed': '已完成',
            'rejected': '已拒绝'
        }
        return status_map.get(self.status, self.status)

    @property
    def status_class(self):
        status_map = {
            'pending': 'warning',
            'confirmed': 'success',
            'cancelled': 'danger',
            'completed': 'secondary',
            'rejected': 'danger'
        }
        return status_map.get(self.status, 'secondary')
