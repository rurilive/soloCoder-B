from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import os
import re

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

@app.route('/api/test/api', methods=['POST'])
def run_api_test():
    data = request.get_json()
    form_id = data.get('form_id')
    test_data = data.get('test_data', {})
    
    if not form_id:
        return jsonify({'error': 'Form ID is required'}), 400
    
    form = Form.query.get(form_id)
    if not form:
        return jsonify({'error': 'Form not found'}), 404
    
    results = {
        'steps': [],
        'success': True,
        'message': '',
        'validation_result': None,
        'submission_id': None
    }
    
    try:
        fields = json.loads(form.schema).get('fields', [])
        
        results['steps'].append({
            'action': 'validate',
            'status': 'running',
            'message': '正在验证表单数据...'
        })
        
        validation_result = validate_form_data(form, test_data)
        results['validation_result'] = validation_result
        
        if validation_result['valid']:
            results['steps'].append({
                'action': 'validate',
                'status': 'success',
                'message': '数据验证通过'
            })
            
            results['steps'].append({
                'action': 'submit',
                'status': 'running',
                'message': '正在提交表单...'
            })
            
            submission = FormSubmission(
                form_id=form_id,
                data=json.dumps(test_data)
            )
            db.session.add(submission)
            db.session.commit()
            
            results['submission_id'] = submission.id
            results['steps'].append({
                'action': 'submit',
                'status': 'success',
                'message': f'表单提交成功，提交ID: {submission.id}'
            })
            
            results['message'] = 'API测试执行完成'
            results['success'] = True
        else:
            results['steps'].append({
                'action': 'validate',
                'status': 'error',
                'message': '数据验证失败'
            })
            
            error_details = []
            for field_name, error_msg in validation_result['errors'].items():
                error_details.append(f'{field_name}: {error_msg}')
                results['steps'].append({
                    'action': 'validate_error',
                    'field': field_name,
                    'status': 'error',
                    'message': f'{field_name}: {error_msg}'
                })
            
            results['message'] = '数据验证失败: ' + '; '.join(error_details)
            results['success'] = False
            
    except Exception as e:
        results['success'] = False
        results['message'] = f'测试执行出错: {str(e)}'
        results['steps'].append({
            'action': 'error',
            'status': 'error',
            'message': str(e)
        })
    
    return jsonify(results)

@app.route('/api/test/generate-code/<int:form_id>')
def generate_test_code(form_id):
    form = Form.query.get_or_404(form_id)
    schema = json.loads(form.schema)
    fields = schema.get('fields', [])
    
    fields_info = []
    for field in fields:
        field_info = {
            'name': field.get('name'),
            'type': field.get('type'),
            'label': field.get('label', field.get('name')),
            'required': field.get('required', False),
            'options': field.get('options', [])
        }
        fields_info.append(field_info)
    
    api_test_code = generate_api_test_code(form, fields_info)
    playwright_test_code = generate_playwright_test_code(form, fields_info)
    
    return jsonify({
        'form_name': form.name,
        'form_id': form_id,
        'generated_at': datetime.now().isoformat(),
        'api_test_code': api_test_code,
        'playwright_test_code': playwright_test_code
    })

