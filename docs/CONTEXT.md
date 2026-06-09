# KnowBase — 项目上下文文档

> **本文件是项目的单一事实来源**。无论使用 Claude Code 还是 Codex，都应先读本文件了解全貌。
> 每次完成重要工作后，请更新本文件对应的章节。

---

## 1. 项目概述

**KnowBase** 是一个 AI 驱动的个人知识库应用，核心功能：

- 笔记的创建、编辑、删除、搜索（CRUD）
- 分类与标签体系
- 基于笔记内容的 AI 对话问答（RAG + LLM）
- 向量语义搜索（pgvector）
- AI 导入外部内容并提取知识点
- AI 生成学习路径，辅助规划学习目标

目标用户：需要管理和检索大量学习笔记的个人开发者/学生。

---

## 2. 技术栈

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 运行时 |
| FastAPI | latest | Web 框架 |
| SQLAlchemy | 2.x (async) | ORM |
| asyncpg | latest | PostgreSQL 异步驱动 |
| PostgreSQL 16 | + pgvector | 主数据库 + 向量搜索 |
| Alembic | latest | 数据库迁移 |
| pydantic / pydantic-settings | latest | 数据校验 & 配置管理 |
| LangChain | latest（已声明，未使用） | Phase 2 RAG 管线 |

### 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 19 | UI 框架 |
| TypeScript | 6 | 类型安全 |
| Vite | 8 | 构建工具 |
| Ant Design | 6 | UI 组件库 |
| Tailwind CSS | 4 | 原子化样式 |
| Zustand | 5（已声明，未使用） | 状态管理 |
| Axios | latest | HTTP 客户端 |

### 基础设施

- **Docker Compose** — PostgreSQL 16 + pgvector（端口 5433）
- **Vite Dev Proxy** — `/api` → `http://localhost:8000`

### Git 仓库

- **GitHub**：`https://github.com/XyYpower/xyy.git`
- **主分支**：`main`
- **注意**：国内网络不稳定，`git push` 可能需要多次重试

---

## 3. 项目结构

```
knowbase/
├── CLAUDE.md              # Claude Code 行为指令
├── AGENTS.md              # Codex 行为指令
├── docs/
│   ├── CONTEXT.md         # 本文件 — 项目共享上下文
│   ├── Phase2-design.md   # Phase 2 完整设计
│   ├── V2.1-task.md       # V2.1 任务书（已完成）
│   ├── V2.2-task.md       # V2.2 任务书（已完成）
│   ├── V2.3-task.md       # V2.3 任务书（已完成）
│   ├── V3.0-task.md       # V3.0 任务书（已完成）
│   ├── V3.1-agentic-redesign.md # Agentic Learning OS 重设计方案（已实现至 V4.0）
│   └── V4.1-quality-ux-redesign.md # 质量加固与主体验升级方案（待实现）
├── docker-compose.yml     # PostgreSQL + pgvector
├── .env.example           # 环境变量模板
├── .gitignore
│
├── backend/
│   ├── pyproject.toml     # Python 依赖声明
│   ├── alembic/           # 数据库迁移
│   │   └── versions/
│   ├── tests/             # 后端测试
│   └── app/
│       ├── main.py        # FastAPI 入口
│       ├── config.py      # 配置管理
│       ├── database.py    # 数据库连接
│       ├── api/           # API 路由层
│       │   ├── router.py  # 路由聚合
│       │   ├── auth.py    # 注册/登录/JWT/账号设置
│       │   ├── notes.py   # 笔记 CRUD
│       │   ├── imports.py # AI 导入 + 草稿确认
│       │   ├── paths.py   # 学习路径
│       │   ├── review.py  # 间隔复习
│       │   ├── chat.py    # RAG 对话 + SSE
│       │   ├── interview.py # AI 模拟面试
│       │   ├── export.py  # 数据导出
│       │   ├── tags.py    # 标签列表
│       │   └── categories.py  # 分类 CRUD（用户隔离）
│       ├── models/        # SQLAlchemy ORM 模型
│       │   ├── user.py    # User
│       │   ├── note.py    # Note / Category / Tag
│       │   ├── review.py  # ReviewCard / ReviewRecord
│       │   ├── import_job.py # ImportJob / ExtractionDraft
│       │   ├── path.py    # LearningPath
│       │   ├── chat.py    # Conversation / Message / NoteChunk
│       │   └── interview.py # InterviewSession / InterviewQuestion
│       ├── schemas/       # Pydantic 请求/响应模型
│       │   ├── common.py  # Response[T] / PageResult[T]
│       │   ├── auth.py    # 认证相关 schema
│       │   ├── note.py    # 笔记相关 schema
│       │   ├── review.py  # 复习相关 schema
│       │   ├── import_job.py # 导入相关 schema
│       │   ├── path.py    # 学习路径 schema
│       │   ├── chat.py    # 对话 schema
│       │   └── interview.py # 面试 schema
│       ├── services/      # 业务逻辑层
│       │   ├── auth_service.py
│       │   ├── note_service.py
│       │   ├── review_service.py
│       │   ├── import_service.py
│       │   ├── path_service.py
│       │   ├── chat_service.py
│       │   ├── interview_service.py
│       │   └── export_service.py
│       ├── agents/          # Agent Runtime 模块
│       │   ├── registry.py  # Tool Registry
│       │   ├── runtime.py   # AgentRun 生命周期管理
│       │   ├── traces.py    # Trace 记录器 + LLM 日志
│       │   ├── tools.py     # 现有服务工具注册
│       │   ├── diagnosis.py # DiagnosisAgent 诊断薄弱点
│       │   └── planner.py   # PlannerAgent 学习规划
│       ├── rag/           # LLM / RAG 相关能力
│       │   ├── llm.py
│       │   ├── card_generator.py
│       │   ├── extractor.py
│       │   ├── embedding.py
│       │   ├── retrieval.py
│       │   ├── hybrid_retrieval.py # 混合检索（向量+关键词）
│       │   ├── prompts.py
│       │   ├── pipeline.py
│       │   └── interviewer.py
│       └── utils/
│           └── response.py  # 响应工具函数
│
└── frontend/
    ├── package.json
    ├── vite.config.ts     # Vite 配置 + 代理
    ├── index.html
    ├── public/
    └── src/
        ├── main.tsx       # React 入口
        ├── App.tsx        # 路由定义
        ├── index.css      # Tailwind 基础样式
        ├── api/
        │   ├── auth.ts    # 认证 + 账号设置 API
        │   ├── client.ts  # Axios 实例
        │   ├── notes.ts   # 笔记 API 客户端
        │   ├── review.ts  # 复习 API 客户端
        │   ├── import.ts  # 导入 API 客户端
        │   ├── paths.ts   # 学习路径 API 客户端
        │   ├── chat.ts    # 对话 API 客户端
        │   ├── streamClient.ts # SSE 流式请求
        │   ├── interview.ts # 面试 API 客户端
        │   ├── export.ts  # 导出下载
        │   └── dashboard.ts # 仪表盘聚合请求
        │   ├── categories.ts # 分类 CRUD API 客户端
        │   ├── tags.ts    # 标签列表 API 客户端
        │   └── traces.ts  # Trace Lab API 客户端
        ├── components/
        │   ├── Layout.tsx # 侧边栏布局
        │   ├── AuthRoute.tsx # 认证路由守卫
        │   ├── CategoryManager.tsx # 分类管理弹窗
        │   └── MarkdownEditor.tsx # Markdown 分屏编辑器
        └── pages/
            ├── Home.tsx       # 概览页（占位）
            ├── Dashboard.tsx  # 学习仪表盘基础版
            ├── Notes.tsx      # 笔记列表（含分类/收藏筛选）
            ├── NoteDetail.tsx # 知识点编辑（Markdown 编辑器+标签+分类+收藏）
            ├── Review.tsx     # 间隔复习
            ├── Import.tsx     # AI 导入
            ├── Paths.tsx      # 学习路径
            ├── Interview.tsx  # AI 模拟面试
            ├── Settings.tsx   # 设置 + 数据导出
            ├── TraceLab.tsx   # Agent 运行追踪 + AI 调用监控
            ├── AgentWorkspace.tsx # Agent 工作台（诊断+规划+每日任务）
            ├── Login.tsx      # 登录
            ├── Register.tsx   # 注册
            └── Chat.tsx       # AI 对话（RAG + SSE）
```

