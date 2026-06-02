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
│   └── V2.2-task.md       # V2.2 任务书（已完成）
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
│       │   ├── auth.py    # 注册/登录/JWT
│       │   ├── notes.py   # 笔记 CRUD
│       │   ├── imports.py # AI 导入 + 草稿确认
│       │   ├── paths.py   # 学习路径
│       │   ├── review.py  # 间隔复习
│       │   ├── tags.py    # 标签列表
│       │   └── categories.py  # 分类列表
│       ├── models/        # SQLAlchemy ORM 模型
│       │   ├── user.py    # User
│       │   ├── note.py    # Note / Category / Tag
│       │   ├── review.py  # ReviewCard / ReviewRecord
│       │   ├── import_job.py # ImportJob / ExtractionDraft
│       │   ├── path.py    # LearningPath
│       │   └── chat.py    # V2.3 对话预留
│       ├── schemas/       # Pydantic 请求/响应模型
│       │   ├── common.py  # Response[T] / PageResult[T]
│       │   ├── auth.py    # 认证相关 schema
│       │   ├── note.py    # 笔记相关 schema
│       │   ├── review.py  # 复习相关 schema
│       │   ├── import_job.py # 导入相关 schema
│       │   └── path.py    # 学习路径 schema
│       ├── services/      # 业务逻辑层
│       │   ├── auth_service.py
│       │   ├── note_service.py
│       │   ├── review_service.py
│       │   ├── import_service.py
│       │   └── path_service.py
│       ├── rag/           # LLM / RAG 相关能力
│       │   ├── llm.py
│       │   ├── card_generator.py
│       │   └── extractor.py
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
        │   ├── auth.ts    # 认证 API
        │   ├── client.ts  # Axios 实例
        │   ├── notes.ts   # 笔记 API 客户端
        │   ├── review.ts  # 复习 API 客户端
        │   ├── import.ts  # 导入 API 客户端
        │   └── paths.ts   # 学习路径 API 客户端
        ├── components/
        │   └── Layout.tsx # 侧边栏布局
        └── pages/
            ├── Home.tsx       # 概览页（占位）
            ├── Dashboard.tsx  # 学习仪表盘基础版
            ├── Notes.tsx      # 笔记列表（已实现）
            ├── NoteDetail.tsx # 笔记编辑（已实现）
            ├── Review.tsx     # 间隔复习
            ├── Import.tsx     # AI 导入
            ├── Paths.tsx      # 学习路径
            ├── Login.tsx      # 登录
            ├── Register.tsx   # 注册
            └── Chat.tsx       # AI 对话（V2.3 占位）
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
- [x] 后端测试：`D:\Python\venvs\knowbase\Scripts\python.exe -m pytest -q` → 20 passed
- [x] 前端构建：`npm run build` → 通过（仍有 Vite chunk size 警告）

**V2.3 — RAG 对话 + 模拟面试**
- [ ] note_chunks（分块 + pgvector 向量嵌入）
- [ ] RAG 管线 + AI 对话（SSE 流式）
- [ ] interview_sessions + interview_questions（多题面试）
- [ ] AI 面试官（出题 + 评分 + 总结）
- [ ] 薄弱知识点分析
- [ ] 数据导出（JSON / Markdown / Anki CSV）
- [ ] 前端 Chat + Interview + Settings + Dashboard 完整版

### Phase 3 — 增强
- [ ] Markdown / 富文本编辑器
- [ ] 分类管理 UI（增删改）
- [ ] 标签编辑 UI（添加/移除）
- [ ] 收藏功能 UI
- [ ] 账号设置增强（提醒时间、密码修改、资料维护）

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

1. **编辑器简陋** — NoteDetail 使用原生 `<textarea>`，非 Markdown 编辑器
2. **react-markdown 未使用** — 已声明依赖但未引入
3. **App.css 残留** — 仍是 Vite 模板默认样式
4. **分类/标签管理不完整** — 后端只读接口，前端无管理 UI
5. **测试覆盖仍少** — 当前覆盖 Auth / SM-2 / 卡片生成核心单元、API 学习闭环、tags 认证隔离、后台生成；前端交互测试尚未覆盖
6. **V2.1 卡片生成有本地兜底** — 未配置 LLM API key 时不会真实调用 AI
7. **前端构建体积偏大** — 当前 Vite build 有 chunk size 警告，后续可做动态导入
8. **GitHub 网络不稳定** — 国内访问 GitHub 需多次重试 git push
9. **alembic.ini 不能有中文注释** — Windows GBK 编码问题，会报 UnicodeDecodeError
10. **API 集成测试依赖 Docker 数据库** — `backend/tests/test_api_learning_loop.py` 会在数据库不可用时自动 skip；需要 Docker Desktop + `docker compose up -d` 才会真实执行
11. **V2.2 导入/路径有本地兜底** — 未配置 LLM API key 时不会真实调用 AI，会用规则拆段落和预设学习路径模板
12. **URL 导入是 MVP 抓取** — 当前用 `httpx` + 简单 HTML 去标签，复杂反爬、登录态页面、动态渲染页面后续再增强

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
