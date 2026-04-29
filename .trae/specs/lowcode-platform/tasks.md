# 低代码平台（仿Dify）- 实施计划 (Decomposed and Prioritized Task List)

## [x] Task 1: 项目基础设施搭建与初始化
- **Priority**: P0
- **Depends On**: None
- **Description**: 
  - 使用 `uv init` 初始化 Python 项目
  - 配置 `pyproject.toml`，添加 Flask、RestrictedPython 等核心依赖
  - 创建标准的 `.gitignore` 文件
  - 规划项目目录结构
- **Acceptance Criteria Addressed**: [AC-1]
- **Test Requirements**:
  - `programmatic` TR-1.1: 项目根目录存在 `pyproject.toml` 和 `.gitignore`
  - `programmatic` TR-1.2: 运行 `uv sync` 成功安装依赖
  - `programmatic` TR-1.3: 目录结构符合预期 (backend/, frontend/, data/ 等)
- **Notes**: 端口 2222 和地址 0.0.0.0 在此阶段配置到启动脚本

---

## [x] Task 2: 定义工作流数据模型与存储
- **Priority**: P0
- **Depends On**: [Task 1]
- **Description**: 
  - 定义工作流 (Workflow) 的 JSON 结构：包含 nodes, edges, metadata
  - 定义节点 (Node) 结构：id, type, position, config (输入/输出配置, 代码内容)
  - 定义连接 (Edge) 结构：id, source, target, sourceHandle, targetHandle
  - 实现基于文件系统的存储模块：保存/加载/列出/删除工作流 JSON 文件到 `data/workflows/`
- **Acceptance Criteria Addressed**: [FR-4]
- **Test Requirements**:
  - `programmatic` TR-2.1: 保存工作流 API 调用后，`data/workflows/` 下生成对应 JSON 文件
  - `programmatic` TR-2.2: 加载工作流 API 正确解析 JSON 并返回结构
  - `programmatic` TR-2.3: 数据结构能正确表示 Start -> Code -> End 的简单流程
- **Notes**: 先定义好数据结构是前后端协作的基础

---

## [x] Task 3: 实现节点系统基础架构
- **Priority**: P0
- **Depends On**: [Task 2]
- **Description**: 
  - 创建节点基类 `BaseNode`，定义统一接口 (input_schema, output_schema, execute)
  - 实现 `StartNode`：工作流入口，返回配置的初始参数
  - 实现 `EndNode`：工作流出口，接收输入并作为最终结果
  - 实现 `PythonCodeNode`：核心节点，包含代码模板，执行用户定义的代码
  - (可选V1简化) 实现简单的 `ConditionNode` 或 `MergeNode` 框架
  - 创建节点注册表 `NodeRegistry`，用于根据类型查找节点类
- **Acceptance Criteria Addressed**: [FR-2]
- **Test Requirements**:
  - `programmatic` TR-3.1: `StartNode` execute 返回配置的字典数据
  - `programmatic` TR-3.2: `PythonCodeNode` 能够接收 inputs，执行代码片段，并返回 outputs
  - `programmatic` TR-3.3: 节点注册表能正确根据 "start", "end", "python_code" 字符串找到对应类
- **Notes**: PythonCodeNode 的 execute 方法目前可以先不做沙箱，仅实现逻辑，后续由 Task 5 增强

---

## [x] Task 4: 实现工作流执行引擎 (逻辑层)
- **Priority**: P0
- **Depends On**: [Task 3]
- **Description**: 
  - 实现 `WorkflowRunner` 类
  - **拓扑排序**: 根据 edges 构建 DAG，使用 Kahn 算法或 DFS 确定执行顺序
  - **数据流管理**: 创建上下文对象 (context)，存储每个节点的输出
  - **参数解析**: 实现占位符解析逻辑 (如 `${node_id.output_key}`)，将节点连接映射为变量引用
  - **执行循环**: 按顺序调用每个节点的 execute 方法，传递解析后的输入
- **Acceptance Criteria Addressed**: [FR-3, AC-4]
- **Test Requirements**:
  - `programmatic` TR-4.1: 给定包含 Start -> Code -> End 的 DAG，Runner 能按此顺序执行
  - `programmatic` TR-4.2: Start 节点输出 `{name: "World"}`，Code 节点引用 `${start.name}`，执行后变量被正确替换为 "World"
  - `programmatic` TR-4.3: 最终 End 节点接收的数据正确反映上游处理结果
- **Notes**: 这是核心逻辑，需要详细测试

---

## [x] Task 5: 集成 RestrictedPython 实现安全沙箱
- **Priority**: P0
- **Depends On**: [Task 4]
- **Description**: 
  - 修改 `PythonCodeNode` 或创建 `CodeSandbox` 模块
  - 使用 RestrictedPython 的 `safe_builtins`, `compile_restricted_exec` 等工具
  - 定义允许的全局变量和内置函数 (如只允许 print, list, dict, str 操作等)
  - 捕获执行异常 (SyntaxError, RuntimeError, SecurityError)
  - 重定向 stdout/stderr 以捕获 print 输出
