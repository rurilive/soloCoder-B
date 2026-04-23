#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本 - 诊断LeetCode爬虫问题
"""

import requests
import json
from datetime import datetime, timedelta

# 测试GraphQL API是否可用
def test_graphql_api():
    """测试LeetCode GraphQL API"""
    graphql_url = "https://leetcode.cn/graphql/"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    # 测试获取每日一题
    query = '''
    query dailyCodingChallengeV3($year: Int!, $month: Int!) {
        dailyCodingChallengeV3(year: $year, month: $month) {
            dailyChallenges {
                questionId
                title
                titleSlug
                difficulty
                date
            }
        }
    }
    '''
    
    today = datetime.now()
    variables = {"year": today.year, "month": today.month}
    
    print(f"测试获取 {today.year}年{today.month}月 的每日一题...")
    print(f"变量: {variables}")
    
    try:
        response = requests.post(
            graphql_url,
            json={"query": query, "variables": variables},
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        
        print(f"\nAPI响应状态码: {response.status_code}")
        print(f"响应内容: {json.dumps(result, ensure_ascii=False, indent=2)[:2000]}")
        
        # 检查是否获取到数据
        if result and "data" in result and "dailyCodingChallengeV3" in result["data"]:
            daily_challenges = result["data"]["dailyCodingChallengeV3"]["dailyChallenges"]
            print(f"\n获取到 {len(daily_challenges)} 个每日一题")
            
            # 测试日期比较逻辑
            print("\n测试日期比较逻辑:")
            for i, challenge in enumerate(daily_challenges[:5]):
                challenge_date = datetime.strptime(challenge["date"], "%Y-%m-%d")
                today_full = datetime.now()
                today_date = datetime.now().date()
                
                days_diff_full = (today_full - challenge_date).days
                days_diff_date = (today_date - challenge_date.date()).days
                
                print(f"  [{i+1}] {challenge['date']}: {challenge['title']}")
                print(f"      使用datetime.now()计算天数差: {days_diff_full}")
                print(f"      使用datetime.now().date()计算天数差: {days_diff_date}")
        
        else:
            print("\n警告: 未获取到有效的每日一题数据")
            
    except Exception as e:
        print(f"\nAPI请求失败: {e}")
        import traceback
        traceback.print_exc()


def test_date_comparison():
    """测试日期比较逻辑"""
    print("\n" + "="*50)
    print("测试日期比较逻辑")
    print("="*50)
    
    today_full = datetime.now()
    today_date = datetime.now().date()
    
    print(f"当前完整时间: {today_full}")
    print(f"当前日期: {today_date}")
    
    # 测试不同日期的情况
    test_dates = [
        today_full,
        today_full - timedelta(hours=1),
        today_full - timedelta(days=1),
        today_full - timedelta(days=2),
        today_full - timedelta(days=30),
    ]
    
    print("\n日期比较测试:")
    for i, test_date in enumerate(test_dates):
        test_date_str = test_date.strftime("%Y-%m-%d")
        challenge_date = datetime.strptime(test_date_str, "%Y-%m-%d")
        
        days_diff_full = (today_full - challenge_date).days
        days_diff_date = (today_date - challenge_date.date()).days
        
        print(f"\n  测试日期 {i+1}: {test_date_str}")
        print(f"  使用datetime.now()计算: {days_diff_full} 天前")
        print(f"  使用datetime.now().date()计算: {days_diff_date} 天前")
        print(f"  是否在最近30天内 (使用full): {0 <= days_diff_full < 30}")
        print(f"  是否在最近30天内 (使用date): {0 <= days_diff_date < 30}")


if __name__ == "__main__":
    test_graphql_api()
    test_date_comparison()
