# 后端开发规范

适用范围：`backend/`、后端相关根目录脚本（如 `scripts/export_openapi.py`）以及直接服务于后端契约的测试与导出脚本。

优先级说明：
- 本文是当前项目后端的专项规范。
- 通用约束仍以 [development-standard.md](./development-standard.md) 为基础。
- 若两者冲突，后端范围内以本文为准。

## 1. 目标与基本原则

1. 后端是权限、数据边界、时间语义、错误边界和接口契约的真源。
2. 新增能力必须可测试、可回归、可观测，不能只依赖人工验证。
3. 先保证正确性、可维护性和可恢复性，再做局部性能优化。
4. 任何面向前端或第三方调用方的输出，都必须稳定、可声明、可回归检查。

## 2. 当前后端架构真源

当前项目后端以以下文件和目录为核心：

- `backend/app/main.py`：应用入口、生命周期、全局中间件、异常处理、路由挂载。
- `backend/app/bootstrap.py`：启动阶段一次性执行迁移与运行时引导。
- `backend/app/api/`：HTTP 路由层。
- `backend/app/services/`：业务编排、外部依赖调用、后台任务与长流程。
- `backend/app/models/`：SQLAlchemy 持久化模型。
- `backend/app/schemas/`：对外请求/响应契约，尤其是响应模型与流式事件模型。
- `backend/app/serializers.py`：统一 JSON/SSE 输出组装。
- `backend/app/migration.py` + `backend/alembic/`：数据库迁移真源。
- `backend/app/side_effects.py`：外部副作用降级、错误 ID 和 warning 收集。
- `backend/tests/test_regressions.py`：当前核心后端回归基线。

请求链路默认遵循：

`API -> Service -> Serializer/Schema -> Response`

模型层只承载持久化结构，不承担接口输出职责。

## 3. 分层职责规范

### 3.1 `main.py` 与启动入口

1. `main.py` 只负责应用装配：中间件、异常处理、路由注册、生命周期钩子。
2. 启动时的初始化逻辑统一收口到 `bootstrap.py` 与 `runtime_bootstrap_tasks.py`。
3. 禁止在模块导入阶段执行建表、补 schema、恢复任务、创建目录等副作用。
4. 任何新增全局资源都必须在生命周期结束时显式关闭或回收。

### 3.2 `api/` 路由层

1. 路由层负责参数校验、权限校验、HTTP 状态码选择、调用服务、返回序列化结果。
2. 路由层不得承载复杂业务流程、跨多个资源的长链路编排。
3. 允许少量入口级协调逻辑留在路由层，但必须满足：
   - 逻辑短小且可读
   - 事务边界清晰
   - 外部副作用失败时有明确降级行为
4. 路由层禁止直接返回 ORM 对象、数据库行元组或未声明结构的字典。

### 3.3 `services/` 服务层

1. 服务层负责业务规则、跨资源协作、外部依赖调用和长流程编排。
2. 服务层必须可在 CLI、后台任务和 API 三类入口中复用，避免为每个入口复制实现。
3. 与 OpenAI、OpenViking、OCR、导入任务、DOCX 生成相关的非纯 HTTP 逻辑，优先放在服务层。
4. 需要独立线程池、后台调度或恢复逻辑的能力，必须集中在服务层，不得散落在路由层。

### 3.4 `models/` 模型层

1. 模型层只定义持久化结构、索引、约束和关系。
2. 模型层不写业务分支、权限判断、序列化输出或外部系统调用。
3. 所有业务数据表必须明确账户边界；新增业务表默认应有 `account_id`，除非确认是全局共享表。

### 3.5 `schemas/` 契约层

1. 所有对外 JSON 响应必须有 `response_model`，并由 `app/schemas/` 提供类型定义。
2. 可复用或对外可观察的流式事件，同样要进入 `app/schemas/`，不能只在前端手写约定。
3. 简单且只在单一路由使用的请求模型可以定义在 API 文件内；复用型或对外长期暴露的模型应迁入 `schemas/`。
4. 字段默认值、空数组、空对象语义必须在 schema 层清晰表达，避免前端猜测。

### 3.6 `serializers.py` 序列化层

