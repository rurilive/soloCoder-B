#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
免费代理池管理器
从多个免费代理网站获取代理并验证可用性
"""

import requests
import random
import time
import re
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed


class ProxyManager:
    """代理池管理器"""
    
    def __init__(self, max_proxies: int = 20, timeout: int = 5):
        """
        初始化代理管理器
        
        Args:
            max_proxies: 最大代理数量
            timeout: 代理验证超时时间
        """
        self.max_proxies = max_proxies
        self.timeout = timeout
        self.proxies: List[Dict] = []
        self.current_index = 0
        
        # 常用的免费代理网站
        self.proxy_sources = [
            self._get_from_kuaidaili,
            self._get_from_ihuan,
            self._get_from_89ip,
            self._get_from_jiangxianli,
        ]
        
        # 测试URL（使用百度或LeetCode）
        self.test_urls = [
            "https://www.baidu.com",
            "https://leetcode.cn",
        ]
        
        # 请求头
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
    
    def _get_from_kuaidaili(self) -> List[str]:
        """从快代理获取免费代理"""
        proxies = []
        try:
            url = "https://www.kuaidaili.com/free/inha/1/"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            
            # 使用正则提取IP和端口
            pattern = r'<td data-title="IP">([\d.]+)</td>\s*<td data-title="PORT">(\d+)</td>'
            matches = re.findall(pattern, response.text)
            
            for ip, port in matches:
                proxies.append(f"{ip}:{port}")
                
        except Exception as e:
            print(f"快代理获取失败: {e}")
        
        return proxies
    
    def _get_from_ihuan(self) -> List[str]:
        """从幻代理获取免费代理"""
        proxies = []
        try:
            url = "https://ip.ihuan.me/"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            
            pattern = r'>([\d.]+):(\d+)<'
            matches = re.findall(pattern, response.text)
            
            for ip, port in matches:
                proxies.append(f"{ip}:{port}")
                
        except Exception as e:
            print(f"幻代理获取失败: {e}")
        
        return proxies
    
    def _get_from_89ip(self) -> List[str]:
        """从89代理获取免费代理"""
        proxies = []
        try:
            url = "https://www.89ip.cn/"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            
            pattern = r'<td>([\d.]+)</td>\s*<td>(\d+)</td>'
            matches = re.findall(pattern, response.text)
            
            for ip, port in matches:
                proxies.append(f"{ip}:{port}")
                
        except Exception as e:
            print(f"89代理获取失败: {e}")
        
        return proxies
    
    def _get_from_jiangxianli(self) -> List[str]:
        """从站大爷获取免费代理"""
        proxies = []
        try:
            url = "https://ip.jiangxianli.com/"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            
            pattern = r'>([\d.]+):(\d+)<'
            matches = re.findall(pattern, response.text)
            
            for ip, port in matches:
                proxies.append(f"{ip}:{port}")
                
        except Exception as e:
            print(f"站大爷代理获取失败: {e}")
        
        return proxies
    
    def _validate_proxy(self, proxy_str: str) -> Optional[Dict]:
        """
        验证代理是否可用
        
        Args:
            proxy_str: 代理字符串，格式为 "ip:port"
            
        Returns:
            可用的代理字典，包含http和https，否则返回None
        """
        proxy = {
            "http": f"http://{proxy_str}",
            "https": f"https://{proxy_str}"
        }
        
        # 随机选择一个测试URL
        test_url = random.choice(self.test_urls)
        
        try:
            start_time = time.time()
            response = requests.get(
                test_url,
                proxies=proxy,
                headers=self.headers,
                timeout=self.timeout
            )
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                print(f"  ✅ 验证成功: {proxy_str} (耗时: {elapsed:.2f}s)")
                return {
                    "proxy": proxy,
                    "proxy_str": proxy_str,
                    "response_time": elapsed
                }
        except Exception as e:
            pass
        
        return None
    
    def fetch_proxies(self) -> int:
        """
        从所有源获取代理并验证
        
        Returns:
            获取到的可用代理数量
        """
        print("\n" + "="*60)
        print("开始获取免费代理...")
        print("="*60)
        
        all_proxies = set()
        
        # 从所有源获取代理
        for source in self.proxy_sources:
            try:
                proxies = source()
                for p in proxies:
                    all_proxies.add(p)
                print(f"从 {source.__name__} 获取到 {len(proxies)} 个代理")
            except Exception as e:
                print(f"从 {source.__name__} 获取代理失败: {e}")
        
        print(f"\n总共获取到 {len(all_proxies)} 个代理，开始验证...")
        
        # 并发验证代理
        valid_proxies = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_proxy = {
                executor.submit(self._validate_proxy, proxy_str): proxy_str 
                for proxy_str in list(all_proxies)[:50]  # 最多验证50个
            }
            
            for future in as_completed(future_to_proxy):
                try:
                    result = future.result()
                    if result:
                        valid_proxies.append(result)
                        if len(valid_proxies) >= self.max_proxies:
                            break
                except Exception as e:
                    pass
        
        # 按响应时间排序
        valid_proxies.sort(key=lambda x: x["response_time"])
        self.proxies = valid_proxies
        self.current_index = 0
        
        print(f"\n验证完成！可用代理数量: {len(self.proxies)}")
        for i, p in enumerate(self.proxies[:5]):
            print(f"  {i+1}. {p['proxy_str']} - 响应时间: {p['response_time']:.2f}s")
        
        return len(self.proxies)
    
    def get_random_proxy(self) -> Optional[Dict]:
        """
        随机获取一个代理
        
        Returns:
            代理字典，如果没有可用代理则返回None
        """
        if not self.proxies:
            return None
        return random.choice(self.proxies)["proxy"]
    
    def get_next_proxy(self) -> Optional[Dict]:
        """
        轮询获取下一个代理
        
        Returns:
            代理字典，如果没有可用代理则返回None
        """
        if not self.proxies:
            return None
        
        proxy = self.proxies[self.current_index]["proxy"]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy
    
    def remove_proxy(self, proxy_str: str) -> None:
        """
        移除不可用的代理
        
        Args:
            proxy_str: 代理字符串
        """
        self.proxies = [p for p in self.proxies if p["proxy_str"] != proxy_str]
        print(f"移除不可用代理: {proxy_str}，剩余代理: {len(self.proxies)}")
    
    def has_proxies(self) -> bool:
        """
        检查是否有可用代理
        
        Returns:
            是否有可用代理
        """
        return len(self.proxies) > 0


# 测试代理管理器
if __name__ == "__main__":
    proxy_manager = ProxyManager(max_proxies=10)
    proxy_manager.fetch_proxies()
    
    if proxy_manager.has_proxies():
        print("\n测试代理...")
        proxy = proxy_manager.get_random_proxy()
        print(f"使用代理: {proxy}")
        
        try:
            response = requests.get(
                "https://www.baidu.com",
                proxies=proxy,
                timeout=10
            )
            print(f"测试成功，状态码: {response.status_code}")
        except Exception as e:
            print(f"测试失败: {e}")
    else:
        print("\n没有获取到可用代理，将使用直连模式")
