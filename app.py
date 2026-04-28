from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import os
import base64
import io
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lowcode.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'lowcode-platform-secret-key-2024'

db = SQLAlchemy(app)

class Form(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    schema = db.Column(db.Text, nullable=False)
    validation_rules = db.Column(db.Text, default='{}')
    linkage_rules = db.Column(db.Text, default='{}')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'schema': json.loads(self.schema) if self.schema else {},
            'validation_rules': json.loads(self.validation_rules) if self.validation_rules else {},
            'linkage_rules': json.loads(self.linkage_rules) if self.linkage_rules else {},
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class FormSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('form.id'), nullable=False)
    data = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    form = db.relationship('Form', backref=db.backref('submissions', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'form_id': self.form_id,
            'data': json.loads(self.data) if self.data else {},
            'created_at': self.created_at.isoformat()
        }

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    forms = Form.query.all()
    return render_template('index.html', forms=forms)

@app.route('/designer')
def designer():
    return render_template('designer.html')

@app.route('/form/<int:form_id>')
def view_form(form_id):
    form = Form.query.get_or_404(form_id)
    return render_template('form_view.html', form=form)

@app.route('/api/forms', methods=['GET'])
def get_forms():
    forms = Form.query.all()
    return jsonify([f.to_dict() for f in forms])

@app.route('/api/forms/<int:form_id>', methods=['GET'])
def get_form(form_id):
    form = Form.query.get_or_404(form_id)
    return jsonify(form.to_dict())

@app.route('/api/forms', methods=['POST'])
def create_form():
    data = request.get_json()
    form = Form(
        name=data.get('name', 'Untitled Form'),
        description=data.get('description', ''),
        schema=json.dumps(data.get('schema', {})),
        validation_rules=json.dumps(data.get('validation_rules', {})),
        linkage_rules=json.dumps(data.get('linkage_rules', {}))
    )
    db.session.add(form)
    db.session.commit()
    return jsonify(form.to_dict()), 201

@app.route('/api/forms/<int:form_id>', methods=['PUT'])
def update_form(form_id):
    form = Form.query.get_or_404(form_id)
    data = request.get_json()
    
    if 'name' in data:
        form.name = data['name']
    if 'description' in data:
        form.description = data['description']
    if 'schema' in data:
        form.schema = json.dumps(data['schema'])
    if 'validation_rules' in data:
        form.validation_rules = json.dumps(data['validation_rules'])
    if 'linkage_rules' in data:
        form.linkage_rules = json.dumps(data['linkage_rules'])
    
    db.session.commit()
    return jsonify(form.to_dict())

@app.route('/api/forms/<int:form_id>', methods=['DELETE'])
def delete_form(form_id):
    form = Form.query.get_or_404(form_id)
    db.session.delete(form)
    db.session.commit()
    return jsonify({'message': 'Form deleted'})

@app.route('/api/forms/<int:form_id>/submit', methods=['POST'])
def submit_form(form_id):
    form = Form.query.get_or_404(form_id)
    data = request.get_json()
    
    validation_result = validate_form_data(form, data)
    if not validation_result['valid']:
        return jsonify(validation_result), 400
    
    submission = FormSubmission(
        form_id=form_id,
        data=json.dumps(data)
    )
    db.session.add(submission)
    db.session.commit()
    
    return jsonify({
        'valid': True,
        'submission_id': submission.id,
        'message': 'Form submitted successfully'
    })

@app.route('/api/forms/<int:form_id>/submissions', methods=['GET'])
def get_submissions(form_id):
    form = Form.query.get_or_404(form_id)
    submissions = FormSubmission.query.filter_by(form_id=form_id).all()
    return jsonify([s.to_dict() for s in submissions])

@app.route('/test/<int:form_id>')
def test_form(form_id):
    form = Form.query.get_or_404(form_id)
    return render_template('test_form.html', form=form)

@app.route('/api/test/playwright', methods=['POST'])
def run_playwright_test():
    data = request.get_json()
    form_id = data.get('form_id')
    test_script = data.get('script')
    test_data = data.get('test_data', {})
    
    if not form_id:
        return jsonify({'error': 'Form ID is required'}), 400
    
    form = Form.query.get(form_id)
    if not form:
        return jsonify({'error': 'Form not found'}), 404
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1280, 'height': 800}
            )
            page = context.new_page()
            
            test_url = request.host_url + f'form/{form_id}'
            
            results = {
                'steps': [],
                'screenshots': [],
                'success': True,
                'message': ''
            }
            
            try:
                results['steps'].append({'action': 'navigate', 'status': 'running', 'message': f'正在访问: {test_url}'})
                page.goto(test_url, wait_until='networkidle', timeout=30000)
                
                screenshot = page.screenshot(full_page=True)
                results['screenshots'].append({
                    'name': 'initial_load',
                    'data': base64.b64encode(screenshot).decode('utf-8')
                })
                results['steps'].append({'action': 'navigate', 'status': 'success', 'message': '页面加载成功'})
                
                fields = json.loads(form.schema).get('fields', [])
                
                for field in fields:
                    field_name = field.get('name')
                    field_type = field.get('type')
                    
                    if field_name in test_data:
                        value = test_data[field_name]
                        selector = f'[name="{field_name}"]'
                        
                        try:
                            page.wait_for_selector(selector, timeout=5000)
                            
                            if field_type in ['text', 'email', 'number', 'textarea']:
                                page.fill(selector, str(value))
                                results['steps'].append({
                                    'action': 'fill',
                                    'field': field_name,
                                    'value': value,
                                    'status': 'success',
                                    'message': f'填写字段 {field_name}: {value}'
                                })
                            
                            elif field_type == 'select':
                                page.select_option(selector, value)
                                results['steps'].append({
                                    'action': 'select',
                                    'field': field_name,
                                    'value': value,
                                    'status': 'success',
                                    'message': f'选择字段 {field_name}: {value}'
                                })
                            
                            elif field_type == 'radio':
                                radio_selector = f'input[name="{field_name}"][value="{value}"]'
                                page.check(radio_selector)
                                results['steps'].append({
                                    'action': 'check',
                                    'field': field_name,
                                    'value': value,
                                    'status': 'success',
                                    'message': f'选中单选框 {field_name}: {value}'
                                })
                            
                            elif field_type == 'checkbox':
                                if isinstance(value, list):
                                    for v in value:
                                        checkbox_selector = f'input[name="{field_name}"][value="{v}"]'
                                        page.check(checkbox_selector)
                                    results['steps'].append({
                                        'action': 'check',
                                        'field': field_name,
                                        'value': value,
                                        'status': 'success',
                                        'message': f'选中多选框 {field_name}: {", ".join(value)}'
                                    })
                            
                            elif field_type == 'date':
                                page.fill(selector, value)
                                results['steps'].append({
                                    'action': 'fill',
                                    'field': field_name,
                                    'value': value,
                                    'status': 'success',
                                    'message': f'填写日期 {field_name}: {value}'
                                })
                                
                        except PlaywrightTimeoutError:
                            results['steps'].append({
                                'action': 'fill',
                                'field': field_name,
                                'status': 'warning',
                                'message': f'字段 {field_name} 未找到，跳过'
                            })
                
                fill_screenshot = page.screenshot(full_page=True)
                results['screenshots'].append({
                    'name': 'after_fill',
                    'data': base64.b64encode(fill_screenshot).decode('utf-8')
                })
                results['steps'].append({'action': 'fill', 'status': 'success', 'message': '所有字段填写完成'})
                
                results['steps'].append({'action': 'submit', 'status': 'running', 'message': '正在提交表单...'})
                
                submit_button = page.locator('button[type="submit"]')
                if submit_button.count() > 0:
                    submit_button.click()
                    
                    try:
                        page.wait_for_event('response', timeout=10000)
                    except:
                        pass
                    
                    page.wait_for_timeout(2000)
                    
                    submit_screenshot = page.screenshot(full_page=True)
                    results['screenshots'].append({
                        'name': 'after_submit',
                        'data': base64.b64encode(submit_screenshot).decode('utf-8')
                    })
                    
                    results['steps'].append({'action': 'submit', 'status': 'success', 'message': '表单提交成功'})
                else:
                    results['steps'].append({'action': 'submit', 'status': 'warning', 'message': '未找到提交按钮'})
                
                results['message'] = '测试执行完成'
                results['success'] = True
                
            except PlaywrightTimeoutError as e:
                results['success'] = False
                results['message'] = f'页面加载超时: {str(e)}'
                results['steps'].append({'action': 'error', 'status': 'error', 'message': str(e)})
                
                error_screenshot = page.screenshot(full_page=True)
                results['screenshots'].append({
                    'name': 'error',
                    'data': base64.b64encode(error_screenshot).decode('utf-8')
                })
            
            except Exception as e:
                results['success'] = False
                results['message'] = f'测试执行出错: {str(e)}'
                results['steps'].append({'action': 'error', 'status': 'error', 'message': str(e)})
                
                try:
                    error_screenshot = page.screenshot(full_page=True)
                    results['screenshots'].append({
                        'name': 'error',
                        'data': base64.b64encode(error_screenshot).decode('utf-8')
                    })
                except:
                    pass
            
            finally:
                browser.close()
            
            return jsonify(results)
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Playwright 启动失败: {str(e)}',
            'steps': [{'action': 'error', 'status': 'error', 'message': str(e)}],
            'screenshots': []
        }), 500

