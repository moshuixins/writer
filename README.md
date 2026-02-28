# 公文写作助手

交管支队智能公文写作平台，基于 AI 多轮对话生成标准公文，支持素材语义检索、风格学习、隐式记忆、流式输出。

## 技术栈

- 后端：FastAPI + SQLAlchemy + LangChain + SiliconFlow (DeepSeek-V3.2)
- 前端：Vue 3 + TypeScript + Element Plus + Pinia
- 向量检索与记忆：OpenViking（字节跳动开源 AI Agent 上下文数据库）
- 文档生成：python-docx（GB/T 9704-2012 标准格式）
- 部署：Docker Compose

## 项目结构

```
writer/
├── .env.example                  # 环境变量模板
├── docker-compose.yml            # Docker 编排（backend + frontend + openviking）
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py               # FastAPI 入口、CORS、限流中间件
│       ├── config.py             # 配置管理（路径自动计算）
│       ├── database.py           # SQLAlchemy 连接
│       ├── auth.py               # JWT 认证
│       ├── api/                  # API 路由
│       │   ├── auth.py           # 注册 / 登录
│       │   ├── materials.py      # 素材管理（含批量操作）
│       │   ├── chat.py           # 写作对话（含 SSE 流式）
│       │   ├── documents.py      # 文档导出 / 历史
│       │   └── preferences.py    # 用户偏好
│       ├── services/             # 业务逻辑
│       │   ├── writing_service.py    # 写作引导与内容生成
│       │   ├── material_service.py   # 素材解析、分类、摘要
│       │   ├── style_analyzer.py     # 风格学习与特征提取
│       │   ├── docx_generator.py     # 公文 docx 生成
│       │   ├── context_bridge.py     # OpenViking 适配层
│       │   ├── memory_service.py     # 用户显式偏好管理
│       │   └── llm_service.py        # LLM 调用封装（含流式）
│       ├── models/               # 数据库模型（含复合索引）
│       └── prompts/              # LLM Prompt 模板
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf                # Nginx 反向代理配置
│   └── src/
│       ├── views/
│       │   ├── Login.vue             # 登录页
│       │   ├── WritingChat.vue       # 写作对话页（SSE 打字机效果）
│       │   ├── MaterialManager.vue   # 素材管理页
│       │   ├── ExportHistory.vue     # 导出历史页
│       │   └── Settings.vue          # 偏好设置页
│       ├── types/index.ts        # 共享类型定义
│       ├── api/index.ts          # Axios 客户端
│       └── stores/auth.ts        # Pinia 认证状态
└── data/
    ├── openviking/ov.conf        # OpenViking 配置
    ├── uploads/                  # 上传文件存储
    └── exports/                  # 导出文件存储
```

## 架构设计

```
┌─────────────────────────────────────────────────────┐
│           Frontend (Vue 3 + Element Plus)            │
│  登录  │  写作对话  │  素材管理  │  导出历史  │  设置  │
└───────────────────┬─────────────────────────────────┘
                    │ REST API + SSE
┌───────────────────▼─────────────────────────────────┐
│               FastAPI Backend                        │
│                                                      │
│  认证: JWT (注册/登录/鉴权)                           │
│  安全: CORS 白名单 + IP 限流 (60 req/min)            │
│                                                      │
│  API层:                                              │
│    /api/auth        用户认证                          │
│    /api/chat        写作对话 (含 SSE 流式)            │
│    /api/materials   素材管理 (含批量操作)              │
│    /api/documents   文档导出与历史                     │
│    /api/preferences 用户偏好                          │
│                                                      │
│  服务层:                                              │
│    WritingService   写作引导与内容生成                 │
│    MaterialService  素材上传、解析、分类/摘要          │
│    StyleAnalyzer    风格学习与特征提取                 │
│    DocxGenerator    GB/T 9704 公文格式生成             │
│    ContextBridge    OpenViking 适配层                  │
│    LLMService       LLM 调用封装 (含流式)             │
│                                                      │
│  AI层: LangChain + SiliconFlow (DeepSeek-V3.2)      │
└──────┬──────────────┬──────────────┬─────────────────┘
    SQLite        OpenViking        文件系统
  (结构化数据)  (向量+记忆+会话)   (原始文件)
```

## 核心功能

### 用户认证
- JWT Token 认证，所有 API 均需登录
- 注册 / 登录，密码 bcrypt 加密
- 数据按用户隔离，含所有权校验

### 写作对话
- 多轮对话式写作：分析需求 → 列出所需材料 → 生成公文
- SSE 流式输出，AI 回复逐字显示（打字机效果）
- RAG 检索 top 5 相关参考范文辅助生成
- OpenViking 自动提取写作习惯（隐式记忆）
- 消息发送失败自动回滚，DOMPurify 防 XSS