- **Acceptance Criteria Addressed**: [FR-3, NFR-1, AC-6]
- **Test Requirements**:
  - `programmatic` TR-5.1: 执行 `1 + 1` 返回 `2`，执行 `print("hello")` 捕获到输出
  - `programmatic` TR-5.2: 尝试执行 `import os` 或 `__import__('os')` 抛出安全异常或被阻止
  - `programmatic` TR-5.3: 执行 `1 / 0` 抛出 `ZeroDivisionError` 并被上层正确捕获
- **Notes**: 安全性是重点，但 V1 允许相对宽松的策略 (允许大多数纯 Python 操作，禁止文件/网络)

---

## [x] Task 6: 实现后端 Flask API 服务
- **Priority**: P0
- **Depends On**: [Task 2, Task 5]
- **Description**: 
  - 创建 `app.py` 或 `backend/server.py`
  - 配置 CORS (如果前端是独立的) 或配置静态文件路径
  - **API Endpoints**:
    - `GET /api/workflows`: 列出所有工作流
    - `POST /api/workflows`: 创建新工作流
    - `GET /api/workflows/<id>`: 获取单个工作流详情
    - `PUT /api/workflows/<id>`: 更新工作流
    - `DELETE /api/workflows/<id>`: 删除工作流
    - `POST /api/workflows/<id>/run`: 执行工作流，返回执行结果 (status, output, logs, error)
    - `POST /api/workflows/<id>/export`: 导出为 Python 代码字符串
  - 绑定端口 `0.0.0.0:2222`
- **Acceptance Criteria Addressed**: [AC-1, FR-1, FR-4]
- **Test Requirements**:
  - `programmatic` TR-6.1: 启动服务后，`curl http://localhost:2222/api/workflows` 返回 200
  - `programmatic` TR-6.2: POST 创建工作流返回 201 和 ID
  - `programmatic` TR-6.3: POST `/run` 接口在 2 秒内返回执行结果
- **Notes**: 导出功能逻辑简单起见可以先在后端生成一个 "模拟" 的代码字符串，或者直接调用代码生成器

---

## [/] Task 7: 实现前端基础框架与画布
- **Priority**: P0
- **Depends On**: None (可与后端并行，但最终依赖 API)
- **Description**: 
  - 创建 `frontend/` 目录，包含 `index.html`, `css/`, `js/`
  - **布局**: 三栏布局 (左侧节点面板, 中间画布, 右侧属性面板)
  - **Canvas/Grid**: 使用 CSS Grid 背景，实现可拖拽的无限画布 (Container scroll + transform)
  - **缩放与平移**: 实现鼠标滚轮缩放 (scale) 和拖拽平移 (pan)
- **Acceptance Criteria Addressed**: [FR-1]
- **Test Requirements**:
  - `human-judgement` TR-7.1: 页面加载后显示三栏布局，中间区域为白色/浅色画布背景
  - `human-judgement` TR-7.2: 按住鼠标中键/空格拖动可以平移画布，滚轮可以缩放
- **Notes**: 使用原生 JS 实现，不依赖框架，重点在交互流畅

---

## [x] Task 8: 实现前端节点渲染与拖拽
- **Priority**: P0
- **Depends On**: [Task 7]
- **Description**: 
  - 定义节点组件的 HTML 结构 (Div 元素，包含标题栏、内容区、输入输出点)
  - **节点库**: 左侧面板显示 "Start", "End", "Python Code", "Condition" 等图标/按钮
  - **Drag & Drop**: 从左侧拖拽到画布上，创建新节点实例
  - **节点选中与移动**: 点击选中节点 (高亮)，拖拽节点在画布上移动 (更新 position)
  - **删除**: Delete 键删除选中节点
- **Acceptance Criteria Addressed**: [FR-1, AC-2]
- **Test Requirements**:
  - `human-judgement` TR-8.1: 从左侧拖拽 "Start" 到画布，画布上生成一个矩形节点元素
  - `human-judgement` TR-8.2: 选中节点后按 Delete，节点消失
  - `human-judgement` TR-8.3: 节点可以被自由拖动，坐标随鼠标变化

---

## [x] Task 9: 实现前端连线系统 (Edge Rendering)
- **Priority**: P0
- **Depends On**: [Task 8]
- **Description**: 
  - **连接点 (Handle)**: 节点上下左右或特定位置渲染小圆点，作为输入输出端点
  - **连线交互**: 点击一个节点的输出点，拖拽到另一个节点的输入点，创建连线
  - **SVG 绘制**: 使用 SVG 绘制贝塞尔曲线 (Bezier curve) 或折线连接
  - **连线管理**: 维护 edges 数据结构，点击连线可以选中并删除
