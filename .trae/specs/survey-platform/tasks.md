# 问卷调查平台 - The Implementation Plan (Decomposed and Prioritized Task List)

## 项目结构说明
```
survey_platform/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── extensions.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── role.py
│   │   ├── survey.py
│   │   ├── question.py
│   │   └── response.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── admin.py
│   │   ├── survey.py
│   │   └── stats.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── auth/
│   │   ├── admin/
│   │   ├── survey/
│   │   └── stats/
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── captcha.py
│   │   ├── export.py
│   │   └── security.py
│   └── forms/
│       ├── __init__.py
│       ├── auth.py
│       └── survey.py
├── migrations/
├── tests/
├── .venv/
├── pyproject.toml
├── uv.lock
├── run.py
└── README.md
```

---

## [x] Task 1: 项目初始化与基础配置
- **Priority**: P0
- **Depends On**: None
- **Description**: 
  - 使用 uv 初始化 Python 项目
  - 创建项目目录结构
  - 配置 Flask 应用基础框架
  - 配置 SQLite 数据库连接
  - 安装核心依赖（Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF, Flask-Migrate, bcrypt）
- **Acceptance Criteria Addressed**: [AC-10]
- **Test Requirements**:
  - `programmatic` TR-1.1: 项目可通过 `flask run` 或 `python run.py` 启动
  - `programmatic` TR-1.2: 数据库连接成功，可执行基本查询
  - `programmatic` TR-1.3: 所有依赖包可正确导入
- **Notes**: 确保使用 uv 作为包管理器，在 pyproject.toml 中正确配置

---

## [x] Task 2: 数据库模型设计与创建
- **Priority**: P0
- **Depends On**: [Task 1]
- **Description**: 
  - 设计用户表（User）：id, username, email, password_hash, is_active, created_at
  - 设计角色表（Role）：id, name, description, permissions
  - 设计用户组表（UserGroup）：id, name, description
  - 设计用户-角色关联表（UserRole）
  - 设计用户-用户组关联表（UserGroupMember）
  - 设计问卷表（Survey）：id, title, description, status, creator_id, created_at, start_time, end_time, access_password, max_responses
  - 设计题目表（Question）：id, survey_id, type, text, options, is_required, order, logic_jump
  - 设计答案表（Response）：id, survey_id, user_id, ip_address, user_agent, submitted_at, is_valid
  - 设计答案详情表（ResponseAnswer）：id, response_id, question_id, value
  - 配置 Flask-Migrate 进行数据库迁移
- **Acceptance Criteria Addressed**: [AC-1, AC-2, AC-10]
- **Test Requirements**:
  - `programmatic` TR-2.1: 所有数据表可成功创建
  - `programmatic` TR-2.2: 外键关联正确建立
  - `programmatic` TR-2.3: 索引在关键字段上正确创建
- **Notes**: Question 表的 options 使用 JSON 存储，支持灵活的题型配置

---

## [/] Task 3: 用户认证与授权系统
- **Priority**: P0
- **Depends On**: [Task 2]
- **Description**: 
  - 实现用户注册功能（表单验证、密码加密）
  - 实现用户登录/登出功能（Flask-Login）
  - 实现密码重置功能（可选，先实现基础登录）
  - 实现角色权限装饰器（@admin_required, @survey_creator_required）
  - 实现用户组权限检查
  - 创建默认角色：超级管理员、问卷管理员、普通用户
  - 创建默认超级管理员账号
- **Acceptance Criteria Addressed**: [AC-1, AC-2, AC-10]
- **Test Requirements**:
  - `programmatic` TR-3.1: 用户可成功注册并登录
  - `programmatic` TR-3.2: 密码使用 bcrypt 加密存储
  - `programmatic` TR-3.3: 普通用户无法访问管理员页面
  - `programmatic` TR-3.4: 问卷管理员可以创建和编辑问卷
- **Notes**: 实现 @login_required 基础装饰器，然后扩展角色检查

---