def generate_api_test_code(form, fields_info):
    form_id_str = str(form.id)
    form_name_str = form.name
    timestamp = datetime.now().isoformat()
    
    fields_doc = '\n'.join([f"#   - {f['label']} ({f['name']}): {f['type']}" for f in fields_info])
    
    test_data_dict = {}
    for field in fields_info:
        field_name = field['name']
        field_type = field['type']
        
        if field_type in ['text', 'email']:
            test_data_dict[field_name] = 'test_value' if field_type == 'text' else 'test@example.com'
        elif field_type == 'number':
            test_data_dict[field_name] = 123
        elif field_type == 'textarea':
            test_data_dict[field_name] = '这是测试文本内容'
        elif field_type in ['select', 'radio']:
            if field['options']:
                test_data_dict[field_name] = field['options'][0]['value']
        elif field_type == 'checkbox':
            if field['options']:
                test_data_dict[field_name] = [opt['value'] for opt in field['options'][:2]]
        elif field_type == 'date':
            test_data_dict[field_name] = '2024-01-01'
    
    def format_value(v):
        if isinstance(v, str):
            return f"'{v}'"
        elif isinstance(v, list):
            list_items = ', '.join([f"'{item}'" for item in v])
            return f"[{list_items}]"
        else:
            return str(v)
    
    test_data_lines = []
    test_data_lines.append("    test_data = {")
    for k, v in test_data_dict.items():
        test_data_lines.append(f"        '{k}': {format_value(v)},")
    test_data_lines.append("    }")
    test_data_code = '\n'.join(test_data_lines)
    
    code = f"""# API 测试代码 - 不需要浏览器
# 表单: {form_name_str}
# 生成时间: {timestamp}
# 
# 字段说明:
{fields_doc}

import requests

def test_form_api():
    \"\"\"
    API 测试 - 直接调用后端验证和提交接口
    优点: 快速、稳定、不需要浏览器
    用途: 验证后端逻辑、数据校验规则
    \"\"\"
    
    base_url = "http://localhost:2222"
    form_id = {form_id_str}
    
{test_data_code}
    
    print("=" * 60)
    print("API 测试开始")
    print("=" * 60)
    
    print("\\n1. 准备测试数据:")
    for key, value in test_data.items():
        print(f"   - {{key}}: {{value}}")
    
    print("\\n2. 提交表单到 API...")
    try:
        response = requests.post(
            f"{{base_url}}/api/forms/{{form_id}}/submit",
            headers={{"Content-Type": "application/json"}},
            json=test_data,
            timeout=10
        )
        
        result = response.json()
        
        if response.status_code == 200 and result.get('valid'):
            print("   ✅ 提交成功!")
            print(f"   📋 提交ID: {{result.get('submission_id')}}")
            print(f"   📝 消息: {{result.get('message')}}")
            return True
        else:
            print("   ❌ 提交失败!")
            print(f"   📋 状态码: {{response.status_code}}")
            
            if result.get('errors'):
                print("\\n   验证错误:")
                for field, error in result['errors'].items():
                    print(f"      - {{field}}: {{error}}")
            
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ 请求错误: {{str(e)}}")
        return False

def test_validation():
    \"\"\"
    测试数据验证规则
    \"\"\"
    print("\\n" + "=" * 60)
    print("数据验证测试")
    print("=" * 60)
    
    base_url = "http://localhost:2222"
    form_id = {form_id_str}
    
    invalid_test_cases = [
        {{
            "name": "空数据测试",
            "data": {{}},
            "expected": "应该失败 - 必填字段未填写"
        }},
        {{
            "name": "无效邮箱测试",
            "data": {{"email": "not-an-email"}},
            "expected": "应该失败 - 邮箱格式错误"
        }}
    ]
    
    for case in invalid_test_cases:
        print(f"\\n测试: {{case['name']}}")
        print(f"期望: {{case['expected']}}")
        
        try:
            response = requests.post(
                f"{{base_url}}/api/forms/{{form_id}}/submit",
                headers={{"Content-Type": "application/json"}},
                json=case['data'],
                timeout=10
            )
            
            result = response.json()
            
            if not result.get('valid'):
                print("   ✅ 符合预期 - 验证失败")
                if result.get('errors'):
                    print("   错误信息:")
                    for field, error in result['errors'].items():
                        print(f"      - {{field}}: {{error}}")
            else:
                print("   ⚠️  意外通过 - 可能没有必填字段或验证规则")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ 请求错误: {{str(e)}}")

if __name__ == "__main__":
    success = test_form_api()
    test_validation()
    
    print("\\n" + "=" * 60)
    if success:
        print("✅ 所有测试通过!")
    else:
        print("⚠️  部分测试失败，请检查输出")
    print("=" * 60)
"""
    
    return code

