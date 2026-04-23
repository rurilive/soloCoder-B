import sys
import json
import time
import traceback
import multiprocessing
from datetime import datetime


def run_test_in_process(code, function_name, test_cases, results_queue):
    results = []
    try:
        local_vars = {}
        exec(code, local_vars)
        
        if function_name not in local_vars:
            results_queue.put({
                'status': 'error',
                'error': f'函数 {function_name} 未找到，请检查函数名是否正确。',
                'results': []
            })
            return
        
        func = local_vars[function_name]
        
        for i, test_case in enumerate(test_cases):
            input_data = test_case.get('input', {})
            expected = test_case.get('expected')
            hidden = test_case.get('hidden', False)
            
            start_time = time.time()
            try:
                if isinstance(input_data, dict):
                    output = func(**input_data)
                elif isinstance(input_data, list):
                    output = func(*input_data)
                else:
                    output = func(input_data)
                runtime = (time.time() - start_time) * 1000
                
                passed = output == expected
                
                result = {
                    'test_case': i + 1,
                    'passed': passed,
                    'runtime': round(runtime, 2),
                    'hidden': hidden,
                }
                
                if not hidden:
                    result['input'] = input_data
                    result['expected'] = expected
                    result['output'] = output
                
                results.append(result)
                
                if not passed:
                    break
                    
            except Exception as e:
                runtime = (time.time() - start_time) * 1000
                results_queue.put({
                    'status': 'error',
                    'error': f'运行时错误: {str(e)}',
                    'traceback': traceback.format_exc(),
                    'runtime': round(runtime, 2),
                    'results': []
                })
                return
        
        all_passed = all(r.get('passed', False) for r in results)
        
        results_queue.put({
            'status': 'success',
            'all_passed': all_passed,
            'results': results
        })
        
    except SyntaxError as e:
        results_queue.put({
            'status': 'error',
            'error': f'语法错误: 第 {e.lineno} 行 - {e.msg}',
            'results': []
        })
    except Exception as e:
        results_queue.put({
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc(),
            'results': []
        })


def run_tests(code, function_name, test_cases, timeout=5):
    results_queue = multiprocessing.Queue()
    
    process = multiprocessing.Process(
        target=run_test_in_process,
        args=(code, function_name, test_cases, results_queue)
    )
    
    start_time = time.time()
    process.start()
    process.join(timeout=timeout)
    
    total_runtime = (time.time() - start_time) * 1000
    
    if process.is_alive():
        process.terminate()
        process.join()
        return {
            'status': 'timeout',
            'error': f'运行超时（限制 {timeout} 秒）',
            'runtime': round(total_runtime, 2),
            'results': []
        }
    
    try:
        result = results_queue.get(timeout=1)
        if 'runtime' not in result:
            result['runtime'] = round(total_runtime, 2)
        return result
    except:
        return {
            'status': 'error',
            'error': '无法获取测试结果',
            'runtime': round(total_runtime, 2),
            'results': []
        }


def get_submission_status(test_result):
    status = test_result.get('status')
    
    if status == 'timeout':
        return 'time_limit_exceeded'
    elif status == 'error':
        return 'runtime_error'
    elif status == 'success':
        if test_result.get('all_passed'):
            return 'accepted'
        else:
            return 'wrong_answer'
    
    return 'runtime_error'
