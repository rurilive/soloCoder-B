#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复餐厅座位预订系统的推荐功能bug：
当客户人数为2时，系统会推荐1人的座位

问题原因：
1. alternative_times 和 alternative_dates 的推荐结果中没有存储 capacity 字段
2. get_available_tables 的过滤条件不够严格（if guest_count: 在 guest_count=0 时会跳过）
"""

import re

def fix_app_py():
    """修复 app.py 中的问题"""
    with open('/data/projects/work/soloCoder/soloCoder-B/app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # 修复1: 增强 get_available_tables 的过滤条件
    # 原代码: if guest_count:
    # 新代码: if guest_count is not None and guest_count > 0:
    old_pattern = r'(\s+)if guest_count:\n(\s+)tables = \[t for t in tables if t\.capacity >= guest_count\]'
    new_code = r'\1if guest_count is not None and guest_count > 0:\n\2tables = [t for t in tables if t.capacity >= guest_count]'
    
    content = re.sub(old_pattern, new_code, content)
    
    # 修复2: 在 alternative_times 的推荐结果中添加 capacity 字段
    # 原代码在 'table_number': first_table.table_number, 后缺少 'capacity': first_table.capacity,
    # 查找 alternative_times 的 append 代码块
    alt_times_pattern = r"""
        (\s+)recommendations\['alternative_times'\]\.append\(\{
        (\s+)'time': slot\.strftime\('%H:%M'\),
        (\s+)'end_time': end_time\.strftime\('%H:%M'\),
        (\s+)'tables_available': len\(available_tables\),
        (\s+)'table_id': first_table\.id,
        (\s+)'table_number': first_table\.table_number,
        (\s+)'date': original_date\.isoformat\(\)
        (\s+)\}\)
    """.strip()
    
    # 更简单的方式：找到 'table_number': first_table.table_number, 后面跟着 'date' 的情况
    # 这是 alternative_times 的模式
    alt_times_simple = r"""('table_number': first_table\.table_number,)
(\s+)'date': original_date\.isoformat\(\)"""
    
    alt_times_replacement = r"""\1
\2'capacity': first_table.capacity,
\2'date': original_date.isoformat()"""
    
    # 先检查是否还没有 capacity
    if "'capacity': first_table.capacity," not in content:
        # 修复 alternative_times：在 table_number 和 date 之间添加 capacity
        # alternative_times 中 table_number 后面是 date
        content = re.sub(
            r"('table_number': first_table\.table_number,)\n(\s+)('date': original_date\.isoformat\(\))",
            r"\1\n\2'capacity': first_table.capacity,\n\2\3",
            content
        )
        
        # 修复 alternative_dates：在 table_number 和 start_time 之间添加 capacity
        # alternative_dates 中 table_number 后面是 start_time
        content = re.sub(
            r"('table_number': first_table\.table_number,)\n(\s+)('start_time': original_start\.strftime\('%H:%M'\),)",
            r"\1\n\2'capacity': first_table.capacity,\n\2\3",
            content
        )
    
    # 写入文件
    with open('/data/projects/work/soloCoder/soloCoder-B/app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    if content != original_content:
        print("✓ app.py 已修复")
        # 验证修改
        if "'capacity': first_table.capacity," in content:
            print("  ✓ 已添加 capacity 字段到推荐结果中")
        if "guest_count is not None and guest_count > 0" in content:
            print("  ✓ 已增强 get_available_tables 的过滤条件")
    else:
        print("⚠ app.py 未修改（可能已经修复）")

def fix_template():
    """修复模板，显示 capacity 信息"""
    with open('/data/projects/work/soloCoder/soloCoder-B/templates/query_reservation.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # 修复 alternative_times 的显示
    # 原: {{ time.tables_available }} 桌可用 · {{ time.table_number }}号桌
    # 新: {{ time.tables_available }} 桌可用 · {{ time.table_number }}号桌 ({{ time.capacity }}人)
    if 'time.capacity' not in content:
        content = content.replace(
            '{{ time.tables_available }} 桌可用 · {{ time.table_number }}号桌',
            '{{ time.tables_available }} 桌可用 · {{ time.table_number }}号桌 ({{ time.capacity }}人)'
        )
    
    # 修复 alternative_dates 的显示
    # 原: {{ dt.tables_available }} 桌可用 · {{ dt.table_number }}号桌
    # 新: {{ dt.tables_available }} 桌可用 · {{ dt.table_number }}号桌 ({{ dt.capacity }}人)
    if 'dt.capacity' not in content:
        content = content.replace(
            '{{ dt.tables_available }} 桌可用 · {{ dt.table_number }}号桌',
            '{{ dt.tables_available }} 桌可用 · {{ dt.table_number }}号桌 ({{ dt.capacity }}人)'
        )
    
    with open('/data/projects/work/soloCoder/soloCoder-B/templates/query_reservation.html', 'w', encoding='utf-8') as f:
        f.write(content)
    
    if content != original_content:
        print("✓ query_reservation.html 已修复")
        print("  ✓ 已在 alternative_times 中显示容量信息")
        print("  ✓ 已在 alternative_dates 中显示容量信息")
    else:
        print("⚠ query_reservation.html 未修改（可能已经修复）")

def verify_fix():
    """验证修复是否成功"""
    print("\n=== 验证修复 ===")
    
    with open('/data/projects/work/soloCoder/soloCoder-B/app.py', 'r', encoding='utf-8') as f:
        app_content = f.read()
    
    with open('/data/projects/work/soloCoder/soloCoder-B/templates/query_reservation.html', 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    checks = [
        ("get_available_tables 过滤条件增强", "guest_count is not None and guest_count > 0" in app_content),
        ("alternative_times 包含 capacity", "'capacity': first_table.capacity" in app_content),
        ("模板显示 time.capacity", "time.capacity" in template_content),
        ("模板显示 dt.capacity", "dt.capacity" in template_content),
    ]
    
    all_ok = True
    for desc, ok in checks:
        status = "✓" if ok else "✗"
        print(f"  {status} {desc}")
        if not ok:
            all_ok = False
    
    return all_ok

if __name__ == '__main__':
    print("=== 修复餐厅座位预订系统推荐功能bug ===\n")
    
    print("1. 修复 app.py...")
    fix_app_py()
    
    print("\n2. 修复模板...")
    fix_template()
    
    if verify_fix():
        print("\n=== 修复完成！===")
        print("\n修复内容：")
        print("1. 增强 get_available_tables 的过滤条件，确保 guest_count > 0 时才过滤")
        print("2. 在 alternative_times 和 alternative_dates 的推荐结果中添加 capacity 字段")
        print("3. 在模板中显示推荐座位的容量信息")
        print("\n注意：如果数据库中已有旧的推荐数据（recommendation_suggestions 字段），")
        print("      需要重新生成推荐（即重新拒绝预订）才能看到修复效果。")
    else:
        print("\n=== 修复未完全完成，请检查 ===")
