#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代理池 API 客户端
用于通过 HTTP API 与代理池服务器通信

使用示例:
    from proxy_pool.client import ProxyPoolClient
    
    # 创建客户端
    client = ProxyPoolClient(
        host="localhost",
        port=5010,
        api_key=None  # 可选的 API 密钥
    )
    
    # 获取代理
    proxy = client.get_proxy()
    if proxy:
        print(f"获取到代理: {proxy}")
        
        # 使用代理请求
        try:
            response = requests.get(url, proxies=proxy, timeout=10)
            # 汇报有效
            client.report_proxy(proxy, is_valid=True)
        except Exception as e:
            # 汇报无效（代理将被自动删除）
            client.report_proxy(proxy, is_valid=False, reason=str(e))
"""

import requests
from typing import Dict, Optional, Any, List
from datetime import datetime


class ProxyPoolClient:
    """代理池 API 客户端"""
    
    def __init__(self, 
                 host: str = "localhost",
                 port: int = 5010,
                 scheme: str = "http",
                 api_key: str = None,
                 timeout: int = 10,
                 max_retries: int = 3):
        """
        初始化代理池客户端
        
        Args:
            host: 代理池服务器地址
            port: 代理池服务器端口
            scheme: URL 协议 (http/https)
            api_key: 可选的 API 密钥
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
        """
        self.base_url = f"{scheme}://{host}:{port}"
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        
        # 默认请求头
        self._headers = {
            "Content-Type": "application/json",
            "User-Agent": "ProxyPool-Client/1.0"
        }
        
        # 如果有 API 密钥，添加到请求头
        if api_key:
            self._headers["X-API-Key"] = api_key
    
    def _build_url(self, endpoint: str) -> str:
        """构建完整 URL"""
        return f"{self.base_url}{endpoint}"
    
    def _get_headers(self) -> Dict:
        """获取请求头"""
        return self._headers.copy()
    
    def _request(self, 
                 method: str, 
                 endpoint: str, 
                 json: Dict = None,
                 params: Dict = None) -> Optional[Dict]:
        """
        发送请求到代理池服务器
        
        Args:
            method: HTTP 方法
            endpoint: API 端点
            json: JSON 请求体
            params: 查询参数
        
        Returns:
            响应数据或 None
        """
        url = self._build_url(endpoint)
        headers = self._get_headers()
        
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json,
                    params=params,
                    timeout=self.timeout
                )
                
                # 检查响应
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data.get("success", False):
                            return data.get("data")
                        else:
                            # API 返回失败
                            message = data.get("message", "Unknown error")
                            print(f"[代理池客户端] API 错误: {message}")
                            return None
                    except:
                        print(f"[代理池客户端] 无法解析响应 JSON")
                        return None
                else:
                    print(f"[代理池客户端] HTTP 错误: {response.status_code}")
                    if attempt < self.max_retries - 1:
                        print(f"[代理池客户端] 重试 {attempt + 1}/{self.max_retries}...")
                        
            except requests.exceptions.ConnectionError as e:
                last_exception = e
                print(f"[代理池客户端] 连接错误: {e}")
                if attempt < self.max_retries - 1:
                    print(f"[代理池客户端] 重试 {attempt + 1}/{self.max_retries}...")
                    
            except requests.exceptions.Timeout as e:
                last_exception = e
                print(f"[代理池客户端] 请求超时: {e}")
                if attempt < self.max_retries - 1:
                    print(f"[代理池客户端] 重试 {attempt + 1}/{self.max_retries}...")
                    
            except Exception as e:
                last_exception = e
                print(f"[代理池客户端] 请求错误: {e}")
                if attempt < self.max_retries - 1:
                    print(f"[代理池客户端] 重试 {attempt + 1}/{self.max_retries}...")
        
        print(f"[代理池客户端] 请求失败，已尝试 {self.max_retries} 次")
        return None
    
    # ===== API 方法 =====
    
    def health_check(self) -> Optional[Dict]:
        """
        健康检查
        
        Returns:
            健康状态信息或 None
        """
        return self._request("GET", "/api/health")
    
    def is_healthy(self) -> bool:
        """
        检查代理池是否健康
        
        Returns:
            True 如果健康
        """
        result = self.health_check()
        return result is not None and result.get("status") == "healthy"
    
    def has_proxies(self) -> bool:
        """
        检查是否有可用代理
        
        Returns:
            True 如果有可用代理
        """
        result = self.health_check()
        return result is not None and result.get("has_proxies", False)
    
    def get_proxy(self) -> Optional[Dict]:
        """
        获取一个可用代理
        
        Returns:
            代理字典，格式: {"http": "http://ip:port", "https": "http://ip:port"}
            如果没有可用代理返回 None
        """
        result = self._request("GET", "/api/proxy")
        if result and "proxy" in result:
            return result["proxy"]
        return None
    
    def get_proxy_with_info(self) -> Optional[Dict]:
        """
        获取一个可用代理及其详细信息
        
        Returns:
            包含详细信息的代理字典或 None
            格式: {
                "proxy_str": "ip:port",
                "proxy": {"http": "...", "https": "..."},
                "response_time": 1.5,
                "success_count": 5,
                "fail_count": 0
            }
        """
        return self._request("GET", "/api/proxy/info")
    
    def report_proxy(self, 
                     proxy: Dict, 
                     is_valid: bool, 
                     reason: str = None) -> bool:
        """
        汇报代理使用状态
        
        如果代理被标记为无效，它将被自动从代理池中删除。
        
        Args:
            proxy: 代理字典（从 get_proxy() 获取）
            is_valid: 代理是否有效
            reason: 无效的原因（可选）
        
        Returns:
            True 如果汇报成功
        """
        payload = {
            "proxy": proxy,
            "is_valid": is_valid
        }
        
        if reason:
            payload["reason"] = reason
        
        # 使用 POST 请求，检查是否成功
        url = self._build_url("/api/proxy/report")
        headers = self._get_headers()
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("success", False)
        except Exception as e:
            print(f"[代理池客户端] 汇报代理状态失败: {e}")
        
        return False
    
    def report_proxy_by_str(self,
                            proxy_str: str,
                            is_valid: bool,
                            reason: str = None) -> bool:
        """
        通过代理字符串汇报状态
        
        Args:
            proxy_str: 代理字符串，格式为 "ip:port"
            is_valid: 是否有效
            reason: 原因
        
        Returns:
            True 如果成功
        """
        payload = {
            "proxy_str": proxy_str,
            "is_valid": is_valid
        }
        
        if reason:
            payload["reason"] = reason
        
        try:
            url = self._build_url("/api/proxy/report")
            headers = self._get_headers()
            
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("success", False)
        except Exception as e:
            print(f"[代理池客户端] 汇报代理状态失败: {e}")
        
        return False
    
    def get_all_proxies(self) -> List[Dict]:
        """
        获取所有代理列表
        
        Returns:
            代理列表
        """
        result = self._request("GET", "/api/proxies")
        if result and "proxies" in result:
            return result["proxies"]
        return []
    
    def get_proxy_count(self) -> int:
        """
        获取当前代理数量
        
        Returns:
            代理数量
        """
        result = self._request("GET", "/api/proxies")
        if result:
            return result.get("count", 0)
        return 0
    
    def get_stats(self) -> Optional[Dict]:
        """
        获取代理池统计信息
        
        Returns:
            统计信息字典
        """
        return self._request("GET", "/api/stats")
    
    def add_proxy(self, proxy_str: str, validate: bool = True) -> bool:
        """
        手动添加代理
        
        Args:
            proxy_str: 代理字符串，格式为 "ip:port"
            validate: 是否验证有效性
        
        Returns:
            True 如果添加成功
        """
        payload = {
            "proxy_str": proxy_str,
            "validate": validate
        }
        
        try:
            url = self._build_url("/api/proxy")
            headers = self._get_headers()
            
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("success", False)
        except Exception as e:
            print(f"[代理池客户端] 添加代理失败: {e}")
        
        return False
    
    def remove_proxy(self, proxy_str: str) -> bool:
        """
        手动删除代理
        
        Args:
            proxy_str: 代理字符串
        
        Returns:
            True 如果删除成功
        """
        try:
            url = self._build_url(f"/api/proxy/{proxy_str}")
            headers = self._get_headers()
            
            response = requests.delete(
                url,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("success", False)
        except Exception as e:
            print(f"[代理池客户端] 删除代理失败: {e}")
        
        return False
    
    def start_pool(self) -> bool:
        """启动代理池"""
        try:
            url = self._build_url("/api/start")
            headers = self._get_headers()
            
            response = requests.post(
                url,
                headers=headers,
                timeout=self.timeout
            )
            
            return response.status_code == 200
        except:
            return False
    
    def stop_pool(self) -> bool:
        """停止代理池"""
        try:
            url = self._build_url("/api/stop")
            headers = self._get_headers()
            
            response = requests.post(
                url,
                headers=headers,
                timeout=self.timeout
            )
            
            return response.status_code == 200
        except:
            return False
    
    def refresh_proxies(self) -> int:
        """
        强制刷新代理
        
        Returns:
            可用代理数量
        """
        result = self._request("POST", "/api/refresh")
        if result:
            return result.get("available_proxies", 0)
        return 0
    
    def clear_all(self) -> int:
        """
        清空所有代理
        
        Returns:
            被删除的代理数量
        """
        result = self._request("POST", "/api/clear")
        if result:
            return result.get("removed_count", 0)
        return 0
    
    def get_report_history(self, proxy_str: str = None) -> Optional[Dict]:
        """
        获取代理汇报历史
        
        Args:
            proxy_str: 可选，指定代理的汇报历史
        
        Returns:
            汇报历史
        """
        params = {}
        if proxy_str:
            params["proxy_str"] = proxy_str
        
        return self._request("GET", "/api/report/history", params=params)
    
    # ===== 上下文管理器支持 =====
    
    def __enter__(self):
        """进入上下文"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        # 不需要特殊清理
        pass


# 便捷函数
def create_client(host: str = "localhost",
                  port: int = 5010,
                  api_key: str = None) -> ProxyPoolClient:
    """
    创建代理池客户端的便捷函数
    
    Args:
        host: 服务器地址
        port: 服务器端口
        api_key: API 密钥
    
    Returns:
        ProxyPoolClient 实例
    """
    return ProxyPoolClient(host=host, port=port, api_key=api_key)
