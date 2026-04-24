from collections import Counter
from datetime import datetime, timedelta
import math
import re
import json

try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False


def normalize_option_value(opt):
    if isinstance(opt, dict):
        if 'value' in opt:
            return str(opt['value'])
        elif 'label' in opt:
            return str(opt['label'])
    return str(opt)


def normalize_answer_value(value):
    if value is None:
        return None
    value_str = str(value).strip()
    try:
        parsed = json.loads(value_str)
        if isinstance(parsed, str):
            return parsed.strip()
        return str(parsed)
    except (json.JSONDecodeError, ValueError):
        return value_str


def calculate_percentage(count, total):
    if total == 0:
        return 0.0
    return round((count / total) * 100, 1)


def calculate_median(values):
    if not values:
        return None
    sorted_values = sorted(values)
    n = len(sorted_values)
    mid = n // 2
    if n % 2 == 0:
        return (sorted_values[mid - 1] + sorted_values[mid]) / 2
    return sorted_values[mid]


def analyze_word_frequency(texts, top_n=20, stop_words=None):
    if stop_words is None:
        stop_words = set()
    
    all_words = []
    
    for text in texts:
        if not text or not text.strip():
            continue
        
        if JIEBA_AVAILABLE:
            words = jieba.cut(text)
        else:
            words = re.findall(r'[\u4e00-\u9fa5]+|[a-zA-Z]+', text)
        
        for word in words:
            word = word.strip()
            if len(word) > 1 and word not in stop_words:
                all_words.append(word)
    
    word_counts = Counter(all_words)
    top_words = word_counts.most_common(top_n)
    
    return [{'word': word, 'count': count} for word, count in top_words]


def group_by_time(responses, interval='day'):
    result = []
    grouped = {}
    
    for response in responses:
        submitted_at = response.submitted_at
        if not submitted_at:
            continue
        
        if interval == 'day':
            key = submitted_at.strftime('%Y-%m-%d')
        elif interval == 'week':
            start_of_week = submitted_at - timedelta(days=submitted_at.weekday())
            key = start_of_week.strftime('%Y-%m-%d')
        elif interval == 'month':
            key = submitted_at.strftime('%Y-%m')
        elif interval == 'hour':
            key = submitted_at.strftime('%Y-%m-%d %H:00')
        else:
            key = submitted_at.strftime('%Y-%m-%d')
        
        if key not in grouped:
            grouped[key] = 0
        grouped[key] += 1
    
    sorted_keys = sorted(grouped.keys())
    for key in sorted_keys:
        result.append({
            'time': key,
            'count': grouped[key]
        })
    
    return result


def get_time_range_start(interval='day'):
    now = datetime.utcnow()
    
    if interval == 'day':
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif interval == 'week':
        return now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=now.weekday())
    elif interval == 'month':
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    return now


def calculate_statistics_for_single_choice(question, valid_answers):
    options = question.get_options_list()
    total_responses = len(valid_answers)
    
    option_map = {}
    for opt in options:
        normalized = normalize_option_value(opt)
        option_map[normalized] = opt
    
    option_counts = {normalize_option_value(opt): 0 for opt in options}
    
    for answer in valid_answers:
        if not answer.value:
            continue
        value_normalized = normalize_answer_value(answer.value)
        if value_normalized in option_counts:
            option_counts[value_normalized] += 1
        else:
            try:
                value_int = int(float(value_normalized))
                if str(value_int) in option_counts:
                    option_counts[str(value_int)] += 1
            except (ValueError, TypeError):
                pass
    
    result_options = []
    for opt in options:
        normalized = normalize_option_value(opt)
        count = option_counts[normalized]
        result_options.append({
            'value': opt,
            'count': count,
            'percentage': calculate_percentage(count, total_responses)
        })
    
    return {
        'type': 'single_choice',
        'options': result_options
    }


def calculate_statistics_for_multiple_choice(question, valid_answers):
    options = question.get_options_list()
    total_responses = len(valid_answers)
    
    option_counts = {normalize_option_value(opt): 0 for opt in options}
    selection_counts = []
    total_selections = 0
    
    def match_and_count(opt_value):
        opt_normalized = normalize_option_value(opt_value)
        if opt_normalized in option_counts:
            option_counts[opt_normalized] += 1
            return True
        try:
            opt_int = int(float(opt_normalized))
            if str(opt_int) in option_counts:
                option_counts[str(opt_int)] += 1
                return True
        except (ValueError, TypeError):
            pass
        return False
    
    for answer in valid_answers:
        try:
            value = json.loads(answer.value) if answer.value else []
            if isinstance(value, list):
                selection_count = len(value)
                if selection_count > 0:
                    selection_counts.append(selection_count)
                    total_selections += selection_count
                    for opt in value:
                        match_and_count(opt)
        except (json.JSONDecodeError, ValueError):
            pass
    
    result_options = []
    for opt in options:
        normalized = normalize_option_value(opt)
        count = option_counts[normalized]
        result_options.append({
            'value': opt,
            'count': count,
            'percentage': calculate_percentage(count, total_selections) if total_selections > 0 else 0.0
        })
    
    selection_distribution = []
    if selection_counts:
        selection_counter = Counter(selection_counts)
        max_selections = max(selection_counter.keys()) if selection_counter else 0
        for i in range(1, max_selections + 1):
            count = selection_counter.get(i, 0)
            selection_distribution.append({
                'selections': i,
                'count': count,
                'percentage': calculate_percentage(count, total_responses)
            })
    
    return {
        'type': 'multiple_choice',
        'total_selections': total_selections,
        'options': result_options,
        'selection_distribution': selection_distribution
    }


