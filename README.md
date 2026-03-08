# 公文写作系统

公文写作系统是一个面向正式公文场景的全栈应用，提供写作会话、素材治理、书籍学习、风格增强、DOCX 导出以及基于账户的权限与资源隔离能力。

## 项目定位

系统围绕“写作工作台 + 知识增强 + 账户治理”构建，目标不是做通用聊天，而是把正式公文写作流程收口为一套可管理、可追踪、可部署的业务系统。

当前仓库已经包含：

- 落地页、登录页、写作工作区和管理后台
- FastAPI 后端、Vue 3 前端、OpenViking 知识库接入
- Alembic 数据库迁移
- 一次性邀请码注册与初始化管理员
- 基于账户的 RBAC、资源隔离和权限回归
- EPUB / PDF 书籍学习与扫描版 PDF OCR
- OpenAPI 产物生成、前端权限回归、后端回归测试、GitHub Actions CI

## 核心能力

### 1. 写作工作区

- 会话首页先展示会话列表，再进入具体写作工作台
- 会话内提供对话区、工作流步骤、编辑器草稿和导出链路
- 首轮请求生成写作引导，后续请求走正式写作增强流程
- 流式接口通过 SSE 返回工作流、chunk、error、final 事件
- 会话上下文按最近 20 条消息参与生成

### 2. 素材管理

- 支持上传 `.doc`、`.docx`、`.pdf`、`.txt`
- 自动提取标题、规范文种、摘要、关键词和风格特征
- 素材内容写入数据库后同步进入账户级知识库命名空间
- 支持搜索、查看详情、批量删除、批量分类

### 3. 书籍学习

- 支持扫描 `data/book` 目录，也支持前端直接上传书籍文件
- 支持 `EPUB`、文本型 `PDF`、扫描型 `PDF`
- 扫描型 PDF 可自动降级到 OCR 管线：`pdf2image + Pillow + pytesseract`
- 书籍分片只进入知识库与书籍规则表，不出现在素材列表中
- 每个账户的书籍知识、书籍规则和向量命名空间独立隔离

### 4. 风格增强

- 素材上传时会做统计特征、词汇特征和全文 LLM 风格分析
- 写作生成时会同时融合素材检索、书籍检索、书籍风格规则和用户偏好
- Prompt 内置“仅吸收写法、不直接复用原文”的硬约束

### 5. 账户、角色与权限

- 采用账户级资源隔离，业务资源和记忆按账户管理
- 支持系统角色与自定义角色
- 支持用户角色绑定、邀请码生成/撤销、用户账户迁移
- 支持初始化管理员自动引导创建

### 6. 文档导出

- 支持从写作结果导出 DOCX
- 支持从编辑器草稿导出 DOCX
- 提供导出历史列表和文件下载接口

## 主要页面与路由

公开页面：

- `/`：落地页
- `/login`：登录 / 邀请码注册

写作区：

- `/chat`：会话首页
- `/chat/:sessionId`：写作工作台
- `/materials`：素材管理
- `/book-learning`：书籍学习
- `/history`：导出历史
- `/settings`：写作偏好

管理区：

- `/admin/overview`：管理概览
- `/admin/accounts`：账户、用户、邀请码管理
- `/admin/roles`：角色与权限管理

## 技术栈

前端：

- Vue 3
- TypeScript
- Vite 8 beta
- Element Plus
- Pinia
- UnoCSS
- TinyMCE
- Playwright

后端：

- FastAPI
- SQLAlchemy 2
- Alembic
- LangChain + OpenAI Compatible API
- OpenViking

文档与 OCR：

- python-docx
- PyPDF2
- EbookLib
- BeautifulSoup4
- pdf2image
- pytesseract
- Pillow
- antiword

## 目录结构

```text
writer/
├─ backend/
│  ├─ alembic/
│  ├─ app/
│  │  ├─ api/
│  │  ├─ models/
│  │  ├─ schemas/
│  │  ├─ services/
│  │  └─ prompts/
│  ├─ scripts/
│  ├─ tests/
│  ├─ alembic.ini
│  ├─ Dockerfile
│  └─ requirements.txt
├─ frontend/
│  ├─ src/
│  │  ├─ api/
│  │  ├─ layouts/
│  │  ├─ router/
│  │  └─ views/
│  ├─ scripts/
│  ├─ Dockerfile
│  └─ package.json
├─ data/
│  ├─ book/
│  ├─ exports/
│  ├─ openviking/
│  ├─ uploads/
│  └─ writer.db
├─ docs/
├─ scripts/
├─ .env.example
├─ docker-compose.yml
├─ deploy.sh
└─ README.md
```