## [/] Task 4: 问卷管理核心功能
- **Priority**: P0
- **Depends On**: [Task 3]
- **Description**: 
  - 实现问卷创建（空问卷创建）
  - 实现问卷列表页面（我的问卷）
  - 实现问卷编辑基础信息（标题、描述）
  - 实现问卷状态管理（草稿、发布、暂停、结束）
  - 实现问卷发布设置（开始/结束时间、访问密码、最大响应数）
  - 实现问卷复制功能
  - 实现问卷删除（软删除或标记删除）
- **Acceptance Criteria Addressed**: [AC-4, AC-5, AC-10]
- **Test Requirements**:
  - `programmatic` TR-4.1: 用户可创建新问卷并保存
  - `programmatic` TR-4.2: 问卷状态可正确切换
  - `programmatic` TR-4.3: 问卷复制后生成新的独立问卷
  - `programmatic` TR-4.4: 非创建者无法编辑他人问卷
- **Notes**: 问卷状态枚举：draft, active, paused, closed

---

## [/] Task 5: 拖拽式问卷编辑器（后端 API）
- **Priority**: P0
- **Depends On**: [Task 4]
- **Description**: 
  - 实现题目添加 API（支持所有题型）
  - 实现题目编辑 API
  - 实现题目删除 API
  - 实现题目排序 API（更新 order 字段）
  - 实现题目逻辑跳转配置保存
  - 实现问卷保存（批量保存所有题目）
  - 实现问卷结构 JSON 数据格式定义
- **Acceptance Criteria Addressed**: [AC-3, AC-4, AC-10]
- **Test Requirements**:
  - `programmatic` TR-5.1: 可添加单选题、多选题、填空题、评分题
  - `programmatic` TR-5.2: 题目排序更新后 order 字段正确
  - `programmatic` TR-5.3: 题目删除后相关数据正确清理
  - `programmatic` TR-5.4: 问卷结构可正确序列化为 JSON
- **Notes**: 题型枚举：text, single_choice, multiple_choice, rating, scale, date, file

---

## [x] Task 6: 拖拽式问卷编辑器（前端界面）
- **Priority**: P1
- **Depends On**: [Task 5]
- **Description**: 
  - 创建编辑器页面布局（左侧工具栏、中间编辑区、右侧属性面板）
  - 实现题目组件拖拽功能（原生 JavaScript）
  - 实现题目排序拖拽（上下拖拽调整顺序）
  - 实现题目编辑界面（根据题型显示不同编辑项）
  - 实现题目预览功能
  - 实现问卷预览页面
  - 实现分页配置（可选）
- **Acceptance Criteria Addressed**: [AC-3, AC-4]
- **Test Requirements**:
  - `human-judgement` TR-6.1: 可从工具栏拖拽题目到编辑区
  - `human-judgement` TR-6.2: 可拖拽调整题目顺序
  - `human-judgement` TR-6.3: 不同题型显示不同的编辑选项
  - `human-judgement` TR-6.4: 问卷预览正确显示所有题目
- **Notes**: 使用 HTML5 Drag and Drop API 实现原生拖拽，避免引入额外库

---

## [/] Task 7: 问卷作答功能（后端）
- **Priority**: P0
- **Depends On**: [Task 4]
- **Description**: 
  - 实现问卷访问权限检查（公开/登录/用户组）
  - 实现问卷有效期检查
  - 实现访问密码验证（如果设置）
  - 实现答案验证（必填项检查、格式验证）
  - 实现答案提交保存
  - 实现作答进度保存（Session 存储）
  - 实现提交后页面
- **Acceptance Criteria Addressed**: [AC-5, AC-10]
- **Test Requirements**:
  - `programmatic` TR-7.1: 公开问卷无需登录即可访问
  - `programmatic` TR-7.2: 必填项未填写时提交被拒绝
  - `programmatic` TR-7.3: 答案正确保存到 Response 和 ResponseAnswer 表
  - `programmatic` TR-7.4: 过期问卷无法访问