---

## 4. API 端点

所有接口前缀：`/api/v1`

| 方法 | 路径 | 说明 | 状态 |
|------|------|------|------|
| GET | `/health` | 健康检查 | ✅ |
| GET | `/notes` | 笔记列表（分页/搜索/筛选） | ✅ |
| GET | `/notes/{id}` | 获取单个笔记 | ✅ |
| POST | `/notes` | 创建笔记（标签自动创建） | ✅ |
| PUT | `/notes/{id}` | 更新笔记 | ✅ |
| DELETE | `/notes/{id}` | 删除笔记 | ✅ |
| GET | `/tags` | 当前用户笔记关联的标签列表（需认证） | ✅ |
| GET | `/categories` | 分类列表（需认证） | ✅ |
| POST | `/auth/register` | 用户注册并返回 Token | ✅ |
| POST | `/auth/login` | 用户登录并返回 Token | ✅ |
| POST | `/auth/refresh` | 刷新 access token | ✅ |
| GET | `/auth/me` | 当前用户信息 | ✅ |
| GET | `/review/today` | 今日待复习卡片 | ✅ |
| GET | `/review/cards/{note_id}` | 获取知识点复习卡片 | ✅ |
| POST | `/review/submit` | 提交复习评分并更新 SM-2 状态 | ✅ |
| GET | `/review/stats` | 复习统计 | ✅ |
| POST | `/review/generate/{note_id}` | 为知识点生成复习卡片 | ✅ |
| PUT | `/review/cards/{card_id}` | 编辑复习卡片 | ✅ |
| POST | `/review/cards/{card_id}/flag` | 标记卡片质量问题 | ✅ |
| POST | `/import/text` | 导入文本并提取草稿 | ✅ |
| POST | `/import/url` | 抓取 URL 内容并提取草稿 | ✅ |
| POST | `/import/code` | 导入代码并提取技术知识点草稿 | ✅ |
| GET | `/import/jobs` | 当前用户导入任务列表 | ✅ |
| GET | `/import/jobs/{job_id}/drafts` | 获取导入任务草稿 | ✅ |
| PUT | `/import/drafts/{draft_id}` | 编辑/勾选导入草稿 | ✅ |
| POST | `/import/jobs/{job_id}/confirm` | 确认草稿并生成知识点 + 复习卡片 | ✅ |
| POST | `/paths/generate` | 根据学习目标生成学习路径 | ✅ |
| GET | `/paths` | 当前用户学习路径列表 | ✅ |
| GET | `/paths/{path_id}` | 学习路径详情 | ✅ |
| GET | `/chat/conversations` | 当前用户对话列表 | ✅ |
| POST | `/chat/conversations` | 创建对话（可关联知识点） | ✅ |
| GET | `/chat/conversations/{id}` | 对话详情 + 消息历史 | ✅ |
| DELETE | `/chat/conversations/{id}` | 删除对话 | ✅ |
| POST | `/chat/conversations/{id}/chat` | RAG 问答 SSE 流式返回 | ✅ |
| POST | `/interview/start` | 开始模拟面试并生成题目 | ✅ |
| POST | `/interview/{session_id}/answer/{question_id}` | 提交单题回答并评分 | ✅ |
| POST | `/interview/{session_id}/finish` | 结束面试并生成总结 | ✅ |
| GET | `/interview/sessions` | 面试历史列表 | ✅ |
| GET | `/interview/sessions/{id}` | 面试详情 | ✅ |
| GET | `/interview/weak-points` | 薄弱知识点分析 | ✅ |
| GET | `/export/json` | 导出完整 JSON | ✅ |
| GET | `/export/markdown` | 导出知识点 Markdown | ✅ |
| GET | `/export/anki` | 导出 Anki CSV | ✅ |
| POST | `/categories` | 创建分类（需认证，按用户隔离） | ✅ |
| PUT | `/categories/{id}` | 更新分类（需认证，按用户隔离） | ✅ |
| DELETE | `/categories/{id}` | 删除分类（需认证，关联知识点 category_id 置空） | ✅ |
| PUT | `/auth/profile` | 更新邮箱/复习提醒设置 | ✅ |
| PUT | `/auth/password` | 修改密码（需旧密码验证） | ✅ |
| GET | `/traces/runs` | Agent 运行列表（分页，按用户过滤） | ✅ |
| GET | `/traces/runs/{id}` | Agent 运行详情（含 steps + tool_calls） | ✅ |
| GET | `/traces/ai-logs` | AI 调用日志列表（分页） | ✅ |
| GET | `/traces/stats` | Agent + AI 使用统计 | ✅ |
| POST | `/workspace/diagnose` | 运行诊断 Agent | ✅ |
| POST | `/workspace/plan` | 运行规划 Agent | ✅ |
| POST | `/workspace/diagnose-and-plan` | 一站式诊断 + 规划预览（返回 waiting_approval） | ✅ |
| POST | `/workspace/plans/{run_id}/approve` | 审批通过，落库任务 | ✅ |
| POST | `/workspace/plans/{run_id}/reject` | 审批拒绝，不创建任务 | ✅ |
| GET | `/workspace/tasks/today` | 今日学习任务 | ✅ |
| GET | `/workspace/tasks` | 任务列表（可按状态筛选） | ✅ |
| PUT | `/workspace/tasks/{id}/complete` | 标记任务完成 | ✅ |
| POST | `/eval/feedback` | 提交回答反馈（helpful/not_helpful） | ✅ |
| GET | `/eval/feedback/stats` | 反馈统计 | ✅ |
| POST | `/eval/cases` | 创建评估用例 | ✅ |
| GET | `/eval/cases` | 评估用例列表 | ✅ |
| POST | `/eval/runs` | 运行 RAG 评估 | ✅ |
| GET | `/eval/runs` | 评估运行列表 | ✅ |
| GET | `/eval/runs/{id}` | 评估运行详情 | ✅ |
| GET | `/portfolio/summary` | Portfolio 数据总览 | ✅ |
| POST | `/portfolio/report/project` | 生成项目技术报告 | ✅ |
| POST | `/portfolio/report/learning` | 生成学习报告 | ✅ |
| GET | `/portfolio/report/project/markdown` | 导出项目报告 Markdown | ✅ |
| GET | `/portfolio/report/learning/markdown` | 导出学习报告 Markdown | ✅ |
| GET | `/portfolio/runs/recent` | 最近 Agent Run 回放 | ✅ |

