#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代理池 API 服务器
提供 RESTful API 接口，可独立运行

API 端点:
- GET  /api/health          - 健康检查
- GET  /api/proxy           - 获取一个可用代理
- GET  /api/proxy/info      - 获取一个可用代理及其详细信息
- POST /api/proxy/report    - 汇报代理使用状态
- GET  /api/proxies         - 获取所有代理列表
- GET  /api/stats           - 获取代理池统计信息
- POST /api/proxy           - 手动添加代理
- DELETE /api/proxy/<proxy_str> - 手动删除代理
- POST /api/start           - 启动代理池
- POST /api/stop            - 停止代理池
- POST /api/refresh         - 强制刷新代理
- POST /api/clear           - 清空所有代理
- GET  /api/report/history  - 获取代理汇报历史
"""

import os
import json
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify, g
from datetime import datetime

# 确保可以导入同一目录下的 pool.py
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pool import ProxyPool

# Flask 应用
app = Flask(__name__)

# 全局代理池实例
proxy_pool_instance = None

# 默认配置
DEFAULT_CONFIG = {
    "HOST": "0.0.0.0",
    "PORT": 5010,
    "DEBUG": False,
    "LOG_LEVEL": "INFO",
    "LOG_FILE": "proxy_pool.log",
    
    # 代理池配置
    "MAX_PROXIES": 30,
    "VALIDATION_INTERVAL": 60,
    "REFRESH_INTERVAL": 300,
    "PROXY_RETURN_INTERVAL": 5.0,
    "TIMEOUT": 10,
    "POOL_DEBUG": True,
    
    # API 认证（可选）
    "API_KEY": None,
}


def setup_logging():
    """设置日志"""
    log_level = os.getenv("LOG_LEVEL", DEFAULT_CONFIG["LOG_LEVEL"])
    log_file = os.getenv("LOG_FILE", DEFAULT_CONFIG["LOG_FILE"])
    
    # 创建日志目录（如果需要）
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 设置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # 格式
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 文件输出（滚动日志）
    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"警告: 无法创建日志文件: {e}")
    
    # 禁止 werkzeug 的默认日志，让它通过我们的日志器
    logging.getLogger("werkzeug").setLevel(logging.WARNING)


def get_config():
    """获取配置（从环境变量或默认值）"""
    config = DEFAULT_CONFIG.copy()
    
    # 从环境变量覆盖配置
    env_mappings = {
        "HOST": "PROXY_HOST",
        "PORT": "PROXY_PORT",
        "DEBUG": "PROXY_DEBUG",
        "LOG_LEVEL": "LOG_LEVEL",
        "LOG_FILE": "LOG_FILE",
        "MAX_PROXIES": "MAX_PROXIES",
        "VALIDATION_INTERVAL": "VALIDATION_INTERVAL",
        "REFRESH_INTERVAL": "REFRESH_INTERVAL",
        "PROXY_RETURN_INTERVAL": "PROXY_RETURN_INTERVAL",
        "TIMEOUT": "PROXY_TIMEOUT",
        "POOL_DEBUG": "POOL_DEBUG",
        "API_KEY": "API_KEY",
    }
    
    for config_key, env_key in env_mappings.items():
        env_value = os.getenv(env_key)
        if env_value is not None:
            # 类型转换
            if config_key in ["PORT", "MAX_PROXIES", "VALIDATION_INTERVAL", "REFRESH_INTERVAL", "TIMEOUT"]:
                config[config_key] = int(env_value)
            elif config_key in ["DEBUG", "POOL_DEBUG"]:
                config[config_key] = env_value.lower() in ["true", "1", "yes"]
            elif config_key == "PROXY_RETURN_INTERVAL":
                config[config_key] = float(env_value)
            else:
                config[config_key] = env_value
    
    return config


def get_proxy_pool():
    """获取代理池实例（单例模式）"""
    global proxy_pool_instance
    
    if proxy_pool_instance is None:
        config = get_config()
        
        proxy_pool_instance = ProxyPool(
            max_proxies=config["MAX_PROXIES"],
            validation_interval=config["VALIDATION_INTERVAL"],
            refresh_interval=config["REFRESH_INTERVAL"],
            proxy_return_interval=config["PROXY_RETURN_INTERVAL"],
            timeout=config["TIMEOUT"],
            debug=config["POOL_DEBUG"]
        )
        
        # 添加默认回调函数
        def on_proxy_invalid(proxy_str, proxy_info):
            app.logger.info(f"[事件] 代理无效: {proxy_str}")
        
        def on_proxy_removed(proxy_str, proxy_info):
            app.logger.info(f"[事件] 代理已移除: {proxy_str}")
        
        def on_proxy_added(proxy_str, proxy_info):
            app.logger.info(f"[事件] 新代理添加: {proxy_str}")
        
        proxy_pool_instance.add_callback('proxy_invalid', on_proxy_invalid)
        proxy_pool_instance.add_callback('proxy_removed', on_proxy_removed)
        proxy_pool_instance.add_callback('proxy_added', on_proxy_added)
        
        # 自动启动
        proxy_pool_instance.start()
        app.logger.info("代理池已启动")
    
    return proxy_pool_instance


def check_api_key():
    """检查 API 密钥（如果配置了）"""
    config = get_config()
    api_key = config.get("API_KEY")
    
    if api_key is None:
        return True  # 没有配置 API 密钥，允许访问
    
    # 从请求头或查询参数获取 API 密钥
    request_key = request.headers.get("X-API-Key") or request.args.get("api_key")
    
    if request_key != api_key:
        return False
    
    return True


def api_response(success: bool, data=None, message: str = None, code: int = 200):
    """统一的 API 响应格式"""
    response = {
        "success": success,
        "code": code,
        "timestamp": datetime.now().isoformat()
    }
    
    if data is not None:
        response["data"] = data
    
    if message is not None:
        response["message"] = message
    
    return jsonify(response), code


# ===== API 端点 =====

@app.before_request
def before_request():
    """请求前处理"""
    g.start_time = datetime.now()
    
    # 检查 API 密钥
    if not check_api_key():
        return api_response(
            success=False,
            message="Invalid or missing API key",
            code=401
        )


@app.after_request
def after_request(response):
    """请求后处理"""
    if hasattr(g, 'start_time'):
        elapsed = (datetime.now() - g.start_time).total_seconds()
        app.logger.debug(f"请求耗时: {elapsed:.3f}s - {request.method} {request.path}")
    return response


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    pool = get_proxy_pool()
    stats = pool.get_stats()
    
    return api_response(
        success=True,
        data={
            "status": "healthy",
            "current_proxies": stats["current_proxies"],
            "has_proxies": pool.has_proxies()
        },
        message="Proxy pool API is running"
    )


@app.route('/api/proxy', methods=['GET'])
def get_proxy():
    """获取一个可用代理"""
    pool = get_proxy_pool()
    proxy = pool.get_proxy()
    
    if proxy:
        return api_response(
            success=True,
            data={
                "proxy": proxy,
                "proxy_str": proxy.get('http', '').replace('http://', '') if proxy.get('http') else None
            }
        )
    else:
        return api_response(
            success=False,
            message="No available proxy",
            code=503
        )


@app.route('/api/proxy/info', methods=['GET'])
def get_proxy_with_info():
    """获取一个可用代理及其详细信息"""
    pool = get_proxy_pool()
    proxy_info = pool.get_proxy_with_info()
    
    if proxy_info:
        # 转换为可 JSON 序列化的格式
        data = {
            "proxy_str": proxy_info.get("proxy_str"),
            "proxy": proxy_info.get("proxy"),
            "response_time": proxy_info.get("response_time"),
            "last_validated": proxy_info.get("last_validated"),
            "success_count": proxy_info.get("success_count", 0),
            "fail_count": proxy_info.get("fail_count", 0),
        }
        return api_response(success=True, data=data)
    else:
        return api_response(
            success=False,
            message="No available proxy",
            code=503
        )


@app.route('/api/proxy/report', methods=['POST'])
def report_proxy_status():
    """
    汇报代理使用状态
    
    请求体格式:
    {
        "proxy": {"http": "http://ip:port", "https": "http://ip:port"},
        // 或
        "proxy_str": "ip:port",
        "is_valid": true/false,
        "reason": "可选的原因描述"
    }
    """
    pool = get_proxy_pool()
    
    try:
        data = request.get_json(force=True)
    except:
        return api_response(
            success=False,
            message="Invalid JSON body",
            code=400
        )
    
    proxy = data.get("proxy")
    proxy_str = data.get("proxy_str")
    is_valid = data.get("is_valid")
    reason = data.get("reason")
    
    if is_valid is None:
        return api_response(
            success=False,
            message="Missing 'is_valid' parameter",
            code=400
        )
    
    result = False
    
    if proxy:
        result = pool.report_proxy_status(proxy, is_valid, reason)
    elif proxy_str:
        result = pool.report_proxy_status_by_str(proxy_str, is_valid, reason)
    else:
        return api_response(
            success=False,
            message="Missing 'proxy' or 'proxy_str' parameter",
            code=400
        )
    
    if result:
        return api_response(
            success=True,
            message=f"Proxy status reported: {'valid' if is_valid else 'invalid'}"
        )
    else:
        return api_response(
            success=False,
            message="Proxy not found in pool or invalid format",
            code=404
        )


@app.route('/api/proxies', methods=['GET'])
def get_all_proxies():
    """获取所有代理列表"""
    pool = get_proxy_pool()
    proxies = pool.get_proxy_list()
    
    # 转换为可 JSON 序列化的格式
    result = []
    for p in proxies:
        result.append({
            "proxy_str": p.get("proxy_str"),
            "proxy": p.get("proxy"),
            "response_time": p.get("response_time"),
            "last_validated": p.get("last_validated"),
            "success_count": p.get("success_count", 0),
            "fail_count": p.get("fail_count", 0),
        })
    
    return api_response(
        success=True,
        data={
            "count": len(result),
            "proxies": result
        }
    )


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取代理池统计信息"""
    pool = get_proxy_pool()
    stats = pool.get_stats()
    
    return api_response(success=True, data=stats)


