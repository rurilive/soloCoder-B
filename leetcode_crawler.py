#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LeetCode每日一题爬虫（增强版 - 使用高级代理池）
- 集成高级代理池管理器
- 后台线程自动验证和刷新代理
- 代理获取规则：不连续返回相同代理，相同代理间隔5秒以上
"""

import requests
import sqlite3
import json
import time
import random
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# 导入代理池模块
try:
    from proxy_pool import ProxyPool
    HAS_PROXY_POOL = True
except ImportError:
    HAS_PROXY_POOL = False
    print("警告: 未找到 proxy_pool 模块，将使用直连模式")


class LeetCodeCrawler:
    """LeetCode爬虫类"""
    
    def __init__(self, db_path: str = "leetcode.db", use_proxy: bool = True):
        """
        初始化爬虫
        
        Args:
            db_path: SQLite数据库文件路径
            use_proxy: 是否使用代理池
        """
        self.db_path = db_path
        self.base_url = "https://leetcode.cn/api/"
        self.graphql_url = "https://leetcode.cn/graphql/"
        
        # 代理池配置
        self.use_proxy = use_proxy and HAS_PROXY_POOL
        self.proxy_pool: Optional[AdvancedProxyPool] = None
        
        # 请求间隔配置
        self.min_delay = 1.5  # 最小请求间隔（秒）
        self.max_delay = 3.0  # 最大请求间隔（秒）
        self.retry_count = 3  # 重试次数
        self.retry_delay = 5  # 重试间隔（秒）
        
        # 增强请求头 - 模拟Chrome浏览器
        self._init_headers()
        
        # 初始化数据库
        self._init_db()
        
        # 初始化代理池（如果需要）
        if self.use_proxy:
            self._init_proxy_pool()
    
    def _init_headers(self) -> None:
        """初始化增强的请求头"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        ]
        
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": random.choice(user_agents),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": "https://leetcode.cn",
            "Referer": "https://leetcode.cn/problemset/all/",
            "Connection": "keep-alive",
            "sec-ch-ua": '"Chromium";v="123", "Not:A-Brand";v="8", "Google Chrome";v="123"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        
        # 添加Cookie
        self.cookies = {
            "gr_user_id": f"{random.randint(10000000, 99999999)}-{random.randint(1000, 9999)}",
            "gr_session_id": f"{random.randint(10000000, 99999999)}_{random.randint(10000000, 99999999)}",
            "_ga": f"GA1.2.{random.randint(1000000000, 9999999999)}.{int(time.time())}",
            "_gid": f"GA1.2.{random.randint(1000000000, 9999999999)}.{int(time.time())}",
        }
    
    def _init_proxy_pool(self) -> None:
        """初始化代理池"""
        if not self.use_proxy:
            return
        
        print("\n" + "="*70)
        print("初始化代理池...")
        print("="*70)
        
        self.proxy_pool = ProxyPool(
            max_proxies=20,
            validation_interval=60,
            refresh_interval=300,
            proxy_return_interval=5.0,
            timeout=10,
            debug=True
        )
        
        # 添加回调函数
        def on_proxy_invalid(proxy_str, proxy_info):
            print(f"  [代理事件] 代理 {proxy_str} 被标记为无效，已从池中移除")
        
        def on_proxy_removed(proxy_str, proxy_info):
            print(f"  [代理事件] 代理 {proxy_str} 已从池中移除")
        
        def on_proxy_added(proxy_str, proxy_info):
            print(f"  [代理事件] 新代理 {proxy_str} 已添加到池中")
        
        self.proxy_pool.add_callback('proxy_invalid', on_proxy_invalid)
        self.proxy_pool.add_callback('proxy_removed', on_proxy_removed)
        self.proxy_pool.add_callback('proxy_added', on_proxy_added)
        
        # 启动代理池
        self.proxy_pool.start()
        
        # 等待代理池初始化
        print("\n等待代理池初始化...")
        for i in range(30):
            time.sleep(1)
            if self.proxy_pool.has_proxies():
                print(f"代理池初始化完成！可用代理: {self.proxy_pool.get_stats()['current_proxies']} 个")
                break
            if (i + 1) % 5 == 0:
                print(f"  等待中... ({i+1}/30秒)")
        else:
            print("\n警告: 代理池初始化超时，将切换到直连模式")
            self.use_proxy = False
            self.proxy_pool.stop()
            self.proxy_pool = None
    
    def _get_proxy(self) -> Optional[Dict]:
        """
        从代理池获取代理
        
        Returns:
            代理字典或None
        """
        if not self.use_proxy or not self.proxy_pool:
            return None
        
        return self.proxy_pool.get_proxy()
    
    def _random_delay(self) -> None:
        """随机延迟"""
        delay = random.uniform(self.min_delay, self.max_delay)
        print(f"  等待 {delay:.1f} 秒...")
        time.sleep(delay)
    
    def _report_proxy_status(self, proxy: Optional[Dict], is_valid: bool, reason: str = None) -> None:
        """
        汇报代理使用状态
        
        Args:
            proxy: 代理字典
            is_valid: 是否有效
            reason: 原因
        """
        if not proxy or not self.use_proxy or not self.proxy_pool:
            return
        
        self.proxy_pool.report_proxy_status(proxy, is_valid, reason)
    
    def _make_request(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """
        发送HTTP请求（带代理支持和重试，以及代理汇报机制）
        
        Args:
            method: HTTP方法
            url: 请求URL
            **kwargs: 其他参数
            
        Returns:
            Response对象或None
        """
        last_exception = None
        
        for attempt in range(self.retry_count):
            proxy = None
            try:
                # 准备请求参数
                request_kwargs = {
                    "headers": self.headers,
                    "cookies": self.cookies,
                    "timeout": 30,
                }
                
                # 获取代理
                proxy = self._get_proxy()
                if proxy:
                    request_kwargs["proxies"] = proxy
                    print(f"  使用代理: {proxy.get('http', proxy.get('https', '未知'))}")
                
                # 合并用户提供的参数
                request_kwargs.update(kwargs)
                
                # 发送请求
                if method.upper() == "GET":
                    response = requests.get(url, **request_kwargs)
                else:
                    response = requests.post(url, **request_kwargs)
                
                # 检查状态码
                if response.status_code == 200:
                    # 汇报代理有效
                    self._report_proxy_status(proxy, is_valid=True)
                    return response
                elif response.status_code == 429:
                    print(f"  请求被限流 (429)，尝试 {attempt+1}/{self.retry_count}")
                    # 429 通常是目标网站限流，不是代理问题，汇报为有效
                    self._report_proxy_status(proxy, is_valid=True, reason="目标网站限流")
                    print(f"  等待 {self.retry_delay} 秒后重试...")
                    time.sleep(self.retry_delay)
                else:
                    print(f"  HTTP错误: {response.status_code}")
                    # HTTP错误可能是代理问题，汇报为无效
                    self._report_proxy_status(proxy, is_valid=False, reason=f"HTTP错误 {response.status_code}")
                    if attempt < self.retry_count - 1:
                        print(f"  等待 {self.retry_delay} 秒后重试...")
                        time.sleep(self.retry_delay)
                        
            except requests.exceptions.ProxyError as e:
                last_exception = e
                error_msg = str(e)[:50]
                print(f"  代理错误: {error_msg}")
                # 代理错误，汇报为无效，代理将从池中移除
                self._report_proxy_status(proxy, is_valid=False, reason=f"代理错误: {error_msg}")
                if attempt < self.retry_count - 1:
                    print(f"  尝试获取新代理并重试...")
                    time.sleep(1)
                    
            except requests.exceptions.Timeout as e:
                last_exception = e
                print(f"  请求超时: {e}")
                # 超时可能是代理问题，汇报为无效
                self._report_proxy_status(proxy, is_valid=False, reason=f"请求超时")
                if attempt < self.retry_count - 1:
                    print(f"  等待 {self.retry_delay} 秒后重试...")
                    time.sleep(self.retry_delay)
                    
            except Exception as e:
                last_exception = e
                error_msg = str(e)[:50]
                print(f"  请求错误: {error_msg}")
                # 其他错误也可能是代理问题，汇报为无效
                self._report_proxy_status(proxy, is_valid=False, reason=f"请求错误: {error_msg}")
                if attempt < self.retry_count - 1:
                    print(f"  等待 {self.retry_delay} 秒后重试...")
                    time.sleep(self.retry_delay)
        
        print(f"  请求失败，已尝试 {self.retry_count} 次")
        return None
    
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
            
            response = self._make_request(
                "POST",
                self.graphql_url,
                json=payload
            )
            
            if response:
                try:
                    return response.json()
                except json.JSONDecodeError as e:
                    print(f"  JSON解析错误: {e}")
                    print(f"  响应内容: {response.text[:500]}")
                    return None
            return None
            
        except Exception as e:
            print(f"GraphQL请求异常: {e}")
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
        
        print(f"\n当前日期: {today_date}, 获取最近{days}天的每日一题")
        
        # 获取当前月和前一个月的数据
        months_to_check = [
            (today_date.year, today_date.month),
            ((today_date.replace(day=1) - timedelta(days=1)).year, 
             (today_date.replace(day=1) - timedelta(days=1)).month)
        ]
        
        print(f"需要检查的月份: {months_to_check}")
        
        for year, month in months_to_check:
            variables = {"year": year, "month": month}
            print(f"\n正在获取 {year}年{month}月 的每日一题...")
            
            # 添加随机延迟
            self._random_delay()
            
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
        """获取题目详情"""
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
        
        print(f"\n  正在获取题目详情: {title_slug}...")
        self._random_delay()
        
        variables = {"titleSlug": title_slug}
        result = self._graphql_request(query, variables)
        
        if result and "data" in result and "question" in result["data"]:
            question = result["data"]["question"]
            if question:
                print(f"    成功获取题目: {question.get('title', '未知')} (ID: {question.get('questionId', '未知')})")
                return question
            else:
                print(f"    警告: 题目数据为空")
        else:
            print(f"    警告: 未获取到题目详情")
            if result:
                print(f"    API响应: {json.dumps(result, ensure_ascii=False)[:500]}")
        return None
    
    def get_official_solution(self, title_slug: str) -> Optional[Dict]:
        """获取官方答案"""
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
        self._random_delay()
        
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
        """获取按赞数排序的前N条评论"""
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
        
        print(f"  正在获取题目ID {question_id} 的评论...")
        self._random_delay()
        
        variables = {
            "questionId": question_id,
            "skip": 0,
            "first": limit,
            "orderBy": "hot"
        }
        
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
        """保存题目到数据库"""
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
        """保存官方答案到数据库"""
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
        """保存评论到数据库"""
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
        """检查数据库中的数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        print("\n" + "="*70)
        print("数据库检查报告")
        print("="*70)
        
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
        print("\n" + "="*70)
    
    def crawl_daily_challenges(self, days: int = 30) -> None:
        """
        爬取最近n天的每日一题
        
        Args:
            days: 天数，默认30天
        """
        print(f"\n开始爬取最近{days}天的每日一题...")
        
        # 获取每日一题列表
        daily_challenges = self.get_daily_challenges(days)
        print(f"找到{len(daily_challenges)}个每日一题")
        
        if len(daily_challenges) == 0:
            print("\n❌ 没有找到任何每日一题")
            print("建议:")
            print("  1. 检查网络连接")
            print("  2. 尝试不使用代理模式: python leetcode_crawler.py --no-proxy")
            print("  3. 稍后再试（LeetCode可能有限制）")
            return
        
        for i, challenge in enumerate(daily_challenges):
            title_slug = challenge.get("titleSlug")
            date = challenge.get("date")
            title = challenge.get("title")
            
            print(f"\n{'='*70}")
            print(f"[{i+1}/{len(daily_challenges)}] 处理 {date}: {title}")
            print(f"{'='*70}")
            
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
    
    def stop(self) -> None:
        """停止爬虫和代理池"""
        if self.proxy_pool:
            self.proxy_pool.stop()


def main():
    """主函数"""
    import sys
    
    days = 30
    use_proxy = True
    
    # 解析命令行参数
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--no-proxy":
            use_proxy = False
        elif arg == "--days" and i + 1 < len(sys.argv):
            try:
                days = int(sys.argv[i + 1])
                i += 1
            except ValueError:
                pass
        elif arg.isdigit():
            try:
                days = int(arg)
            except ValueError:
                pass
        i += 1
    
    print("\n" + "="*70)
    print("LeetCode 每日一题爬虫（增强版 - 高级代理池）")
    print("="*70)
    print(f"目标: 爬取最近 {days} 天的每日一题")
    print(f"代理模式: {'启用' if use_proxy else '禁用'}")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    crawler = None
    try:
        # 创建爬虫实例
        crawler = LeetCodeCrawler("leetcode.db", use_proxy=use_proxy)
        
        # 先检查现有数据
        print("\n检查现有数据库...")
        crawler.check_database()
        
        # 开始爬取
        print("\n开始爬取...")
        crawler.crawl_daily_challenges(days=days)
        
        # 显示代理池统计（如果使用代理）
        if use_proxy and crawler.proxy_pool:
            print("\n" + "="*70)
            print("代理池统计")
            print("="*70)
            stats = crawler.proxy_pool.get_stats()
            for key, value in stats.items():
                print(f"  {key}: {value}")
        
        print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("任务完成！")
        
    except KeyboardInterrupt:
        print("\n\n用户中断，正在清理...")
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if crawler:
            crawler.stop()


if __name__ == "__main__":
    main()