@app.route('/api/test/generate-code/<int:form_id>')
def generate_test_code(form_id):
    form = Form.query.get_or_404(form_id)
    schema = json.loads(form.schema)
    fields = schema.get('fields', [])
    
    test_code = f'''# 自动生成的 Playwright 测试代码
# 表单: {form.name}
# 生成时间: {datetime.now().isoformat()}

from playwright.sync_api import sync_playwright

def test_form():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={{'width': 1280, 'height': 800}}
        )
        page = context.new_page()
        
        # 访问表单页面
        form_url = "http://localhost:2222/form/{form_id}"
        page.goto(form_url, wait_until='networkidle')
        
        # 填写表单字段
'''
    
    for field in fields:
        field_name = field.get('name')
        field_type = field.get('type')
        field_label = field.get('label', field_name)
        
        if field_type in ['text', 'email']:
            test_code += f'''
        # {field_label} ({field_type})
        page.fill('[name="{field_name}"]', "test_value")
'''
        elif field_type == 'number':
            test_code += f'''
        # {field_label} ({field_type})
        page.fill('[name="{field_name}"]', "123")
'''
        elif field_type == 'textarea':
            test_code += f'''
        # {field_label} ({field_type})
        page.fill('[name="{field_name}"]', "这是测试文本内容")
'''
        elif field_type == 'select':
            options = field.get('options', [])
            if options:
                test_code += f'''
        # {field_label} ({field_type})
        # 选项: {', '.join([o.get('label') for o in options])}
        page.select_option('[name="{field_name}"]', "{options[0].get('value')}")
'''
        elif field_type == 'radio':
            options = field.get('options', [])
            if options:
                test_code += f'''
        # {field_label} ({field_type})
        # 选项: {', '.join([o.get('label') for o in options])}
        page.check('input[name="{field_name}"][value="{options[0].get('value')}"]')
'''
        elif field_type == 'checkbox':
            options = field.get('options', [])
            if options:
                test_code += f'''
        # {field_label} ({field_type})
        # 选项: {', '.join([o.get('label') for o in options])}
'''
                for opt in options:
                    test_code += f'''        page.check('input[name="{field_name}"][value="{opt.get('value')}"]')
'''
        elif field_type == 'date':
            test_code += f'''
        # {field_label} ({field_type})
        page.fill('[name="{field_name}"]', "2024-01-01")
'''
    
    test_code += f'''
        # 截图
        page.screenshot(path="before_submit.png", full_page=True)
        
        # 提交表单
        submit_button = page.locator('button[type="submit"]')
        if submit_button.count() > 0:
            submit_button.click()
            page.wait_for_timeout(2000)
            page.screenshot(path="after_submit.png", full_page=True)
        
        browser.close()

if __name__ == "__main__":
    test_form()
'''
    
    return jsonify({
        'form_name': form.name,
        'form_id': form_id,
        'generated_at': datetime.now().isoformat(),
        'code': test_code
    })