1. 一切对外 JSON 结构组装必须通过 serializer 统一完成。
2. 路由层不手拼时间字段、状态字段、分页结构和 SSE 事件。
3. 新增列表接口优先复用 `serialize_collection_response(items, total=...)`。
4. 新增流式事件必须在 serializer 中提供统一封装，并由回归测试锁定输出格式。

### 3.7 `prompts/`、`jobs/`、`scripts/`

1. `prompts/` 只维护提示词、文种目录和相关校验，不直接访问数据库。
2. `jobs/` 只做离线入口，必须复用服务层，不得复制业务实现。
3. 根目录与 `scripts/` 下的后端辅助脚本，必须与正式后端契约保持一致，不能绕过真实启动路径制造第二套逻辑。

## 4. 接口契约规范

1. 每个 JSON 路由都必须显式声明 `response_model`。
2. 列表接口统一返回：
   - `items`
   - `total`
3. 详情接口统一返回稳定对象，不返回匿名嵌套结构。
4. 文件下载接口可以例外返回 `blob/file response`，但错误仍应返回稳定 JSON。
5. SSE 事件统一使用带 `event` 判别字段的结构化负载；当前标准事件为：
   - `workflow`
   - `chunk`
   - `error`
   - `final`
   - 结束标记仍使用 `data: [DONE]`
6. 契约变更后必须同步执行：
   - `pnpm -C frontend run generate:openapi`
   - `pnpm -C frontend run verify:openapi`
7. 任何接口字段重命名、数组/对象空值语义变化、SSE 事件变化，都视为契约变更，必须补回归测试。

## 5. 数据库与事务规范

1. 数据库结构变更以 Alembic revision 为唯一真源。
2. 禁止继续把 `Base.metadata.create_all()` 当作正式迁移方案。
3. 仅允许在兼容旧库且缺少 `alembic_version` 时使用一次性 bootstrap + `stamp head`。
4. 请求内数据库会话统一通过 `Depends(get_db)` 获取。
5. 事务边界必须显式：
   - 成功时 `commit`
   - 失败时 `rollback`
   - 失败后再抛出或转换异常
6. 可复用服务方法应尽量避免隐式提交；如果必须提交，要么在命名上说明，要么提供 `commit=False` 之类的显式控制。
7. 后台任务、线程池任务、调度器任务不得复用请求会话，必须自己创建和关闭 `SessionLocal()`。
8. 查询业务数据时必须先加账户过滤；用户私有资源还要再加 `user_id` 过滤。

## 6. 权限与账户隔离规范

1. 所有受保护接口必须使用 `require_permission()` 或等价后端权限校验。
2. 仅获取当前用户自身信息的接口，才允许只依赖 `get_current_user`。
3. 账户范围校验统一走 `_ensure_account_scope()` 或等价辅助逻辑，不能在多个接口手写不同规则。
4. RBAC 真源是持久化模型与 `RBACService`，不是前端菜单状态，也不是 `user.role` 单字段的临时判断。
5. 涉及以下资源时，必须明确账户隔离边界：
   - 素材
   - 会话
   - 草稿
   - 导出记录
   - 用户偏好
   - 写作习惯
   - 账户级记忆/上下文
6. 全局共享资源必须在设计文档中明确标注，不能因为“方便”默认做成全局。

## 7. 错误处理与可观测性规范

1. 对外错误响应只返回通用错误信息，必要时追加 `error_id`。
2. 禁止向前端暴露：
   - 绝对路径
   - Python 堆栈
   - 第三方 SDK 原始异常
   - 数据库内部错误细节
3. `AppError` 用于业务可预期错误；未知异常统一进入全局异常处理。
4. 所有 5xx 问题必须能在日志中通过 `error_id` 追踪。
5. 日志必须记录最小必要上下文，例如：`operation`、`account_id`、`user_id`、`task_id`、`error_id`。
6. 日志中禁止打印密钥、令牌、密码、完整邀请码、原始凭证内容。

## 8. 外部副作用与降级规范

