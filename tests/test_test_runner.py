import pytest
import json
from app.test_runner import run_tests, get_submission_status


class TestTestRunner:
    def test_run_tests_correct_code(self):
        code = '''
def two_sum(nums, target):
    num_map = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in num_map:
            return [num_map[complement], i]
        num_map[num] = i
    return []
'''
        
        test_cases = [
            {'input': {'nums': [2, 7, 11, 15], 'target': 9}, 'expected': [0, 1]},
            {'input': {'nums': [3, 2, 4], 'target': 6}, 'expected': [1, 2]},
        ]
        
        result = run_tests(code, 'two_sum', test_cases, timeout=5)
        
        assert result['status'] == 'success'
        assert result['all_passed'] is True
        assert len(result['results']) == 2
        assert all(r['passed'] for r in result['results'])

    def test_run_tests_wrong_answer(self):
        code = '''
def two_sum(nums, target):
    return [0, 0]
'''
        
        test_cases = [
            {'input': {'nums': [2, 7, 11, 15], 'target': 9}, 'expected': [0, 1]},
        ]
        
        result = run_tests(code, 'two_sum', test_cases, timeout=5)
        
        assert result['status'] == 'success'
        assert result['all_passed'] is False
        assert result['results'][0]['passed'] is False

    def test_run_tests_function_not_found(self):
        code = '''
def wrong_function(nums, target):
    return [0, 1]
'''
        
        test_cases = [
            {'input': {'nums': [2, 7, 11, 15], 'target': 9}, 'expected': [0, 1]},
        ]
        
        result = run_tests(code, 'two_sum', test_cases, timeout=5)
        
        assert result['status'] == 'error'
        assert '函数' in result['error']
        assert 'two_sum' in result['error']

    def test_run_tests_syntax_error(self):
        code = '''
def two_sum(nums, target)
    return [0, 1]
'''
        
        test_cases = [
            {'input': {'nums': [2, 7, 11, 15], 'target': 9}, 'expected': [0, 1]},
        ]
        
        result = run_tests(code, 'two_sum', test_cases, timeout=5)
        
        assert result['status'] == 'error'
        assert '语法错误' in result['error']

    def test_run_tests_runtime_error(self):
        code = '''
def two_sum(nums, target):
    raise ValueError('Something went wrong')
'''
        
        test_cases = [
            {'input': {'nums': [2, 7, 11, 15], 'target': 9}, 'expected': [0, 1]},
        ]
        
        result = run_tests(code, 'two_sum', test_cases, timeout=5)
        
        assert result['status'] == 'error'

    def test_run_tests_list_arguments(self):
        code = '''
def add(a, b):
    return a + b
'''
        
        test_cases = [
            {'input': [2, 3], 'expected': 5},
            {'input': [10, 20], 'expected': 30},
        ]
        
        result = run_tests(code, 'add', test_cases, timeout=5)
        
        assert result['status'] == 'success'
        assert result['all_passed'] is True

    def test_run_tests_single_argument(self):
        code = '''
def square(n):
    return n * n
'''
        
        test_cases = [
            {'input': 2, 'expected': 4},
            {'input': 5, 'expected': 25},
        ]
        
        result = run_tests(code, 'square', test_cases, timeout=5)
        
        assert result['status'] == 'success'
        assert result['all_passed'] is True

    def test_get_submission_status_success_accepted(self):
        test_result = {
            'status': 'success',
            'all_passed': True
        }
        
        status = get_submission_status(test_result)
        assert status == 'accepted'

    def test_get_submission_status_success_wrong(self):
        test_result = {
            'status': 'success',
            'all_passed': False
        }
        
        status = get_submission_status(test_result)
        assert status == 'wrong_answer'

    def test_get_submission_status_timeout(self):
        test_result = {
            'status': 'timeout'
        }
        
        status = get_submission_status(test_result)
        assert status == 'time_limit_exceeded'

    def test_get_submission_status_error(self):
        test_result = {
            'status': 'error'
        }
        
        status = get_submission_status(test_result)
        assert status == 'runtime_error'

    def test_run_tests_with_hidden_test_cases(self):
        code = '''
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)
'''
        
        test_cases = [
            {'input': {'n': 2}, 'expected': 1, 'hidden': False},
            {'input': {'n': 10}, 'expected': 55, 'hidden': True},
        ]
        
        result = run_tests(code, 'fib', test_cases, timeout=10)
        
        assert result['status'] == 'success'
        assert result['all_passed'] is True
        assert len(result['results']) == 2

    def test_run_tests_fib_correct(self):
        code = '''
def fib(n):
    if n == 0:
        return 0
    if n == 1:
        return 1
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
'''
        
        test_cases = [
            {'input': {'n': 0}, 'expected': 0},
            {'input': {'n': 1}, 'expected': 1},
            {'input': {'n': 2}, 'expected': 1},
            {'input': {'n': 3}, 'expected': 2},
            {'input': {'n': 10}, 'expected': 55},
        ]
        
        result = run_tests(code, 'fib', test_cases, timeout=5)
        
        assert result['status'] == 'success'
        assert result['all_passed'] is True
        assert all(r['passed'] for r in result['results'])
