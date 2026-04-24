from datetime import datetime
import bcrypt
from flask_login import UserMixin
from app.extensions import db


user_role = db.Table('user_role',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id', ondelete='CASCADE'), primary_key=True),
    extend_existing=True
)


user_group_member = db.Table('user_group_member',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True),
    db.Column('group_id', db.Integer, db.ForeignKey('user_group.id', ondelete='CASCADE'), primary_key=True),
    extend_existing=True
)


class User(db.Model, UserMixin):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    roles = db.relationship('Role', secondary=user_role, backref=db.backref('users', lazy='dynamic'))
    groups = db.relationship('UserGroup', secondary=user_group_member, backref=db.backref('members', lazy='dynamic'))
    surveys = db.relationship('Survey', backref='creator', lazy='dynamic')
    responses = db.relationship('Response', backref='user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def has_role(self, role_name):
        for role in self.roles:
            if role.name == role_name:
                return True
        return False
    
    def has_permission(self, permission):
        for role in self.roles:
            if role.permissions & permission:
                return True
        return False


class Role(db.Model):
    __tablename__ = 'role'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.String(200))
    permissions = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<Role {self.name}>'


class UserGroup(db.Model):
    __tablename__ = 'user_group'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False, index=True)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserGroup {self.name}>'
