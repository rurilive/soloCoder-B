#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LeetCode每日一题爬虫
爬取最近30天的每日一题，包括题目、官方答案和按赞数排序的前三个评论
并将数据格式化保存到SQLite数据库中
"""

import requests
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any


class LeetCodeCrawler:
    """LeetCode爬虫类"""
    
    def __init__(self, db_path: str = "leetcode.db"):
        """
        初始化爬虫
        
        Args:
            db_path: SQLite数据库文件路径
        """
        self.db_path = db_path
        self.base_url = "https://leetcode.cn/api/"
        self.graphql_url = "https://leetcode.cn/graphql/"
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self._init_db()
    
    def _init_db(self) -> None:
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建题目表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS problems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER UNIQUE NOT NULL,
            title TEXT NOT NULL,
            title_slug TEXT NOT NULL,
            difficulty TEXT,
            content TEXT,
            tags TEXT,
            date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建官方答案表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS solutions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            problem_id INTEGER NOT NULL,
            title TEXT,
            content TEXT,
            author TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (problem_id) REFERENCES problems (id)
        )
        ''')
        
        # 创建评论表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            problem_id INTEGER NOT NULL,
            comment_id INTEGER UNIQUE,
            author TEXT,
            content TEXT,
            vote_count INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (problem_id) REFERENCES problems (id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def _graphql_request(self, query: str, variables: Dict[str, Any] = None) -> Optional[Dict]:
        """
        发送GraphQL请求
        
        Args:
            query: GraphQL查询语句
            variables: 查询变量
            
        Returns:
            JSON响应数据或None
        """
        try:
            payload = {"query": query}
            if variables:
                payload["variables"] = variables
            
            response = requests.post(
                self.graphql_url,
                json=payload,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"GraphQL请求失败: {e}")
            return None
    
    def get_daily_challenges(self, days: int = 30) -> List[Dict]:
        """
        获取最近n天的每日一题
        
        Args:
            days: 天数，默认30天
            
        Returns:
            每日一题列表
        """
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
        
        challenges = []
        today_date = datetime.now().date()
        
        print(f"当前日期: {today_date}, 获取最近{days}天的每日一题")
        
        # 获取当前月和前一个月的数据
        months_to_check = [
            (today_date.year, today_date.month),
            ((today_date.replace(day=1) - timedelta(days=1)).year, 
             (today_date.replace(day=1) - timedelta(days=1)).month)
        ]
        
        print(f"需要检查的月份: {months_to_check}")
        
        for year, month in months_to_check:
            variables = {"year": year, "month": month}
            print(f"正在获取 {year}年{month}月 的每日一题...")
            
            result = self._graphql_request(query, variables)
            
            if result and "data" in result and "dailyCodingChallengeV3" in result["data"]:
                daily_challenges = result["data"]["dailyCodingChallengeV3"]["dailyChallenges"]
                print(f"  获取到 {len(daily_challenges)} 个每日一题")
                
                for challenge in daily_challenges:
                    challenge_date = datetime.strptime(challenge["date"], "%Y-%m-%d").date()
                    days_diff = (today_date - challenge_date).days
                    
                    if 0 <= days_diff < days:
                        challenges.append(challenge)
                        print(f"    添加: {challenge['date']} - {challenge['title']} (天数差: {days_diff})")
                    else:
                        print(f"    跳过: {challenge['date']} - {challenge['title']} (天数差: {days_diff}, 超出范围)")
            else:
                print(f"  警告: 未获取到 {year}年{month}月 的每日一题数据")
                if result:
                    print(f"  API响应: {json.dumps(result, ensure_ascii=False)[:500]}")
        
        # 按日期排序
        challenges.sort(key=lambda x: x["date"], reverse=True)
        print(f"\n总共获取到 {len(challenges)} 个符合条件的每日一题")
        return challenges
    
    def get_problem_detail(self, title_slug: str) -> Optional[Dict]:
        """
        获取题目详情
        
        Args:
            title_slug: 题目标识
            
        Returns:
            题目详情
        """
        query = '''
        query questionData($titleSlug: String!) {
            question(titleSlug: $titleSlug) {
                questionId
                questionFrontendId
                title
                titleSlug
                content
                difficulty
                topicTags {
                    name
                    slug
                }
            }
        }
        '''
        
        print(f"  正在获取题目详情: {title_slug}...")
        variables = {"titleSlug": title_slug}
        result = self._graphql_request(query, variables)
        
        if result and "data" in result and "question" in result["data"]:
            question = result["data"]["question"]
            print(f"    成功获取题目: {question.get('title', '未知')} (ID: {question.get('questionId', '未知')})")
            return question
        else:
            print(f"    警告: 未获取到题目详情")
            if result:
                print(f"    API响应: {json.dumps(result, ensure_ascii=False)[:500]}")
        return None
    
    def get_official_solution(self, title_slug: str) -> Optional[Dict]:
        """
        获取官方答案
        
        Args:
            title_slug: 题目标识
            
        Returns:
            官方答案
        """
        query = '''
        query questionSolution($titleSlug: String!) {
            questionSolution(titleSlug: $titleSlug) {
                solution {
                    id
                    title
                    content
                    author {
                        username
                    }
                }
            }
        }
        '''
        
        print(f"  正在获取官方答案: {title_slug}...")
        variables = {"titleSlug": title_slug}
        result = self._graphql_request(query, variables)
        
        if result and "data" in result and "questionSolution" in result["data"]:
            solution_data = result["data"]["questionSolution"]
            if solution_data and "solution" in solution_data and solution_data["solution"]:
                solution = solution_data["solution"]
                print(f"    成功获取官方答案: {solution.get('title', '未知')}")
                return solution
            else:
                print(f"    该题目暂无官方答案")
        else:
            print(f"    警告: 未获取到官方答案数据")
            if result:
                print(f"    API响应: {json.dumps(result, ensure_ascii=False)[:500]}")
        return None
    
    def get_top_comments(self, question_id: int, limit: int = 3) -> List[Dict]:
        """
        获取按赞数排序的前N条评论
        
        Args:
            question_id: 题目ID
            limit: 返回评论数量限制
            
        Returns:
            评论列表
        """
        query = '''
        query QuestionTopics($questionId: Int!, $skip: Int!, $first: Int!, $orderBy: String) {
            questionTopics(
                questionId: $questionId
                skip: $skip
                first: $first
                orderBy: $orderBy
            ) {
                id
                title
                content
                author {
                    username
                }
                post {
                    id
                    voteCount
                }
            }
        }
        '''
        
        # 使用查询来获取评论，按赞数排序
        variables = {
            "questionId": question_id,
            "skip": 0,
            "first": limit,
            "orderBy": "hot"
        }
        
        print(f"  正在获取题目ID {question_id} 的评论...")
        result = self._graphql_request(query, variables)
        comments = []
        
        if result and "data" in result and "questionTopics" in result["data"]:
            topics = result["data"]["questionTopics"]
            print(f"    获取到 {len(topics)} 条评论")
            
            for topic in topics:
                comment = {
                    "id": topic.get("id"),
                    "title": topic.get("title"),
                    "content": topic.get("content"),
                    "author": topic.get("author", {}).get("username", "") if topic.get("author") else "",
                    "vote_count": topic.get("post", {}).get("voteCount", 0) if topic.get("post") else 0
                }
                comments.append(comment)
                print(f"      评论: {comment['author']} - 赞数: {comment['vote_count']}")
        else:
            print(f"    警告: 未获取到评论数据")
            if result:
                print(f"    API响应: {json.dumps(result, ensure_ascii=False)[:500]}")
        
        return comments
    
    def save_problem(self, problem_data: Dict, daily_challenge: Dict) -> int:
        """
        保存题目到数据库
        
        Args:
            problem_data: 题目详情数据
            daily_challenge: 每日一题数据（包含日期）
            
        Returns:
            数据库中的题目ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 处理标签
        tags = []
        if problem_data.get("topicTags"):
            tags = [tag.get("name", "") for tag in problem_data["topicTags"]]
        
        question_id = int(problem_data.get("questionId", 0))
        title = problem_data.get("title", "")
        date = daily_challenge.get("date", "")
        
        print(f"  正在保存题目到数据库: ID={question_id}, 标题={title}, 日期={date}")
        
        try:
            # 先检查是否已存在
            cursor.execute('''
            SELECT id FROM problems WHERE question_id = ?
            ''', (question_id,))
            existing = cursor.fetchone()
            
            if existing:
                print(f"    题目已存在，更新记录 (数据库ID: {existing[0]})")
                cursor.execute('''
                UPDATE problems 
                SET title = ?, title_slug = ?, difficulty = ?, content = ?, tags = ?, date = ?
                WHERE question_id = ?
                ''', (
                    title,
                    problem_data.get("titleSlug", ""),
                    problem_data.get("difficulty", ""),
                    problem_data.get("content", ""),
                    json.dumps(tags, ensure_ascii=False),
                    date,
                    question_id
                ))
                problem_id = existing[0]
            else:
                print(f"    题目不存在，插入新记录")
                cursor.execute('''
                INSERT INTO problems 
                (question_id, title, title_slug, difficulty, content, tags, date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    question_id,
                    title,
                    problem_data.get("titleSlug", ""),
                    problem_data.get("difficulty", ""),
                    problem_data.get("content", ""),
                    json.dumps(tags, ensure_ascii=False),
                    date
                ))
                problem_id = cursor.lastrowid
            
            conn.commit()
            print(f"    题目保存成功，数据库ID: {problem_id}")
            return problem_id
        except Exception as e:
            print(f"    保存题目失败: {e}")
            import traceback
            traceback.print_exc()
            conn.rollback()
            return 0
        finally:
            conn.close()
    
    def save_solution(self, problem_id: int, solution: Dict) -> bool:
        """
        保存官方答案到数据库
        
        Args:
            problem_id: 数据库中的题目ID
            solution: 官方答案数据
            
        Returns:
            是否保存成功
        """
        if not solution:
            return False
        
        print(f"  正在保存官方答案到数据库: 题目ID={problem_id}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 先检查是否已存在
            cursor.execute('''
            SELECT id FROM solutions WHERE problem_id = ?
            ''', (problem_id,))
            existing = cursor.fetchone()
            
            if existing:
                print(f"    答案已存在，更新记录 (数据库ID: {existing[0]})")
                cursor.execute('''
                UPDATE solutions 
                SET title = ?, content = ?, author = ?
                WHERE problem_id = ?
                ''', (
                    solution.get("title", ""),
                    solution.get("content", ""),
                    solution.get("author", {}).get("username", "") if solution.get("author") else "",
                    problem_id
                ))
            else:
                print(f"    答案不存在，插入新记录")
                cursor.execute('''
                INSERT INTO solutions 
                (problem_id, title, content, author)
                VALUES (?, ?, ?, ?)
                ''', (
                    problem_id,
                    solution.get("title", ""),
                    solution.get("content", ""),
                    solution.get("author", {}).get("username", "") if solution.get("author") else ""
                ))
            
            conn.commit()
            print(f"    官方答案保存成功")
            return True
        except Exception as e:
            print(f"    保存官方答案失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def save_comments(self, problem_id: int, comments: List[Dict]) -> int:
        """
        保存评论到数据库
        
        Args:
            problem_id: 数据库中的题目ID
            comments: 评论列表
            
        Returns:
            保存的评论数量
        """
        if not comments:
            return 0
        
        print(f"  正在保存评论到数据库: 题目ID={problem_id}, 评论数量={len(comments)}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        saved_count = 0
        
        try:
            # 先删除该题目的旧评论
            cursor.execute('''
            DELETE FROM comments WHERE problem_id = ?
            ''', (problem_id,))
            print(f"    已删除旧评论")
            
            for i, comment in enumerate(comments):
                cursor.execute('''
                INSERT INTO comments 
                (problem_id, comment_id, author, content, vote_count)
                VALUES (?, ?, ?, ?, ?)
                ''', (
                    problem_id,
                    comment.get("id"),
                    comment.get("author", ""),
                    comment.get("content", ""),
                    comment.get("vote_count", 0)
                ))
                saved_count += 1
                print(f"    保存评论 {i+1}: 作者={comment.get('author', '未知')}, 赞数={comment.get('vote_count', 0)}")
            
            conn.commit()
            print(f"    评论保存成功，共保存 {saved_count} 条")
        except Exception as e:
            print(f"    保存评论失败: {e}")
            conn.rollback()
        finally:
            conn.close()
        
        return saved_count
    
    def check_database(self) -> None:
        """
        检查数据库中的数据
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        print("\n" + "="*60)
        print("数据库检查报告")
        print("="*60)
        
        # 检查表中的数据数量
        cursor.execute("SELECT COUNT(*) FROM problems")
        problems_count = cursor.fetchone()[0]
        print(f"\n题目表 (problems) 中的记录数: {problems_count}")
        
        cursor.execute("SELECT COUNT(*) FROM solutions")
        solutions_count = cursor.fetchone()[0]
        print(f"官方答案表 (solutions) 中的记录数: {solutions_count}")
        
        cursor.execute("SELECT COUNT(*) FROM comments")
        comments_count = cursor.fetchone()[0]
        print(f"评论表 (comments) 中的记录数: {comments_count}")
        
        # 显示前10条题目
        if problems_count > 0:
            print(f"\n前10条题目:")
            cursor.execute('''
            SELECT id, question_id, title, difficulty, date 
            FROM problems 
            ORDER BY date DESC 
            LIMIT 10
            ''')
            for row in cursor.fetchall():
                print(f"  ID: {row[0]}, QuestionID: {row[1]}, 标题: {row[2][:30]}..., 难度: {row[3]}, 日期: {row[4]}")
        
        conn.close()
        print("\n" + "="*60)
    
    def crawl_daily_challenges(self, days: int = 30) -> None:
        """
        爬取最近n天的每日一题
        
        Args:
            days: 天数，默认30天
        """
        print(f"开始爬取最近{days}天的每日一题...")
        
        # 获取每日一题列表
        daily_challenges = self.get_daily_challenges(days)
        print(f"找到{len(daily_challenges)}个每日一题")
        
        for i, challenge in enumerate(daily_challenges):
            title_slug = challenge.get("titleSlug")
            date = challenge.get("date")
            title = challenge.get("title")
            
            print(f"\n[{i+1}/{len(daily_challenges)}] 处理 {date}: {title}")
            
            # 获取题目详情
            problem_detail = self.get_problem_detail(title_slug)
            if not problem_detail:
                print(f"  无法获取题目详情，跳过")
                continue
            
            # 保存题目
            problem_id = self.save_problem(problem_detail, challenge)
            if not problem_id:
                print(f"  无法保存题目，跳过")
                continue
            print(f"  题目已保存 (ID: {problem_id})")
            
            # 获取并保存官方答案
            solution = self.get_official_solution(title_slug)
            if solution:
                self.save_solution(problem_id, solution)
                print(f"  官方答案已保存")
            else:
                print(f"  未找到官方答案")
            
            # 获取并保存评论
            question_id = int(problem_detail.get("questionId", 0))
            if question_id > 0:
                comments = self.get_top_comments(question_id, limit=3)
                saved_count = self.save_comments(problem_id, comments)
                print(f"  已保存{saved_count}条评论")
            else:
                print(f"  无法获取评论（题目ID无效）")
        
        print(f"\n爬取完成！数据已保存到 {self.db_path}")
        
        # 检查数据库
        self.check_database()


def main():
    """主函数"""
    import sys
    
    days = 30
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            print(f"参数错误: {sys.argv[1]}, 使用默认值30天")
    
    print(f"LeetCode 每日一题爬虫")
    print(f"="*60)
    print(f"目标: 爬取最近 {days} 天的每日一题")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"="*60)
    
    crawler = LeetCodeCrawler("leetcode.db")
    
    # 先检查现有数据
    print("\n检查现有数据库...")
    crawler.check_database()
    
    # 开始爬取
    print("\n开始爬取...")
    crawler.crawl_daily_challenges(days=days)
    
    print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("任务完成！")


if __name__ == "__main__":
    main()
