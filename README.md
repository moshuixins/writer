# 公文写作系统

一个面向公文写作场景的多账户智能写作系统，提供写作会话、写作工作台、素材管理、书籍学习、风格学习、权限管理和 DOCX 导出能力。

## 项目概览

本项目围绕“公文起草、素材沉淀、风格复用、知识增强、权限隔离”构建，当前架构由三部分组成：

- 前端：Vue 3 + TypeScript + Vite + Element Plus
- 后端：FastAPI + SQLAlchemy + LangChain
- 检索与记忆：OpenViking

系统默认使用 SQLite 落库，OpenViking 承担素材、书籍知识和账户级记忆检索。

## 当前能力

### 1. 写作会话与工作台

- 支持多轮对话式公文写作
- 支持 SSE 流式输出
- 对话过程中展示工作流步骤，例如搜索素材、检索书籍知识、融合书籍风格规则
- 会话上下文默认使用最近 20 条消息
- 支持富文本编辑、自动草稿保存、导出 DOCX

### 2. 素材管理

- 支持上传 `txt`、`doc`、`docx`、`pdf`
- 上传后自动解析正文、识别标题、摘要、关键词、文种
- 风格学习包含统计特征、关键词/术语、结构化风格分析、数据要素分析
- 支持批量删除、批量分类、语义检索
- 素材、风格、记忆均按账户隔离

### 3. 书籍学习

- 书籍目录固定为 `data/book`
- 支持 `epub` 和 `pdf`
- 扫描版 PDF 可自动走 OCR
- 导入结果写入 OpenViking，不进入素材列表
- 支持页面手动触发学习，也支持 CLI 导入

### 4. 权限与账户管理

- 采用 RBAC 模型：账户、用户、角色、权限持久化管理
- 注册依赖一次性邀请码
- 管理后台支持账户、账号、角色、权限、邀请码管理
- 资源和记忆以账户为边界隔离

### 5. 文档导出

- 支持从写作会话和编辑器导出 DOCX
- DOCX 由后端统一生成
- 生成记录可在导出历史中追踪

## 技术栈

### 前端

- Vue 3
- TypeScript
- Vite
- Element Plus
- Pinia
- TinyMCE

### 后端

- FastAPI
- SQLAlchemy 2.x
- Pydantic Settings
- LangChain
- OpenAI Compatible API
- Jieba

### 文档与解析

- python-docx
- PyPDF2
- ebooklib
- beautifulsoup4
- antiword
- pdf2image
- pytesseract
- Pillow

### 部署

- Docker Compose
- Nginx
- OpenViking

## 目录结构

```text
writer/
├─ backend/                    # FastAPI 后端
│  ├─ app/
│  │  ├─ api/                  # HTTP 路由
│  │  ├─ models/               # 数据模型
│  │  ├─ services/             # 业务服务
│  │  ├─ prompts/              # 提示词与文种目录
│  │  ├─ serializers.py        # 响应序列化
│  │  ├─ bootstrap.py          # 启动引导
│  │  └─ main.py               # 应用入口
│  ├─ requirements.txt
│  └─ Dockerfile
├─ frontend/                   # Vue 前端
│  ├─ src/
│  │  ├─ api/
│  │  ├─ router/
│  │  ├─ store/
│  │  ├─ types/
│  │  └─ views/
│  ├─ package.json
│  └─ Dockerfile
├─ data/
│  ├─ book/                    # 待学习书籍目录
│  ├─ exports/                 # 导出文件目录
│  ├─ uploads/                 # 上传素材目录
│  └─ openviking/
│     ├─ ov.conf               # 本地运行配置，不提交 Git
│     ├─ ov.conf.example       # OpenViking 配置示例
│     ├─ entrypoint.sh
│     └─ workspace/
├─ docs/
├─ scripts/
├─ .env.example
├─ docker-compose.yml
├─ deploy.sh
└─ README.md
```

## 运行要求

### Docker 部署

- Docker
- Docker Compose v2

### 本地开发

- Python 3.11
- Node.js `^20.19.0 || >=22.12.0`
- pnpm `10.26.2`
- 建议保留 Docker 方式运行 OpenViking

