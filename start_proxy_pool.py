#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代理池 API 服务器启动脚本

使用方式:
    # 默认启动（0.0.0.0:5010）
    python start_proxy_pool.py
    
    # 指定端口
    python start_proxy_pool.py --port 8080
    
    # 指定主机
    python start_proxy_pool.py --host 127.0.0.1
    
    # 启用调试模式
    python start_proxy_pool.py --debug
    
    # 使用环境变量配置
    PROXY_HOST=127.0.0.1 PROXY_PORT=8080 PROXY_DEBUG=true python start_proxy_pool.py
    
    # 启用 API Key 认证
    API_KEY=my_secret_key python start_proxy_pool.py
"""

import os
import sys
import argparse


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='代理池 API 服务器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  %(prog)s                      # 默认启动 0.0.0.0:5010
  %(prog)s --port 8080          # 指定端口
  %(prog)s --host 127.0.0.1     # 只监听本地
  %(prog)s --debug               # 调试模式
  %(prog)s --api-key secret123   # 启用 API Key 认证

环境变量:
  PROXY_HOST      - 监听地址 (默认: 0.0.0.0)
  PROXY_PORT      - 监听端口 (默认: 5010)
  PROXY_DEBUG     - 调试模式 (true/false, 默认: false)
  LOG_LEVEL       - 日志级别 (DEBUG/INFO/WARNING/ERROR, 默认: INFO)
  LOG_FILE        - 日志文件路径 (默认: proxy_pool.log)
  API_KEY         - API 认证密钥 (可选，不设置则不启用认证)
  
  MAX_PROXIES              - 最大代理数量 (默认: 30)
  VALIDATION_INTERVAL      - 验证间隔秒 (默认: 60)
  REFRESH_INTERVAL         - 刷新间隔秒 (默认: 300)
  PROXY_RETURN_INTERVAL    - 代理返回间隔秒 (默认: 5.0)
  PROXY_TIMEOUT            - 验证超时秒 (默认: 10)
  POOL_DEBUG               - 代理池调试模式 (默认: true)
        '''
    )
    
    parser.add_argument(
        '--host', 
        default=os.getenv('PROXY_HOST', '0.0.0.0'),
        help='监听地址 (默认: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=int(os.getenv('PROXY_PORT', '5010')),
        help='监听端口 (默认: 5010)'
    )
    
    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        default=os.getenv('PROXY_DEBUG', 'false').lower() in ('true', '1', 'yes'),
        help='启用 Flask 调试模式 (默认: false)'
    )
    
    parser.add_argument(
        '--api-key',
        default=os.getenv('API_KEY'),
        help='API 认证密钥 (不设置则不启用认证)'
    )
    
    parser.add_argument(
        '--log-level',
        default=os.getenv('LOG_LEVEL', 'INFO'),
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='日志级别 (默认: INFO)'
    )
    
    parser.add_argument(
        '--log-file',
        default=os.getenv('LOG_FILE', 'proxy_pool.log'),
        help='日志文件路径 (默认: proxy_pool.log)'
    )
    
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()
    
    # 设置环境变量（供 server.py 使用）
    os.environ['PROXY_HOST'] = args.host
    os.environ['PROXY_PORT'] = str(args.port)
    os.environ['PROXY_DEBUG'] = 'true' if args.debug else 'false'
    os.environ['LOG_LEVEL'] = args.log_level
    os.environ['LOG_FILE'] = args.log_file
    
    if args.api_key:
        os.environ['API_KEY'] = args.api_key
    
    # 打印启动信息
    print("=" * 70)
    print("代理池 API 服务器")
    print("=" * 70)
    print(f"  监听地址: {args.host}:{args.port}")
    print(f"  调试模式: {'启用' if args.debug else '禁用'}")
    print(f"  API 认证: {'启用' if args.api_key else '禁用'}")
    print(f"  日志级别: {args.log_level}")
    print(f"  日志文件: {args.log_file}")
    print("=" * 70)
    print()
    print("API 端点:")
    print("  GET    /api/health          - 健康检查")
    print("  GET    /api/proxy           - 获取代理")
    print("  GET    /api/proxy/info      - 获取代理及详细信息")
    print("  POST   /api/proxy/report    - 汇报代理状态")
    print("  GET    /api/proxies         - 获取所有代理列表")
    print("  GET    /api/stats           - 获取统计信息")
    print("  POST   /api/proxy           - 添加代理")
    print("  DELETE /api/proxy/<proxy>   - 删除代理")
    print("  POST   /api/start           - 启动代理池")
    print("  POST   /api/stop            - 停止代理池")
    print("  POST   /api/refresh         - 强制刷新代理")
    print("  POST   /api/clear           - 清空所有代理")
    print("  GET    /api/report/history  - 获取汇报历史")
    print()
    print("使用示例:")
    print("  # 获取代理")
    print(f"  curl http://{args.host}:{args.port}/api/proxy")
    print()
    print("  # 汇报代理无效")
    print(f"  curl -X POST http://{args.host}:{args.port}/api/proxy/report \\")
    print(f"       -H \"Content-Type: application/json\" \\")
    print(f"       -d '{{\"proxy_str\": \"1.2.3.4:8080\", \"is_valid\": false, \"reason\": \"timeout\"}}'")
    print()
    
    if args.api_key:
        print("注意: 已启用 API Key 认证，请求需包含 X-API-Key 头或 api_key 参数")
        print("示例:")
        print(f"  curl -H \"X-API-Key: {args.api_key}\" http://{args.host}:{args.port}/api/proxy")
        print(f"  curl http://{args.host}:{args.port}/api/proxy?api_key={args.api_key}")
        print()
    
    print("=" * 70)
    print("按 Ctrl+C 停止服务器")
    print("=" * 70)
    print()
    
    # 导入并启动服务器
    try:
        from proxy_pool.server import app, setup_logging, get_config, get_proxy_pool
        
        # 设置日志
        setup_logging()
        
        # 获取配置
        config = get_config()
        
        # 立即初始化代理池（启动前自动搜集代理）
        print("\n正在初始化代理池，开始自动搜集代理...")
        print("这可能需要一些时间，请耐心等待...\n")
        
        # 调用 get_proxy_pool() 会立即：
        # 1. 创建 ProxyPool 实例
        # 2. 调用 start() 方法
        # 3. start() 会同步从各代理源获取代理并验证
        # 4. 启动后台线程定期刷新和验证
        get_proxy_pool()
        
        print("\n代理池初始化完成！")
        print("后台线程已启动，将定期自动刷新和验证代理")
        print("=" * 70)
        
        # 启动 Flask 应用
        app.run(
            host=config["HOST"],
            port=config["PORT"],
            debug=config["DEBUG"],
            threaded=True
        )
        
    except KeyboardInterrupt:
        print("\n\n服务器已停止")
        sys.exit(0)
    except ImportError as e:
        print(f"错误: 缺少依赖模块: {e}")
        print("请先安装依赖: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