def generate_playwright_test_code(form, fields_info):
    fields_doc = '\n'.join([f"#   - {f['label']} ({f['name']}): {f['type']}" for f in fields_info])
    
    def build_fill_code():
        lines = []
        for field in fields_info:
            field_name = field['name']
            field_type = field['type']
            field_label = field['label']
            
            if field_type in ['text', 'email']:
                test_value = 'test_value' if field_type == 'text' else 'test@example.com'
                lines.append("")
                lines.append(f"        # {field_label}")
                lines.append(f"        page.fill('[name=\"{field_name}\"]', '{test_value}')")
                lines.append(f"        print('   ✅ 已填写: {field_label}')")
            elif field_type == 'number':
                lines.append("")
                lines.append(f"        # {field_label}")
                lines.append(f"        page.fill('[name=\"{field_name}\"]', '123')")
                lines.append(f"        print('   ✅ 已填写: {field_label}')")
            elif field_type == 'textarea':
                lines.append("")
                lines.append(f"        # {field_label}")
                lines.append(f"        page.fill('[name=\"{field_name}\"]', '这是测试文本内容')")
                lines.append(f"        print('   ✅ 已填写: {field_label}')")
            elif field_type == 'select':
                if field['options']:
                    first_option = field['options'][0]
                    lines.append("")
                    lines.append(f"        # {field_label}")
                    lines.append(f"        page.select_option('[name=\"{field_name}\"]', '{first_option['value']}')")
                    lines.append(f"        print('   ✅ 已选择: {field_label} = {first_option['label']}')")
            elif field_type == 'radio':
                if field['options']:
                    first_option = field['options'][0]
                    lines.append("")
                    lines.append(f"        # {field_label}")
                    lines.append(f"        page.check(\"input[name='{field_name}'][value='{first_option['value']}']\")")
                    lines.append(f"        print('   ✅ 已选择: {field_label} = {first_option['label']}')")
            elif field_type == 'checkbox':
                if field['options']:
                    first_option = field['options'][0]
                    lines.append("")
                    lines.append(f"        # {field_label}")
                    lines.append(f"        page.check(\"input[name='{field_name}'][value='{first_option['value']}']\")")
                    lines.append(f"        print('   ✅ 已选择: {field_label} = {first_option['label']}')")
            elif field_type == 'date':
                lines.append("")
                lines.append(f"        # {field_label}")
                lines.append(f"        page.fill('[name=\"{field_name}\"]', '2024-01-01')")
                lines.append(f"        print('   ✅ 已填写: {field_label}')")
        
        return '\n'.join(lines)
    
    fill_code = build_fill_code()
    
    code_parts = [
        f"# Playwright 端到端测试代码",
        f"# 表单: {form.name}",
        f"# 生成时间: {datetime.now().isoformat()}",
        f"# ",
        f"# 字段说明:",
        fields_doc,
        f"#",
        f"# 使用说明:",
        f"# 1. 确保服务器已启动: python app.py",
        f"# 2. 安装依赖: pip install playwright",
        f"# 3. 安装浏览器: playwright install chromium",
        f"# 4. 运行测试: python this_file.py",
        f"",
        f"from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError",
        f"import os",
        f"",
        f"def test_form_e2e(headless=True):",
        f'    """',
        f'    端到端测试 - 使用 Playwright 模拟真实用户操作',
        f'    优点: 测试完整的用户流程、验证前端交互',
        f'    用途: 验证表单渲染、用户交互、提交流程',
        f'    """',
        f"    ",
        f'    print("=" * 60)',
        f'    print("Playwright 端到端测试开始")',
        f'    print("=" * 60)',
        f"    ",
        f"    with sync_playwright() as p:",
        f'        print("\\n1. 启动浏览器...")',
        f"        browser = p.chromium.launch(headless=headless)",
        f"        context = browser.new_context(",
        f'            viewport={{"width": 1280, "height": 800}},',
        f'            locale="zh-CN"',
        f"        )",
        f"        page = context.new_page()",
        f"        ",
        f"        form_url = f\"http://localhost:2222/form/{form.id}\"",
        f"        ",
        f"        try:",
        f'            print(f"\\n2. 访问表单页面: {{form_url}}")',
        f'            page.goto(form_url, wait_until="networkidle", timeout=30000)',
        f"            ",
        f'            page.screenshot(path="screenshot_01_page_loaded.png", full_page=True)',
        f'            print("   ✅ 页面加载成功")',
        f'            print("   📸 截图已保存: screenshot_01_page_loaded.png")',
        f"            ",
        f'            print(f"\\n3. 填写表单字段...")',
        fill_code,
        f"            ",
        f'            page.screenshot(path="screenshot_02_fields_filled.png", full_page=True)',
        f'            print("\\n   📸 截图已保存: screenshot_02_fields_filled.png")',
        f"            ",
        f'            print(f"\\n4. 提交表单...")',
        f'            submit_button = page.locator(\'button[type="submit"]\')',
        f"            ",
        f"            if submit_button.count() > 0:",
        f"                submit_button.click()",
        f"                ",
        f'                print("   ⏳ 等待提交响应...")',
        f'                page.wait_for_timeout(3000)',
        f"                ",
        f'                page.screenshot(path="screenshot_03_after_submit.png", full_page=True)',
        f'                print("   ✅ 提交完成")',
        f'                print("   📸 截图已保存: screenshot_03_after_submit.png")',
        f"            else:",
        f'                print("   ⚠️  未找到提交按钮")',
        f"            ",
        f'            print("\\n" + "=" * 60)',
        f'            print("✅ 测试完成!")',
        f'            print("=" * 60)',
        f'            print("\\n生成的截图文件:")',
        f"            for f in os.listdir('.'):",
        f"                if f.startswith('screenshot_') and f.endswith('.png'):",
        f'                    print(f"   - {{f}}")',
        f"            ",
        f"            return True",
        f"            ",
        f"        except PlaywrightTimeoutError as e:",
        f'            print(f"\\n❌ 超时错误: {{str(e)}}")',
        f'            page.screenshot(path="screenshot_error.png", full_page=True)',
        f'            print("   📸 错误截图已保存: screenshot_error.png")',
        f"            return False",
        f"            ",
        f"        except Exception as e:",
        f'            print(f"\\n❌ 测试失败: {{str(e)}}")',
        f"            try:",
        f'                page.screenshot(path="screenshot_error.png", full_page=True)',
        f'                print("   📸 错误截图已保存: screenshot_error.png")',
        f"            except:",
        f"                pass",
        f"            return False",
        f"            ",
        f"        finally:",
        f"            browser.close()",
        f"",
        f"def test_linkage_rules():",
        f'    """',
        f'    测试表单联动规则',
        f'    """',
        f'    print("\\n" + "=" * 60)',
        f'    print("联动规则测试 (需要手动实现)")',
        f'    print("=" * 60)',
        f'    print("\\n提示: 如果表单包含联动规则，可以在此添加测试:")',
        f'    print("# 示例: 测试字段显示/隐藏联动")',
        f'    print("# 1. 填写触发字段")',
        f'    print("# page.fill(\'[name=trigger_field]\', \'某些值\')")',
        f'    print("# 2. 等待联动生效")',
        f'    print("# page.wait_for_timeout(500)")',
        f'    print("# 3. 验证目标字段状态")',
        f'    print("# target_field = page.locator(\'[data-field-name=target_field]\')")',
        f'    print("# assert target_field.is_visible() == expected_visibility")',
        f"",
        f"if __name__ == \"__main__\":",
        f"    import sys",
        f"    ",
        f"    headless = len(sys.argv) > 1 and sys.argv[1] == '--headless'",
        f"    ",
        f'    print("\\n提示:")',
        f'    print("  - 运行可视化测试: python this_file.py")',
        f'    print("  - 运行无头测试:   python this_file.py --headless")',
        f"    print()",
        f"    ",
        f"    success = test_form_e2e(headless=headless)",
        f"    test_linkage_rules()",
        f"    ",
        f"    sys.exit(0 if success else 1)",
    ]
    
    return '\n'.join(code_parts)

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
