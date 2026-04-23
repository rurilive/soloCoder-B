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
        today = datetime.now()
        
        # 获取当前月和前一个月的数据
        months_to_check = [
            (today.year, today.month),
            ((today.replace(day=1) - timedelta(days=1)).year, 
             (today.replace(day=1) - timedelta(days=1)).month)
        ]
        
        for year, month in months_to_check:
            variables = {"year": year, "month": month}
            result = self._graphql_request(query, variables)
            
            if result and "data" in result and "dailyCodingChallengeV3" in result["data"]:
                daily_challenges = result["data"]["dailyCodingChallengeV3"]["dailyChallenges"]
                for challenge in daily_challenges:
                    challenge_date = datetime.strptime(challenge["date"], "%Y-%m-%d")
                    days_diff = (today - challenge_date).days
                    if 0 <= days_diff < days:
                        challenges.append(challenge)
        
        # 按日期排序
        challenges.sort(key=lambda x: x["date"], reverse=True)
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
        
        variables = {"titleSlug": title_slug}
        result = self._graphql_request(query, variables)
        
        if result and "data" in result and "question" in result["data"]:
            return result["data"]["question"]
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
        
        variables = {"titleSlug": title_slug}
        result = self._graphql_request(query, variables)
        
        if result and "data" in result and "questionSolution" in result["data"]:
            solution_data = result["data"]["questionSolution"]
            if solution_data and "solution" in solution_data:
                return solution_data["solution"]
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
        query questionCommentTopicTags($questionId: Int!) {
            questionCommentTopicTags(questionId: $questionId) {
                id
                name
            }
        }
        
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
        
        # 使用第二个查询来获取评论，按赞数排序
        variables = {
            "questionId": question_id,
            "skip": 0,
            "first": limit,
            "orderBy": "hot"
        }
        
        result = self._graphql_request(query, variables)
        comments = []
        
        if result and "data" in result and "questionTopics" in result["data"]:
            for topic in result["data"]["questionTopics"]:
                comment = {
                    "id": topic.get("id"),
                    "title": topic.get("title"),
                    "content": topic.get("content"),
                    "author": topic.get("author", {}).get("username", "") if topic.get("author") else "",
                    "vote_count": topic.get("post", {}).get("voteCount", 0) if topic.get("post") else 0
                }
                comments.append(comment)
        
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
        
        try:
            cursor.execute('''
            INSERT OR REPLACE INTO problems 
            (question_id, title, title_slug, difficulty, content, tags, date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                int(problem_data.get("questionId", 0)),
                problem_data.get("title", ""),
                problem_data.get("titleSlug", ""),
                problem_data.get("difficulty", ""),
                problem_data.get("content", ""),
                json.dumps(tags, ensure_ascii=False),
                daily_challenge.get("date", "")
            ))
            
            # 获取插入的ID
            if cursor.lastrowid:
                problem_id = cursor.lastrowid
            else:
                # 如果是更新，查询已有ID
                cursor.execute('''
                SELECT id FROM problems WHERE question_id = ?
                ''', (int(problem_data.get("questionId", 0)),))
                result = cursor.fetchone()
                problem_id = result[0] if result else 0
            
            conn.commit()
            return problem_id
        except Exception as e:
            print(f"保存题目失败: {e}")
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
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            INSERT OR REPLACE INTO solutions 
            (problem_id, title, content, author)
            VALUES (?, ?, ?, ?)
            ''', (
                problem_id,
                solution.get("title", ""),
                solution.get("content", ""),
                solution.get("author", {}).get("username", "") if solution.get("author") else ""
            ))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"保存官方答案失败: {e}")
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
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        saved_count = 0
        
        try:
            for comment in comments:
                cursor.execute('''
                INSERT OR REPLACE INTO comments 
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
            
            conn.commit()
        except Exception as e:
            print(f"保存评论失败: {e}")
            conn.rollback()
        finally:
            conn.close()
        
        return saved_count
    
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


def main():
    """主函数"""
    crawler = LeetCodeCrawler("leetcode.db")
    crawler.crawl_daily_challenges(days=30)


if __name__ == "__main__":
    main()
