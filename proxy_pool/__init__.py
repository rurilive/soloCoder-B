#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代理池模块 - 独立的代理管理系统

三种使用方式:

1. 直接导入使用 (本地模式):
   from proxy_pool import ProxyPool
   pool = ProxyPool(...)
   pool.start()
   proxy = pool.get_proxy()

2. API 服务模式 (独立运行服务器):
   # 启动服务器
   python -m proxy_pool.server
   
   # 客户端连接
   from proxy_pool import ProxyPoolClient
   client = ProxyPoolClient(host="localhost", port=5010)
   proxy = client.get_proxy()

3. 统一适配器模式 (自动选择):
   from proxy_pool import create_proxy_adapter
   # auto 模式优先尝试 API，失败则使用本地
   adapter = create_proxy_adapter(mode="auto")
   adapter.init()
   proxy = adapter.get_proxy()

特性:
- 后台线程定期验证代理可用性
- 线程安全的代理获取机制
- 不允许连续返回相同代理
- 相同代理返回间隔5秒以上
- 自动从多个源获取新代理
- 支持代理汇报机制，无效代理自动删除
- RESTful API 接口
- 可选的 API Key 认证
"""

from proxy_pool.pool import ProxyPool
from proxy_pool.client import ProxyPoolClient, create_client
from proxy_pool.adapter import ProxyAdapter, ProxyMode, create_proxy_adapter

__all__ = [
    'ProxyPool', 
    'ProxyPoolClient', 
    'create_client',
    'ProxyAdapter',
    'ProxyMode',
    'create_proxy_adapter'
]
__version__ = '1.0.0'
