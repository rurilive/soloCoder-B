from datetime import datetime
from app.extensions import db


class Response(db.Model):
    __tablename__ = 'response'
    
    id = db.Column(db.Integer, primary_key=True)
    survey_id = db.Column(db.Integer, db.ForeignKey('survey.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    ip_address = db.Column(db.String(50), index=True)
    user_agent = db.Column(db.String(500))
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    is_valid = db.Column(db.Boolean, default=True)
    invalid_reason = db.Column(db.String(100))
    
    answers = db.relationship('ResponseAnswer', backref='response', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Response {self.id} for Survey {self.survey_id}>'


class ResponseAnswer(db.Model):
    __tablename__ = 'response_answer'
    
    id = db.Column(db.Integer, primary_key=True)
    response_id = db.Column(db.Integer, db.ForeignKey('response.id', ondelete='CASCADE'), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id', ondelete='CASCADE'), nullable=False, index=True)
    value = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('response_id', 'question_id', name='uq_response_question'),
    )
    
    def __repr__(self):
        return f'<ResponseAnswer {self.id} for Question {self.question_id}>'