## 快速开始

### 1. 准备环境变量

复制环境变量文件：

```bash
cp .env.example .env
```

必须修改以下配置：

- `OPENAI_API_KEY`
- `SECRET_KEY`
- `OPENVIKING_ROOT_API_KEY`

说明：

- `SECRET_KEY` 不能使用默认值，否则后端会拒绝启动
- `OPENVIKING_ROOT_API_KEY` 不能使用默认值，否则后端会拒绝启动
- `.env` 中的 `OPENVIKING_ROOT_API_KEY` 必须与 `data/openviking/ov.conf` 中的 `server.root_api_key` 保持一致

路径相关变量说明：

- `BOOKS_DIR`、`UPLOAD_DIR`、`EXPORT_DIR`、`OPENVIKING_CONFIG_FILE`、`OPENVIKING_SHARED_BACKEND_DIR` 如果写相对路径，会统一按项目根目录 `writer/` 解析，而不是按 `backend/` 或当前 shell 目录解析
- 因此本地使用 `cd backend && uvicorn ...` 与 Docker Compose 使用同一份 `.env` 时，路径语义保持一致
- 如果同一份 `.env` 同时用于本地和 Docker，优先使用仓库相对路径，例如 `./data/book`
- `OPENVIKING_SHARED_OV_DIR` 是 OpenViking 容器内路径，应保持 `/app/data/...` 这类容器路径
- 如果改成宿主机绝对路径，Docker 容器必须有对应 volume 挂载，否则会出现“本地能扫到、容器扫不到”或扫描结果为 `0` 的问题

### 2. 准备 OpenViking 配置

首次部署前复制配置示例：

```bash
cp data/openviking/ov.conf.example data/openviking/ov.conf
```

需要修改：

- `embedding.dense.api_key`
- `embedding.dense.api_base`
- `embedding.dense.model`
- `vlm.api_key`
- `vlm.api_base`
- `vlm.model`
- `server.root_api_key`

注意：

- `data/openviking/ov.conf` 是本地运行文件，不应提交到 Git
- 配置文件必须为 UTF-8 无 BOM，否则 OpenViking 会报 JSON 解析错误

### 3. 可选：初始化管理员

如果希望系统首次启动后自动创建管理员，请在 `.env` 中填写：

```env
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=your-strong-password
INITIAL_ADMIN_DISPLAY_NAME=系统管理员
INITIAL_ADMIN_DEPARTMENT=信息中心
```

说明：

- 仅在用户不存在时创建
- 密码长度至少 8 位
- 默认创建到 `account_id=1`
- 角色为系统管理员

### 4. 启动服务

Linux 上推荐直接使用部署脚本：

```bash
bash deploy.sh
```

脚本行为：

- 检查 Docker 与 Docker Compose
- 若 `.env` 不存在，则从 `.env.example` 复制并提示手工修改
- 若 `data/openviking/ov.conf` 不存在，则从示例复制并提示手工修改
- 执行 `docker compose up -d --build`

也可以手工启动：

```bash
docker compose up -d --build
```

### 5. 访问地址

- 前端：`http://localhost`
- 后端 OpenAPI：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/api/health`
- OpenViking：`http://localhost:1933`

## 本地开发

### 方案一：前后端本地运行，OpenViking 用 Docker

先启动 OpenViking：

```bash
docker compose up -d openviking
```

启动后端：

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动前端：

```bash
cd frontend
pnpm install
pnpm dev
```

前端开发默认端口：`http://localhost:9000`

### 方案二：全部使用 Docker Compose

```bash
docker compose up -d --build
```

### 数据库迁移（Alembic）

后端已切换为 Alembic 迁移管理。应用启动时会自动执行 `upgrade head`；开发阶段也可以手动执行：

```bash
cd backend
python -m alembic -c alembic.ini upgrade head
```

创建新迁移：

```bash
cd backend
python -m alembic -c alembic.ini revision --autogenerate -m "描述本次结构变更"
```

注意：

- 旧数据库如果已经有业务表但没有 `alembic_version`，启动时会走一次兼容补齐并自动 `stamp head`
- 新增或修改模型后，不再使用 `create_all` 作为正式迁移手段，必须补 Alembic revision