## 运行要求

推荐部署方式：Docker Compose。

如需本地开发，建议环境：

- Python `3.11`
- Node.js `22`
- pnpm `10.26.2`
- Docker + Docker Compose v2
- 本地 OCR 场景下额外安装 `tesseract-ocr`、中文语言包、`poppler-utils`

## 快速开始（Docker 推荐）

### 1. 准备环境变量

在项目根目录复制示例文件：

```bash
cp .env.example .env
```

至少需要修改这些配置：

- `OPENAI_API_KEY`
- `SECRET_KEY`
- `OPENVIKING_ROOT_API_KEY`
- `OPENAI_BASE_URL`、`OPENAI_MODEL`、`OPENAI_EMBEDDING_MODEL`（如果不使用默认 OpenAI 兼容服务）

注意：

- `SECRET_KEY` 和 `OPENVIKING_ROOT_API_KEY` 不能保留默认占位值，否则后端会拒绝启动
- `OPENVIKING_ROOT_API_KEY` 必须与 `data/openviking/ov.conf` 中的 `server.root_api_key` 保持一致
- `BOOKS_DIR`、`UPLOAD_DIR`、`EXPORT_DIR`、`OPENVIKING_CONFIG_FILE`、`OPENVIKING_SHARED_BACKEND_DIR` 如果是相对路径，都会按项目根目录 `writer/` 解析

### 2. 准备 OpenViking 配置

首次部署前执行：

```bash
cp data/openviking/ov.conf.example data/openviking/ov.conf
```

然后手工修改 `data/openviking/ov.conf`。

重要约束：

- 该文件是本地运行文件，不应提交到 Git
- 文件编码必须是 `UTF-8 无 BOM`
- 如果使用 Windows 编辑器，保存时不要带 BOM，否则 OpenViking 会报 `Unexpected UTF-8 BOM`

### 3. 可选：初始化管理员

如果希望首次启动后自动创建平台管理员，在 `.env` 中设置：

```env
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=your-strong-password
INITIAL_ADMIN_DISPLAY_NAME=系统管理员
INITIAL_ADMIN_DEPARTMENT=信息中心
```

说明：

- 仅当用户名不存在时才会创建
- 密码长度必须至少 8 位
- 初始化管理员默认归属默认账户 `account_id=1`

### 4. 启动服务

Linux 服务器可直接使用部署脚本：

```bash
bash deploy.sh
```

脚本会自动：

- 检查 Docker 和 Docker Compose
- 若 `.env` 不存在则从 `.env.example` 复制
- 若 `data/openviking/ov.conf` 不存在则从示例复制
- 执行 `docker compose up -d --build`

也可以手工执行：

```bash
docker compose up -d --build
```

### 5. 访问地址

- 前端：`http://localhost`
- 后端健康检查：`http://localhost:8000/api/health`
- OpenViking 健康检查：`http://localhost:1933/health`

## 本地开发

### 方案一：前后端本地运行，OpenViking 用 Docker

先启动 OpenViking：

```bash
docker compose up -d openviking
```

启动后端：

```bash
cd backend
python -m venv .venv
# 激活虚拟环境后执行
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动前端：

```bash
cd frontend
pnpm install
pnpm dev
```

本地开发地址：

- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000`

说明：

- 后端启动时会自动执行 Alembic 迁移和运行时引导任务
- 如果你在本地运行后端且需要 OCR，请自行安装 `tesseract` 与 `poppler`
- 如果你在本地运行后端且需要解析 `.doc`，建议安装 `antiword`

### 方案二：前后端全部使用 Docker Compose

```bash
docker compose up -d --build
```

## 数据库迁移

项目以 Alembic revision 为数据库结构真源。

后端启动时会自动迁移到最新版本；如需手工执行：

```bash
cd backend
python -m alembic -c alembic.ini upgrade head
```

新增迁移：

```bash
cd backend
python -m alembic -c alembic.ini revision --autogenerate -m "describe change"
```

兼容说明：

- 旧数据库如果已有业务表但没有 `alembic_version`，系统会做一次兼容补齐并自动 `stamp head`
- 不要再用“手工改表代替迁移”的方式维护结构

## 认证、账户与权限模型

### 注册与登录

- 登录使用用户名 + 密码
- 注册必须使用一次性邀请码
- 邀请码绑定到账户，注册后用户自动进入对应账户

### 角色与权限

系统内置两个系统角色：

- `admin`：账户管理、用户、角色、邀请码及业务资源全管理
- `writer`：写作、素材、文档、偏好、书籍学习等业务功能使用权限

