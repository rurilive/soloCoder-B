# 低代码平台（仿Dify）- 验证清单

## 基础设施验证 (Task 1)
- [ ] 项目根目录存在 `pyproject.toml` 文件
- [ ] 项目根目录存在 `.gitignore` 文件，规则包含 Python 标准忽略项
- [ ] 运行 `uv sync` 成功安装依赖 (无报错)
- [ ] 目录结构包含 `backend/`, `frontend/`, `data/` (或类似逻辑划分)
- [ ] 启动命令后，服务监听在 `http://0.0.0.0:2222` (可通过 `netstat` 或 `curl` 验证)

## 后端核心逻辑验证

### 数据模型与存储 (Task 2)
- [ ] 调用保存 API 后，`data/workflows/` 目录下生成了 JSON 文件
- [ ] 调用加载 API 后，返回的 JSON 结构与保存时一致 (包含 nodes, edges)
- [ ] JSON 结构中节点包含 `id`, `type`, `position`, `config` 关键字段

### 节点系统 (Task 3)
- [ ] `StartNode.execute({"params": {"x": 1}})` 返回 `{"x": 1}`
- [ ] `EndNode` 能够接收输入并透传
- [ ] `PythonCodeNode` 能够执行简单的赋值语句并返回结果

### 执行引擎 (Task 4)
- [ ] 拓扑排序功能：给定一个 DAG，能正确生成拓扑序列
- [ ] 参数引用解析：`${node_a.output}` 能被正确替换为实际值
- [ ] 数据流：节点 A 的输出能被节点 B 的输入接收

### 沙箱安全 (Task 5)
- [ ] 正常代码 `2 + 2` 能执行并返回 4
- [ ] 危险操作 `import os` 被阻止或抛出异常
- [ ] `print("test")` 的输出能被捕获到日志中
- [ ] `1 / 0` 抛出 `ZeroDivisionError` 并被上层捕获

### API 服务 (Task 6)
- [ ] `GET /api/workflows` 返回 200 OK 和数组
- [ ] `POST /api/workflows` 返回 201 Created 和包含 `id` 的对象
- [ ] `POST /api/workflows/<id>/run` 返回包含 `status`, `result`, `logs` 的 JSON 对象
- [ ] `POST /api/workflows/<id>/export` 返回 200 和字符串内容

## 前端交互验证

### 基础 UI (Task 7)
- [ ] 浏览器访问 `http://localhost:2222/` 能看到页面 (三栏布局)
- [ ] 中间区域为画布背景
- [ ] 鼠标滚轮能缩放画布 (视觉上变大变小)
- [ ] 按住空格拖动能平移画布

### 节点操作 (Task 8)
- [ ] 左侧面板显示 "Start", "End", "Python Code" 等图标
- [ ] 拖拽 "Start" 到画布，画布上出现一个矩形元素
- [ ] 选中节点后按 Delete 键，节点消失
- [ ] 拖拽已存在的节点，节点位置随鼠标移动

### 连线操作 (Task 9)
- [ ] 节点上有明显的连接点 (Handle)
- [ ] 从节点 A 输出点拖拽到节点 B 输入点，两者之间出现连线 (曲线)
- [ ] 移动节点 A，连线会跟随更新端点位置
- [ ] 选中连线后可以删除

### 属性面板 (Task 10)
- [ ] 选中 "Python Code" 节点，右侧显示多行文本框 (textarea)
- [ ] 在文本框中输入代码，失焦后内容保留在内存中 (再次选中内容不变)
- [ ] 选中 "Start" 节点，显示配置初始参数的界面

## 端到端集成验证

### 保存与加载 (Task 11)
- [ ] 点击 "Save" 按钮，页面提示保存成功 (或 Network 显示 200/201)
- [ ] 刷新页面后，通过列表重新加载该工作流，节点和连线完全复现
- [ ] 节点位置坐标与保存前一致

### 执行与结果 (Task 12)
- [ ] **场景 1 (Hello World)**:
  - Start 定义 `name: "World"`
  - Python Code 写 `return f"Hello {name}"`
  - Start -> Code -> End 连接
  - 点击 Run，Result 面板显示 `Hello World`
- [ ] **场景 2 (异常处理)**:
  - Python Code 写 `1 / 0`
  - 点击 Run，Error 面板显示红色错误信息，包含 `ZeroDivisionError`
- [ ] **场景 3 (日志输出)**:
  - Python Code 写 `print("Log Test")`
  - 点击 Run，Logs 面板显示 `Log Test`

### 代码导出 (Task 13)
- [ ] 点击 "Export Python" 按钮，浏览器下载 `.py` 文件
- [ ] 打开下载的文件，代码结构清晰，包含执行逻辑
- [ ] 在终端直接运行 `python exported_file.py`，程序正常结束并输出预期结果

## 最终验收
- [ ] 所有上述检查点均已通过
- [ ] 页面交互流畅，无明显卡顿
- [ ] 后端服务稳定运行，无崩溃
