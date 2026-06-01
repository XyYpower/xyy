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

---

## 3. 项目结构

```
knowbase/
├── CLAUDE.md              # Claude Code 行为指令
├── AGENTS.md              # Codex 行为指令
├── docs/
│   └── CONTEXT.md         # 本文件 — 项目共享上下文
├── docker-compose.yml     # PostgreSQL + pgvector
├── .env.example           # 环境变量模板
├── .gitignore
│
├── backend/
│   ├── pyproject.toml     # Python 依赖声明
│   ├── alembic/           # 数据库迁移（待配置）
│   │   └── versions/
│   ├── tests/             # 测试（待编写）
│   └── app/
│       ├── main.py        # FastAPI 入口
│       ├── config.py      # 配置管理
│       ├── database.py    # 数据库连接
│       ├── api/           # API 路由层
│       │   ├── router.py  # 路由聚合
│       │   ├── notes.py   # 笔记 CRUD
│       │   ├── tags.py    # 标签列表
│       │   └── categories.py  # 分类列表
│       ├── models/        # SQLAlchemy ORM 模型
│       │   └── note.py    # Note / Category / Tag
│       ├── schemas/       # Pydantic 请求/响应模型
│       │   ├── common.py  # Response[T] / PageResult[T]
│       │   └── note.py    # 笔记相关 schema
│       ├── services/      # 业务逻辑层
│       │   └── note_service.py
│       ├── rag/           # RAG 管线（Phase 2 占位）
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
        │   ├── client.ts  # Axios 实例
        │   └── notes.ts   # 笔记 API 客户端
        ├── components/
        │   └── Layout.tsx # 侧边栏布局
        └── pages/
            ├── Home.tsx       # 概览页（占位）
            ├── Notes.tsx      # 笔记列表（已实现）
            ├── NoteDetail.tsx # 笔记编辑（已实现）
            └── Chat.tsx      # AI 对话（Phase 2 占位）
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
| GET | `/tags` | 标签列表 | ✅ |
| GET | `/categories` | 分类列表 | ✅ |

**查询参数**（GET /notes）：
- `keyword` — 标题/内容模糊搜索
- `category_id` — 按分类筛选
- `tag_id` — 按标签筛选
- `page` / `page_size` — 分页

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
| title | VARCHAR(200) | 标题 |
| content | TEXT | 正文 |
| summary | TEXT | 摘要（Phase 2 AI 生成） |
| category_id | UUID (FK) | 所属分类 |
| is_favorite | BOOLEAN | 是否收藏 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

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

---

## 6. 开发环境启动

```bash
# 1. 启动数据库
docker compose up -d

# 2. 后端（需要先配置 Alembic + 安装依赖）
cd backend
pip install -e ".[ai,dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 3. 前端
cd frontend
npm install   # 已完成
npm run dev   # http://localhost:5173
```

**数据库连接**（默认）：
- Host: localhost, Port: 5433
- User: knowbase, Password: knowbase123, DB: knowbase

---

## 7. 当前进度 & 路线图

### Phase 1 — 基础功能（当前）
- [x] 项目结构搭建
- [x] 后端：数据模型 + CRUD API + 统一响应格式
- [x] 前端：侧边栏布局 + 路由 + 笔记列表/编辑页
- [x] Docker 数据库配置
- [ ] Alembic 数据库迁移配置
- [ ] 端到端联调验证
- [ ] 首次 Git 提交 + GitHub 远程仓库

### Phase 2 — AI 功能
- [ ] RAG 管线（文档切分 → Embedding → pgvector 存储）
- [ ] AI 对话接口（基于笔记内容的问答）
- [ ] 前端 Chat 页面实现
- [ ] LLM 集成（DeepSeek / GLM / OpenAI 三选一）

### Phase 3 — 增强
- [ ] Markdown / 富文本编辑器
- [ ] 分类管理 UI（增删改）
- [ ] 标签编辑 UI（添加/移除）
- [ ] 收藏功能 UI
- [ ] 用户认证

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

1. **Alembic 未配置** — `alembic/` 目录为空，需要初始化并生成首次迁移
2. **编辑器简陋** — NoteDetail 使用原生 `<textarea>`，非 Markdown 编辑器
3. **react-markdown 未使用** — 已声明依赖但未引入
4. **zustand 未使用** — 已声明依赖但没有 store 文件
5. **App.css 残留** — 仍是 Vite 模板默认样式
6. **分类/标签管理不完整** — 后端只读接口，前端无管理 UI
7. **无认证系统** — 当前无用户体系
8. **无测试** — `tests/` 目录为空

---

## 10. 更新日志

| 日期 | 内容 |
|------|------|
| 2026-06-01 | 初始项目上下文文档创建 |