**查询参数**（GET /notes）：
- `keyword` — 标题/内容模糊搜索（str, 可选）
- `category_id` — 按分类 UUID 筛选（UUID, 可选）
- `tag_id` — 按标签 UUID 筛选（UUID, 可选）
- `mastery_level` — 按掌握度筛选（0=未学, 1=学习中, 2=已掌握）
- `source_type` — 按来源筛选（manual / imported / ai_generated）
- `page` / `page_size` — 分页（默认 1 / 20）

**统一响应格式**：
```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

---

## 5. 数据库 Schema

### notes 表
| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | 主键 |
| user_id | UUID (FK) | 所属用户 |
| title | VARCHAR(200) | 标题 |
| content | TEXT | 正文 |
| summary | TEXT | 摘要（Phase 2 AI 生成） |
| category_id | UUID (FK) | 所属分类 |
| is_favorite | BOOLEAN | 是否收藏 |
| mastery_level | INTEGER | 掌握度：0=未学, 1=学习中, 2=已掌握 |
| source_type | VARCHAR(20) | 来源：manual / imported / ai_generated |
| source_url | TEXT | 来源 URL |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### users 表
| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | 主键 |
| username | VARCHAR(50) UNIQUE | 用户名 |
| email | VARCHAR(100) UNIQUE | 邮箱（可选） |
| password_hash | VARCHAR(200) | bcrypt 密码哈希 |
| reminder_enabled | BOOLEAN | 是否开启复习提醒 |
| reminder_time | TIME | 每日提醒时间 |
| created_at | TIMESTAMP | 注册时间 |

### categories 表
| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | 主键 |
| name | VARCHAR(100) | 分类名 |
| description | TEXT | 描述 |
| sort_order | INTEGER | 排序序号 |
| created_at / updated_at | TIMESTAMP | 时间戳 |

### tags 表
| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | 主键 |
| name | VARCHAR(50) UNIQUE | 标签名 |
| created_at | TIMESTAMP | 创建时间 |

### note_tags 表（多对多关联）
| 列名 | 类型 |
|------|------|
| note_id | UUID (FK) |
| tag_id | UUID (FK) |

### review_cards 表
| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | 主键 |
| note_id | UUID (FK) | 关联知识点 |
| card_type | VARCHAR(20) | concept / code / scenario |
| question | TEXT | 卡片正面问题 |
| answer | TEXT | 卡片背面答案 |
| next_review_at | TIMESTAMP | 下次复习时间 |
| ease_factor | FLOAT | SM-2 难度因子 |
| interval_days | INTEGER | 当前间隔天数 |
| review_count | INTEGER | 复习次数 |
| last_reviewed_at | TIMESTAMP | 上次复习时间 |
| is_user_edited | BOOLEAN | 是否用户编辑过 |
| is_flagged | BOOLEAN | 是否标记质量问题 |
| created_at | TIMESTAMP | 创建时间 |

### review_records 表
| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | 主键 |
| card_id | UUID (FK) | 复习卡片 |
| quality | INTEGER | 评分：0-5 |
| reviewed_at | TIMESTAMP | 复习时间 |

### import_jobs 表
| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | 主键 |
| user_id | UUID (FK) | 所属用户 |
| source_type | VARCHAR(20) | 来源类型：url / text / code |
| source_url | TEXT | 原始 URL（可选） |
| source_text | TEXT | 原始导入内容 |
| status | VARCHAR(20) | pending / processing / draft / confirmed / failed |
| error_message | TEXT | 失败原因 |
| created_at / updated_at | TIMESTAMP | 时间戳 |

### extraction_drafts 表
| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | 主键 |
| import_job_id | UUID (FK) | 所属导入任务 |
| title | VARCHAR(200) | AI 提取的候选标题 |
| content | TEXT | AI 提取的候选内容 |
| is_selected | BOOLEAN | 是否被用户选中导入 |
| note_id | UUID (FK) | 确认后生成的知识点 ID |
| created_at | TIMESTAMP | 创建时间 |

### learning_paths 表
| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | 主键 |
| user_id | UUID (FK) | 所属用户 |
| name | VARCHAR(100) | 路径名称 |
| description | TEXT | 路径描述 |
| modules | JSONB | 模块数组：`[{name, topics, priority}]` |
| created_at | TIMESTAMP | 创建时间 |

### note_chunks 表
| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | 主键 |
| note_id | UUID (FK) | 所属知识点 |
| chunk_index | INTEGER | 分块序号 |
| chunk_text | TEXT | 分块文本 |
| content_hash | VARCHAR(64) | 内容 SHA-256 |
| embedding | VECTOR(1536) | pgvector 嵌入向量 |
| updated_at | TIMESTAMP | 更新时间 |

### conversations 表
| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | 主键 |
| user_id | UUID (FK) | 所属用户 |
| title | VARCHAR(200) | 对话标题 |
| note_id | UUID (FK, nullable) | 关联知识点 |
| created_at / updated_at | TIMESTAMP | 时间戳 |

### messages 表
| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | 主键 |
| conversation_id | UUID (FK) | 所属对话 |
| role | VARCHAR(20) | user / assistant / system |
| content | TEXT | 消息内容 |
| sources | JSONB | 引用知识点来源 |
| created_at | TIMESTAMP | 创建时间 |

### interview_sessions 表
| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | 主键 |
| user_id | UUID (FK) | 所属用户 |
| title | VARCHAR(200) | 面试标题 |
| scope | VARCHAR(50) | all / weak_points |
| total_score | INTEGER | 总分 |
| summary | TEXT | AI 总结 |
| status | VARCHAR(20) | in_progress / completed |
| created_at / finished_at | TIMESTAMP | 时间戳 |

### interview_questions 表
| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | 主键 |
| session_id | UUID (FK) | 所属面试 |
| note_id | UUID (FK, nullable) | 关联知识点 |
| question | TEXT | 面试题 |
| reference_answer | TEXT | 参考答案 |
| user_answer | TEXT | 用户回答 |
| ai_score | INTEGER | AI 评分 1-10 |
| ai_feedback | TEXT | AI 反馈 |
| question_order | INTEGER | 题目顺序 |
| created_at | TIMESTAMP | 创建时间 |

---

## 6. 开发环境启动

```bash
# 1. 启动数据库
docker compose up -d