- **Acceptance Criteria Addressed**: [FR-1, AC-3]
- **Test Requirements**:
  - `human-judgement` TR-9.1: 节点上有明显的连接点 (如蓝色圆点)
  - `human-judgement` TR-9.2: 从 NodeA 输出点拖拽到 NodeB 输入点，两点之间出现曲线
  - `human-judgement` TR-9.3: 移动 NodeA，连线会随之更新位置

---

## [x] Task 10: 实现前端属性面板与数据绑定
- **Priority**: P0
- **Depends On**: [Task 8]
- **Description**: 
  - **状态管理**: 前端维护 `currentWorkflow` 对象 (nodes, edges)
  - **属性面板渲染**: 选中节点后，右侧面板根据节点类型显示不同的表单
  - **表单交互**:
    - Start 节点：显示 Key-Value 输入框，定义初始参数
    - Python Code 节点：显示多行文本编辑器 (textarea)，输入代码
    - 通用：显示节点 ID (只读)
  - **双向绑定**: 修改表单内容，实时更新 `currentWorkflow` 中对应 node 的 config
- **Acceptance Criteria Addressed**: [FR-1, AC-2]
- **Test Requirements**:
  - `human-judgement` TR-10.1: 选中 Python Code 节点，右侧显示文本框
  - `human-judgement` TR-10.2: 在文本框中输入 `print(1)`，再次点击其他节点再点回来，内容保持不变 (状态已保存到内存)

---

## [ ] Task 11: 前后端联调 - 工作流 CRUD
- **Priority**: P1
- **Depends On**: [Task 6, Task 10]
- **Description**: 
  - 实现前端 API 调用封装 (fetch/axios 原生封装)
  - **保存 (Save)**: 点击保存按钮，POST/PUT 当前 `currentWorkflow` 到后端
  - **加载 (Load)**: 实现工作流列表页面，点击加载某个工作流，用后端数据覆盖前端 `currentWorkflow` 并重新渲染画布
  - **新建 (New)**: 清空画布
- **Acceptance Criteria Addressed**: [AC-2]
- **Test Requirements**:
  - `programmatic` TR-11.1: 点击保存，浏览器 Network 面板看到 POST 请求成功
  - `programmatic` TR-11.2: 刷新页面后重新加载该工作流，节点和连线位置与保存前一致

---

## [x] Task 12: 前后端联调 - 执行与结果展示
- **Priority**: P1
- **Depends On**: [Task 11]
- **Description**: 
  - **运行 (Run)**: 点击运行按钮，调用 `/run` 接口
  - **Loading 状态**: 显示运行中动画
  - **结果面板**: 底部或右侧增加输出面板
    - Logs Tab: 显示 stdout/stderr
    - Result Tab: 显示 End 节点的输出数据 (JSON 格式化)
    - Error Tab: 显示异常堆栈
- **Acceptance Criteria Addressed**: [AC-4, AC-6]
- **Test Requirements**:
  - `programmatic` TR-12.1: 运行包含 `print("Hello")` 的工作流，Logs 面板显示 "Hello"
  - `programmatic` TR-12.2: 运行包含 `return {"data": 123}` 的工作流，Result 面板显示 JSON 对象
  - `programmatic` TR-12.3: 运行 `1/0`，Error 面板显示红色的错误信息

---

## [x] Task 13: 代码导出功能实现
- **Priority**: P1
- **Depends On**: [Task 4]
- **Description**: 
  - 增强后端 `WorkflowExporter` 模块
  - 根据执行顺序生成 Python 代码
  - 生成的代码应包含注释、变量定义、顺序执行的函数调用
  - 提供入口函数 `main()`
  - 前端点击 Export 按钮，下载 `.py` 文件
- **Acceptance Criteria Addressed**: [AC-5]
- **Test Requirements**:
  - `human-judgement` TR-13.1: 导出的代码文件结构清晰，变量名有意义
  - `programmatic` TR-13.2: 直接用 Python 解释器运行导出的 `.py` 文件，能得到与平台执行相同的输出结果

---

## [x] Task 14: 整体测试与 Bug 修复
- **Priority**: P1
- **Depends On**: [Task 12, Task 13]
- **Description**: 
  - 进行端到端 (E2E) 测试：创建完整工作流 -> 保存 -> 运行 -> 导出
  - 修复发现的交互 Bug (如连线不随节点移动、缩放后坐标计算错误等)
  - 优化错误提示
- **Acceptance Criteria Addressed**: [All ACs]
- **Test Requirements**:
  - `human-judgement` TR-14.1: 模拟 Dify 官网 Demo 的简单逻辑，能在本平台复现
  - `programmatic` TR-14.2: 所有核心 API 接口测试通过 (使用 curl 或简单脚本)
