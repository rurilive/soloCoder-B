import os
from app import create_app, db
from app.models import User, Problem, Submission, DailyProblem

app = create_app(os.getenv('FLASK_ENV') or 'default')


@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Problem': Problem,
        'Submission': Submission,
        'DailyProblem': DailyProblem
    }


@app.cli.command()
def initdb():
    """Initialize the database."""
    db.create_all()
    print('Database initialized.')
    
    admin = User.query.filter_by(email='admin@example.com').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@example.com',
            is_admin=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        
        two_sum_answer = '''def two_sum(nums, target):
    num_map = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in num_map:
            return [num_map[complement], i]
        num_map[num] = i
    return []'''
        
        test_problem = Problem(
            title='两数之和',
            description='给定一个整数数组 nums 和一个整数目标值 target，请你在该数组中找出 和为目标值 target 的那 两个 整数，并返回它们的数组下标。\n\n你可以假设每种输入只会对应一个答案。但是，数组中同一个元素在答案里不能重复出现。\n\n示例 1：\n输入：nums = [2,7,11,15], target = 9\n输出：[0,1]\n解释：因为 nums[0] + nums[1] == 9 ，返回 [0, 1] 。',
            difficulty='easy',
            function_name='two_sum',
            test_cases='[{"input": {"nums": [2,7,11,15], "target": 9}, "expected": [0, 1], "hidden": false}, {"input": {"nums": [3,2,4], "target": 6}, "expected": [1, 2], "hidden": true}]',
            correct_answer=two_sum_answer
        )
        db.session.add(test_problem)
        
        fib_answer = '''def fib(n):
    if n == 0:
        return 0
    if n == 1:
        return 1
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b'''
        
        fib_problem = Problem(
            title='斐波那契数',
            description='斐波那契数，通常用 F(n) 表示，形成的序列称为 斐波那契数列 。该数列由 0 和 1 开始，后面的每一项数字都是前面两项数字的和。也就是：\n\nF(0) = 0，F(1) = 1\nF(n) = F(n - 1) + F(n - 2)，其中 n > 1\n\n给你 n ，请计算 F(n) 。',
            difficulty='easy',
            function_name='fib',
            test_cases='[{"input": {"n": 2}, "expected": 1, "hidden": false}, {"input": {"n": 3}, "expected": 2, "hidden": false}, {"input": {"n": 10}, "expected": 55, "hidden": true}]',
            correct_answer=fib_answer
        )
        db.session.add(fib_problem)
        
        db.session.flush()
        
        from datetime import date
        DailyProblem.set_for_date(test_problem.id, date.today())
        
        db.session.commit()
        print('Default data created.')
        print('Admin user: admin@example.com / admin123')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5100)
