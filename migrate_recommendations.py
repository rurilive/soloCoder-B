#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：处理旧的推荐数据

问题：旧的推荐数据（recommendation_suggestions）中缺少 capacity 字段
这会导致：
1. 推荐座位的容量无法显示
2. 即使过滤逻辑正确，旧数据可能包含不符合要求的座位

修复方案：
1. 遍历所有被拒绝的预订
2. 检查推荐数据是否缺少 capacity 字段
3. 重新生成推荐数据（使用正确的过滤逻辑）
4. 保存修复后的数据
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, date, time, timedelta

def safe_parse_recommendations(data_str):
    if not data_str:
        return None
    try:
        return json.loads(data_str)
    except (json.JSONDecodeError, TypeError):
        return None

def migrate_old_data():
    """迁移旧数据：为所有被拒绝的预订重新生成推荐数据"""
    from app import app, db
    from models import Restaurant, Table, Reservation, User
    
    print("=" * 70)
    print("数据库迁移：修复旧推荐数据")
    print("=" * 70)
    
    with app.app_context():
        # 获取所有被拒绝的预订
        rejected_reservations = Reservation.query.filter_by(status='rejected').all()
        print(f"\n找到 {len(rejected_reservations)} 个被拒绝的预订")
        
        if not rejected_reservations:
            print("没有需要迁移的旧数据")
            return 0
        
        fixed_count = 0
        errors = []
        
        for idx, res in enumerate(rejected_reservations, 1):
            print(f"\n[{idx}/{len(rejected_reservations)}] 处理预订 ID: {res.id}")
            print(f"    客人数量: {res.guest_count}")
            print(f"    原订桌号: {res.table.table_number} (容量: {res.table.capacity})")
            
            # 检查现有推荐数据
            existing_recs = safe_parse_recommendations(res.recommendation_suggestions)
            
            needs_fix = False
            if existing_recs:
                # 检查是否缺少 capacity 字段
                for key in ['alternative_times', 'alternative_dates', 'alternative_tables']:
                    items = existing_recs.get(key, [])
                    if items:
                        first_item = items[0]
                        if 'capacity' not in first_item:
                            print(f"    ⚠ {key} 缺少 capacity 字段，需要修复")
                            needs_fix = True
                            break
                if needs_fix:
                    print(f"    → 重新生成推荐数据...")
            else:
                print(f"    ⚠ 没有推荐数据，需要生成")
                needs_fix = True
            
            if needs_fix:
                try:
                    # 重新生成推荐数据
                    new_recs = generate_recommendations_v2(res)
                    
                    if new_recs:
                        # 验证新数据
                        verify_recommendations(new_recs, res.guest_count)
                        
                        # 保存
                        res.recommendation_suggestions = json.dumps(new_recs, ensure_ascii=False)
                        db.session.commit()
                        fixed_count += 1
                        print(f"    ✓ 推荐数据已更新")
                    else:
                        print(f"    ✗ 无法生成推荐数据")
                        
                except Exception as e:
                    error_msg = f"预订 {res.id} 处理失败: {str(e)}"
                    print(f"    ✗ {error_msg}")
                    errors.append(error_msg)
                    db.session.rollback()
        
        print("\n" + "=" * 70)
        print(f"迁移完成！")
        print(f"  - 处理预订数: {len(rejected_reservations)}")
        print(f"  - 修复成功: {fixed_count}")
        print(f"  - 错误: {len(errors)}")
        if errors:
            for e in errors:
                print(f"    - {e}")
        print("=" * 70)
        
        return fixed_count