def calculate_statistics_for_rating(question, valid_answers):
    options = question.options or {}
    min_value = options.get('min_value', 1)
    max_value = options.get('max_value', 5)
    
    values = []
    value_counts = {v: 0 for v in range(min_value, max_value + 1)}
    
    for answer in valid_answers:
        try:
            value = int(answer.value)
            if min_value <= value <= max_value:
                values.append(value)
                value_counts[value] += 1
        except (ValueError, TypeError):
            pass
    
    total_responses = len(values)
    average = sum(values) / total_responses if total_responses > 0 else 0.0
    median = calculate_median(values)
    
    distribution = []
    for v in range(min_value, max_value + 1):
        count = value_counts[v]
        distribution.append({
            'value': v,
            'count': count,
            'percentage': calculate_percentage(count, total_responses)
        })
    
    return {
        'type': 'rating',
        'min_value': min_value,
        'max_value': max_value,
        'average': round(average, 2),
        'median': median,
        'distribution': distribution
    }


def calculate_statistics_for_scale(question, valid_answers):
    import json
    
    options = question.options or {}
    items = options.get('items', [])
    scale_values = options.get('scale_values', [1, 2, 3, 4, 5])
    scale_values = [int(v) for v in scale_values]
    
    item_stats = []
    all_values = []
    
    for item_idx, item in enumerate(items):
        item_key = f'item_{item_idx}'
        item_values = []
        value_counts = {v: 0 for v in scale_values}
        
        for answer in valid_answers:
            try:
                answer_dict = json.loads(answer.value) if answer.value else {}
                value_str = answer_dict.get(item_key)
                if value_str is not None:
                    value = int(value_str)
                    if value in scale_values:
                        item_values.append(value)
                        value_counts[value] += 1
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
        
        total_responses = len(item_values)
        average = sum(item_values) / total_responses if total_responses > 0 else 0.0
        all_values.extend(item_values)
        
        distribution = []
        for v in scale_values:
            count = value_counts[v]
            distribution.append({
                'value': v,
                'count': count,
                'percentage': calculate_percentage(count, total_responses)
            })
        
        item_stats.append({
            'item_id': item_key,
            'text': item,
            'average': round(average, 2),
            'distribution': distribution
        })
    
    overall_average = sum(all_values) / len(all_values) if all_values else 0.0
    
    return {
        'type': 'scale',
        'items': item_stats,
        'overall_average': round(overall_average, 2)
    }


def calculate_statistics_for_text(question, valid_answers):
    texts = []
    sample_responses = []
    
    for answer in valid_answers:
        if answer.value and answer.value.strip():
            texts.append(answer.value)
            if len(sample_responses) < 10:
                sample_responses.append(answer.value[:200])
    
    word_frequency = analyze_word_frequency(texts, top_n=20)
    
    return {
        'type': 'text',
        'response_count': len(texts),
        'word_frequency': word_frequency,
        'sample_responses': sample_responses
    }


def calculate_statistics_for_date(question, valid_answers):
    dates = []
    
    for answer in valid_answers:
        try:
            if answer.value:
                dt = datetime.strptime(answer.value, '%Y-%m-%d')
                dates.append(dt)
        except (ValueError, TypeError):
            pass
    
    if not dates:
        return {
            'type': 'date',
            'date_range': {'min': None, 'max': None},
            'distribution': []
        }
    
    min_date = min(dates)
    max_date = max(dates)
    
    month_counts = Counter()
    for dt in dates:
        month_key = dt.strftime('%Y-%m')
        month_counts[month_key] += 1
    
    sorted_months = sorted(month_counts.keys())
    distribution = []
    for month in sorted_months:
        distribution.append({
            'month': month,
            'count': month_counts[month],
            'percentage': calculate_percentage(month_counts[month], len(dates))
        })
    
    return {
        'type': 'date',
        'date_range': {
            'min': min_date.strftime('%Y-%m-%d'),
            'max': max_date.strftime('%Y-%m-%d')
        },
        'distribution': distribution
    }