同时支持自定义角色，并将权限持久化到数据库中。

### 账户级数据隔离

以下资源按账户隔离：

- 素材
- 写作会话与消息
- 会话草稿
- 导出记录
- 用户偏好与写作习惯
- 书籍来源与书籍规则
- OpenViking 中的 materials / books / memory 命名空间

## 写作流程说明

典型链路如下：

1. 新建会话
2. 首轮请求生成写作引导
3. 后续请求走正式写作流程
4. 流式工作流步骤依次展示：
   - 分析请求意图
   - 搜索素材
   - 检索书籍知识
   - 融合书籍风格规则
   - 生成回复
5. 在编辑器中保存草稿或直接导出 DOCX

非流式接口：`/api/chat/send`

流式接口：`/api/chat/send-stream`

## 素材管理说明

支持格式：

- `.doc`
- `.docx`
- `.pdf`
- `.txt`

上传后会产出：

- 标题
- 规范文种
- 摘要
- 关键词
- 风格特征
- 字数统计

素材入库后会同步到当前账户的知识库命名空间，用于后续写作增强。

## 书籍学习与 OCR

### 目录与路径

默认书籍目录是：

```text
data/book
```

如果 `.env` 中写的是：

```env
BOOKS_DIR=./data/book
```

则无论本地运行还是 Docker Compose，都会按项目根目录解析到同一位置。

### 导入方式

前端页面：

- 书籍学习页面可扫描目录、上传书籍、启动学习、查看任务进度和导入记录

后端 API：

- `GET /api/materials/books/scan`
- `POST /api/materials/books/upload`
- `POST /api/materials/books/import`
- `GET /api/materials/books/tasks/{task_id}`
- `GET /api/materials/books/sources`

CLI：

```bash
cd backend
python -m app.jobs.import_books
python -m app.jobs.import_books --rebuild
python -m app.jobs.import_books --dir ../data/book
python -m app.jobs.import_books --selected-file 示例.pdf --selected-file 分类/示例.epub
```

### OCR 说明

- 文本型 PDF 优先走文本层提取
- 扫描型 PDF 会自动切换到 OCR
- OCR 参数由 `PDF_OCR_ENABLED`、`PDF_OCR_LANG`、`PDF_OCR_DPI`、`PDF_OCR_MAX_PAGES` 控制
- Docker 后端镜像已经安装 OCR 依赖；本地运行需要自行安装系统依赖

## 质量保障与常用命令

后端：

```bash
python -m compileall backend/app backend/tests scripts
python -m pytest backend/tests/test_regressions.py -q
python scripts/check_text_encoding.py --all
```

前端：

```bash
pnpm -C frontend run verify:openapi
pnpm -C frontend exec vue-tsc --noEmit
pnpm -C frontend run lint:eslint:check
pnpm -C frontend run lint:stylelint:check
pnpm -C frontend run test:permissions
pnpm -C frontend run --config.verify-deps-before-run=false build
```

可选的视觉回归：

```bash
pnpm -C frontend run test:visual
```

GitHub Actions 已配置 CI，推送与 PR 会自动执行后端回归、OpenAPI 校验、前端类型检查、Lint、权限回归与构建。

## 常见问题

### 1. 后端启动时报 `SECRET_KEY must be overridden`

说明 `.env` 里仍在使用默认占位密钥。请至少修改：

- `SECRET_KEY`
- `OPENVIKING_ROOT_API_KEY`

### 2. OpenViking 启动时报 JSON BOM 错误

请检查 `data/openviking/ov.conf`：

- 必须是 `UTF-8 无 BOM`
- 不要用会自动加 BOM 的编辑器保存
- 重新从 `ov.conf.example` 复制后再修改通常可以恢复

### 3. 书籍学习页面明明有 `data/book`，扫描却是 0

优先检查：

- `.env` 中的 `BOOKS_DIR` 是否仍为相对路径，例如 `./data/book`
- Docker Compose 是否仍保留 `./data:/app/data` 挂载
- 目录下文件扩展名是否为系统支持的 `epub` 或 `pdf`

### 4. 本地 OCR 不生效

请确认本机已安装：

- `tesseract-ocr`
- 中文语言包 `chi_sim`
- `poppler-utils`

## 相关文档

- [docs/development-standard.md](./docs/development-standard.md)
- [docs/backend-development-standard.md](./docs/backend-development-standard.md)
- [docs/frontend-design-standard.md](./docs/frontend-design-standard.md)
- [`.env.example`](./.env.example)

## License

本项目采用 [Apache-2.0](./LICENSE) 开源协议。
