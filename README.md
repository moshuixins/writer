# 公文写作助手

基于 AI 的公文写作辅助系统，支持素材管理、智能分类摘要、风格学习、多轮对话写作、标准公文格式导出。

## 技术栈

- 后端：FastAPI + SQLAlchemy + LangChain + OpenAI API
- 前端：Vue 3 + TypeScript + Element Plus + Pinia
- 向量检索与记忆：OpenViking（字节跳动开源 AI Agent 上下文数据库）
- 文档生成：python-docx（GB/T 9704-2012 标准格式）
- 中文分词：jieba

## 项目结构

```
writer/
├── .env                          # 环境变量配置
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── main.py               # FastAPI 入口
│       ├── config.py             # 配置管理
│       ├── database.py           # 数据库连接
│       ├── api/                  # API 路由
│       │   ├── materials.py      # 素材管理
│       │   ├── chat.py           # 写作对话
│       │   ├── documents.py      # 文档导出
│       │   └── preferences.py    # 用户偏好
│       ├── services/             # 业务逻辑
│       │   ├── material_service.py   # 素材解析、分类、摘要
│       │   ├── writing_service.py    # 写作引导与内容生成
│       │   ├── style_analyzer.py     # 风格学习与特征提取
│       │   ├── docx_generator.py     # 公文 docx 生成
│       │   ├── context_bridge.py     # OpenViking 适配层
│       │   ├── memory_service.py     # 用户显式偏好管理
│       │   └── llm_service.py        # LLM 调用封装
│       ├── models/               # 数据库模型
│       ├── prompts/              # LLM Prompt 模板
│       └── templates/
├── frontend/
│   └── src/
│       ├── views/
│       │   ├── MaterialManager.vue   # 素材管理页
│       │   ├── WritingChat.vue       # 写作对话页
│       │   └── Settings.vue          # 偏好设置页
│       ├── api/index.ts          # API 客户端
│       └── router/index.ts
└── data/
    ├── openviking/ov.conf        # OpenViking 配置
    ├── uploads/                  # 上传文件存储
    └── exports/                  # 导出文件存储
```

## 架构设计

```
┌─────────────────────────────────────────────────┐
│          Frontend (Vue 3 + Element Plus)         │
│  素材管理 │ 写作对话 │ 文档预览 │ 偏好设置       │
└──────────────────┬──────────────────────────────┘
                   │ REST API
┌──────────────────▼──────────────────────────────┐
│              FastAPI Backend                      │
│                                                  │
│  API层: /materials /chat /documents /preferences │
│                                                  │
│  服务层:                                         │
│    MaterialService  - 素材上传、解析、分类/摘要   │
│    WritingService   - 写作引导与内容生成          │
│    StyleAnalyzer    - 风格学习与特征提取          │
│    DocxGenerator    - GB/T 9704 公文格式生成      │
│    MemoryService    - 用户显式偏好管理            │
│    ContextBridge    - OpenViking 适配层           │
│                                                  │
│  AI层: LangChain + OpenAI (GPT-4o)              │
└───────┬──────────────┬──────────────┬────────────┘
   SQLite/PG      OpenViking        文件系统
  (结构化数据)  (向量+记忆+会话)   (原始文件)
```

## 核心功能

### 素材管理
- 上传 docx/pdf/txt 文件，自动提取文本内容
- LLM 自动分类（通知、报告、请示、批复、函、纪要等）
- LLM 自动生成摘要
- jieba 提取关键词
- OpenViking 层级检索（L0摘要 → L1概览 → L2全文），精度优于扁平 RAG

### 写作对话
- 多轮对话式写作：先分析需求 → 告知所需材料 → 生成公文
- 首条消息自动触发写作引导，分析用户需求并列出所需素材清单
- RAG 检索相关参考范文辅助生成
- OpenViking 自动提取写作习惯（隐式记忆），结合用户显式偏好

### 风格学习
- 分析上传素材的写作风格特征（用词、句式、结构）
- 按公文类型积累风格指南
- 生成时自动应用对应类型的风格规范

### 文档导出
- 生成符合 GB/T 9704-2012 标准的 docx 文件
- 支持标题、正文、落款等公文要素格式化
- 中文字体：方正小标宋（标题）、仿宋_GB2312（正文）

### 记忆系统
- 显式偏好：用户手动设置的写作偏好（MemoryService，SQLAlchemy 存储）
- 隐式记忆：OpenViking 自动从对话中提取用户习惯、偏好、实体等 6 类记忆
- 记忆去重与热度衰减，自动管理生命周期

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- OpenAI API Key（GPT-4o + text-embedding-3-small）
- OpenViking Server（可选，不启动时系统仍可正常运行）

### 1. 配置环境变量

编辑项目根目录 `.env` 文件：

```bash
OPENAI_API_KEY=sk-your-actual-key
OPENAI_BASE_URL=https://api.openai.com/v1    # 或兼容 API 地址
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
SECRET_KEY=your-random-secret-key
```

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 4. 启动 OpenViking（可选）

OpenViking 提供向量检索和自动记忆提取能力。不启动时系统仍可正常使用，但语义搜索和隐式记忆功能不可用。

```bash
cd OpenViking-main
# 需要 Go 编译器 + CMake，详见 OpenViking 文档
pip install -e .
openviking-server --config ../data/openviking/ov.conf
```

服务默认监听 `http://127.0.0.1:1933`。

## API 接口

后端启动后可访问 `http://localhost:8000/docs` 查看 Swagger 文档。

### 素材管理 `/api/materials`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/upload` | 上传素材文件（docx/pdf/txt），自动分类摘要 |
| GET | `/` | 获取素材列表，支持 `doc_type`、`keyword` 筛选 |
| GET | `/search?query=` | 语义搜索素材（OpenViking 层级检索） |
| GET | `/{id}` | 获取素材详情（含全文） |
| DELETE | `/{id}` | 删除素材 |

### 写作对话 `/api/chat`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/sessions` | 创建写作会话 |
| GET | `/sessions` | 获取会话列表 |
| GET | `/sessions/{id}/messages` | 获取会话消息历史 |
| POST | `/send` | 发送消息并获取 AI 回复 |

### 文档管理 `/api/documents`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/export` | 导出公文为 docx 文件（GB/T 9704 格式） |

### 用户偏好 `/api/preferences`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 获取用户所有偏好 |
| PUT | `/` | 设置用户偏好（key-value） |

### 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 服务健康检查 |

## OpenViking 整合说明

本项目通过 `ContextBridge` 适配层（HTTP 客户端模式）接入 OpenViking，避免了 OpenViking 的重量级 C++ 编译依赖。

### 整合范围

**由 OpenViking 负责：**
- 向量检索：替代原 ChromaDB，使用层级递归检索（Hierarchical Retrieval）
- 隐式记忆：会话结束自动提取用户写作习惯、偏好等 6 类记忆
- 会话上下文：L0/L1/L2 分层加载，按需使用 token

**保留自有实现：**
- 公文分类/摘要：领域特色功能，OpenViking 不具备
- 风格学习：StyleAnalyzer 是核心差异化能力
- docx 生成：GB/T 9704 公文格式，OpenViking 无此功能
- 显式偏好：简单 KV 存储，SQLAlchemy 更直接

### 优雅降级

所有 OpenViking 调用均包裹在 `try/except` 中。当 OpenViking 服务未启动时：
- 素材上传正常工作，仅跳过向量入库
- 写作生成使用 "暂无参考范文" 兜底
- 隐式记忆为空，仅使用显式偏好
- 系统不会报错或中断
