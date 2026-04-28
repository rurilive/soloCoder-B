#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处理旧数据并验证过滤逻辑
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, time, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurant.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

from models import Restaurant, Table, Reservation, User

def safe_parse_recommendations(data_str):
    if not data_str:
        return None
    try:
        return json.loads(data_str)
    except (json.JSONDecodeError, TypeError):
        return None

def verify_filter_logic():
    """验证过滤逻辑是否正常工作"""
    print("=" * 60)
    print("验证过滤逻辑")
    print("=" * 60)
    
    with app.app_context():
        # 检查所有餐桌容量
        tables = Table.query.filter_by(is_active=True).all()
        print(f"\n数据库中共有 {len(tables)} 张活跃餐桌：")
        for t in tables:
            print(f"  桌号: {t.table_number}, 容量: {t.capacity}, 餐厅: {t.restaurant.name}")
        
        # 检查被拒绝的预订
        rejected_reservations = Reservation.query.filter_by(status='rejected').all()
        print(f"\n被拒绝的预订: {len(rejected_reservations)} 个")
        
        for res in rejected_reservations:
            print(f"\n  预订ID: {res.id}")
            print(f"  客人数量: {res.guest_count}")
            print(f"  原订桌号: {res.table.table_number} (容量: {res.table.capacity})")
            
            if res.recommendation_suggestions:
                recs = safe_parse_recommendations(res.recommendation_suggestions)
                if recs:
                    print(f"  推荐数据存在:")
                    
                    # 检查 alternative_times
                    if recs.get('alternative_times'):
                        print(f"    - alternative_times: {len(recs['alternative_times'])} 个")
                        for t in recs['alternative_times']:
                            has_cap = 'capacity' in t
                            cap_val = t.get('capacity', 'N/A')
                            status = "✓" if has_cap else "✗"
                            print(f"      {status} 时间: {t.get('time')}, 桌号: {t.get('table_number')}, 容量: {cap_val}")
                    
                    # 检查 alternative_dates
                    if recs.get('alternative_dates'):
                        print(f"    - alternative_dates: {len(recs['alternative_dates'])} 个")
                        for d in recs['alternative_dates']:
                            has_cap = 'capacity' in d
                            cap_val = d.get('capacity', 'N/A')
                            status = "✓" if has_cap else "✗"
                            print(f"      {status} 日期: {d.get('date')}, 桌号: {d.get('table_number')}, 容量: {cap_val}")
                    
                    # 检查 alternative_tables
                    if recs.get('alternative_tables'):
                        print(f"    - alternative_tables: {len(recs['alternative_tables'])} 个")
                        for t in recs['alternative_tables']:
                            has_cap = 'capacity' in t
                            cap_val = t.get('capacity', 'N/A')
                            status = "✓" if has_cap else "✗"
                            print(f"      {status} 桌号: {t.get('table_number')}, 容量: {cap_val}")

def fix_old_data():
    """修复旧数据：为没有 capacity 字段的推荐数据添加 capacity"""
    print("\n" + "=" * 60)
    print("处理旧数据")
    print("=" * 60)
    
    fixed_count = 0
    
    with app.app_context():
        rejected_reservations = Reservation.query.filter_by(status='rejected').all()
        
        for res in rejected_reservations:
            if not res.recommendation_suggestions:
                continue
            
            recs = safe_parse_recommendations(res.recommendation_suggestions)
            if not recs:
                continue
            
            needs_fix = False
            
            # 修复 alternative_times
            if recs.get('alternative_times'):
                for t in recs['alternative_times']:
                    if 'capacity' not in t:
                        # 根据 table_id 查找容量
                        table = Table.query.get(t.get('table_id'))
                        if table:
                            t['capacity'] = table.capacity
                            needs_fix = True
                            print(f"  修复 alternative_times: 桌号 {t.get('table_number')} 添加容量 {table.capacity}")
            
            # 修复 alternative_dates
            if recs.get('alternative_dates'):
                for d in recs['alternative_dates']:
                    if 'capacity' not in d:
                        table = Table.query.get(d.get('table_id'))
                        if table:
                            d['capacity'] = table.capacity
                            needs_fix = True
                            print(f"  修复 alternative_dates: 桌号 {d.get('table_number')} 添加容量 {table.capacity}")
            
            if needs_fix:
                res.recommendation_suggestions = json.dumps(recs, ensure_ascii=False)
                fixed_count += 1
        
        db.session.commit()
    
    print(f"\n修复完成: 共修复 {fixed_count} 条记录")
    return fixed_count

def verify_filter_correctness():
    """验证过滤逻辑的正确性：模拟 get_available_tables 的行为"""
    print("\n" + "=" * 60)
    print("验证过滤逻辑正确性")
    print("=" * 60)
    
    with app.app_context():
        # 获取所有活跃餐桌
        all_tables = Table.query.filter_by(is_active=True).all()
        if not all_tables:
            print("  没有餐桌数据")
            return
        
        print(f"\n  测试场景: 客人数量为 2 人")
        guest_count = 2
        
        # 模拟过滤
        filtered = [t for t in all_tables if t.capacity >= guest_count]
        
        print(f"  所有餐桌: {len(all_tables)} 张")
        print(f"  过滤后 (容量 >= {guest_count}): {len(filtered)} 张")
        
        print(f"\n  详细信息:")
        for t in all_tables:
            status = "✓ 符合条件" if t.capacity >= guest_count else "✗ 不符合"
            print(f"    桌号 {t.table_number}: 容量 {t.capacity} - {status}")
        
        # 检查是否有容量为1的餐桌被错误地包含在过滤结果中
        capacity_1_tables = [t for t in all_tables if t.capacity == 1]
        if capacity_1_tables:
            print(f"\n  ⚠ 警告: 存在容量为1的餐桌:")
            for t in capacity_1_tables:
                print(f"      桌号 {t.table_number} (容量 1)")
                if t.capacity >= guest_count:
                    print(f"         ✗ 错误: 被包含在过滤结果中!")
                else:
                    print(f"         ✓ 正确: 被排除在过滤结果外")
        else:
            print(f"\n  ✓ 没有容量为1的餐桌")

if __name__ == '__main__':
    print("\n餐厅座位预订系统 - 数据修复和验证工具")
    print("=" * 60)
    
    # 1. 验证当前过滤逻辑
    verify_filter_logic()
    
    # 2. 修复旧数据
    fix_old_data()
    
    # 3. 验证过滤逻辑正确性
    verify_filter_correctness()
    
    print("\n" + "=" * 60)
    print("处理完成!")
    print("=" * 60)