- **Notes**: 使用 Session 存储作答进度，支持用户中途离开后继续

---

## [/] Task 8: 问卷作答功能（前端）
- **Priority**: P1
- **Depends On**: [Task 7]
- **Description**: 
  - 创建问卷作答页面
  - 根据题型渲染不同的输入控件
  - 实现表单验证前端提示
  - 实现分页导航（如果启用分页）
  - 实现进度保存自动触发
  - 实现提交按钮和确认弹窗
- **Acceptance Criteria Addressed**: [AC-5]
- **Test Requirements**:
  - `human-judgement` TR-8.1: 不同题型正确显示对应输入方式
  - `human-judgement` TR-8.2: 必填项未填写时有明确提示
  - `human-judgement` TR-8.3: 提交后显示成功反馈
- **Notes**: 确保移动端适配，使用响应式设计

---

## [/] Task 9: 防刷票机制
- **Priority**: P1
- **Depends On**: [Task 7]
- **Description**: 
  - 实现 IP 限制：记录每个 IP 的作答次数，超过限制拒绝
  - 实现 Cookie 跟踪：设置 Cookie 标记已作答设备
  - 实现图形验证码：使用 Pillow 生成验证码，提交时验证
  - 实现登录限制：可设置必须登录才能作答
  - 实现异常检测：短时间内大量相同答案标记为无效
  - 实现答卷有效性标记（is_valid 字段）
- **Acceptance Criteria Addressed**: [AC-6, AC-7, AC-10]
- **Test Requirements**:
  - `programmatic` TR-9.1: 同一 IP 超过限制次数后无法提交
  - `programmatic` TR-9.2: 验证码错误时提交被拒绝
  - `programmatic` TR-9.3: 设置"必须登录"后，未登录用户无法访问
  - `programmatic` TR-9.4: Cookie 存在时阻止重复提交
- **Notes**: 防刷票策略可按问卷配置，每个问卷可独立启用/禁用

---

## [x] Task 10: 统计分析功能（后端）
- **Priority**: P1
- **Depends On**: [Task 8, Task 9]
- **Description**: 
  - 实现基本统计：总作答数、有效作答数、人均答题时间
  - 实现单选题统计：各选项选择人数、百分比
  - 实现多选题统计：各选项选择人数、百分比（多选一选多选分开统计）
  - 实现评分题/量表题统计：平均分、各分数段分布
  - 实现填空题统计：词频分析（简单空格分词+计数）
  - 实现交叉分析：两个题目答案的关联统计
  - 实现作答时间分布统计
- **Acceptance Criteria Addressed**: [AC-8, AC-10]
- **Test Requirements**:
  - `programmatic` TR-10.1: 单选题统计返回各选项计数和百分比
  - `programmatic` TR-10.2: 评分题返回正确的平均分
  - `programmatic` TR-10.3: 无效答卷不参与统计
  - `programmatic` TR-10.4: 统计数据按问卷隔离
- **Notes**: 统计计算时只使用 is_valid=True 的答卷

---

## [ ] Task 11: 统计分析功能（前端可视化）
- **Priority**: P2
- **Depends On**: [Task 10]
- **Description**: 
  - 创建统计页面布局
  - 集成轻量级图表库（如 Chart.js，可选，或使用原生 Canvas）
  - 实现单选题/多选题饼图/柱状图
  - 实现评分题柱状图/雷达图
  - 实现填空题词云展示（可选，或列表形式）
  - 实现交叉分析表格
- **Acceptance Criteria Addressed**: [AC-8]
- **Test Requirements**:
  - `human-judgement` TR-11.1: 图表正确渲染统计数据
  - `human-judgement` TR-11.2: 无数据时显示空状态提示
  - `human-judgement` TR-11.3: 数值标签正确显示
- **Notes**: 如果不引入额外库，可使用简单的 CSS 柱状图；Chart.js 是 CDN 引入的推荐选项

---