## 认证、账户与权限

### 登录与注册

- 用户注册接口：`/api/auth/register`
- 注册必须使用一次性邀请码
- 注册成功后默认分配写作角色
- 登录后返回 token 与当前用户权限上下文

### 管理后台页面

- `/admin/overview`
- `/admin/accounts`
- `/admin/roles`

### 权限边界

- 后端使用权限码强制校验
- 前端路由、菜单、按钮与后端权限保持一致
- 账户是资源隔离边界
- OpenViking 资源命名空间按账户划分

## 素材管理

### 支持格式

- `txt`
- `doc`
- `docx`
- `pdf`

### 解析说明

- `docx` 通过 `python-docx` 提取文本
- `doc` 优先调用系统工具 `antiword`，若缺失也会尝试 `catdoc` 或 `wvText`
- `pdf` 使用 `PyPDF2`
- 上传流程会同步完成解析、分类和风格分析

### 素材分析输出

- 标题
- 摘要
- 关键词
- 文种
- 字数
- 风格统计
- 结构化风格结论
- 数据要素及其主题归属

## 书籍学习

### 书籍目录

```text
data/book
```

路径说明：

- 页面扫描与默认导入读取 `settings.books_dir`
- `BOOKS_DIR=./data/book` 会统一解析到项目根目录下的 `data/book`
- Docker Compose 默认通过 `./data:/app/data` 挂载数据目录，因此容器内对应路径为 `/app/data/book`
- 如果自定义书籍目录，要同步调整 Docker volume 挂载；仅修改 `.env` 而不挂载目录，容器内仍会扫描不到文件

### 支持格式

- `epub`
- `pdf`

### OCR 说明

当 PDF 文本层不足时，系统会自动切换 OCR。

Docker 镜像已包含以下依赖：

- `poppler-utils`
- `tesseract-ocr`
- `tesseract-ocr-chi-sim`

### 使用方式

#### 前端页面

- 菜单：`书籍学习`
- 路由：`/book-learning`

#### 后端接口

- `GET /api/materials/books/scan`
- `POST /api/materials/books/import`
- `GET /api/materials/books/tasks/{task_id}`
- `GET /api/materials/books/sources`

#### CLI

默认读取 `.env` 中的 `BOOKS_DIR`：

```bash
cd backend
python -m app.jobs.import_books
```

全量重建：

```bash
cd backend
python -m app.jobs.import_books --rebuild
```

显式指定目录时，`--dir` 同样按项目根目录 `writer/` 解析，而不是按 `backend/` 当前目录解析：

```bash
cd backend
python -m app.jobs.import_books --dir ./data/book
```

指定文件：

```bash
cd backend
python -m app.jobs.import_books --selected-file 示例.pdf --selected-file 分类/示例.epub
```

## 写作与导出

### 写作流程

- 第一轮对话会优先给出写作引导
- 后续对话会检索素材、书籍知识、书籍风格规则
- 流式接口会返回工作流步骤事件
- 生成成功后保存助手消息和账户级记忆笔记

### 导出能力

- 支持会话导出 DOCX
- 支持编辑器内容导出 DOCX
- 导出记录可在导出历史页面查询和下载

## 关键环境变量

以下变量最常用，完整示例见 [`.env.example`](./.env.example)：

说明：

- `OPENVIKING_CONFIG_FILE`、`OPENVIKING_SHARED_BACKEND_DIR`、`UPLOAD_DIR`、`EXPORT_DIR`、`BOOKS_DIR` 若使用相对路径，会统一按项目根目录 `writer/` 解析
- `OPENVIKING_SHARED_OV_DIR` 是 OpenViking 容器内路径，不参与项目根路径归一化
- 如果 `.env` 同时给本地和 Docker Compose 使用，建议保留 `./data/...` 这类仓库相对路径

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

DATABASE_URL=sqlite:///./data/writer.db

OPENVIKING_SERVER_URL=http://openviking:1933
OPENVIKING_ROOT_API_KEY=
OPENVIKING_CONFIG_FILE=./data/openviking/ov.conf
OPENVIKING_SHARED_BACKEND_DIR=./data/openviking/workspace/_staging
OPENVIKING_SHARED_OV_DIR=/app/data/_staging