@app.route('/api/proxy', methods=['POST'])
def add_proxy():
    """
    手动添加代理
    
    请求体格式:
    {
        "proxy_str": "ip:port",
        "validate": true  // 是否验证有效性
    }
    """
    pool = get_proxy_pool()
    
    try:
        data = request.get_json(force=True)
    except:
        return api_response(
            success=False,
            message="Invalid JSON body",
            code=400
        )
    
    proxy_str = data.get("proxy_str")
    validate = data.get("validate", True)
    
    if not proxy_str:
        return api_response(
            success=False,
            message="Missing 'proxy_str' parameter",
            code=400
        )
    
    result = pool.add_proxy(proxy_str, validate=validate)
    
    if result:
        return api_response(
            success=True,
            message=f"Proxy {proxy_str} added successfully"
        )
    else:
        return api_response(
            success=False,
            message=f"Failed to add proxy {proxy_str} (invalid or already exists)",
            code=400
        )


@app.route('/api/proxy/<proxy_str>', methods=['DELETE'])
def remove_proxy(proxy_str):
    """手动删除代理"""
    pool = get_proxy_pool()
    
    result = pool.remove_proxy(proxy_str)
    
    if result:
        return api_response(
            success=True,
            message=f"Proxy {proxy_str} removed successfully"
        )
    else:
        return api_response(
            success=False,
            message=f"Proxy {proxy_str} not found",
            code=404
        )


