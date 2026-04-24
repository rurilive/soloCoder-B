from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, TextAreaField, SelectField, SelectMultipleField, IntegerField, DateTimeField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Length, Optional, NumberRange
from datetime import datetime


class AccessPasswordForm(FlaskForm):
    password = PasswordField('访问密码', validators=[
        DataRequired(message='请输入访问密码')
    ])
    submit = SubmitField('提交')


def create_survey_response_form(questions):
    from wtforms import Form as WTForm
    from wtforms import FieldList, FormField
    from wtforms.validators import StopValidation
    
    class QuestionForm(WTForm):
        pass
    
    class SurveyResponseForm(FlaskForm):
        submit = SubmitField('提交问卷')
    
    for question in questions:
        field_name = f'q_{question.id}'
        validators = []
        
        if question.is_required:
            validators.append(DataRequired(message='此题必填'))
        
        if question.type == 'text':
            field = TextAreaField(question.text, validators=validators)
        elif question.type == 'single_choice':
            choices = [(opt, opt) for opt in question.get_options_list()]
            field = SelectField(question.text, choices=choices, validators=validators, coerce=str)
        elif question.type == 'multiple_choice':
            choices = [(opt, opt) for opt in question.get_options_list()]
            min_choices = question.options.get('min_choices', 1) if question.options else 1
            field = SelectMultipleField(question.text, choices=choices, validators=validators, coerce=str)
        elif question.type == 'rating':
            min_value = question.options.get('min_value', 1) if question.options else 1
            max_value = question.options.get('max_value', 5) if question.options else 5
            field = IntegerField(question.text, validators=validators + [
                NumberRange(min=min_value, max=max_value, message=f'评分必须在 {min_value} 到 {max_value} 之间')
            ])
        elif question.type == 'scale':
            items = question.options.get('items', []) if question.options else []
            scale_values = question.options.get('scale_values', []) if question.options else []
            scale_labels = question.options.get('scale_labels', []) if question.options else []
            
            choices = []
            for i, value in enumerate(scale_values):
                label = scale_labels[i] if i < len(scale_labels) else str(value)
                choices.append((str(value), label))
            
            class ScaleItemForm(WTForm):
                pass
            
            for i, item in enumerate(items):
                item_text = item.get('text', item) if isinstance(item, dict) else item
                item_field = SelectField(item_text, choices=choices, validators=validators if question.is_required else [], coerce=str)
                setattr(ScaleItemForm, f'item_{i}', item_field)
            
            field = FormField(ScaleItemForm)
        elif question.type == 'date':
            field = DateTimeField(question.text, format='%Y-%m-%d', validators=validators)
        else:
            field = StringField(question.text, validators=validators)
        
        setattr(SurveyResponseForm, field_name, field)
    
    return SurveyResponseForm
