#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级代理池管理器
- 后台线程定期验证代理可用性
- 线程安全的代理获取机制
- 不允许连续返回相同代理
- 相同代理返回间隔5秒以上
- 自动从多个源获取新代理
"""

import requests
import random
import time
import re
import threading
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    print("警告: 未安装 beautifulsoup4，某些代理源可能无法正确解析")


class AdvancedProxyPool:
    """高级代理池管理器"""
    
    def __init__(self, 
                 max_proxies: int = 30,
                 validation_interval: int = 60,
                 refresh_interval: int = 300,
                 proxy_return_interval: float = 5.0,
                 timeout: int = 10,
                 debug: bool = True):
        """
        初始化高级代理池
        
        Args:
            max_proxies: 最大代理数量
            validation_interval: 验证间隔（秒）
            refresh_interval: 刷新代理间隔（秒）
            proxy_return_interval: 相同代理返回间隔（秒）
            timeout: 代理验证超时时间
            debug: 是否开启调试模式
        """
        self.max_proxies = max_proxies
        self.validation_interval = validation_interval
        self.refresh_interval = refresh_interval
        self.proxy_return_interval = proxy_return_interval
        self.timeout = timeout
        self.debug = debug
        
        # 代理存储
        self._proxies: List[Dict] = []
        
        # 代理使用记录
        self._last_used: Dict[str, float] = {}  # proxy_str -> last_used_time
        self._last_returned: Optional[str] = None  # 上一次返回的代理
        
        # 线程安全
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        
        # 后台线程
        self._validator_thread: Optional[threading.Thread] = None
        self._refresh_thread: Optional[threading.Thread] = None
        
        # 请求头
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        
        # 测试URL
        self.test_urls = [
            ("http://www.baidu.com", "http"),
            ("http://httpbin.org/ip", "http"),
        ]
        
        # 统计信息
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "proxies_refreshed": 0,
            "proxies_validated": 0,
        }
    
    def _debug_print(self, msg: str) -> None:
        """调试打印"""
        if self.debug:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] [代理池] {msg}")
    
    # ==================== 代理获取和解析 ====================
    
    def _get_page_content(self, url: str, headers: Dict = None) -> Tuple[bool, str]:
        """获取页面内容"""
        try:
            response = requests.get(
                url,
                headers=headers or self.headers,
                timeout=15,
                allow_redirects=True
            )
            response.encoding = 'utf-8'
            return True, response.text
        except Exception as e:
            return False, str(e)
    
    def _is_valid_ip_port(self, ip: str, port: str) -> bool:
        """验证IP和端口是否有效"""
        if not ip or not port:
            return False
        
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(ip_pattern, ip.strip()):
            return False
        
        try:
            port_num = int(port.strip())
            if not (0 < port_num <= 65535):
                return False
        except ValueError:
            return False
        
        return True
    
    def _parse_with_regex(self, html: str, patterns: List[str]) -> List[str]:
        """使用正则解析代理"""
        proxies = []
        for pattern in patterns:
            matches = re.findall(pattern, html, re.MULTILINE | re.DOTALL)
            for match in matches:
                if isinstance(match, tuple) and len(match) >= 2:
                    ip, port = match[0], match[1]
                else:
                    continue
                
                if self._is_valid_ip_port(ip, port):
                    proxies.append(f"{ip}:{port}")
        
        return list(set(proxies))
    
    def _parse_with_bs4(self, html: str) -> List[str]:
        """使用BeautifulSoup解析代理"""
        if not HAS_BS4:
            return []
        
        proxies = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            rows = soup.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    ip_text = cells[0].get_text(strip=True)
                    port_text = cells[1].get_text(strip=True)
                    
                    if self._is_valid_ip_port(ip_text, port_text):
                        proxies.append(f"{ip_text}:{port_text}")
        except Exception:
            pass
        
        return list(set(proxies))
    
    def _get_from_kuaidaili(self) -> List[str]:
        """从快代理获取"""
        proxies = []
        urls = [
            "https://www.kuaidaili.com/free/inha/1/",
            "https://www.kuaidaili.com/free/intr/1/",
        ]
        
        for url in urls:
            success, content = self._get_page_content(url)
            if success:
                patterns = [
                    r'<td[^>]*data-title="IP"[^>]*>([\d.]+)</td>\s*<td[^>]*data-title="PORT"[^>]*>(\d+)</td>',
                    r'<td[^>]*>\s*([\d.]+)\s*</td>\s*<td[^>]*>\s*(\d+)\s*</td>',
                ]
                regex_proxies = self._parse_with_regex(content, patterns)
                bs4_proxies = self._parse_with_bs4(content)
                all_proxies = list(set(regex_proxies + bs4_proxies))
                proxies.extend(all_proxies)
                if len(all_proxies) > 0:
                    break
        
        return list(set(proxies))
    
    def _get_from_89ip(self) -> List[str]:
        """从89代理获取"""
        proxies = []
        urls = ["https://www.89ip.cn/", "https://www.89ip.cn/index_1.html"]
        
        for url in urls:
            success, content = self._get_page_content(url)
            if success:
                patterns = [
                    r'<td[^>]*>\s*([\d.]+)\s*</td>\s*<td[^>]*>\s*(\d+)\s*</td>',
                ]
                regex_proxies = self._parse_with_regex(content, patterns)
                bs4_proxies = self._parse_with_bs4(content)
                all_proxies = list(set(regex_proxies + bs4_proxies))
                proxies.extend(all_proxies)
                if len(all_proxies) > 0:
                    break
        
        return list(set(proxies))
    
    def _get_from_proxy_api(self) -> List[str]:
        """从代理API获取"""
        proxies = []
        api_urls = [
            "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
        ]
        
        for url in api_urls:
            success, content = self._get_page_content(url)
            if success:
                lines = content.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if ':' in line:
                        parts = line.split(':')
                        if len(parts) == 2 and self._is_valid_ip_port(parts[0], parts[1]):
                            proxies.append(line)
                if len(proxies) > 0:
                    break
        
        return list(set(proxies))
    
    # ==================== 代理验证 ====================
    
    def _validate_single_proxy(self, proxy_str: str) -> Optional[Dict]:
        """验证单个代理"""
        for test_url, protocol in self.test_urls:
            proxy_config = {
                "http": f"http://{proxy_str}",
                "https": f"http://{proxy_str}"
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
                
                if response.status_code in [200, 301, 302, 304]:
                    return {
                        "proxy_str": proxy_str,
                        "proxy": proxy_config,
                        "response_time": elapsed,
                        "last_validated": time.time(),
                        "success_count": 1,
                        "fail_count": 0,
                    }
            except Exception:
                pass
        
        return None
    
    def _validate_proxies_batch(self, proxy_list: List[str], max_workers: int = 10) -> List[Dict]:
        """批量验证代理"""
        valid_proxies = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_proxy = {
                executor.submit(self._validate_single_proxy, proxy_str): proxy_str
                for proxy_str in proxy_list
            }
            
            for future in as_completed(future_to_proxy):
                try:
                    result = future.result()
                    if result:
                        valid_proxies.append(result)
                except Exception:
                    pass
        
        # 按响应时间排序
        valid_proxies.sort(key=lambda x: x["response_time"])
        return valid_proxies
    
    # ==================== 后台线程任务 ====================
    
    def _refresh_proxies_task(self) -> None:
        """刷新代理任务（后台线程）"""
        while not self._stop_event.is_set():
            self._debug_print("开始从各代理源获取新代理...")
            
            # 从所有源获取代理
            all_proxies = set()
            
            sources = [
                ("快代理", self._get_from_kuaidaili),
                ("89代理", self._get_from_89ip),
                ("代理API", self._get_from_proxy_api),
            ]
            
            for source_name, source_func in sources:
                try:
                    proxies = source_func()
                    for p in proxies:
                        all_proxies.add(p)
                    self._debug_print(f"从 {source_name} 获取到 {len(proxies)} 个代理")
                except Exception as e:
                    self._debug_print(f"从 {source_name} 获取失败: {e}")
            
            self._debug_print(f"总共获取到 {len(all_proxies)} 个代理，开始验证...")
            
            # 验证新获取的代理
            new_valid_proxies = self._validate_proxies_batch(list(all_proxies))
            
            with self._lock:
                # 合并现有代理和新代理
                existing_proxy_strs = {p["proxy_str"] for p in self._proxies}
                
                for proxy in new_valid_proxies:
                    if proxy["proxy_str"] not in existing_proxy_strs:
                        self._proxies.append(proxy)
                        # 初始化使用记录
                        if proxy["proxy_str"] not in self._last_used:
                            self._last_used[proxy["proxy_str"]] = 0
                
                # 限制最大数量
                if len(self._proxies) > self.max_proxies:
                    self._proxies.sort(key=lambda x: x["response_time"])
                    self._proxies = self._proxies[:self.max_proxies]
                
                self._stats["proxies_refreshed"] += len(new_valid_proxies)
            
            self._debug_print(f"刷新完成！当前可用代理: {len(self._proxies)} 个")
            
            # 等待下一次刷新
            self._stop_event.wait(self.refresh_interval)
    
    def _validate_existing_proxies_task(self) -> None:
        """验证现有代理任务（后台线程）"""
        while not self._stop_event.is_set():
            # 等待验证间隔
            self._stop_event.wait(self.validation_interval)
            
            if self._stop_event.is_set():
                break
            
            with self._lock:
                if not self._proxies:
                    self._debug_print("没有代理需要验证")
                    continue
                
                proxy_list = [p["proxy_str"] for p in self._proxies]
                self._debug_print(f"开始验证现有 {len(proxy_list)} 个代理...")
            
            # 验证代理（不在锁内执行，避免阻塞）
            validation_results = {}
            for proxy_str in proxy_list:
                result = self._validate_single_proxy(proxy_str)
                validation_results[proxy_str] = result is not None
            
            # 更新代理状态
            with self._lock:
                new_proxies = []
                for proxy in self._proxies:
                    proxy_str = proxy["proxy_str"]
                    is_valid = validation_results.get(proxy_str, False)
                    
                    if is_valid:
                        proxy["last_validated"] = time.time()
                        proxy["success_count"] = proxy.get("success_count", 0) + 1
                        new_proxies.append(proxy)
                    else:
                        proxy["fail_count"] = proxy.get("fail_count", 0) + 1
                        # 失败次数超过3次则移除
                        if proxy["fail_count"] < 3:
                            new_proxies.append(proxy)
                
                removed_count = len(self._proxies) - len(new_proxies)
                self._proxies = new_proxies
                self._stats["proxies_validated"] += len(proxy_list)
                
                if removed_count > 0:
                    self._debug_print(f"移除了 {removed_count} 个不可用代理")
                self._debug_print(f"验证完成！剩余可用代理: {len(self._proxies)} 个")
    
    # ==================== 公共接口 ====================
    
    def start(self) -> None:
        """启动代理池后台线程"""
        if self._validator_thread and self._validator_thread.is_alive():
            self._debug_print("代理池已经在运行中")
            return
        
        self._stop_event.clear()
        
        # 先同步获取一次代理
        self._debug_print("初始化代理池...")
        self._debug_print("先从各源获取代理...")
        
        # 同步获取初始代理
        all_proxies = set()
        sources = [
            ("快代理", self._get_from_kuaidaili),
            ("89代理", self._get_from_89ip),
            ("代理API", self._get_from_proxy_api),
        ]
        
        for source_name, source_func in sources:
            try:
                proxies = source_func()
                for p in proxies:
                    all_proxies.add(p)
                self._debug_print(f"从 {source_name} 获取到 {len(proxies)} 个代理")
            except Exception as e:
                self._debug_print(f"从 {source_name} 获取失败: {e}")
        
        # 验证初始代理
        if all_proxies:
            self._debug_print(f"验证 {len(all_proxies)} 个代理...")
            valid_proxies = self._validate_proxies_batch(list(all_proxies))
            
            with self._lock:
                self._proxies = valid_proxies
                for proxy in valid_proxies:
                    self._last_used[proxy["proxy_str"]] = 0
            
            self._debug_print(f"初始化完成！可用代理: {len(self._proxies)} 个")
        else:
            self._debug_print("警告: 初始获取代理失败，后台线程将继续尝试")
        
        # 启动后台线程
        self._refresh_thread = threading.Thread(
            target=self._refresh_proxies_task,
            daemon=True,
            name="ProxyRefreshThread"
        )
        self._refresh_thread.start()
        
        self._validator_thread = threading.Thread(
            target=self._validate_existing_proxies_task,
            daemon=True,
            name="ProxyValidationThread"
        )
        self._validator_thread.start()
        
        self._debug_print("代理池后台线程已启动")
    
    def stop(self) -> None:
        """停止代理池后台线程"""
        self._debug_print("正在停止代理池...")
        self._stop_event.set()
        
        if self._refresh_thread and self._refresh_thread.is_alive():
            self._refresh_thread.join(timeout=5)
        
        if self._validator_thread and self._validator_thread.is_alive():
            self._validator_thread.join(timeout=5)
        
        self._debug_print("代理池已停止")
    
    def get_proxy(self) -> Optional[Dict]:
        """
        获取可用代理
        
        规则：
        1. 不允许连续返回相同代理
        2. 相同代理返回间隔5秒以上
        3. 优先返回响应快的代理
        
        Returns:
            代理字典，如果没有可用代理则返回None
        """
        with self._lock:
            self._stats["total_requests"] += 1
            
            if not self._proxies:
                self._stats["failed_requests"] += 1
                self._debug_print("没有可用代理")
                return None
            
            current_time = time.time()
            
            # 按响应时间排序
            sorted_proxies = sorted(self._proxies, key=lambda x: x["response_time"])
            
            # 寻找符合条件的代理
            selected_proxy = None
            
            for proxy in sorted_proxies:
                proxy_str = proxy["proxy_str"]
                last_used = self._last_used.get(proxy_str, 0)
                time_since_last_use = current_time - last_used
                
                # 检查条件
                # 1. 不是上一次返回的代理
                # 2. 距离上次使用超过5秒
                if (proxy_str != self._last_returned and 
                    time_since_last_use >= self.proxy_return_interval):
                    selected_proxy = proxy
                    break
            
            # 如果没有找到符合条件的，选择最早使用的那个
            if not selected_proxy:
                # 按最后使用时间排序
                sorted_by_usage = sorted(
                    self._proxies,
                    key=lambda x: self._last_used.get(x["proxy_str"], 0)
                )
                
                # 尝试选择不是上一次返回的
                for proxy in sorted_by_usage:
                    if proxy["proxy_str"] != self._last_returned:
                        selected_proxy = proxy
                        break
                
                # 如果所有代理都是上一次返回的（只有一个代理的情况）
                if not selected_proxy and self._proxies:
                    # 检查是否超过5秒
                    proxy = self._proxies[0]
                    last_used = self._last_used.get(proxy["proxy_str"], 0)
                    time_since_last_use = current_time - last_used
                    
                    if time_since_last_use >= self.proxy_return_interval:
                        selected_proxy = proxy
                    else:
                        self._debug_print(
                            f"代理 {proxy['proxy_str']} 距离上次使用仅 {time_since_last_use:.1f}秒，"
                            f"需要等待 {self.proxy_return_interval - time_since_last_use:.1f}秒"
                        )
                        self._stats["failed_requests"] += 1
                        return None
            
            if selected_proxy:
                # 更新使用记录
                proxy_str = selected_proxy["proxy_str"]
                self._last_used[proxy_str] = current_time
                self._last_returned = proxy_str
                self._stats["successful_requests"] += 1
                
                self._debug_print(
                    f"返回代理: {proxy_str} (响应时间: {selected_proxy['response_time']:.2f}s)"
                )
                return selected_proxy["proxy"]
            
            self._stats["failed_requests"] += 1
            return None
    
    def get_stats(self) -> Dict:
        """获取代理池统计信息"""
        with self._lock:
            return {
                **self._stats,
                "current_proxies": len(self._proxies),
                "last_returned": self._last_returned,
            }
    
    def has_proxies(self) -> bool:
        """检查是否有可用代理"""
        with self._lock:
            return len(self._proxies) > 0


# 测试
if __name__ == "__main__":
    print("="*70)
    print("高级代理池测试")
    print("="*70)
    
    # 创建代理池
    proxy_pool = AdvancedProxyPool(
        max_proxies=20,
        validation_interval=60,
        refresh_interval=300,
        proxy_return_interval=5.0,
        debug=True
    )
    
    try:
        # 启动代理池
        proxy_pool.start()
        
        # 等待初始化
        time.sleep(3)
        
        # 测试获取代理
        print("\n" + "="*70)
        print("测试获取代理（连续获取10次）")
        print("="*70)
        
        for i in range(10):
            print(f"\n第 {i+1} 次请求:")
            proxy = proxy_pool.get_proxy()
            
            if proxy:
                print(f"  获取到代理: {proxy}")
                
                # 测试代理
                try:
                    response = requests.get(
                        "http://www.baidu.com",
                        proxies=proxy,
                        timeout=10
                    )
                    print(f"  代理测试成功，状态码: {response.status_code}")
                except Exception as e:
                    print(f"  代理测试失败: {e}")
            else:
                print(f"  没有可用代理")
            
            # 等待一小段时间
            time.sleep(1)
        
        # 显示统计
        print("\n" + "="*70)
        print("代理池统计")
        print("="*70)
        stats = proxy_pool.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
            
    except KeyboardInterrupt:
        print("\n用户中断")
    finally:
        proxy_pool.stop()