### 素材管理
- 上传 docx/pdf/txt 文件，自动提取文本
- LLM 自动分类（通知、报告、请示、批复、函、纪要等）
- LLM 自动生成摘要，jieba 提取关键词
- 支持批量删除、批量分类
- OpenViking 层级检索（L0摘要 → L1概览 → L2全文）
- 分页、搜索防抖、上传进度显示

### 风格学习
- 分析上传素材的写作风格特征（用词、句式、结构）
- 按公文类型积累风格指南
- 生成时自动应用对应类型的风格规范

### 文档导出
- 生成符合 GB/T 9704-2012 标准的 docx 文件
- 支持标题、正文、落款等公文要素格式化
- 导出历史记录，支持重新下载

### 记忆系统
- 显式偏好：用户手动设置的写作偏好（SQLAlchemy 存储）
- 隐式记忆：OpenViking 自动从对话中提取用户习惯、偏好等
- 记忆去重与热度衰减，自动管理生命周期

### 安全机制
- JWT 认证，所有接口鉴权
- CORS 白名单（仅允许配置的前端域名）
- IP 级滑动窗口限流（默认 60 次/分钟）
- 数据所有权校验（403 拒绝越权访问）
- DOMPurify 前端 XSS 防护

## 快速开始

### Docker 部署（推荐）

1. 复制环境变量模板并填写：

```bash
cp .env.example .env
# 编辑 .env，填入你的 API Key 和 Secret Key
```

2. 启动所有服务：

```bash
docker compose up -d
```

启动顺序：OpenViking（等待健康检查通过）→ Backend → Frontend

3. 访问 `http://localhost`，注册账号即可使用。

### 本地开发

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

前端开发服务器默认 `http://localhost:3000`，已配置代理转发 `/api` 到后端。

### 环境变量

参考 `.env.example`：

| 变量 | 说明 | 示例 |
|------|------|------|
| `OPENAI_API_KEY` | LLM API 密钥 | `sk-xxx` |
| `OPENAI_BASE_URL` | API 地址 | `https://api.siliconflow.cn/v1` |
| `OPENAI_MODEL` | 对话模型 | `deepseek-ai/DeepSeek-V3.2` |
| `OPENAI_EMBEDDING_MODEL` | 向量模型 | `Qwen/Qwen3-Embedding-8B` |
| `OPENVIKING_SERVER_URL` | OV 地址（Docker: `http://openviking:1933`） | `http://127.0.0.1:1933` |
| `SECRET_KEY` | JWT 签名密钥 | 随机字符串 |

## API 接口

后端启动后可访问 `http://localhost:8000/docs` 查看 Swagger 文档。

### 认证 `/api/auth`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/register` | 用户注册 |
| POST | `/login` | 用户登录，返回 JWT Token |

### 写作对话 `/api/chat`（需认证）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/sessions` | 创建写作会话 |
| GET | `/sessions` | 获取会话列表 |
| GET | `/sessions/{id}/messages` | 获取会话消息历史 |
| POST | `/send` | 发送消息，同步返回 AI 回复 |
| POST | `/send-stream` | 发送消息，SSE 流式返回 AI 回复 |
| DELETE | `/sessions/{id}` | 删除会话 |
| POST | `/sessions/{id}/finish` | 结束会话（触发记忆提取） |
| POST | `/review` | AI 审核公文内容 |

### 素材管理 `/api/materials`（需认证）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/upload` | 上传素材文件（docx/pdf/txt） |
| GET | `/` | 获取素材列表，支持 `doc_type`、`keyword` 筛选 |
| GET | `/search?query=` | 语义搜索素材 |
| GET | `/{id}` | 获取素材详情 |
| DELETE | `/{id}` | 删除素材 |
| POST | `/batch-delete` | 批量删除素材 |
| POST | `/batch-classify` | 批量重新分类 |

### 文档管理 `/api/documents`（需认证）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/export` | 导出公文为 docx（GB/T 9704 格式） |
| GET | `/history` | 导出历史列表 |
| GET | `/history/{id}/download` | 重新下载历史文档 |

### 用户偏好 `/api/preferences`（需认证）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 获取用户所有偏好 |
| PUT | `/` | 设置单个偏好 |
| PUT | `/batch` | 批量设置偏好 |

## OpenViking 整合说明

通过 `ContextBridge` 适配层（HTTP 客户端）接入 OpenViking，无需 C++ 编译依赖。

**由 OpenViking 负责：**
- 向量检索：层级递归检索（L0摘要 → L1概览 → L2全文）
- 隐式记忆：会话结束自动提取用户写作习惯等
- 会话上下文：分层加载，按需使用 token

**保留自有实现：**
- 公文分类/摘要、风格学习、docx 生成、显式偏好

**优雅降级：** OpenViking 未启动时系统正常运行，语义检索和隐式记忆功能不可用，写作生成使用"暂无参考范文"兜底。
