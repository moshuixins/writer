# 项目开发规范

适用范围：`backend/`、`frontend/`、根目录运维脚本与文档。

## 1. 目标与原则

1. 优先保证正确性、可维护性、可观测性，其次再做局部性能优化。
2. 后端权限校验、错误处理、时区与数据边界必须以后端为准；前端权限仅负责体验层收口。
3. 新增能力必须可测试、可回退、可定位问题，禁止只靠人工回归。

## 2. 分层规范

### 后端
1. `api/` 只负责参数校验、权限校验、HTTP 响应拼装，不承载复杂业务编排。
2. `services/` 负责业务流程与跨资源协作。
3. `models/` 只定义持久化结构，不写业务分支逻辑。
4. `prompts/` 只维护提示词、文种目录和校验，不直接操作数据库。
5. 启动初始化统一走显式 bootstrap，禁止在模块导入阶段执行建表、补 schema、恢复任务等副作用。

### 前端
1. 页面组件负责展示与交互编排；可复用权限、状态映射、格式化逻辑必须抽到 `utils/` 或同目录纯函数模块。
2. 路由、菜单、按钮权限必须共用同一套判断规则，禁止各自写一套分支。
3. 大页面中与模板无关的业务规则优先抽离，避免单文件持续膨胀。

## 2.1 数据库迁移规范

1. 数据库结构变更以 Alembic revision 为唯一真源，禁止继续把 `Base.metadata.create_all()` 当成正式迁移方案。
2. 新增表、字段、索引、唯一约束后，必须同步生成并提交 Alembic migration。
3. 仅允许在兼容旧库且缺少 `alembic_version` 时使用一次性 bootstrap + `stamp head`；新逻辑不得继续追加新的 schema patch 分支。
4. 提交前至少执行一次 `python -m alembic -c alembic.ini upgrade head` 和 `python -m alembic -c alembic.ini check`。

## 3. 权限与安全规范

1. 所有受保护接口必须在后端使用 `require_permission()` 或等价能力校验。
2. 前端路由 `meta.auth`、菜单过滤、按钮显隐必须与后端权限编码保持一致。
3. 错误响应对外只返回通用信息与 `error_id`，内部异常、绝对路径、堆栈只写日志。
4. 默认密钥、示例密钥不得直接用于启动生产环境。

## 4. 时间与时区规范

1. 数据库存储统一使用 UTC。
2. API 对外展示时间统一转换为上海时间（UTC+8）。
3. 涉及 SQLite 的 `DateTime` 比较要显式考虑 naive/aware 差异，避免运行时崩溃。

## 5. 文本文件规范

1. 所有源码、配置、文档统一使用 UTF-8 无 BOM。
2. 修改文件时保持原有换行风格，避免无意义整文件噪音。
3. JSON/配置文件禁止写入 BOM，防止 OpenViking、Node、浏览器工具链解析失败。
4. 在 PowerShell 中处理中文输出或文本文件前，先执行 `. .\scripts\powershell_utf8.ps1`，统一控制台与文件写入编码。
5. PowerShell 禁止使用 `Set-Content`、`Add-Content`、`Out-File`、`>`、`>>` 直接写仓库文本文件；需要写文件时优先用 `apply_patch`，否则使用 `Write-Utf8NoBomFile`。
6. 修复历史编码问题统一使用 `python scripts/check_text_encoding.py --all --fix-bom` 或 `Convert-FileToUtf8NoBom`，不要手工另写一套转换逻辑。

## 6. 错误处理与可观测性规范

1. 业务异常使用统一异常类型；未知异常统一记录 `error_id`。
2. 后端长流程任务必须持久化状态，并在重启后可恢复到可观测状态。
3. 流式接口失败时不得写入半成品结果。

## 7. 测试规范

1. 任何权限、会话、导入任务、记忆写入相关改动必须补回归测试。
2. 后端至少覆盖接口级或服务级回归；前端至少覆盖纯逻辑回归或页面权限回归。
3. 新增脚本必须能在本地直接运行，不依赖隐式手工步骤。

## 8. 重构触发条件

满足以下任一条件必须优先重构：
1. 同一规则在三处及以上重复实现。
2. 模块在导入时存在副作用。
3. 一次事故已证明该类问题会反复出现，例如 BOM、权限漏控、流式失败写脏数据。
4. 页面按钮显示与真实权限不一致。

## 9. 提交前最小检查

### 后端
1. `python -m py_compile ...` 或等价语法检查
2. 关键回归：`python -m unittest discover -s backend/tests -v`

### 前端
1. `pnpm -s exec vue-tsc --noEmit`
2. `pnpm -s run test:permissions`
3. `pnpm run --config.verify-deps-before-run=false build`

## 10. 当前阶段的强制规范

1. RBAC 以后端持久化模型为真源。
2. 书籍导入任务必须持久化，且重启后标记 `interrupted`。
3. `finish_session` 不再提交记忆。
4. 风格学习仍维持两次全量 LLM 调用，不在本规范中改动。
