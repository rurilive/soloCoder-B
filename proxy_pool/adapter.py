#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代理池适配器
提供统一的接口，支持本地模式和 API 客户端模式

使用方式:
    # 本地模式
    adapter = ProxyAdapter(mode="local")
    adapter.init()
    
    # API 客户端模式
    adapter = ProxyAdapter(mode="api", host="localhost", port=5010)
    adapter.init()
    
    # 使用统一接口
    proxy = adapter.get_proxy()
    if proxy:
        try:
            response = requests.get(url, proxies=proxy)
            adapter.report_proxy(proxy, is_valid=True)
        except:
            adapter.report_proxy(proxy, is_valid=False, reason="error")
"""

from typing import Dict, Optional, Any, List
from enum import Enum


class ProxyMode(Enum):
    """代理模式"""
    LOCAL = "local"      # 本地模式，直接使用 ProxyPool
    API = "api"          # API 客户端模式，连接到独立的 API 服务器
    AUTO = "auto"        # 自动检测，优先尝试 API 模式，失败则使用本地模式


class ProxyAdapter:
    """代理池适配器 - 统一接口"""
    
    def __init__(self,
                 mode: str = "auto",
                 host: str = "localhost",
                 port: int = 5010,
                 api_key: str = None,
                 # 本地模式配置
                 max_proxies: int = 20,
                 validation_interval: int = 60,
                 refresh_interval: int = 300,
                 proxy_return_interval: float = 5.0,
                 timeout: int = 10,
                 debug: bool = True):
        """
        初始化代理适配器
        
        Args:
            mode: 模式选择: "local", "api", "auto"
            host: API 服务器地址（API 模式）
            port: API 服务器端口（API 模式）
            api_key: API 密钥（API 模式，可选）
            max_proxies: 最大代理数量（本地模式）
            validation_interval: 验证间隔秒（本地模式）
            refresh_interval: 刷新间隔秒（本地模式）
            proxy_return_interval: 代理返回间隔秒（本地模式）
            timeout: 超时时间（本地模式）
            debug: 是否调试模式（本地模式）
        """
        self.mode = ProxyMode(mode)
        self._pool = None
        self._client = None
        self._initialized = False
        
        # 保存配置
        self._local_config = {
            "max_proxies": max_proxies,
            "validation_interval": validation_interval,
            "refresh_interval": refresh_interval,
            "proxy_return_interval": proxy_return_interval,
            "timeout": timeout,
            "debug": debug,
        }
        
        self._api_config = {
            "host": host,
            "port": port,
            "api_key": api_key,
        }
    
    def _init_local(self) -> bool:
        """初始化本地模式"""
        try:
            from proxy_pool import ProxyPool
            
            self._pool = ProxyPool(**self._local_config)
            
            # 添加回调函数
            def on_proxy_invalid(proxy_str, proxy_info):
                print(f"  [代理事件] 代理 {proxy_str} 被标记为无效，已从池中移除")
            
            def on_proxy_removed(proxy_str, proxy_info):
                print(f"  [代理事件] 代理 {proxy_str} 已从池中移除")
            
            def on_proxy_added(proxy_str, proxy_info):
                print(f"  [代理事件] 新代理 {proxy_str} 已添加到池中")
            
            self._pool.add_callback('proxy_invalid', on_proxy_invalid)
            self._pool.add_callback('proxy_removed', on_proxy_removed)
            self._pool.add_callback('proxy_added', on_proxy_added)
            
            # 启动代理池
            self._pool.start()
            
            self._initialized = True
            self.mode = ProxyMode.LOCAL
            print("[代理适配器] 本地模式初始化成功")
            return True
            
        except ImportError as e:
            print(f"[代理适配器] 本地模式初始化失败: {e}")
            return False
        except Exception as e:
            print(f"[代理适配器] 本地模式初始化错误: {e}")
            return False
    
    def _init_api(self) -> bool:
        """初始化 API 客户端模式"""
        try:
            from proxy_pool import ProxyPoolClient
            
            self._client = ProxyPoolClient(
                host=self._api_config["host"],
                port=self._api_config["port"],
                api_key=self._api_config["api_key"],
            )
            
            # 检查 API 服务器是否可用
            if not self._client.is_healthy():
                print(f"[代理适配器] API 服务器不可用: {self._api_config['host']}:{self._api_config['port']}")
                self._client = None
                return False
            
            self._initialized = True
            self.mode = ProxyMode.API
            print(f"[代理适配器] API 模式初始化成功，连接到: {self._api_config['host']}:{self._api_config['port']}")
            return True
            
        except ImportError as e:
            print(f"[代理适配器] API 模式初始化失败: {e}")
            return False
        except Exception as e:
            print(f"[代理适配器] API 模式初始化错误: {e}")
            self._client = None
            return False
    
    def init(self) -> bool:
        """
        初始化适配器
        
        Returns:
            True 如果初始化成功
        """
        print("\n" + "=" * 70)
        print("初始化代理池...")
        print("=" * 70)
        
        if self.mode == ProxyMode.LOCAL:
            success = self._init_local()
            
        elif self.mode == ProxyMode.API:
            success = self._init_api()
            
        else:  # AUTO 模式
            print("[代理适配器] 自动检测模式，优先尝试 API 模式...")
            success = self._init_api()
            if not success:
                print("[代理适配器] API 模式失败，切换到本地模式...")
                success = self._init_local()
        
        if success:
            # 等待代理池有可用代理
            print("\n等待代理池初始化...")
            for i in range(30):
                import time
                time.sleep(1)
                if self.has_proxies():
                    stats = self.get_stats()
                    print(f"代理池初始化完成！可用代理: {stats.get('current_proxies', 0)} 个")
                    break
                if (i + 1) % 5 == 0:
                    print(f"  等待中... ({i+1}/30秒)")
            else:
                print("\n警告: 代理池初始化超时，可能没有可用代理")
        else:
            print("\n警告: 代理池初始化失败，将使用直连模式")
        
        return success
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
    
    def get_mode(self) -> str:
        """获取当前模式"""
        return self.mode.value
    
    # ===== 统一接口 =====
    
    def get_proxy(self) -> Optional[Dict]:
        """
        获取一个可用代理
        
        Returns:
            代理字典或 None
        """
        if not self._initialized:
            return None
        
        if self.mode == ProxyMode.LOCAL and self._pool:
            return self._pool.get_proxy()
        elif self.mode == ProxyMode.API and self._client:
            return self._client.get_proxy()
        
        return None
    
    def report_proxy(self, proxy: Dict, is_valid: bool, reason: str = None) -> bool:
        """
        汇报代理使用状态
        
        Args:
            proxy: 代理字典
            is_valid: 是否有效
            reason: 原因
        
        Returns:
            True 如果汇报成功
        """
        if not self._initialized:
            return False
        
        if self.mode == ProxyMode.LOCAL and self._pool:
            return self._pool.report_proxy_status(proxy, is_valid, reason)
        elif self.mode == ProxyMode.API and self._client:
            return self._client.report_proxy(proxy, is_valid, reason)
        
        return False
    
    def has_proxies(self) -> bool:
        """检查是否有可用代理"""
        if not self._initialized:
            return False
        
        if self.mode == ProxyMode.LOCAL and self._pool:
            return self._pool.has_proxies()
        elif self.mode == ProxyMode.API and self._client:
            return self._client.has_proxies()
        
        return False
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        if not self._initialized:
            return {}
        
        if self.mode == ProxyMode.LOCAL and self._pool:
            return self._pool.get_stats()
        elif self.mode == ProxyMode.API and self._client:
            stats = self._client.get_stats()
            return stats if stats else {}
        
        return {}
    
    def get_all_proxies(self) -> List[Dict]:
        """获取所有代理列表"""
        if not self._initialized:
            return []
        
        if self.mode == ProxyMode.LOCAL and self._pool:
            return self._pool.get_proxy_list()
        elif self.mode == ProxyMode.API and self._client:
            return self._client.get_all_proxies()
        
        return []
    
    def add_proxy(self, proxy_str: str, validate: bool = True) -> bool:
        """添加代理"""
        if not self._initialized:
            return False
        
        if self.mode == ProxyMode.LOCAL and self._pool:
            return self._pool.add_proxy(proxy_str, validate)
        elif self.mode == ProxyMode.API and self._client:
            return self._client.add_proxy(proxy_str, validate)
        
        return False
    
    def remove_proxy(self, proxy_str: str) -> bool:
        """删除代理"""
        if not self._initialized:
            return False
        
        if self.mode == ProxyMode.LOCAL and self._pool:
            return self._pool.remove_proxy(proxy_str)
        elif self.mode == ProxyMode.API and self._client:
            return self._client.remove_proxy(proxy_str)
        
        return False
    
    def refresh(self) -> int:
        """强制刷新代理"""
        if not self._initialized:
            return 0
        
        if self.mode == ProxyMode.LOCAL and self._pool:
            return self._pool.force_refresh()
        elif self.mode == ProxyMode.API and self._client:
            return self._client.refresh_proxies()
        
        return 0
    
    def clear(self) -> int:
        """清空所有代理"""
        if not self._initialized:
            return 0
        
        if self.mode == ProxyMode.LOCAL and self._pool:
            return self._pool.clear_all()
        elif self.mode == ProxyMode.API and self._client:
            return self._client.clear_all()
        
        return 0
    
    def stop(self) -> None:
        """停止代理池"""
        if self.mode == ProxyMode.LOCAL and self._pool:
            self._pool.stop()
            print("[代理适配器] 本地代理池已停止")
        elif self.mode == ProxyMode.API and self._client:
            # API 模式不需要停止客户端
            print("[代理适配器] API 客户端已断开")
        
        self._initialized = False
        self._pool = None
        self._client = None


# 便捷函数
def create_proxy_adapter(mode: str = "auto", **kwargs) -> ProxyAdapter:
    """
    创建代理适配器的便捷函数
    
    Args:
        mode: 模式选择: "local", "api", "auto"
        **kwargs: 其他配置参数
    
    Returns:
        ProxyAdapter 实例
    """
    return ProxyAdapter(mode=mode, **kwargs)
