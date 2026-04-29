# 低代码平台 (Low-Code Platform)

一个模仿 Dify 的可视化工作流编辑器，支持拖拽节点、编写代码、执行工作流。

## 功能特性

- **可视化工作流编辑器**: 拖拽式节点操作，直观的工作流设计
- **多种节点类型**:
  - `Start`: 工作流入口，设置初始参数
  - `End`: 工作流出口，收集最终结果
  - `Python Code`: 编写 Python 代码，支持变量输入输出
  - `Condition`: 条件判断节点，支持分支逻辑
- **安全沙箱**: 使用 RestrictedPython 限制危险操作
- **代码导出**: 将工作流导出为独立的 Python 脚本
- **数据流管理**: 节点间参数自动传递，支持 `${node_id.key}` 语法
- **DAG 执行**: 基于拓扑排序的有向无环图执行

## 技术栈

- **后端**: Python + Flask + RestrictedPython
- **包管理**: UV
- **前端**: 原生 HTML/CSS/JavaScript (无框架)
- **服务端口**: 2222

## 快速开始

### 环境要求

- Python 3.8+
- UV (Python 包管理器)

### 安装依赖

```bash
# 安装依赖
uv sync
```

### 启动服务

```bash
# 方式一：直接运行
uv run python -c "from backend.server import main; main()"

# 方式二：使用启动脚本
./start.sh

# 方式三：后台运行
nohup ./start.sh > server.log 2>&1 &
```

### 停止服务

```bash
# 使用停止脚本
./stop.sh

# 或手动查找进程并终止
pkill -f "backend.server"
```

### 访问应用

启动后在浏览器访问: http://localhost:2222

## 使用指南

### 创建工作流

1. 点击顶部 **新建** 按钮创建新工作流
2. 从左侧 **节点库** 拖拽节点到画布
3. 从节点的 **输出点** (右侧蓝点) 拖拽到另一个节点的 **输入点** (左侧蓝点) 创建连接

### 配置节点

点击选中节点后，右侧 **属性面板** 显示配置项：

**Start 节点**:
- 设置初始参数 (Key-Value 形式)
- 点击 `+ 添加参数` 新增参数

**Python Code 节点**:
- 在代码编辑器中编写 Python 代码
- 上游节点的输出自动作为变量可用
- 使用 `result` 变量或 `return` 语句输出结果

**Condition 节点**:
- 条件表达式: 支持 `value > 10`、`value == 'success'` 等
- 真值输出: 条件为真时的输出 (JSON 格式)
- 假值输出: 条件为假时的输出 (JSON 格式)

### 保存与运行

1. 点击顶部 **保存** 按钮保存工作流
2. 点击 **运行** 按钮执行工作流
3. 底部 **输出面板** 显示:
   - `日志`: 执行过程日志
   - `结果`: End 节点的输出数据
   - `错误`: 异常信息

### 导出代码

点击 **导出** 按钮，将工作流导出为独立的 Python 脚本。

## 项目结构

```
.
├── backend/                    # 后端代码
│   ├── __init__.py
│   ├── server.py              # Flask API 服务入口
│   ├── models.py              # 数据模型定义
│   ├── storage.py             # 文件系统存储
│   ├── nodes.py               # 节点系统实现
│   ├── runner.py              # 工作流执行引擎
│   ├── sandbox.py             # RestrictedPython 安全沙箱
│   ├── exporter.py            # 代码导出模块
│   └── test_task*.py          # 单元测试
├── frontend/                   # 前端代码
│   ├── index.html             # 主页面
│   ├── css/style.css          # 样式文件
│   └── js/
│       ├── app.js             # 主应用入口
│       ├── utils.js           # 工具函数
│       ├── api.js             # API 调用封装
│       ├── canvas.js          # 画布控制
│       ├── nodes.js           # 节点管理
│       ├── edges.js           # 连线管理
│       └── properties.js      # 属性面板
├── data/                       # 数据存储目录
│   └── workflows/             # 工作流 JSON 文件
├── start.sh                    # 启动脚本
├── stop.sh                     # 停止脚本
├── pyproject.toml             # UV 项目配置
├── uv.lock                    # 依赖锁定文件
├── .gitignore                 # Git 忽略规则
└── README.md                  # 本文档
```

## 安全沙箱

代码执行使用 RestrictedPython 进行安全限制：

**允许的操作**:
- 基本数学运算、字符串操作
- `print()` 语句
- 大部分内置类型 (list, dict, str, int, float 等)
- 部分安全模块 (math, random, json)

**禁止的操作**:
- `import` 语句
- 文件读写 (`open()`, `os.*`)
- 网络操作 (`socket`, `urllib`)
- 系统调用 (`subprocess`, `exec`)
- 危险的内置函数 (`eval`, `exec`, `__import__`)

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/workflows` | 列出所有工作流 |
| POST | `/api/workflows` | 创建新工作流 |
| GET | `/api/workflows/<id>` | 获取工作流详情 |
| PUT | `/api/workflows/<id>` | 更新工作流 |
| DELETE | `/api/workflows/<id>` | 删除工作流 |
| POST | `/api/workflows/<id>/run` | 执行工作流 |
| POST | `/api/workflows/<id>/export` | 导出为 Python 代码 |

## 示例工作流

创建一个简单的工作流：

1. **Start** 节点:
   - Key: `name`, Value: `"World"`
   - Key: `multiplier`, Value: `3`

2. **Python Code** 节点:
```python
greeting = f"Hello {name}"
tripled = 10 * multiplier
result = {"greeting": greeting, "tripled": tripled}
```

3. **End** 节点

4. 连接: `Start → Python Code → End`

5. 保存 → 运行 → 查看结果

## 开发说明

### 运行测试

```bash
# 运行所有测试
uv run python backend/test_task2.py
uv run python backend/test_task3.py
# ... 其他测试文件
```

### 添加新节点类型

1. 在 `backend/nodes.py` 继承 `BaseNode` 创建新节点类
2. 实现 `execute` 方法
3. 使用 `NodeRegistry.register()` 注册
4. 在 `frontend/index.html` 的节点库添加对应项
5. 在 `frontend/js/nodes.js` 的 `getDefaultConfig` 添加默认配置

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request。