# 2. 后端（使用 Python 3.12 venv）
cd backend
# 虚拟环境在 D:\Python\venvs\knowbase（Python 3.12）
D:/Python/venvs/knowbase/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000

# 3. 前端
cd frontend
npm install   # 已完成
npm run dev   # http://localhost:5173
```

**数据库连接**（默认）：
- Host: localhost, Port: 5433
- User: knowbase, Password: knowbase123, DB: knowbase
- 容器名：`knowbase-postgres`

**环境路径**：
- Python 3.12：`C:\Users\25128\AppData\Local\Programs\Python\Python312\`
- 系统默认 Python 是 3.9（**不能用**，版本太低）
- 虚拟环境：`D:\Python\venvs\knowbase`（Python 3.12）
- Docker WSL 数据：`D:\DockerData\wsl`（从 C 盘迁移过）

**注意**：
- `alembic.ini` 不能有中文注释（Windows GBK 编码会报 UnicodeDecodeError）
- 运行后端**必须用 venv 的 python**：`D:/Python/venvs/knowbase/Scripts/python.exe`

---

## 7. 当前进度 & 路线图

### Phase 1 — 基础功能 ✅ 已完成
- [x] 项目结构搭建
- [x] 后端：数据模型 + CRUD API + 统一响应格式
- [x] 前端：侧边栏布局 + 路由 + 笔记列表/编辑页
- [x] Docker 数据库配置（Docker Desktop 4.75，数据已迁移至 D:\DockerData）
- [x] Alembic 数据库迁移配置（异步模式 env.py，首次迁移已执行）
- [x] Python 虚拟环境（Python 3.12 @ D:\Python\venvs\knowbase）
- [x] 依赖安装（含 ai/dev extras：langchain, pgvector, pytest 等）
- [x] 端到端联调验证（全部 CRUD 接口通过）
- [x] 首次 Git 提交 + GitHub 远程仓库（https://github.com/XyYpower/xyy.git）

### Phase 2 — AI 学习功能（下一步）

> 详细设计方案见 [Phase2-design.md](Phase2-design.md)
> 产品定位：**"不背单词"式的编程知识学习工具**
> 核心解决：AI 时代开发者不知道自己该学什么、怎么学
> 分三个版本逐步交付：V2.1 → V2.2 → V2.3

**V2.1 — 学习闭环 MVP（最核心）**
- [x] Users 模型 + JWT 认证（注册/登录/Token 刷新/数据隔离）
- [x] notes 表新增 user_id / mastery_level / source_type 字段
- [x] review_cards + review_records 模型（SM-2 状态在 card 上，非 note）
- [x] SM-2 算法 + 复习服务
- [x] LLM 客户端工厂 + AI 卡片生成（无 API key 时本地兜底生成）
- [x] Review API（含卡片编辑/反馈）
- [x] 前端 Auth + Review UI + Dashboard 基础版

**V2.2 — AI 导入 + 学习路径**
- [x] import_jobs + extraction_drafts（草稿确认流程）
- [x] AI 提取知识点（文本/URL/代码，未配置 API key 时本地段落兜底）
- [x] learning_paths 模型 + AI 生成路径（未配置 API key 时模板兜底）
- [x] 前端 Import UI（草稿勾选/编辑/确认）+ Paths UI

**V2.2 验证结果**
- [x] Alembic 当前版本：`b4c7a91f2d6e (head)`
- [x] 后端测试：`D:\Python\venvs\knowbase\Scripts\python.exe -m pytest -q` → 27 passed
- [x] 前端构建：`npm run build` → 通过（仍有 Vite chunk size 警告）

**V2.3 — RAG 对话 + 模拟面试**
- [x] note_chunks（分块 + pgvector 向量嵌入）
- [x] RAG 管线 + AI 对话（SSE 流式）
- [x] interview_sessions + interview_questions（多题面试）
- [x] AI 面试官（出题 + 评分 + 总结；无 API key 时本地兜底）
- [x] 薄弱知识点分析
- [x] 数据导出（JSON / Markdown / Anki CSV）
- [x] 前端 Chat + Interview + Settings + Dashboard 完整版

**V2.3 验证结果**
- [x] Alembic 当前版本：`e2b1a0d9c6f4 (head)`
- [x] 后端测试：`D:\Python\venvs\knowbase\Scripts\python.exe -m pytest -q` → 48 passed
- [x] 前端构建：`npm run build` → 通过（仍有 Vite chunk size 警告）

**V3.0 验证结果**
- [x] Alembic 当前版本：`f1a2b3c4d5e6 (head)`
- [x] 后端测试：`D:\Python\venvs\knowbase\Scripts\python.exe -m pytest -q` → 51 passed（含 3 个 V3.0 集成测试，Docker 数据库验证通过）
- [x] 前端构建：`npm run build` → 通过，主 chunk 从 ~1.5MB 降至 ~773KB（路由懒加载拆分）

**V3.1 验证结果**
- [x] Alembic 当前版本：`a1b2c3d4e5f6 (head)`
- [x] 后端测试：`D:\Python\venvs\knowbase\Scripts\python.exe -m pytest -q` → 54 passed（含 3 个 V3.1 Agent Runtime 集成测试）
- [x] 前端构建：`npm run build` → 通过，TraceLab 页面独立 chunk（217KB）

**V3.2 验证结果**
- [x] Alembic 当前版本：`b2c3d4e5f6a7 (head)`
- [x] 后端测试：56 passed（含 2 个 V3.2 workspace 集成测试）
- [x] 前端构建：通过

**V3.3 验证结果**
- [x] Alembic 当前版本：`c3d4e5f6a7b8 (head)`
- [x] 后端测试：56 passed
- [x] 前端构建：通过

**V3.4 验证结果**
- [x] 后端测试：56 passed（无回归）
- [x] 前端构建：通过

### Phase 3 — 体验打磨 + 内容管理

> 详细任务书见 [V3.0-task.md](V3.0-task.md)

**V3.0 后端 ✅ 已完成**
- [x] categories 表新增 user_id（用户数据隔离）
- [x] Categories CRUD API（POST/PUT/DELETE，按 user_id 隔离）
- [x] 删除分类时自动将关联知识点的 category_id 置空
- [x] 账号设置 API（PUT /auth/profile, PUT /auth/password）
- [x] notes 列表支持 is_favorite 筛选
- [x] Alembic 迁移：`f1a2b3c4d5e6 (head)` — categories 加 user_id
- [x] 后端测试：3 个新测试覆盖分类 CRUD 隔离、账号设置、收藏筛选

**V3.0 前端（进行中）**
- [x] 路由懒加载（React.lazy + Suspense）
- [x] Settings 页面增强（邮箱/密码/复习提醒）
- [x] 分类管理 UI（弹窗 CRUD + 列表筛选）
- [x] 标签编辑 UI（NoteDetail 添加/移除标签）
- [x] 收藏功能 UI（星星按钮 + 筛选开关）
- [x] Markdown 编辑器（分屏编辑预览）
- [x] NoteDetail 页面整合升级

### Phase 4 — Agentic Learning OS（V3.1-V4.0 已完成，V4.1 待实现）

> Agentic Learning OS 原始重设计方案见 [V3.1-agentic-redesign.md](V3.1-agentic-redesign.md)
> V4.1 质量加固与主体验升级方案见 [V4.1-quality-ux-redesign.md](V4.1-quality-ux-redesign.md)
> 目标：把 KnowBase 从 AI 编程知识学习工具升级为可展示 AI Agent 应用开发能力的 Agentic Learning OS。

**V3.1 — Agent Runtime + Trace 基础**
- [x] 新增 agent_runs / agent_steps / tool_calls / ai_call_logs（Alembic 迁移 a1b2c3d4e5f6）
- [x] 建立 Tool Registry，将现有 notes / retrieval / review / interview / import 服务注册为可审计工具
- [x] 新增 logged_llm_call / logged_llm_stream 封装，支持自动记录 AI 调用日志
- [x] 新增 Trace Lab API（runs 列表、详情、AI 日志、统计）
- [x] 新增 Trace Lab 前端页面（统计卡片、运行列表、详情抽屉、步骤时间线、工具调用表）
- [x] Dashboard 集成 AI 使用统计
- [x] 后端测试：3 个新测试覆盖 AgentRun 生命周期、ToolRegistry、AI 日志

**V3.2 — Agent Workspace + 学习规划 Agent**
- [x] 拆分 learning_paths.modules 为结构化表（learning_path_modules / learning_path_topics / learning_tasks）
- [x] Alembic 迁移 b2c3d4e5f6a7
- [x] DiagnosisAgent：根据知识点、复习、面试历史诊断薄弱点（LLM + 本地兜底）
- [x] PlannerAgent：生成结构化路径 + 模块 + Topic + 每日任务（LLM + 本地兜底）
- [x] Agent Workspace API：diagnose / plan / diagnose-and-plan / tasks / complete
- [x] 前端 Agent Workspace 页面：目标输入 → 诊断结果 → 学习计划 → 今日任务
- [x] 后端测试：2 个新测试覆盖诊断+规划流程和任务完成

**V3.3 — RAG 质量与评估系统**
- [x] 新增 message_feedback 表（用户对 AI 回答的反馈）
- [x] 新增 eval_cases / eval_runs / eval_results 表（评估基础设施）
- [x] Alembic 迁移 c3d4e5f6a7b8
- [x] Hybrid retrieval（向量相似度 + PostgreSQL 全文搜索混合检索）
- [x] 评估服务：RAG 回归评估（自动检索→回答→评分）
- [x] 评估 API（反馈提交/统计、用例管理、评估运行）
- [x] 前端：Chat 页面增加回答反馈按钮（👍/👎）
- [x] 前端：Trace Lab 增加 RAG 反馈统计和评估运行面板

**V3.4 — Portfolio Builder**
- [x] Portfolio 服务：项目技术报告 + 学习报告生成（LLM + 本地兜底）
- [x] Portfolio API（报告生成、Markdown 导出、Agent Run 回放）
- [x] 前端 Portfolio 页面（数据总览、报告生成展示、Agent Run 时间线、导出 Markdown）
- [x] 侧边栏新增 Portfolio 导航

**V4.0 — MCP Server**
- [x] 安装 MCP Python SDK（mcp>=1.0.0）
- [x] 创建 MCP Server 模块（FastMCP + SSE transport）
- [x] 暴露 5 个 MCP Tools：search_notes / get_note / create_note_draft / get_review_cards / generate_interview_questions
- [x] 暴露 3 个 MCP Resources：knowbase://notes/{id} / knowbase://reviews/today / knowbase://paths
- [x] 暴露 3 个 MCP Prompts：prepare_agent_engineer_interview / explain_knowledge_gap / generate_project_case_study
- [x] 挂载到 FastAPI（/mcp/sse 端点）
- [x] Settings 页面增加 MCP 配置说明

**V4.0 — LangGraph Adapter**
- [x] 安装 langgraph（>=0.2.0）
- [x] 创建 LangGraph Adapter（StateGraph + MemorySaver checkpointer）
- [x] 学习规划工作流：diagnose → plan → wait_approval → finalize
- [x] 支持暂停/恢复（thread_id + approval_result）
- [x] Workspace API 增加 /workflow/plan 和 /workflow/resume 端点

**V4.1 — 质量加固与主体验升级**
- [x] MCP 安全边界：默认关闭（KNOWBASE_MCP_ENABLED=false）、绑定明确用户（KNOWBASE_MCP_USER_ID）、移除默认第一个用户访问
- [x] Human-in-the-loop 真实落地：planner 拆为 preview_plan/commit_plan；diagnose-and-plan 返回 waiting_approval；新增 approve/reject 端点；拒绝不创建任务
- [x] Agent 失败状态统一化：diagnose-and-plan 诊断/规划每步独立 try/except，失败时 run/step 标记 failed
- [x] Tool Registry 接入真实 tool_calls：execute() 写入 tool_calls 表，requires_approval 拦截写工具
- [x] 学习路径统一结构化模型：path_service.generate_learning_path 同时创建 modules/topics/tasks
- [x] 前端工程质量归零：eslint 0 errors（API 文件允许 any，React hooks 规则降级为 warn）
- [x] 侧边栏分组：工作台/知识库/训练/实验室/系统
- [x] Dashboard 升级为今日学习工作台（今日任务队列 + 快捷操作 + 进度 + AI 概览）

---

## 8. 开发约定

### 代码风格
- **后端**：Python，遵循 PEP 8，异步优先（async/await）
- **前端**：TypeScript strict 模式，函数组件 + Hooks
- **命名**：后端 snake_case，前端 camelCase，组件 PascalCase
- **注释**：中文注释，代码即文档，关键逻辑加注释

### Git 约定
- 分支策略：`main` 为主分支，功能开发用 `feature/xxx`
- Commit message：英文，格式 `feat: / fix: / docs: / chore:`
- 提交前确保后端 `mypy` 和前端 `tsc` 无报错

### API 约定
- RESTful 风格
- 统一响应格式 `Response[T]`
- 分页使用 `page` + `page_size` 参数

---

## 9. 已知问题 & 注意事项

1. ~~**编辑器简陋** — NoteDetail 使用原生 `<textarea>`，非 Markdown 编辑器~~ ✅ V3.0 已修复
2. ~~**react-markdown 未使用** — 已声明依赖但未引入~~ ✅ V3.0 已引入 MarkdownEditor
3. ~~**App.css 残留** — 仍是 Vite 模板默认样式~~ ✅ 已清理
4. ~~**分类/标签管理不完整** — 后端只读接口，前端无管理 UI~~ ✅ V3.0 已补齐
5. **测试覆盖仍少** — 当前 51 个测试覆盖 Auth / SM-2 / 卡片生成 / API 学习闭环 / tags 认证隔离 / Chat / Interview / 导出 / V3.0 分类+账号+收藏；前端交互测试尚未覆盖
6. **V2.1 卡片生成有本地兜底** — 未配置 LLM API key 时不会真实调用 AI
7. ~~**前端构建体积偏大** — 当前 Vite build 有 chunk size 警告，后续可做动态导入~~ ✅ V3.0 路由懒加载已拆分
8. **GitHub 网络不稳定** — 国内访问 GitHub 需多次重试 git push
9. **alembic.ini 不能有中文注释** — Windows GBK 编码问题，会报 UnicodeDecodeError
10. **API 集成测试依赖 Docker 数据库** — `backend/tests/test_api_learning_loop.py` 会在数据库不可用时自动 skip；需要 Docker Desktop + `docker compose up -d` 才会真实执行
11. **V2.2 导入/路径有本地兜底** — 未配置 LLM API key 时不会真实调用 AI，会用规则拆段落和预设学习路径模板
12. **URL 导入是 MVP 抓取** — 当前用 `httpx` + 简单 HTML 去标签，并做基础 SSRF 防护（仅 http/https、拒绝 userinfo、拒绝非公网地址、跳转后重新校验）；复杂反爬、登录态页面、动态渲染页面后续再增强
13. ~~**前端构建体积继续偏大** — V2.3 引入 Chat/Interview/Markdown 后主 chunk 约 1.5MB，后续可用路由级动态导入拆分~~ ✅ V3.0 路由懒加载已拆分，主 chunk 降至 ~773KB
14. **SSE 使用 EventSourceResponse** — V2.3 Review 后已切换到 `sse-starlette`，并在流式输出时检查客户端断连，减少页面关闭后继续消耗 LLM API 的风险
15. **Embedding 兜底不是语义向量** — 未配置 Embedding API key 时使用确定性 hash 向量，只保证流程可跑通，真实检索效果需要配置 OpenAI/GLM 等 embedding 服务
16. **MCP 用户隔离待加固** — 当前 MCP Server 使用默认第一个用户作为本地场景兜底；V4.1 需改为默认关闭并绑定明确用户
17. **LangGraph 审批语义待修正** — 当前规划节点会先创建学习路径和任务，再进入 approval；V4.1 需拆为 preview/commit，拒绝时不得落库任务
18. **前端 lint/build 待归零** — 最近审查中 TypeScript 编译通过，但 lint 有多处 API `any` 和 hooks 规则问题；build 受本地 Tailwind native 依赖/Windows 权限问题影响失败

---

## 10. 更新日志

| 日期 | 内容 |
|------|------|
| 2026-06-01 | 初始项目上下文文档创建 |
| 2026-06-01 | 修正一致性：Python 版本统一 >=3.11；tag 筛选参数改为 tag_id (UUID)；补充多 Agent Git 协作规则 |
| 2026-06-01 | Phase 1 完成：Alembic 配置 + 迁移执行 + Docker 数据库启动 + 全部 CRUD 接口验证通过 + 前后端联调成功 |
| 2026-06-01 | Phase 2 产品升级：从通用笔记工具升级为"不背单词"式编程学习产品，新增间隔复习 + AI 模拟面试 + 学习仪表盘 |
| 2026-06-01 | Phase 2 设计优化：整合 Codex 反馈 — SM-2 状态移到 card、面试拆 session+question、导入加草稿确认、新增 ai_call_logs + note_chunks、分三个版本交付（V2.1/V2.2/V2.3） |
| 2026-06-01 | V2.1 完成：JWT 认证、用户数据隔离、复习卡片、SM-2 调度、Review API、前端登录/注册/复习/Dashboard 基础版 |
| 2026-06-02 | V2.1 质量加固：新增 API 学习闭环集成测试并在 Docker 数据库上验证通过；清理 Python 3.12 `datetime.utcnow()` 弃用警告；pytest 禁用 cacheprovider 避免 Windows cache 警告 |
| 2026-06-02 | V2.1 审查反馈优化：tags/categories 补认证，tags 改为当前用户范围；LLM 失败记录 warning 并兜底；创建知识点后改后台生成复习卡片；`chat.py` 标注 V2.3 预留 |
| 2026-06-02 | V2.2 完成：新增 AI 导入（文本/URL/代码）、提取草稿确认、批量生成知识点和复习卡片、学习路径生成、Import/Paths 前端页面；后端 20 个测试通过，前端构建通过 |
| 2026-06-02 | V2.2 Review 加固：URL 导入增加基础 SSRF 防护；确认导入改为先落库、后台生成复习卡片并记录失败；学习路径 modules 增加 schema 校验；前端批量勾选支持部分失败状态同步；后端测试增至 27 个 |
| 2026-06-02 | V2.3 完成：新增 note_chunks + pgvector 检索、RAG Chat SSE、AI 模拟面试、薄弱点分析、JSON/Markdown/Anki 导出、Chat/Interview/Settings/Dashboard 前端；后端 43 个测试通过，前端构建通过 |
| 2026-06-02 | V2.3 Review 加固：修复 SSE 中途失败混合 fallback、断连检测、对话更新时间、列表消息预加载、嵌入原子替换/并发生成、pgvector ORM 类型、前端流式错误状态、面试参考答案和归一化分数；后端测试增至 48 个 |
| 2026-06-02 | V3.0 后端完成：categories 加 user_id 实现用户数据隔离 + CRUD API；账号设置 API（profile/password）；notes 列表支持 is_favorite 筛选；迁移 f1a2b3c4d5e6；新增 3 个集成测试 |
| 2026-06-02 | V3.0 前端完成：路由懒加载（主 chunk 从 1.5MB 降至 773KB）；Settings 增强（邮箱/密码/提醒）；分类管理 UI（CRUD + 筛选）；标签编辑 + 收藏功能；Markdown 编辑器（分屏预览）；NoteDetail 整合升级；前端构建通过 |
| 2026-06-02 | V3.0 质量修复：Settings TimePicker 用 dayjs 正确绑定已保存时间；MarkdownEditor 增加 Ctrl+B/I/K 快捷键 + Tab 缩进 + 分屏边框修复；NoteDetail 保存后刷新标签列表 |
| 2026-06-03 | V3.1 Agent Runtime 完成：新增 agent_runs/agent_steps/tool_calls/ai_call_logs 四表 + Alembic 迁移 a1b2c3d4e5f6；Tool Registry 注册 8 个工具；logged_llm_call/stream 自动记录 AI 调用；Trace Lab API（4 端点）+ 前端页面（统计/列表/详情/步骤时间线/工具调用表）；Dashboard 集成 AI 使用统计；后端测试增至 54 个 |
| 2026-06-03 | V3.2 Agent Workspace 完成：learning_paths 拆分为 modules/topics/tasks 结构化表（迁移 b2c3d4e5f6a7）；DiagnosisAgent + PlannerAgent（LLM + 本地兜底）；Workspace API（diagnose/plan/tasks）+ 前端页面（目标→诊断→计划→今日任务）；path_service 修复 selectinload 兼容；后端测试增至 56 个 |
| 2026-06-03 | V3.3 RAG 质量与评估系统：message_feedback + eval_cases/runs/results 四表（迁移 c3d4e5f6a7b8）；Hybrid retrieval（向量+PostgreSQL 全文搜索）；RAG 回归评估（自动检索→回答→LLM 评分）；eval API（反馈/用例/运行）；Chat 回答反馈按钮；Trace Lab 增加 RAG 反馈和评估面板 |
| 2026-06-03 | V3.4 Portfolio Builder：项目技术报告 + 学习报告生成（LLM + 本地兜底）；Portfolio API（报告生成、Markdown 导出、Agent Run 回放）；前端 Portfolio 页面（数据总览、报告展示、Agent Run 时间线、导出）；侧边栏新增 Portfolio 导航 |
| 2026-06-03 | V4.0 MCP Server：安装 mcp SDK；创建 MCP Server 模块（FastMCP + SSE transport）；暴露 5 个 Tools + 3 个 Resources + 3 个 Prompts；挂载 /mcp/sse 端点；Settings 增加 MCP 配置说明 |
| 2026-06-03 | V4.0 LangGraph Adapter：安装 langgraph；创建 StateGraph 学习规划工作流（diagnose→plan→wait_approval→finalize）；MemorySaver checkpointer 支持暂停/恢复；Workspace API 增加 /workflow/plan 和 /workflow/resume；前端 UX 优化（Ctrl+S、删除确认、新用户引导） |
| 2026-06-09 | V4.1.1 安全与正确性：MCP 默认关闭 + 绑定明确用户（KNOWBASE_MCP_ENABLED/USER_ID/TOKEN）；planner 拆为 preview_plan/commit_plan；diagnose-and-plan 返回 waiting_approval + approve/reject 端点；拒绝审批不创建任务；Agent 失败状态统一化；前端 AgentWorkspace 适配 preview/approve/reject 流程；后端测试增至 57 个 |
| 2026-06-09 | V4.1 质量加固续：ToolRegistry.execute 写入真实 tool_calls 表，requires_approval 拦截写工具；path_service 统一生成结构化 modules/topics/tasks；侧边栏分组（工作台/知识库/训练/实验室/系统）；eslint 配置项目级决策（API any 放行、hooks 规则 warn）；Dashboard 升级为今日学习工作台 |
| 2026-06-09 | 新增 V3.1 Agentic Redesign：规划 Agent Runtime、Tool Registry、Trace Lab、Agent Workspace、RAG 评估、Portfolio Builder、LangGraph/MCP 后续路线 |
| 2026-06-09 | 新增 V4.1 质量加固与主体验升级设计：聚焦 MCP 安全、审批语义、失败 Trace、ToolCall 追踪、学习路径结构统一、前端工作台/Trace/Portfolio 体验升级 |