@app.route('/api/start', methods=['POST'])
def start_pool():
    """启动代理池"""
    pool = get_proxy_pool()
    pool.start()
    
    return api_response(
        success=True,
        message="Proxy pool started"
    )


@app.route('/api/stop', methods=['POST'])
def stop_pool():
    """停止代理池"""
    pool = get_proxy_pool()
    pool.stop()
    
    return api_response(
        success=True,
        message="Proxy pool stopped"
    )


@app.route('/api/refresh', methods=['POST'])
def refresh_proxies():
    """强制刷新代理"""
    pool = get_proxy_pool()
    count = pool.force_refresh()
    
    return api_response(
        success=True,
        data={"available_proxies": count},
        message=f"Proxy pool refreshed, {count} proxies available"
    )


@app.route('/api/clear', methods=['POST'])
def clear_proxies():
    """清空所有代理"""
    pool = get_proxy_pool()
    count = pool.clear_all()
    
    return api_response(
        success=True,
        data={"removed_count": count},
        message=f"All {count} proxies cleared"
    )


@app.route('/api/report/history', methods=['GET'])
def get_report_history():
    """
    获取代理汇报历史
    
    查询参数:
    - proxy_str: 可选，指定代理的汇报历史
    """
    pool = get_proxy_pool()
    proxy_str = request.args.get("proxy_str")
    
    history = pool.get_proxy_report_history(proxy_str)
    
    return api_response(success=True, data=history)


