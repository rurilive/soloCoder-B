#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级代理池管理器
- 后台线程定期验证代理可用性
- 线程安全的代理获取机制
- 不允许连续返回相同代理
- 相同代理返回间隔5秒以上
- 自动从多个源获取新代理
- 支持代理汇报机制，无效代理自动删除
"""

import requests
import random
import time
import re
import threading
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from collections import deque

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    print("警告: 未安装 beautifulsoup4，某些代理源可能无法正确解析")


class ProxyPool:
    """高级代理池管理器"""
    
    def __init__(self, 
                 max_proxies: int = 30,
                 validation_interval: int = 60,
                 refresh_interval: int = 300,
                 proxy_return_interval: float = 5.0,
                 timeout: int = 10,
                 debug: bool = True,
                 test_urls: List[Tuple[str, str]] = None,
                 sources: List[Tuple[str, callable]] = None):
        """
        初始化高级代理池
        
        Args:
            max_proxies: 最大代理数量
            validation_interval: 验证间隔（秒）
            refresh_interval: 刷新代理间隔（秒）
            proxy_return_interval: 相同代理返回间隔（秒）
            timeout: 代理验证超时时间
            debug: 是否开启调试模式
            test_urls: 测试URL列表，格式为 [(url, protocol), ...]
            sources: 代理源列表，格式为 [(name, function), ...]
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
        self.test_urls = test_urls or [
            ("http://www.baidu.com", "http"),
            ("http://httpbin.org/ip", "http"),
        ]
        
        # 代理源
        self._sources = sources or [
            ("快代理", self._get_from_kuaidaili),
            ("89代理", self._get_from_89ip),
            ("代理API", self._get_from_proxy_api),
        ]
        
        # 统计信息
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "proxies_refreshed": 0,
            "proxies_validated": 0,
            "proxies_reported_invalid": 0,
            "proxies_reported_valid": 0,
        }
        
        # 汇报历史（用于追踪代理使用情况）
        self._report_history: Dict[str, deque] = {}  # proxy_str -> deque of (timestamp, is_valid)
        self._max_report_history = 10  # 最多保存10条汇报记录
        
        # 回调函数列表
        self._on_proxy_invalid: List[callable] = []
        self._on_proxy_valid: List[callable] = []
        self._on_proxy_added: List[callable] = []
        self._on_proxy_removed: List[callable] = []
    
    def _debug_print(self, msg: str) -> None:
        """调试打印"""
        if self.debug:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] [代理池] {msg}")
    
    # ==================== 回调机制 ====================
    
    def add_callback(self, event: str, callback: callable) -> None:
        """
        添加事件回调函数
        
        Args:
            event: 事件类型，可选值:
                - 'proxy_invalid': 代理被标记为无效时
                - 'proxy_valid': 代理被标记为有效时
                - 'proxy_added': 新代理添加时
                - 'proxy_removed': 代理被移除时
            callback: 回调函数，接收参数 (proxy_str, proxy_info)
        """
        callback_lists = {
            'proxy_invalid': self._on_proxy_invalid,
            'proxy_valid': self._on_proxy_valid,
            'proxy_added': self._on_proxy_added,
            'proxy_removed': self._on_proxy_removed,
        }
        
        if event in callback_lists:
            callback_lists[event].append(callback)
        else:
            raise ValueError(f"未知的事件类型: {event}，可选值: {list(callback_lists.keys())}")
    
    def _trigger_callbacks(self, callbacks: List[callable], proxy_str: str, proxy_info: Dict) -> None:
        """触发回调函数"""
        for callback in callbacks:
            try:
                callback(proxy_str, proxy_info)
            except Exception as e:
                self._debug_print(f"回调函数执行错误: {e}")
    
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
            
            for source_name, source_func in self._sources:
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
                        # 触发回调
                        self._trigger_callbacks(self._on_proxy_added, proxy["proxy_str"], proxy)
                
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
                removed_proxies = []
                
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
                        else:
                            removed_proxies.append(proxy)
                
                # 触发移除回调
                for proxy in removed_proxies:
                    self._trigger_callbacks(self._on_proxy_removed, proxy["proxy_str"], proxy)
                
                removed_count = len(removed_proxies)
                self._proxies = new_proxies
                self._stats["proxies_validated"] += len(proxy_list)
                
                if removed_count > 0:
                    self._debug_print(f"移除了 {removed_count} 个不可用代理")
                self._debug_print(f"验证完成！剩余可用代理: {len(self._proxies)} 个")
    
    # ==================== 代理汇报机制 ====================
    
    def report_proxy_status(self, proxy: Dict, is_valid: bool, reason: str = None) -> bool:
        """
        汇报代理使用状态
        
        此方法允许调用者在使用代理后汇报其有效性。
        如果代理被标记为无效，将立即从代理池中删除。
        
        Args:
            proxy: 代理字典（从 get_proxy() 获取的代理配置）
            is_valid: 代理是否有效
            reason: 无效的原因（可选）
        
        Returns:
            bool: 如果代理被成功处理返回True，否则返回False
        
        Example:
            >>> proxy = proxy_pool.get_proxy()
            >>> try:
            ...     response = requests.get(url, proxies=proxy, timeout=10)
            ...     proxy_pool.report_proxy_status(proxy, is_valid=True)
            ... except Exception as e:
            ...     proxy_pool.report_proxy_status(proxy, is_valid=False, reason=str(e))
        """
        # 从代理字典中提取代理字符串
        proxy_str = None
        if isinstance(proxy, dict):
            # 尝试从 http 或 https 键中提取
            for key in ['http', 'https']:
                if key in proxy:
                    # 格式: http://127.0.0.1:8080 -> 127.0.0.1:8080
                    url = proxy[key]
                    match = re.search(r'://([^/]+)', url)
                    if match:
                        proxy_str = match.group(1)
                        break
        
        if not proxy_str:
            self._debug_print(f"无法识别代理格式: {proxy}")
            return False
        
        return self.report_proxy_status_by_str(proxy_str, is_valid, reason)
    
    def report_proxy_status_by_str(self, proxy_str: str, is_valid: bool, reason: str = None) -> bool:
        """
        通过代理字符串汇报代理使用状态
        
        Args:
            proxy_str: 代理字符串，格式为 "ip:port"
            is_valid: 代理是否有效
            reason: 无效的原因（可选）
        
        Returns:
            bool: 如果代理被成功处理返回True，否则返回False
        """
        with self._lock:
            # 记录汇报历史
            if proxy_str not in self._report_history:
                self._report_history[proxy_str] = deque(maxlen=self._max_report_history)
            
            self._report_history[proxy_str].append((time.time(), is_valid))
            
            # 查找代理信息
            proxy_info = None
            proxy_index = -1
            
            for i, p in enumerate(self._proxies):
                if p["proxy_str"] == proxy_str:
                    proxy_info = p
                    proxy_index = i
                    break
            
            if not proxy_info:
                self._debug_print(f"代理 {proxy_str} 不在代理池中，忽略汇报")
                return False
            
            # 更新统计
            if is_valid:
                self._stats["proxies_reported_valid"] += 1
                proxy_info["success_count"] = proxy_info.get("success_count", 0) + 1
                self._debug_print(f"代理 {proxy_str} 汇报有效")
                self._trigger_callbacks(self._on_proxy_valid, proxy_str, proxy_info)
                return True
            else:
                self._stats["proxies_reported_invalid"] += 1
                proxy_info["fail_count"] = proxy_info.get("fail_count", 0) + 1
                
                reason_msg = f"，原因: {reason}" if reason else ""
                self._debug_print(f"代理 {proxy_str} 汇报无效{reason_msg}，将从代理池中移除")
                
                # 立即从代理池中移除
                if proxy_index >= 0:
                    removed_proxy = self._proxies.pop(proxy_index)
                    # 清除使用记录
                    if proxy_str in self._last_used:
                        del self._last_used[proxy_str]
                    # 如果是上一次返回的代理，清除记录
                    if self._last_returned == proxy_str:
                        self._last_returned = None
                    
                    # 触发回调
                    self._trigger_callbacks(self._on_proxy_invalid, proxy_str, removed_proxy)
                    self._trigger_callbacks(self._on_proxy_removed, proxy_str, removed_proxy)
                    
                    self._debug_print(f"代理 {proxy_str} 已从代理池中移除")
                    return True
            
            return False
    
    def get_proxy_report_history(self, proxy_str: str = None) -> Dict:
        """
        获取代理汇报历史
        
        Args:
            proxy_str: 代理字符串，如果为None则返回所有代理的汇报历史
        
        Returns:
            Dict: 汇报历史信息
        """
        with self._lock:
            if proxy_str:
                history = self._report_history.get(proxy_str, deque())
                return {
                    "proxy_str": proxy_str,
                    "report_count": len(history),
                    "valid_count": sum(1 for _, is_valid in history if is_valid),
                    "invalid_count": sum(1 for _, is_valid in history if not is_valid),
                    "history": list(history)
                }
            else:
                result = {}
                for p_str, history in self._report_history.items():
                    result[p_str] = {
                        "report_count": len(history),
                        "valid_count": sum(1 for _, is_valid in history if is_valid),
                        "invalid_count": sum(1 for _, is_valid in history if not is_valid),
                    }
                return result
    
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
        
        for source_name, source_func in self._sources:
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
            代理字典格式: {"http": "http://ip:port", "https": "http://ip:port"}
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
    
    def get_proxy_with_info(self) -> Optional[Dict]:
        """
        获取可用代理及其详细信息
        
        Returns:
            包含详细信息的代理字典，如果没有可用代理则返回None
            格式: {
                "proxy_str": "ip:port",
                "proxy": {"http": "...", "https": "..."},
                "response_time": 1.5,
                "success_count": 5,
                "fail_count": 0,
                ...
            }
        """
        # 先获取代理配置
        proxy_config = self.get_proxy()
        if not proxy_config:
            return None
        
        # 找到对应的详细信息
        with self._lock:
            # 从代理配置中提取proxy_str
            proxy_str = None
            for key in ['http', 'https']:
                if key in proxy_config:
                    url = proxy_config[key]
                    match = re.search(r'://([^/]+)', url)
                    if match:
                        proxy_str = match.group(1)
                        break
            
            if proxy_str:
                for proxy in self._proxies:
                    if proxy["proxy_str"] == proxy_str:
                        return proxy
        
        return None
    
    def get_stats(self) -> Dict:
        """获取代理池统计信息"""
        with self._lock:
            return {
                **self._stats,
                "current_proxies": len(self._proxies),
                "last_returned": self._last_returned,
            }
    
    def get_proxy_list(self) -> List[Dict]:
        """获取当前所有代理的列表（复制）"""
        with self._lock:
            return [p.copy() for p in self._proxies]
    
    def has_proxies(self) -> bool:
        """检查是否有可用代理"""
        with self._lock:
            return len(self._proxies) > 0
    
    def add_proxy(self, proxy_str: str, validate: bool = True) -> bool:
        """
        手动添加代理到代理池
        
        Args:
            proxy_str: 代理字符串，格式为 "ip:port"
            validate: 是否验证代理有效性
        
        Returns:
            bool: 添加成功返回True
        """
        if not self._is_valid_ip_port(*proxy_str.split(':')) if ':' in proxy_str else False:
            self._debug_print(f"无效的代理格式: {proxy_str}")
            return False
        
        with self._lock:
            # 检查是否已存在
            for p in self._proxies:
                if p["proxy_str"] == proxy_str:
                    self._debug_print(f"代理 {proxy_str} 已存在")
                    return False
        
        # 验证代理
        if validate:
            result = self._validate_single_proxy(proxy_str)
            if not result:
                self._debug_print(f"代理 {proxy_str} 验证失败")
                return False
            
            with self._lock:
                self._proxies.append(result)
                self._last_used[proxy_str] = 0
                self._trigger_callbacks(self._on_proxy_added, proxy_str, result)
                self._debug_print(f"代理 {proxy_str} 已添加到代理池")
                return True
        else:
            # 不验证直接添加
            proxy_config = {
                "http": f"http://{proxy_str}",
                "https": f"http://{proxy_str}"
            }
            proxy_info = {
                "proxy_str": proxy_str,
                "proxy": proxy_config,
                "response_time": 999.0,  # 默认设置为高响应时间
                "last_validated": time.time(),
                "success_count": 0,
                "fail_count": 0,
            }
            
            with self._lock:
                self._proxies.append(proxy_info)
                self._last_used[proxy_str] = 0
                self._trigger_callbacks(self._on_proxy_added, proxy_str, proxy_info)
                self._debug_print(f"代理 {proxy_str} 已添加到代理池（未验证）")
                return True
    
    def remove_proxy(self, proxy_str: str) -> bool:
        """
        手动从代理池中移除代理
        
        Args:
            proxy_str: 代理字符串
        
        Returns:
            bool: 移除成功返回True
        """
        with self._lock:
            for i, p in enumerate(self._proxies):
                if p["proxy_str"] == proxy_str:
                    removed = self._proxies.pop(i)
                    if proxy_str in self._last_used:
                        del self._last_used[proxy_str]
                    if self._last_returned == proxy_str:
                        self._last_returned = None
                    
                    self._trigger_callbacks(self._on_proxy_removed, proxy_str, removed)
                    self._debug_print(f"代理 {proxy_str} 已从代理池中移除")
                    return True
            
            self._debug_print(f"代理 {proxy_str} 不在代理池中")
            return False
    
    def clear_all(self) -> int:
        """
        清空所有代理
        
        Returns:
            int: 被移除的代理数量
        """
        with self._lock:
            count = len(self._proxies)
            
            # 触发回调
            for proxy in self._proxies:
                self._trigger_callbacks(self._on_proxy_removed, proxy["proxy_str"], proxy)
            
            self._proxies.clear()
            self._last_used.clear()
            self._last_returned = None
            
            self._debug_print(f"已清空所有 {count} 个代理")
            return count
    
    def force_refresh(self) -> int:
        """
        强制立即刷新代理（不从源获取，仅重新验证现有代理）
        
        Returns:
            int: 当前可用代理数量
        """
        self._debug_print("开始强制刷新代理...")
        
        with self._lock:
            if not self._proxies:
                self._debug_print("没有代理需要刷新")
                return 0
            
            proxy_list = [p["proxy_str"] for p in self._proxies]
        
        # 验证所有代理
        validation_results = {}
        for proxy_str in proxy_list:
            result = self._validate_single_proxy(proxy_str)
            validation_results[proxy_str] = result is not None
        
        with self._lock:
            new_proxies = []
            removed_count = 0
            
            for proxy in self._proxies:
                proxy_str = proxy["proxy_str"]
                is_valid = validation_results.get(proxy_str, False)
                
                if is_valid:
                    proxy["last_validated"] = time.time()
                    new_proxies.append(proxy)
                else:
                    removed_count += 1
                    self._trigger_callbacks(self._on_proxy_removed, proxy_str, proxy)
            
            self._proxies = new_proxies
            
            if removed_count > 0:
                self._debug_print(f"强制刷新完成，移除了 {removed_count} 个无效代理")
            self._debug_print(f"当前可用代理: {len(self._proxies)} 个")
            
            return len(self._proxies)
