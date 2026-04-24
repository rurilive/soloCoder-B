from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db, csrf
from app.models import Survey, Question

editor = Blueprint('editor', __name__)

QUESTION_TYPES = [
    'single_choice',
    'multiple_choice',
    'text',
    'rating',
    'scale',
    'date'
]


@editor.route('/survey/<int:survey_id>/editor')
@login_required
def editor_page(survey_id):
    survey_obj = Survey.query.get_or_404(survey_id)
    
    if not survey_obj.can_edit(current_user.id):
        return jsonify({'success': False, 'message': '您没有权限编辑此问卷'}), 403
    
    return render_template('survey/editor.html', survey=survey_obj)


@editor.route('/api/survey/<int:survey_id>/questions', methods=['GET'])
@login_required
def get_questions(survey_id):
    survey_obj = Survey.query.get_or_404(survey_id)
    
    if not survey_obj.can_edit(current_user.id):
        return jsonify({'success': False, 'message': '您没有权限编辑此问卷'}), 403
    
    questions = Question.query.filter_by(survey_id=survey_id).order_by(Question.order).all()
    
    return jsonify({
        'success': True,
        'survey': {
            'id': survey_obj.id,
            'title': survey_obj.title,
            'description': survey_obj.description,
            'status': survey_obj.status
        },
        'questions': [q.to_dict() for q in questions]
    })


@editor.route('/api/survey/<int:survey_id>/questions', methods=['POST'])
@login_required
def add_question(survey_id):
    survey_obj = Survey.query.get_or_404(survey_id)
    
    if not survey_obj.can_edit(current_user.id):
        return jsonify({'success': False, 'message': '您没有权限编辑此问卷'}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '无效的请求数据'}), 400
    
    question_type = data.get('type')
    if question_type not in QUESTION_TYPES:
        return jsonify({'success': False, 'message': f'不支持的题目类型: {question_type}'}), 400
    
    if not data.get('text'):
        return jsonify({'success': False, 'message': '题目文本不能为空'}), 400
    
    max_order = db.session.query(db.func.max(Question.order)).filter_by(
        survey_id=survey_id
    ).scalar() or 0
    
    new_question = Question(
        survey_id=survey_id,
        type=question_type,
        text=data.get('text'),
        options=data.get('options', {}),
        is_required=data.get('is_required', True),
        order=data.get('order', max_order + 1),
        logic_jump=data.get('logic_jump', {})
    )
    
    db.session.add(new_question)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'question': new_question.to_dict()
    }), 201


@editor.route('/api/survey/<int:survey_id>/questions/<int:question_id>', methods=['PUT'])
@login_required
@csrf.exempt
def update_question(survey_id, question_id):
    survey_obj = Survey.query.get_or_404(survey_id)
    
    if not survey_obj.can_edit(current_user.id):
        return jsonify({'success': False, 'message': '您没有权限编辑此问卷'}), 403
    
    question = Question.query.filter_by(id=question_id, survey_id=survey_id).first()
    if not question:
        return jsonify({'success': False, 'message': '题目不存在'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '无效的请求数据'}), 400
    
    question_type = data.get('type')
    if question_type and question_type not in QUESTION_TYPES:
        return jsonify({'success': False, 'message': f'不支持的题目类型: {question_type}'}), 400
    
    question.from_dict(data)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'question': question.to_dict()
    })


@editor.route('/api/survey/<int:survey_id>/questions/<int:question_id>', methods=['DELETE'])
@login_required
def delete_question(survey_id, question_id):
    survey_obj = Survey.query.get_or_404(survey_id)
    
    if not survey_obj.can_edit(current_user.id):
        return jsonify({'success': False, 'message': '您没有权限编辑此问卷'}), 403
    
    question = Question.query.filter_by(id=question_id, survey_id=survey_id).first()
    if not question:
        return jsonify({'success': False, 'message': '题目不存在'}), 404
    
    deleted_order = question.order
    
    db.session.delete(question)
    db.session.flush()
    
    remaining_questions = Question.query.filter(
        Question.survey_id == survey_id,
        Question.order > deleted_order
    ).order_by(Question.order).all()
    
    for q in remaining_questions:
        q.order = -q.id
    
    db.session.flush()
    
    for idx, q in enumerate(remaining_questions, deleted_order):
        q.order = idx
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': '题目已删除'})


