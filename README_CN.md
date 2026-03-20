# VibeReading
中文 | [English](./README.md)
> Stop Reading books by yourself, vibe reading now. 

VibeReading 是一个面向文档深度阅读的 AI 助手：上传文档后，系统会构建知识图谱索引，并通过流式对话帮助你定位、解释和串联文档内容。

项目当前支持文本与 PDF 场景，包含多项目管理、对话历史、文档内跳转和 PDF 精准定位。

## 1. 核心能力

- 文档上传与索引
  - 支持 `.txt`、`.md`、`.pdf`
  - 文本文件直接进入 GraphRAG 索引流程
  - PDF 文件先经 MinerU 解析为 Markdown，再建立索引

- 知识图谱检索与问答
  - 使用 `nano-graphrag` 构建实体关系图
  - Agent 可执行本地/全局检索、实体详情、邻居探索等工具调用
  - 聊天接口采用 SSE 流式输出，前端实时渲染

- 文档阅读联动
  - 支持点击 `doc://scroll?line=N` 形式的引用链接定位文档
  - PDF 模式下可将 Markdown 行号映射回 PDF 页码/页内位置
  - 内置 PDF.js 阅读器，支持缩放、翻页、页码跳转、文本选择

- 项目管理
  - 每次索引结果按项目持久化到 `projects/<slug>/`
  - 支持列出历史项目、激活项目、删除非当前项目
  - 支持从旧目录 `nano_graphrag_cache/` 一次性迁移到新结构

- 对话体验
  - 支持多轮上下文（history）
  - 本地保存会话快照（按项目区分）
  - 当 Agent 达到递归/步数上限时，前端可一键继续

## 2. 技术栈

- 后端
  - FastAPI
  - LangChain + LangGraph ReAct Agent
  - `nano-graphrag`（GraphRAG）
  - OpenAI 兼容接口（可对接通义千问兼容端点）

- 前端
  - 原生 HTML/CSS/JavaScript
  - marked（Markdown 渲染）
  - KaTeX（数学公式渲染）
  - PDF.js（PDF 渲染与交互）

## 3. 项目结构（关键目录）

```text
VibeReading/
├── backend/
│   ├── app.py                     # FastAPI 入口，挂载 API 与前端静态资源
│   ├── config.py                  # .env 配置读取
│   ├── api/
│   │   ├── schemas.py             # Pydantic 模型
│   │   └── routes/
│   │       ├── files.py           # 上传/状态/内容/原文件接口
│   │       ├── chat.py            # SSE 流式聊天接口
│   │       └── projects.py        # 项目列表/激活/删除
│   └── core/
│       ├── agent.py               # Agent 构建与系统提示词
│       ├── rag_tools.py           # Agent 工具集合（RAG + 文档导航）
│       ├── mineru.py              # MinerU PDF 解析客户端
│       └── state.py               # 全局状态
├── frontend/
│   ├── index.html                 # 页面骨架
│   ├── css/styles.css             # 样式
│   └── js/
│       ├── app.js                 # 上传、状态轮询、项目管理、主题切换
│       ├── viewer.js              # 文档/PDF 阅读器
│       └── chat.js                # 聊天流式渲染与历史管理
├── NanoRAG.py                     # GraphRAG 封装（索引、查询、图谱导出）
├── projects/                      # 项目化索引数据目录
├── uploads/                       # 上传文件目录
├── pyproject.toml                 # Python 项目依赖
└── README.md                      # 英文说明
```

## 4. 环境准备

- Python 3.11+
- 建议使用 `uv` 管理依赖与运行
- 可用的 LLM/Embedding API Key
- 若需要解析 PDF，需准备 MinerU Token

安装依赖：

```bash
uv sync
```

## 5. 配置 `.env`

复制模板：

```bash
cp .env.example .env
```

核心变量说明：

- NanoRAG（必需）
  - `NANO_GRAPHRAG_API_KEY`：必填
  - `NANO_GRAPHRAG_BASE_URL`：可选，默认 DashScope 兼容地址
  - `NANO_GRAPHRAG_BEST_MODEL`：可选
  - `NANO_GRAPHRAG_CHEAP_MODEL`：可选
  - `NANO_GRAPHRAG_EMBEDDING_MODEL`：可选

- Agent（可选，不填时回退到 NanoRAG 相关配置）
  - `AGENT_API_KEY`
  - `AGENT_BASE_URL`
  - `AGENT_MODEL`

- MinerU（仅 PDF 上传时需要,从https://mineru.net/apiManage/docs 获取）
  - `MINERU_API_KEY`

- 存储路径（可选）
  - `PROJECTS_DIR`：项目目录，默认 `projects`
  - `UPLOAD_DIR`：上传目录，默认 `uploads`

说明：当前代码实际使用 `PROJECTS_DIR` 与 `UPLOAD_DIR`。如果你在 `.env.example` 中看到 `NANO_WORKING_DIR`，它属于旧字段，不是当前主流程配置项。

## 6. 启动方式

```bash
uv run uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

浏览器访问：

```text
http://localhost:8000
```

## 7. 使用流程

1. 上传文档（`.txt` / `.md` / `.pdf`）
2. 等待状态从 `indexing` 变为 `ready`
3. 在右侧聊天框提问
4. 点击回答中的文档链接（`doc://scroll?line=N`）进行定位
5. 可从顶部 `Projects` 下拉切换历史项目

补充：

- PDF 文档会先转成 Markdown 供索引和语义定位使用，再映射回 PDF 页内位置。
- 对话历史按项目保存在浏览器本地存储。

## 8. 主要后端接口

- 文件相关
  - `POST /api/files/upload`：上传并触发后台索引
  - `GET /api/files/status`：获取索引状态与文件类型
  - `GET /api/files/content`：获取当前文档文本内容（Markdown/文本）
  - `GET /api/files/raw`：获取原始文件（PDF 内嵌预览使用）

- 聊天
  - `POST /api/chat/stream`：SSE 流式响应

- 项目
  - `GET /api/projects`：列出项目
  - `POST /api/projects/{slug}/activate`：激活项目
  - `DELETE /api/projects/{slug}`：删除项目（不能删除当前激活项目）

## 9. 数据目录说明

- `uploads/`
  - 原始上传文件

- `projects/<slug>/`
  - `session_meta.json`：项目元信息
  - `graph_chunk_entity_relation.graphml`：图谱结构
  - `kv_store_*.json`、`vdb_entities.json`：GraphRAG 索引数据
  - `full.md`：PDF 转换后的 Markdown（仅 PDF 项目）
  - `page_map.json` / `paragraph_map.json`：Markdown 行到 PDF 定位映射（仅 PDF 项目）
  - `original.pdf`（或同名后缀）：项目内保存的原 PDF 副本
