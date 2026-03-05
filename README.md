# 公文写作助手

一个面向公文场景的智能写作系统，集成多轮对话、素材检索、书籍学习、风格学习与文档导出，支持账号隔离与角色权限控制。

## 功能概览

- 多轮写作对话（SSE 流式输出，工作流步骤可视化）
- 素材管理（上传解析、分类、批量操作、语义检索）
- 书籍学习（EPUB/PDF 导入、OCR、规则提炼、知识检索）
- 风格学习（统计特征 + 术语/关键词 + LLM 风格结构化分析）
- 文档导出（GB/T 9704-2012 格式的 docx）
- 账户隔离与权限控制（RABC：账户 + 角色 + 权限）

## 技术栈

- 后端：FastAPI + SQLAlchemy + LangChain + Python
- 前端：Vue 3 + TypeScript + Vite + Element Plus + Pinia（基于 Fantastic-admin）
- 向量与记忆：OpenViking
- 部署：Docker Compose

## 项目结构

```
writer/
  .env.example
  deploy.sh
  docker-compose.yml
  backend/
    Dockerfile
    requirements.txt
    app/
      main.py
      config.py
      database.py
      auth.py
      api/
      models/
      services/
      prompts/
  frontend/
    Dockerfile
    nginx.conf
    src/
      views/
      api/
      store/
      types/
  data/
    openviking/
      ov.conf            # 本地配置（已加入 .gitignore）
      ov.conf.example    # 配置示例（可提交）
      workspace/
    book/
    uploads/
    exports/
```

## 快速开始（Docker）

### 1) 准备配置

- 复制环境变量：

```bash
cp .env.example .env
```

- 复制 OpenViking 配置示例：

```bash
cp data/openviking/ov.conf.example data/openviking/ov.conf
```

- 修改 `.env` 和 `data/openviking/ov.conf` 中的密钥与模型配置：
  - `SECRET_KEY` 必须替换为随机值
  - `OPENVIKING_ROOT_API_KEY` 必须替换
  - OpenViking 配置里的 `root_api_key` 必须与上面一致

### 2) 一键部署

```bash
bash deploy.sh
```

访问：
- 前端：`http://localhost`
- 后端：`http://localhost:8000/docs`

## 账号与权限

- 注册必须使用一次性邀请码（由管理员创建）
- 管理员页面：
  - `/admin/overview`
  - `/admin/accounts`
  - `/admin/roles`
- 初始管理员可通过环境变量注入：

```
INITIAL_ADMIN_USERNAME=
INITIAL_ADMIN_PASSWORD=
INITIAL_ADMIN_DISPLAY_NAME=admin
INITIAL_ADMIN_DEPARTMENT=admin
```

## 书籍学习

- 书籍目录：`data/book`
- 支持：EPUB / PDF（扫描版 PDF 自动 OCR）
- 学习结果：
  - `book_sources`：来源与导入状态
  - `book_style_rules`：写作规则
- 写作时自动检索书籍知识并融合风格规则

## 风格学习

- 素材上传后自动分析：
  - 统计特征（句长、段长、句/段数量）
  - 关键词/术语（Jieba + LLM 总结）
  - LLM 风格结构化分析（开头/结尾/结构/句式/过渡词等）
  - 数据要素（类型/用法/主题归属）

## 上下文与记忆

- 会话上下文：最近 20 条消息，以 Chat API messages 方式传入
- 长期记忆：按账户写入 OpenViking memory 命名空间

## 环境变量

关键配置见 `.env.example`：

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_MODEL`
- `OPENAI_EMBEDDING_MODEL`
- `OPENVIKING_SERVER_URL`
- `OPENVIKING_ROOT_API_KEY`
- `SECRET_KEY`
- 书籍学习与 OCR 相关配置

## 常见问题

## License

Apache-2.0


### 1) 报错：SECRET_KEY must be overridden
- 说明：生产安全校验，必须替换默认密钥。
- 处理：修改 `.env` 中 `SECRET_KEY` 与 `OPENVIKING_ROOT_API_KEY`。

### 2) OpenViking 认证失败
- 确认 `.env` 中 `OPENVIKING_ROOT_API_KEY` 与 `data/openviking/ov.conf` 中 `root_api_key` 一致。

## 本地开发

后端：
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

前端：
```bash
cd frontend
pnpm install
pnpm dev
```

前端默认 `http://localhost:9000`，已配置 `/api` 代理。

## API 概览

- `/api/auth` 用户认证
- `/api/accounts` 账户/角色/邀请码管理
- `/api/chat` 写作对话（含 SSE）
- `/api/materials` 素材管理 + 书籍学习接口
- `/api/documents` 文档导出与历史
- `/api/preferences` 用户偏好

## 说明

- `data/openviking/ov.conf` 不应提交到 Git（已加入 `.gitignore`）。
- 系统不使用数据库迁移工具，启动时通过 `schema_bootstrap` 进行增量补齐。