@editor.route('/api/survey/<int:survey_id>/questions/reorder', methods=['POST'])
@login_required
def reorder_questions(survey_id):
    survey_obj = Survey.query.get_or_404(survey_id)
    
    if not survey_obj.can_edit(current_user.id):
        return jsonify({'success': False, 'message': '您没有权限编辑此问卷'}), 403
    
    data = request.get_json()
    if not data or 'order' not in data:
        return jsonify({'success': False, 'message': '无效的请求数据'}), 400
    
    order_list = data.get('order', [])
    if not isinstance(order_list, list):
        return jsonify({'success': False, 'message': 'order 必须是数组'}), 400
    
    existing_questions = Question.query.filter_by(survey_id=survey_id).all()
    existing_ids = {q.id for q in existing_questions}
    requested_ids = set(order_list)
    
    if requested_ids != existing_ids:
        return jsonify({'success': False, 'message': '排序的题目列表不完整或包含不存在的题目'}), 400
    
    for question in existing_questions:
        question.order = -question.id
    
    db.session.flush()
    
    for index, question_id in enumerate(order_list, 1):
        question = Question.query.filter_by(id=question_id).first()
        if question:
            question.order = index
    
    db.session.commit()
    
    return jsonify({'success': True})


@editor.route('/api/survey/<int:survey_id>/questions/batch', methods=['POST'])
@login_required
def batch_questions(survey_id):
    survey_obj = Survey.query.get_or_404(survey_id)
    
    if not survey_obj.can_edit(current_user.id):
        return jsonify({'success': False, 'message': '您没有权限编辑此问卷'}), 403
    
    data = request.get_json()
    if not data or 'questions' not in data:
        return jsonify({'success': False, 'message': '无效的请求数据'}), 400
    
    questions_data = data.get('questions', [])
    if not isinstance(questions_data, list):
        return jsonify({'success': False, 'message': 'questions 必须是数组'}), 400
    
    existing_questions = {q.id: q for q in Question.query.filter_by(survey_id=survey_id).all()}
    processed_ids = set()
    result_questions = []
    temp_order_map = {}
    
    for q_id, question in existing_questions.items():
        temp_order = -q_id
        question.order = temp_order
        temp_order_map[temp_order] = question
    
    db.session.flush()
    
    for idx, q_data in enumerate(questions_data, 1):
        q_id = q_data.get('id')
        q_type = q_data.get('type')
        q_text = q_data.get('text')
        
        if q_type and q_type not in QUESTION_TYPES:
            return jsonify({'success': False, 'message': f'不支持的题目类型: {q_type}'}), 400
        
        if q_id and q_id in existing_questions:
            question = existing_questions[q_id]
            question.from_dict(q_data)
            question.order = idx
            processed_ids.add(q_id)
            result_questions.append(question)
        else:
            if not q_type or not q_text:
                continue
            
            new_question = Question(
                survey_id=survey_id,
                type=q_type,
                text=q_text,
                options=q_data.get('options', {}),
                is_required=q_data.get('is_required', True),
                order=idx,
                logic_jump=q_data.get('logic_jump', {})
            )
            db.session.add(new_question)
            result_questions.append(new_question)
    
    for q_id, question in existing_questions.items():
        if q_id not in processed_ids:
            db.session.delete(question)
    
    db.session.commit()
    db.session.refresh(survey_obj)
    
    result_questions = sorted(result_questions, key=lambda x: x.order)
    
    return jsonify({
        'success': True,
        'questions': [q.to_dict() for q in result_questions]
    })
