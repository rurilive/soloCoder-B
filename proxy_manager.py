#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
免费代理池管理器（增强版）
- 支持多种代理源
- 详细的调试输出
- 改进的代理验证逻辑
- 支持HTTP和HTTPS代理
"""

import requests
import random
import time
import re
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    print("警告: 未安装 beautifulsoup4，某些代理源可能无法正确解析")
    print("建议安装: pip install beautifulsoup4")


class ProxyManager:
    """代理池管理器（增强版）"""
    
    def __init__(self, max_proxies: int = 20, timeout: int = 10, debug: bool = True):
        """
        初始化代理管理器
        
        Args:
            max_proxies: 最大代理数量
            timeout: 代理验证超时时间
            debug: 是否开启调试模式
        """
        self.max_proxies = max_proxies
        self.timeout = timeout
        self.debug = debug
        self.proxies: List[Dict] = []
        self.current_index = 0
        
        # 增强的请求头
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        
        # 测试URL列表（包含http和https）
        self.test_urls = [
            ("http://www.baidu.com", "http"),
            ("http://httpbin.org/ip", "http"),
            ("https://www.baidu.com", "https"),
        ]
    
    def _debug_print(self, msg: str) -> None:
        """调试打印"""
        if self.debug:
            print(f"  [调试] {msg}")
    
    def _get_page_content(self, url: str, headers: Dict = None) -> Tuple[bool, str]:
        """
        获取页面内容
        
        Args:
            url: 目标URL
            headers: 请求头
            
        Returns:
            (是否成功, 页面内容或错误信息)
        """
        try:
            response = requests.get(
                url,
                headers=headers or self.headers,
                timeout=15,
                allow_redirects=True
            )
            response.encoding = 'utf-8'
            return True, response.text
        except requests.exceptions.Timeout:
            return False, "请求超时"
        except requests.exceptions.ConnectionError as e:
            return False, f"连接错误: {e}"
        except Exception as e:
            return False, f"未知错误: {e}"
    
    def _parse_with_regex(self, html: str, patterns: List[str]) -> List[str]:
        """
        使用正则表达式解析代理
        
        Args:
            html: HTML内容
            patterns: 正则表达式列表
            
        Returns:
            代理列表 (ip:port)
        """
        proxies = []
        for pattern in patterns:
            matches = re.findall(pattern, html, re.MULTILINE | re.DOTALL)
            for match in matches:
                if isinstance(match, tuple) and len(match) >= 2:
                    ip, port = match[0], match[1]
                else:
                    continue
                
                if self._is_valid_ip_port(ip, port):
                    proxy_str = f"{ip}:{port}"
                    proxies.append(proxy_str)
        
        return list(set(proxies))
    
    def _parse_with_bs4(self, html: str) -> List[str]:
        """
        使用BeautifulSoup解析代理
        
        Args:
            html: HTML内容
            
        Returns:
            代理列表 (ip:port)
        """
        if not HAS_BS4:
            return []
        
        proxies = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找所有包含IP和端口的表格行
            rows = soup.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    ip_text = cells[0].get_text(strip=True)
                    port_text = cells[1].get_text(strip=True)
                    
                    if self._is_valid_ip_port(ip_text, port_text):
                        proxy_str = f"{ip_text}:{port_text}"
                        proxies.append(proxy_str)
        except Exception as e:
            self._debug_print(f"BeautifulSoup解析错误: {e}")
        
        return list(set(proxies))
    
    def _is_valid_ip_port(self, ip: str, port: str) -> bool:
        """
        验证IP和端口是否有效
        
        Args:
            ip: IP地址
            port: 端口号
            
        Returns:
            是否有效
        """
        if not ip or not port:
            return False
        
        # 验证IP格式
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(ip_pattern, ip.strip()):
            return False
        
        # 验证端口
        try:
            port_num = int(port.strip())
            if not (0 < port_num <= 65535):
                return False
        except ValueError:
            return False
        
        return True
    
    def _get_from_kuaidaili(self) -> List[str]:
        """从快代理获取免费代理"""
        proxies = []
        self._debug_print("尝试从快代理获取...")
        
        # 尝试多个URL
        urls = [
            "https://www.kuaidaili.com/free/inha/1/",
            "https://www.kuaidaili.com/free/intr/1/",
        ]
        
        for url in urls:
            success, content = self._get_page_content(url)
            
            if success:
                self._debug_print(f"快代理页面获取成功，长度: {len(content)} 字符")
                
                # 尝试多种正则模式
                patterns = [
                    r'<td[^>]*data-title="IP"[^>]*>([\d.]+)</td>\s*<td[^>]*data-title="PORT"[^>]*>(\d+)</td>',
                    r'<td[^>]*>\s*([\d.]+)\s*</td>\s*<td[^>]*>\s*(\d+)\s*</td>',
                    r'([\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3})\s*[\s:：]\s*(\d{2,5})',
                ]
                
                # 使用正则解析
                regex_proxies = self._parse_with_regex(content, patterns)
                self._debug_print(f"正则解析到 {len(regex_proxies)} 个代理")
                
                # 使用BeautifulSoup解析
                bs4_proxies = self._parse_with_bs4(content)
                self._debug_print(f"BS4解析到 {len(bs4_proxies)} 个代理")
                
                # 合并结果
                all_proxies = list(set(regex_proxies + bs4_proxies))
                proxies.extend(all_proxies)
                
                if len(all_proxies) > 0:
                    self._debug_print(f"从快代理共获取到 {len(all_proxies)} 个代理")
                    break
            else:
                self._debug_print(f"快代理获取失败: {content}")
        
        return list(set(proxies))
    
    def _get_from_89ip(self) -> List[str]:
        """从89代理获取免费代理"""
        proxies = []
        self._debug_print("尝试从89代理获取...")
        
        urls = [
            "https://www.89ip.cn/",
            "https://www.89ip.cn/index_1.html",
        ]
        
        for url in urls:
            success, content = self._get_page_content(url)
            
            if success:
                self._debug_print(f"89代理页面获取成功，长度: {len(content)} 字符")
                
                patterns = [
                    r'<td[^>]*>\s*([\d.]+)\s*</td>\s*<td[^>]*>\s*(\d+)\s*</td>',
                    r'([\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3})\s*[\s:：]\s*(\d{2,5})',
                ]
                
                regex_proxies = self._parse_with_regex(content, patterns)
                bs4_proxies = self._parse_with_bs4(content)
                
                all_proxies = list(set(regex_proxies + bs4_proxies))
                proxies.extend(all_proxies)
                
                if len(all_proxies) > 0:
                    self._debug_print(f"从89代理共获取到 {len(all_proxies)} 个代理")
                    break
            else:
                self._debug_print(f"89代理获取失败: {content}")
        
        return list(set(proxies))
    
    def _get_from_jiangxianli(self) -> List[str]:
        """从站大爷获取免费代理"""
        proxies = []
        self._debug_print("尝试从站大爷获取...")
        
        urls = [
            "https://ip.jiangxianli.com/",
            "https://ip.jiangxianli.com/?page=1",
        ]
        
        for url in urls:
            success, content = self._get_page_content(url)
            
            if success:
                self._debug_print(f"站大爷页面获取成功，长度: {len(content)} 字符")
                
                patterns = [
                    r'<td[^>]*>\s*([\d.]+)\s*</td>\s*<td[^>]*>\s*(\d+)\s*</td>',
                    r'([\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3})\s*[\s:：]\s*(\d{2,5})',
                    r'>([\d.]+):(\d+)<',
                ]
                
                regex_proxies = self._parse_with_regex(content, patterns)
                bs4_proxies = self._parse_with_bs4(content)
                
                all_proxies = list(set(regex_proxies + bs4_proxies))
                proxies.extend(all_proxies)
                
                if len(all_proxies) > 0:
                    self._debug_print(f"从站大爷共获取到 {len(all_proxies)} 个代理")
                    break
            else:
                self._debug_print(f"站大爷获取失败: {content}")
        
        return list(set(proxies))
    
    def _get_from_ihuan(self) -> List[str]:
        """从幻代理获取免费代理"""
        proxies = []
        self._debug_print("尝试从幻代理获取...")
        
        urls = [
            "https://ip.ihuan.me/",
            "https://ip.ihuan.me/ti.html",
        ]
        
        for url in urls:
            success, content = self._get_page_content(url)
            
            if success:
                self._debug_print(f"幻代理页面获取成功，长度: {len(content)} 字符")
                
                patterns = [
                    r'([\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3})\s*[\s:：]\s*(\d{2,5})',
                    r'>([\d.]+):(\d+)<',
                    r'([\d.]+)\s*[:：]\s*(\d+)',
                ]
                
                regex_proxies = self._parse_with_regex(content, patterns)
                bs4_proxies = self._parse_with_bs4(content)
                
                all_proxies = list(set(regex_proxies + bs4_proxies))
                proxies.extend(all_proxies)
                
                if len(all_proxies) > 0:
                    self._debug_print(f"从幻代理共获取到 {len(all_proxies)} 个代理")
                    break
            else:
                self._debug_print(f"幻代理获取失败: {content}")
        
        return list(set(proxies))
    
    def _get_from_proxy_list(self) -> List[str]:
        """从代理列表API获取"""
        proxies = []
        self._debug_print("尝试从代理列表API获取...")
        
        # 一些公开的代理API
        api_urls = [
            "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
            "https://www.proxy-list.download/api/v1/get?type=http",
        ]
        
        for url in api_urls:
            success, content = self._get_page_content(url)
            
            if success:
                self._debug_print(f"代理API获取成功，长度: {len(content)} 字符")
                
                # 解析每行的代理
                lines = content.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if ':' in line:
                        parts = line.split(':')
                        if len(parts) == 2:
                            ip, port = parts
                            if self._is_valid_ip_port(ip, port):
                                proxies.append(f"{ip}:{port}")
                
                if len(proxies) > 0:
                    self._debug_print(f"从代理API共获取到 {len(proxies)} 个代理")
                    break
            else:
                self._debug_print(f"代理API获取失败: {content}")
        
        return list(set(proxies))
    
    def _validate_proxy(self, proxy_str: str) -> Optional[Dict]:
        """
        验证代理是否可用（增强版）
        
        Args:
            proxy_str: 代理字符串，格式为 "ip:port"
            
        Returns:
            可用的代理字典，否则返回None
        """
        self._debug_print(f"正在验证代理: {proxy_str}")
        
        # 分别测试http和https代理
        test_results = []
        
        for test_url, protocol in self.test_urls:
            proxy_config = {
                "http": f"http://{proxy_str}",
                "https": f"http://{proxy_str}"  # 大多数免费代理只支持HTTP协议
            }
            
            try:
                start_time = time.time()
                response = requests.get(
                    test_url,
                    proxies=proxy_config,
                    headers=self.headers,
                    timeout=self.timeout,
                    allow_redirects=True
                )
                elapsed = time.time() - start_time
                
                # 检查状态码
                if response.status_code in [200, 301, 302, 304]:
                    result = {
                        "proxy_str": proxy_str,
                        "proxy": proxy_config,
                        "response_time": elapsed,
                        "protocol": protocol,
                        "status_code": response.status_code
                    }
                    test_results.append(result)
                    self._debug_print(f"  ✅ {protocol} 验证成功 (状态码: {response.status_code}, 耗时: {elapsed:.2f}s)")
                    
                    # 如果HTTP验证成功，立即返回
                    if protocol == "http":
                        return result
                        
            except requests.exceptions.ProxyError as e:
                self._debug_print(f"  ❌ {protocol} 代理错误: {str(e)[:50]}")
            except requests.exceptions.Timeout:
                self._debug_print(f"  ❌ {protocol} 超时 ({self.timeout}s)")
            except requests.exceptions.ConnectionError as e:
                self._debug_print(f"  ❌ {protocol} 连接错误: {str(e)[:50]}")
            except Exception as e:
                self._debug_print(f"  ❌ {protocol} 其他错误: {str(e)[:50]}")
        
        # 如果有任何验证成功，返回最快的那个
        if test_results:
            test_results.sort(key=lambda x: x["response_time"])
            return test_results[0]
        
        return None
    
    def fetch_proxies(self) -> int:
        """
        从所有源获取代理并验证
        
        Returns:
            获取到的可用代理数量
        """
        print("\n" + "="*70)
        print("开始获取免费代理...")
        print("="*70)
        
        # 代理源列表
        proxy_sources = [
            ("快代理", self._get_from_kuaidaili),
            ("89代理", self._get_from_89ip),
            ("站大爷", self._get_from_jiangxianli),
            ("幻代理", self._get_from_ihuan),
            ("代理API", self._get_from_proxy_list),
        ]
        
        all_proxies = set()
        
        # 从所有源获取代理
        print("\n[步骤1] 从各个代理源获取代理...")
        for source_name, source_func in proxy_sources:
            print(f"\n正在从 {source_name} 获取...")
            try:
                proxies = source_func()
                for p in proxies:
                    all_proxies.add(p)
                print(f"✅ 从 {source_name} 获取到 {len(proxies)} 个代理")
            except Exception as e:
                print(f"❌ 从 {source_name} 获取代理失败: {e}")
        
        print(f"\n[步骤1完成] 总共获取到 {len(all_proxies)} 个代理")
        
        if len(all_proxies) == 0:
            print("\n❌ 没有获取到任何代理，请检查网络连接或稍后再试")
            return 0
        
        print(f"\n[步骤2] 开始验证代理可用性 (超时: {self.timeout}s)...")
        
        # 并发验证代理
        valid_proxies = []
        proxy_list = list(all_proxies)
        
        # 使用更多的线程来验证
        max_workers = min(20, len(proxy_list))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_proxy = {
                executor.submit(self._validate_proxy, proxy_str): proxy_str 
                for proxy_str in proxy_list
            }
            
            completed = 0
            for future in as_completed(future_to_proxy):
                completed += 1
                if completed % 10 == 0:
                    print(f"  验证进度: {completed}/{len(proxy_list)}, 已找到 {len(valid_proxies)} 个可用代理")
                
                try:
                    result = future.result()
                    if result:
                        valid_proxies.append(result)
                        # 找到足够的代理就提前结束
                        if len(valid_proxies) >= self.max_proxies:
                            print(f"\n  已找到足够的代理 ({self.max_proxies}个)，提前结束验证")
                            break
                except Exception as e:
                    pass
        
        # 按响应时间排序
        valid_proxies.sort(key=lambda x: x["response_time"])
        self.proxies = valid_proxies
        self.current_index = 0
        
        print("\n" + "="*70)
        print("代理验证完成！")
        print("="*70)
        print(f"总体验证代理数: {len(proxy_list)}")
        print(f"可用代理数: {len(self.proxies)}")
        
        if len(self.proxies) > 0:
            print(f"\n最快的 {min(5, len(self.proxies))} 个代理:")
            for i, p in enumerate(self.proxies[:5]):
                print(f"  {i+1}. {p['proxy_str']} - 响应时间: {p['response_time']:.2f}s, 协议: {p.get('protocol', 'http')}")
        else:
            print("\n❌ 没有找到可用的免费代理")
            print("建议:")
            print("  1. 尝试不使用代理模式运行: python leetcode_crawler.py --no-proxy")
            print("  2. 稍后再试（免费代理可用性波动较大）")
            print("  3. 使用付费代理服务")
        
        return len(self.proxies)
    
    def get_random_proxy(self) -> Optional[Dict]:
        """随机获取一个代理"""
        if not self.proxies:
            return None
        return random.choice(self.proxies)["proxy"]
    
    def get_next_proxy(self) -> Optional[Dict]:
        """轮询获取下一个代理"""
        if not self.proxies:
            return None
        
        proxy = self.proxies[self.current_index]["proxy"]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy
    
    def remove_proxy(self, proxy_str: str) -> None:
        """移除不可用的代理"""
        original_count = len(self.proxies)
        self.proxies = [p for p in self.proxies if p["proxy_str"] != proxy_str]
        
        if len(self.proxies) < original_count:
            print(f"移除不可用代理: {proxy_str}，剩余代理: {len(self.proxies)}")
    
    def has_proxies(self) -> bool:
        """检查是否有可用代理"""
        return len(self.proxies) > 0


# 测试代理管理器
if __name__ == "__main__":
    print("="*70)
    print("代理池管理器测试")
    print("="*70)
    
    # 创建代理管理器（开启调试模式）
    proxy_manager = ProxyManager(max_proxies=10, timeout=8, debug=True)
    
    # 获取代理
    proxy_count = proxy_manager.fetch_proxies()
    
    if proxy_count > 0:
        print(f"\n\n测试最快的代理...")
        proxy = proxy_manager.get_random_proxy()
        print(f"使用代理: {proxy}")
        
        test_urls = [
            "http://www.baidu.com",
            "https://leetcode.cn",
        ]
        
        for url in test_urls:
            print(f"\n测试访问: {url}")
            try:
                response = requests.get(
                    url,
                    proxies=proxy,
                    timeout=15,
                    headers=proxy_manager.headers
                )
                print(f"  ✅ 成功! 状态码: {response.status_code}")
            except Exception as e:
                print(f"  ❌ 失败: {e}")
    else:
        print("\n测试失败: 没有可用代理")