def validate_form_data(form, data):
    validation_rules = json.loads(form.validation_rules) if form.validation_rules else {}
    schema = json.loads(form.schema) if form.schema else {}
    errors = {}
    
    fields = schema.get('fields', [])
    for field in fields:
        field_name = field.get('name')
        field_type = field.get('type')
        field_rules = validation_rules.get(field_name, {})
        
        if field_name not in data:
            if field_rules.get('required'):
                errors[field_name] = 'This field is required'
            continue
        
        value = data[field_name]
        
        if field_rules.get('required') and (value is None or value == ''):
            errors[field_name] = 'This field is required'
            continue
        
        if value is None or value == '':
            continue
        
        if field_type == 'number':
            try:
                num_value = float(value)
                if 'min' in field_rules and num_value < field_rules['min']:
                    errors[field_name] = f'Minimum value is {field_rules["min"]}'
                elif 'max' in field_rules and num_value > field_rules['max']:
                    errors[field_name] = f'Maximum value is {field_rules["max"]}'
            except (ValueError, TypeError):
                errors[field_name] = 'Must be a valid number'
        
        elif field_type == 'text':
            if 'min_length' in field_rules and len(str(value)) < field_rules['min_length']:
                errors[field_name] = f'Minimum length is {field_rules["min_length"]}'
            elif 'max_length' in field_rules and len(str(value)) > field_rules['max_length']:
                errors[field_name] = f'Maximum length is {field_rules["max_length"]}'
            elif 'pattern' in field_rules:
                import re
                if not re.match(field_rules['pattern'], str(value)):
                    errors[field_name] = field_rules.get('pattern_message', 'Invalid format')
        
        elif field_type == 'email':
            import re
            email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
            if not re.match(email_pattern, str(value)):
                errors[field_name] = 'Invalid email format'
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=2222, debug=True)