def generate_recommendations_v2(reservation):
    """重新实现 generate_recommendations 函数，使用正确的过滤逻辑"""
    from models import Table, Restaurant
    
    recommendations = {
        'alternative_times': [],
        'alternative_tables': [],
        'alternative_dates': [],
        'reservation_id': reservation.id,
        'restaurant_id': reservation.table.restaurant_id,
        'guest_count': reservation.guest_count
    }
    
    restaurant = reservation.table.restaurant
    original_date = reservation.reservation_date
    original_start = reservation.start_time
    original_end = reservation.end_time
    original_guest_count = reservation.guest_count
    
    # 获取所有时间段
    time_slots = get_time_slots_v2(restaurant.id, original_date)
    
    # 推荐其他时段
    for slot in time_slots:
        if slot == original_start:
            continue
        
        end_dt = datetime.combine(original_date, slot) + timedelta(hours=2)
        end_time = end_dt.time()
        
        available_tables = get_available_tables_v2(
            restaurant.id,
            original_date,
            slot,
            end_time,
            original_guest_count
        )
        
        if available_tables:
            first_table = available_tables[0]
            recommendations['alternative_times'].append({
                'time': slot.strftime('%H:%M'),
                'end_time': end_time.strftime('%H:%M'),
                'tables_available': len(available_tables),
                'table_id': first_table.id,
                'table_number': first_table.table_number,
                'capacity': first_table.capacity,
                'date': original_date.isoformat()
            })
    
    # 推荐其他日期（未来7天）
    for days_offset in range(1, 8):
        alt_date = original_date + timedelta(days=days_offset)
        alt_end = (datetime.combine(alt_date, original_start) + timedelta(hours=2)).time()
        
        available_tables = get_available_tables_v2(
            restaurant.id,
            alt_date,
            original_start,
            alt_end,
            original_guest_count
        )
        
        if available_tables:
            first_table = available_tables[0]
            weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
            recommendations['alternative_dates'].append({
                'date': alt_date.isoformat(),
                'weekday': weekday_names[alt_date.weekday()],
                'tables_available': len(available_tables),
                'table_id': first_table.id,
                'table_number': first_table.table_number,
                'capacity': first_table.capacity,
                'start_time': original_start.strftime('%H:%M'),
                'end_time': alt_end.strftime('%H:%M')
            })
    
    # 推荐其他餐桌（同一时段）
    all_tables = Table.query.filter_by(
        restaurant_id=restaurant.id,
        is_active=True
    ).all()
    
    # 关键：只选择容量 >= 客人数量的餐桌
    suitable_tables = [t for t in all_tables if t.capacity >= original_guest_count]
    
    for table in suitable_tables:
        if table.id == reservation.table_id:
            continue
        if table.is_available(original_date, original_start, original_end):
            recommendations['alternative_tables'].append({
                'table_id': table.id,
                'table_number': table.table_number,
                'capacity': table.capacity,
                'date': original_date.isoformat(),
                'start_time': original_start.strftime('%H:%M'),
                'end_time': original_end.strftime('%H:%M')
            })
    
    return recommendations

def get_available_tables_v2(restaurant_id, reservation_date, start_time, end_time, guest_count=None):
    """获取可用餐桌，使用严格的过滤逻辑"""
    from models import Table, Restaurant
    
    from app import db
    restaurant = db.session.get(Restaurant, restaurant_id)
    if not restaurant:
        return []
    
    tables = Table.query.filter_by(restaurant_id=restaurant_id, is_active=True).all()
    
    # 严格过滤：只有 guest_count > 0 时才过滤
    if guest_count is not None and guest_count > 0:
        tables = [t for t in tables if t.capacity >= guest_count]
    
    available_tables = []
    for table in tables:
        if table.is_available(reservation_date, start_time, end_time):
            available_tables.append(table)
    
    return available_tables

def get_time_slots_v2(restaurant_id, reservation_date):
    """获取餐厅的营业时间间隔"""
    from models import Restaurant
    from app import db
    
    restaurant = db.session.get(Restaurant, restaurant_id)
    if not restaurant:
        return []
    
    slots = []
    current_time = restaurant.open_time
    close_time = restaurant.close_time
    
    while current_time < close_time:
        slots.append(current_time)
        current_dt = datetime.combine(date.today(), current_time)
        next_dt = current_dt + timedelta(hours=1)
        current_time = next_dt.time()
    
    return slots

def verify_recommendations(recs, guest_count):
    """验证推荐数据是否正确"""
    print(f"    验证推荐数据（客人数量: {guest_count}）:")
    
    issues = []
    
    # 检查 alternative_times
    for idx, item in enumerate(recs.get('alternative_times', [])):
        if 'capacity' not in item:
            issues.append(f"alternative_times[{idx}] 缺少 capacity")
        elif item['capacity'] < guest_count:
            issues.append(f"alternative_times[{idx}] 容量 {item['capacity']} < {guest_count}")
    
    # 检查 alternative_dates
    for idx, item in enumerate(recs.get('alternative_dates', [])):
        if 'capacity' not in item:
            issues.append(f"alternative_dates[{idx}] 缺少 capacity")
        elif item['capacity'] < guest_count:
            issues.append(f"alternative_dates[{idx}] 容量 {item['capacity']} < {guest_count}")
    
    # 检查 alternative_tables
    for idx, item in enumerate(recs.get('alternative_tables', [])):
        if 'capacity' not in item:
            issues.append(f"alternative_tables[{idx}] 缺少 capacity")
        elif item['capacity'] < guest_count:
            issues.append(f"alternative_tables[{idx}] 容量 {item['capacity']} < {guest_count}")
    
    if issues:
        for issue in issues:
            print(f"      ✗ {issue}")
    else:
        print(f"      ✓ 所有推荐数据验证通过")
    
    return len(issues) == 0

if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("餐厅座位预订系统 - 数据库迁移工具")
    print("=" * 70)
    print("\n功能：")
    print("1. 检查所有被拒绝的预订")
    print("2. 发现缺少 capacity 字段的推荐数据")
    print("3. 重新生成推荐数据（使用正确的过滤逻辑）")
    print("4. 验证推荐数据的容量是否满足客人数量需求")
    
    migrate_old_data()
