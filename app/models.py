from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from . import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    submissions = db.relationship('Submission', backref='user', lazy='dynamic',
                                   cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Problem(db.Model):
    __tablename__ = 'problems'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    function_name = db.Column(db.String(100), nullable=False)
    test_cases = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    submissions = db.relationship('Submission', backref='problem', lazy='dynamic',
                                   cascade='all, delete-orphan')
    daily_problems = db.relationship('DailyProblem', backref='problem', lazy='dynamic',
                                      cascade='all, delete-orphan')

    def get_test_cases_list(self):
        import json
        try:
            return json.loads(self.test_cases)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_test_cases_list(self, test_cases):
        import json
        self.test_cases = json.dumps(test_cases, ensure_ascii=False)

    def get_difficulty_display(self):
        difficulty_map = {
            'easy': '简单',
            'medium': '中等',
            'hard': '困难'
        }
        return difficulty_map.get(self.difficulty, self.difficulty)

    def get_failed_submissions_count(self, user_id):
        failed_statuses = [
            Submission.STATUS_WRONG_ANSWER,
            Submission.STATUS_TIME_LIMIT_EXCEEDED,
            Submission.STATUS_RUNTIME_ERROR,
            Submission.STATUS_COMPILE_ERROR,
        ]
        return Submission.query.filter_by(
            user_id=user_id,
            problem_id=self.id
        ).filter(Submission.status.in_(failed_statuses)).count()

    def has_accepted_submission(self, user_id):
        return Submission.query.filter_by(
            user_id=user_id,
            problem_id=self.id,
            status=Submission.STATUS_ACCEPTED
        ).count() > 0

    def can_show_hint(self, user_id):
        if self.has_accepted_submission(user_id):
            return False
        if not self.correct_answer:
            return False
        failed_count = self.get_failed_submissions_count(user_id)
        return failed_count >= 3

    def __repr__(self):
        return f'<Problem {self.id}: {self.title}>'


class Submission(db.Model):
    __tablename__ = 'submissions'

    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_ACCEPTED = 'accepted'
    STATUS_WRONG_ANSWER = 'wrong_answer'
    STATUS_TIME_LIMIT_EXCEEDED = 'time_limit_exceeded'
    STATUS_RUNTIME_ERROR = 'runtime_error'
    STATUS_COMPILE_ERROR = 'compile_error'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    problem_id = db.Column(db.Integer, db.ForeignKey('problems.id'), nullable=False, index=True)
    code = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default=STATUS_PENDING)
    runtime = db.Column(db.Float, nullable=True)
    memory = db.Column(db.Float, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    test_results = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    def get_test_results_list(self):
        import json
        try:
            return json.loads(self.test_results) if self.test_results else []
        except (json.JSONDecodeError, TypeError):
            return []

    def set_test_results_list(self, results):
        import json
        self.test_results = json.dumps(results, ensure_ascii=False)

    def get_status_display(self):
        status_map = {
            self.STATUS_PENDING: '等待中',
            self.STATUS_RUNNING: '运行中',
            self.STATUS_ACCEPTED: '通过',
            self.STATUS_WRONG_ANSWER: '答案错误',
            self.STATUS_TIME_LIMIT_EXCEEDED: '超时',
            self.STATUS_RUNTIME_ERROR: '运行时错误',
            self.STATUS_COMPILE_ERROR: '编译错误',
        }
        return status_map.get(self.status, self.status)

    def __repr__(self):
        return f'<Submission {self.id}: {self.status}>'


class DailyProblem(db.Model):
    __tablename__ = 'daily_problems'

    id = db.Column(db.Integer, primary_key=True)
    problem_id = db.Column(db.Integer, db.ForeignKey('problems.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def get_for_date(target_date=None):
        if target_date is None:
            target_date = date.today()
        return DailyProblem.query.filter_by(date=target_date).first()

    @staticmethod
    def set_for_date(problem_id, target_date=None):
        if target_date is None:
            target_date = date.today()
        existing = DailyProblem.query.filter_by(date=target_date).first()
        if existing:
            existing.problem_id = problem_id
            return existing
        daily = DailyProblem(problem_id=problem_id, date=target_date)
        db.session.add(daily)
        return daily

    def __repr__(self):
        return f'<DailyProblem {self.date}: Problem {self.problem_id}>'