## [x] Task 12: 数据导出功能
- **Priority**: P2
- **Depends On**: [Task 10]
- **Description**: 
  - 实现 CSV 格式导出（原始答卷数据）
  - 实现 Excel 格式导出（使用 openpyxl）
  - 实现统计摘要导出（可选）
  - 导出文件命名包含问卷名称和时间
  - 导出时过滤无效答卷
- **Acceptance Criteria Addressed**: [AC-9, AC-10]
- **Test Requirements**:
  - `programmatic` TR-12.1: CSV 文件可正确下载，内容完整
  - `programmatic` TR-12.2: Excel 文件可正确打开，数据格式正确
  - `programmatic` TR-12.3: 无效答卷不在导出结果中
  - `programmatic` TR-12.4: 文件名符合预期格式
- **Notes**: 使用流式响应处理大数据量导出，避免内存溢出

---

## [x] Task 13: 安全防护增强
- **Priority**: P1
- **Depends On**: [Task 3]
- **Description**: 
  - 实现 CSRF 保护（Flask-WTF）
  - 实现 SQL 注入防护（使用 SQLAlchemy 参数化查询）
  - 实现 XSS 防护（Jinja2 自动转义 + 额外过滤）
  - 实现 Session 安全配置（Secure, HttpOnly, SameSite）
  - 实现请求频率限制（Flask-Limiter）
  - 实现敏感操作日志记录
- **Acceptance Criteria Addressed**: [AC-2, AC-10]
- **Test Requirements**:
  - `programmatic` TR-13.1: 表单提交包含 CSRF token，缺失则拒绝
  - `programmatic` TR-13.2: SQL 注入尝试被拦截，无数据泄露
  - `programmatic` TR-13.3: XSS 脚本被转义，无法执行
  - `programmatic` TR-13.4: 超过频率限制的请求被拒绝
- **Notes**: 这是安全关键任务，需要仔细测试

---

## [ ] Task 14: 用户组与权限管理界面
- **Priority**: P2
- **Depends On**: [Task 3]
- **Description**: 
  - 实现用户列表管理页面
  - 实现角色管理页面（创建、编辑、删除角色）
  - 实现用户组管理页面
  - 实现用户角色分配
  - 实现用户组成员管理
  - 实现权限配置界面
- **Acceptance Criteria Addressed**: [AC-2]
- **Test Requirements**:
  - `human-judgement` TR-14.1: 管理员可看到用户列表
  - `human-judgement` TR-14.2: 可创建新角色并分配权限
  - `human-judgement` TR-14.3: 可将用户添加到用户组
- **Notes**: 仅超级管理员可访问这些页面

---

## [/] Task 15: 测试与修复
- **Priority**: P0
- **Depends On**: [Task 1-14]
- **Description**: 
  - 编写单元测试（核心功能）
  - 进行功能测试（手动测试所有主要流程）
  - 进行安全测试（SQL 注入、XSS、CSRF 等）
  - 修复发现的所有 Bug
  - 优化性能问题
- **Acceptance Criteria Addressed**: [AC-1 到 AC-10]
- **Test Requirements**:
  - `programmatic` TR-15.1: 所有单元测试通过
  - `programmatic` TR-15.2: 安全测试无高危漏洞
  - `human-judgement` TR-15.3: 主要功能流程顺畅无阻塞
- **Notes**: 此任务贯穿整个开发过程，但作为最终验收

---

## 任务优先级汇总

### P0（关键路径）
1. 项目初始化与基础配置
2. 数据库模型设计与创建
3. 用户认证与授权系统
4. 问卷管理核心功能
5. 拖拽式问卷编辑器（后端 API）
7. 问卷作答功能（后端）
15. 测试与修复

### P1（重要功能）
6. 拖拽式问卷编辑器（前端界面）
8. 问卷作答功能（前端）
9. 防刷票机制
10. 统计分析功能（后端）
13. 安全防护增强

### P2（增强功能）
11. 统计分析功能（前端可视化）
12. 数据导出功能
14. 用户组与权限管理界面