1. OpenViking、外部会话上下文、记忆同步、书籍知识同步等能力默认视为“外部副作用”。
2. 若外部副作用不是本次请求的核心成功条件，应采用“主流程成功 + warning 降级”的方式处理。
3. 降级逻辑统一复用 `app/side_effects.py`：
   - 生成 `error_id`
   - 写日志
   - 返回可追踪的 warning 文案
4. 是否允许降级必须明确：
   - 核心写库失败：不能降级，必须失败
   - 外部同步失败：通常允许降级，但必须可观测
5. 禁止在多个服务里各自拼装 warning 文案和 error id 规则。

## 9. 异步、流式与后台任务规范

1. `async def` 路由中不得直接执行阻塞 I/O 或 CPU 密集工作。
2. 阻塞逻辑应迁移到：
   - `BackgroundExecutor`
   - 专用 dispatcher
   - 或明确受控的线程池执行器
3. 聊天流式输出必须通过统一的 SSE serializer 发送事件，不得在路由里手写 JSON 字符串。
4. 长流程任务必须满足三点：
   - 状态可持久化
   - 进度可查询
   - 进程重启后可恢复到可观测状态
5. 导入类后台任务必须限制并发，避免线程风暴和重建竞争。当前单任务串行导入策略是正式约束，不得随意放宽。
6. 应用退出时，线程池和调度器必须在生命周期中显式关闭。

## 10. 时间、路径与文本规范

1. 数据库存储统一使用 UTC。
2. API 对外时间统一通过时区工具转换为上海时区字符串，禁止在路由层直接 `isoformat()`。
3. 所有文件路径必须来自 `Settings`，并通过 `config.py` 中的路径解析逻辑归一化。
4. 禁止在业务代码中硬编码开发机绝对路径。
5. 文本文件统一使用 UTF-8 无 BOM。
6. JSON、配置文件、OpenAPI 导出文件严禁写入 BOM。

## 11. OpenAPI 与前端对接规范

1. 后端响应 schema 是前端类型生成的唯一上游。
2. 修改以下内容时，必须视为前后端联动变更：
   - `response_model`
   - serializer 输出结构
   - SSE 事件格式
   - 错误响应字段
3. 后端变更完成后必须执行：
   - `pnpm -C frontend run generate:openapi`
   - `pnpm -C frontend run verify:openapi`
4. 若 `verify:openapi` 失败，说明生成产物未同步，禁止提交契约变更。

## 12. 测试与交付规范

### 12.1 必跑检查

后端改动提交前至少执行：

```bash
python -m compileall backend/app backend/tests scripts
python -m pytest backend/tests/test_regressions.py -q
python scripts/check_text_encoding.py --all
```

若改动涉及接口契约，还必须执行：

```bash
pnpm -C frontend run generate:openapi
pnpm -C frontend run verify:openapi
```

若改动涉及前端权限或菜单联动，还必须执行：

```bash
pnpm -C frontend run test:permissions
```

### 12.2 回归测试要求

1. 改 JSON 响应结构：补接口形状回归。
2. 改 SSE 事件：补事件序列化与流式回归。
3. 改权限：补权限与账户边界回归。
4. 改迁移或启动逻辑：补 Alembic / bootstrap 回归。
5. 改长流程任务：补任务恢复、并发控制和失败场景回归。

## 13. 禁止事项

1. 禁止在 API 层直接拼接复杂响应结构。
2. 禁止在路由层直接写大段业务流程、重度数据库操作或多阶段外部编排。
3. 禁止新增绕过 Alembic 的正式 schema patch 分支。
4. 禁止让前端承担真实权限判断或账户隔离责任。
5. 禁止把内部异常、绝对路径、堆栈和密钥暴露给客户端。
6. 禁止在后台线程中复用请求上下文对象或请求数据库会话。
7. 禁止无上限并发地执行 OCR、导入、流式生成等重任务。

## 14. 推荐开发流程

1. 先明确资源边界、权限边界和契约变更范围。
2. 先写或修改 schema / serializer，再改路由和服务实现。
3. 若涉及数据库结构，先补 Alembic revision。
4. 若涉及前端消费字段，立即同步生成 OpenAPI 类型。
5. 完成代码后跑最小回归，再补专项测试。
6. 最后检查日志、错误信息、路径与编码是否符合规范。