UPLOAD_DIR=./data/uploads
EXPORT_DIR=./data/exports
BOOKS_DIR=./data/book

SECRET_KEY=
ACCESS_TOKEN_EXPIRE_MINUTES=1440

INITIAL_ADMIN_USERNAME=
INITIAL_ADMIN_PASSWORD=
INITIAL_ADMIN_DISPLAY_NAME=admin
INITIAL_ADMIN_DEPARTMENT=admin

BOOK_AUGMENTATION_ENABLED=true
BOOK_CHUNK_SIZE=800
BOOK_CHUNK_OVERLAP=120
BOOK_RETRIEVAL_TOP_K=4
BOOK_STYLE_TOP_K=6
PDF_OCR_ENABLED=true
PDF_OCR_LANG=chi_sim+eng
PDF_OCR_DPI=300
PDF_OCR_MAX_PAGES=500
```

## 测试与校验

### 后端

```bash
python -m unittest discover -s backend/tests -v
python -m py_compile backend/app/main.py
```

### 前端

```bash
cd frontend
pnpm -s exec vue-tsc --noEmit
pnpm -s run test:permissions
pnpm run --config.verify-deps-before-run=false build
```

### 编码校验

全仓文本文件必须为 UTF-8 无 BOM：

```bash
python scripts/check_text_encoding.py --all
```

自动去除 BOM：

```bash
python scripts/check_text_encoding.py --all --fix-bom
```

PowerShell 环境建议先加载：

```powershell
. .\scripts\powershell_utf8.ps1
```

验证 PowerShell 中文和无 BOM 写入：

```powershell
& .\scripts\verify_powershell_encoding.ps1
```

## 常见问题

### 1. 后端启动时报错 `SECRET_KEY must be overridden`

原因：

- `.env` 仍在使用默认密钥

处理：

- 修改 `.env` 中的 `SECRET_KEY`
- 修改 `.env` 中的 `OPENVIKING_ROOT_API_KEY`
- 确保 `data/openviking/ov.conf` 中的 `root_api_key` 同步更新

### 2. OpenViking 启动时报 JSON BOM 错误

原因：

- `ov.conf` 含 BOM

处理：

```bash
python scripts/check_text_encoding.py --all --fix-bom
```

如果只修复单文件，请确保保存为 UTF-8 无 BOM。

### 3. 书籍学习页面明明有 `data/book`，扫描结果却是 `0`

检查项：

- `.env` 中的 `BOOKS_DIR` 是否仍是仓库相对路径，例如 `./data/book`
- 如果同一份 `.env` 同时用于本地和 Docker，不要直接写宿主机绝对路径，除非容器也有对应 volume 挂载
- `docker-compose.yml` 是否仍保留 `./data:/app/data`，保证容器内能看到 `/app/data/book`
- 自定义目录时，是否同时修改了容器挂载和导入命令中的 `--dir`

### 4. PDF OCR 不生效

检查项：

- `PDF_OCR_ENABLED=true`
- 容器内已安装 `tesseract-ocr`
- 容器内已安装 `poppler-utils`
- `PDF_OCR_LANG` 与实际语言匹配

### 5. 注册失败，提示邀请码无效或已过期

检查项：

- 邀请码是否由管理员在正确账户下创建
- 邀请码是否已被使用
- 邀请码所属账户是否已禁用

### 6. 书籍学习任务中断

说明：

- 服务重启后，运行中的书籍导入任务会被标记为 `interrupted`
- 可在书籍学习页面重新发起任务

## 架构约束

- 数据库结构以 Alembic revision 为真源；启动时自动执行迁移，旧库仅在无 `alembic_version` 时走一次兼容补齐并 `stamp head`
- API 对外时间统一为上海时间
- 内部数据库时间统一以 UTC 存储
- 文本文件统一使用 UTF-8 无 BOM
- `data/openviking/ov.conf` 不应提交到 Git

## License

本项目使用 [Apache-2.0](./LICENSE) 协议。
