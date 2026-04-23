#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代理池模块 - 独立的代理管理系统
- 后台线程定期验证代理可用性
- 线程安全的代理获取机制
- 不允许连续返回相同代理
- 相同代理返回间隔5秒以上
- 自动从多个源获取新代理
- 支持代理汇报机制，无效代理自动删除
"""

from proxy_pool.pool import ProxyPool

__all__ = ['ProxyPool']
__version__ = '1.0.0'
