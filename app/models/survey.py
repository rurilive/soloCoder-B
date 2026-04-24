from datetime import datetime
from app.extensions import db


class Survey(db.Model):
    __tablename__ = 'survey'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='draft', index=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    access_password = db.Column(db.String(128))
    max_responses = db.Column(db.Integer)
    require_login = db.Column(db.Boolean, default=False)
    require_captcha = db.Column(db.Boolean, default=False)
    limit_per_ip = db.Column(db.Integer, default=1)
    limit_per_cookie = db.Column(db.Boolean, default=True)
    is_deleted = db.Column(db.Boolean, default=False, index=True)
    
    questions = db.relationship('Question', backref='survey', lazy='dynamic', cascade='all, delete-orphan')
    responses = db.relationship('Response', backref='survey', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Survey {self.title}>'
    
    def is_active(self):
        if self.status != 'active':
            return False
        if self.is_deleted:
            return False
        now = datetime.utcnow()
        if self.start_time and now < self.start_time:
            return False
        if self.end_time and now > self.end_time:
            return False
        return True
    
    def can_access(self, password=None):
        if self.access_password:
            if not password:
                return False
            from werkzeug.security import check_password_hash
            return check_password_hash(self.access_password, password)
        return True
    
    def is_accessible(self, password=None):
        if self.is_deleted:
            return False
        if self.status not in ['active', 'draft']:
            return False
        now = datetime.utcnow()
        if self.start_time and now < self.start_time:
            return False
        if self.end_time and now > self.end_time:
            return False
        if self.max_responses:
            response_count = self.get_responses_count()
            if response_count >= self.max_responses:
                return False
        if self.access_password:
            if not password:
                return False
            from werkzeug.security import check_password_hash
            return check_password_hash(self.access_password, password)
        return True
    
    def can_edit(self, user_id):
        if self.is_deleted:
            return False
        return self.creator_id == user_id
    
    def get_responses_count(self):
        from app.models import Response
        return Response.query.filter_by(
            survey_id=self.id,
            is_valid=True
        ).count()
