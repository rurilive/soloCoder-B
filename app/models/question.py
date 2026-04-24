from datetime import datetime
from app.extensions import db


class Question(db.Model):
    __tablename__ = 'question'
    
    id = db.Column(db.Integer, primary_key=True)
    survey_id = db.Column(db.Integer, db.ForeignKey('survey.id', ondelete='CASCADE'), nullable=False, index=True)
    type = db.Column(db.String(30), nullable=False)
    text = db.Column(db.Text, nullable=False)
    options = db.Column(db.JSON)
    is_required = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, index=True)
    logic_jump = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    answers = db.relationship('ResponseAnswer', backref='question', lazy='dynamic')
    
    __table_args__ = (
        db.UniqueConstraint('survey_id', 'order', name='uq_survey_question_order'),
    )
    
    def __repr__(self):
        return f'<Question {self.id}: {self.type}>'
    
    def get_options_list(self):
        if not self.options:
            return []
        if isinstance(self.options, list):
            return self.options
        if isinstance(self.options, dict):
            opts = self.options.get('options', [])
            if isinstance(opts, list):
                return opts
        return []
    
    def to_dict(self):
        return {
            'id': self.id,
            'survey_id': self.survey_id,
            'type': self.type,
            'text': self.text,
            'options': self.options or {},
            'is_required': self.is_required,
            'order': self.order,
            'logic_jump': self.logic_jump or {},
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def from_dict(self, data, is_new=False):
        if 'type' in data:
            self.type = data['type']
        if 'text' in data:
            self.text = data['text']
        if 'options' in data:
            self.options = data['options']
        if 'is_required' in data:
            self.is_required = data['is_required']
        if 'order' in data:
            self.order = data['order']
        if 'logic_jump' in data:
            self.logic_jump = data['logic_jump']
        return self