@app.route('/', methods=['GET'])
def index():
    """API 首页"""
    endpoints = {
        "GET /api/health": "健康检查",
        "GET /api/proxy": "获取一个可用代理",
        "GET /api/proxy/info": "获取一个可用代理及其详细信息",
        "POST /api/proxy/report": "汇报代理使用状态",
        "GET /api/proxies": "获取所有代理列表",
        "GET /api/stats": "获取代理池统计信息",
        "POST /api/proxy": "手动添加代理",
        "DELETE /api/proxy/<proxy_str>": "手动删除代理",
        "POST /api/start": "启动代理池",
        "POST /api/stop": "停止代理池",
        "POST /api/refresh": "强制刷新代理",
        "POST /api/clear": "清空所有代理",
        "GET /api/report/history": "获取代理汇报历史",
    }
    
    return api_response(
        success=True,
        data={
            "name": "Proxy Pool API",
            "version": "1.0.0",
            "endpoints": endpoints
        },
        message="Proxy Pool API Server"
    )


# ===== 错误处理 =====

@app.errorhandler(404)
def not_found(error):
    return api_response(
        success=False,
        message="Endpoint not found",
        code=404
    )


@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Internal server error: {error}")
    return api_response(
        success=False,
        message="Internal server error",
        code=500
    )


@app.errorhandler(Exception)
def handle_exception(error):
    app.logger.error(f"Unhandled exception: {error}")
    return api_response(
        success=False,
        message=str(error),
        code=500
    )


def create_app():
    """创建应用（用于生产环境）"""
    setup_logging()
    return app


if __name__ == '__main__':
    # 设置日志
    setup_logging()
    
    # 获取配置
    config = get_config()
    
    app.logger.info("=" * 60)
    app.logger.info("代理池 API 服务器启动")
    app.logger.info("=" * 60)
    app.logger.info(f"监听地址: {config['HOST']}:{config['PORT']}")
    app.logger.info(f"调试模式: {config['DEBUG']}")
    app.logger.info(f"API Key 认证: {'启用' if config['API_KEY'] else '禁用'}")
    app.logger.info("=" * 60)
    
    # 初始化代理池
    get_proxy_pool()
    
    # 启动 Flask 应用
    app.run(
        host=config["HOST"],
        port=config["PORT"],
        debug=config["DEBUG"],
        threaded=True
    )
