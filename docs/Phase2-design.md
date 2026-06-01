# KnowBase Phase 2 — 产品升级设计方案

> 产品定位：**"不背单词"式的编程知识学习工具**
> 本文件是两个 Agent（Claude Code / Codex）共用的设计文档，配合 `CONTEXT.md` 使用。

---

## Context

Phase 1 已完成：笔记 CRUD 前后端联调通过。

Phase 2 的目标：将 KnowBase 从通用笔记工具升级为 **编程知识学习产品**，核心解决一个问题——**AI 时代开发者不知道自己该学什么、怎么学**。

### 核心学习循环

```
诊断（你哪里不会）
  → 学习（三种方式获取知识）
    → 练（间隔复习卡片）
      → 测（AI 模拟面试）
        → 补（回到诊断，查漏补缺）
```

### 和"不背单词"的对应

| 不背单词 | KnowBase |
|---|---|
| 单词 | 技术知识点（JWT、RAG、pgvector...） |
| 例句（电影/新闻原声） | 代码片段、博客摘录、项目踩坑笔记 |
| 词书（四六级/雅思） | 学习路径（后端面试/前端入门/系统设计） |
| 认识 / 不认识 | 掌握 / 未掌握 |
| 间隔复习推送 | 定时复习提醒（SM-2 算法） |
| 艾宾浩斯遗忘曲线 | 同样的算法驱动复习 |
| 学习进度（已掌握 XX 词） | 已掌握 XX 个知识点 |

---

## 概念约定

### "笔记"和"知识点"的关系

产品语言统一叫 **"知识点"**，代码层面复用 `notes` 表作为 MVP 载体：

- `note` = 一个可学习 / 可复习 / 可检索的知识单元
- 一篇导入文章可以拆成多个 note
- 一个 note 可以挂载到：学习路径、标签、复习卡片、面试题
- 后续如果 note 的语义不够用，再考虑拆出 `knowledge_points` 表

**为什么不在 MVP 新建 knowledge_points 表**：增加复杂度，notes 的字段（title、content、tags）完全够用，语义上统一叫"知识点"即可。

---

## 非目标（Phase 2 暂不做）

明确范围边界，避免功能蔓延：

- ~~多用户权限系统~~ → 只做基础 JWT 认证，不做角色/权限
- ~~浏览器插件~~ → 后续再考虑
- ~~复杂定时推送（邮件/微信）~~ → 只做浏览器 Notification
- ~~移动端 App~~ → 只做 PC 端响应式（复习页面优先）
- ~~社交功能（分享/排行榜）~~ → 后续再考虑
- ~~付费/订阅系统~~ → 后续再考虑
- ~~多语言支持~~ → 只做中文

---

## 一、知识从哪来（三种来源）

产品的核心难题不是"存知识"，而是"用户不知道自己该学什么"。知识来源分三层，互相补充：

### 来源一：用户手动记录（最有价值）

用户做项目过程中遇到的问题、踩过的坑、技术决策。

```
示例：用户做 RAG 功能时遇到了 pgvector 索引选择问题
  → 记录到 KnowBase："pgvector 用 HNSW 还是 IVFFlat？"
  → 内容包含：问题描述、解决方案、代码片段
  → 系统自动标记掌握度、生成复习卡片
```

**为什么最有价值**：面试时能讲亲身经历，比背书有说服力得多。

### 来源二：导入外部内容（次之）

粘贴 URL 或文本，AI 提取知识点。**AI 提取的结果先进入草稿，用户确认后才正式入库。**

```
导入流程：
  1. 用户粘贴 URL / 文本 / 代码
  2. 创建 import_jobs 记录（来源、状态）
  3. AI 提取候选知识点 → 存入 extraction_drafts（草稿）
  4. 用户勾选、编辑、合并、删除草稿
  5. 确认保存 → 生成 notes + review_cards + note_chunks
```

**为什么需要草稿确认**：AI 一次提取十几个泛泛知识点，直接入库会把数据库搞脏。用户确认后才入库，保证质量。

### 来源三：AI 生成学习路线和知识点（快速入门）

用户说"我想学后端"，AI 生成结构化的学习路径。

```
用户选择目标："3个月后面试后端开发"
  → AI 生成学习路线（存在 learning_paths 表）
  → 用户选择开始学的模块
  → AI 生成该模块的知识点概览（作为入门草稿，用户确认后入库）
  → 用户在学习过程中用来源一、二不断补充真实内容
```

### AI 的定位：知识加工者，不是知识生产者

| 场景 | 用不用 AI | 原因 |
|------|----------|------|
| AI 凭空生成"JWT 是什么" | 少用 | 太泛，百度也能搜到 |
| 用户粘贴博客，AI 提取知识点 | 用 | 源头是真人写的，AI 做结构化 |
| AI 对已有知识点出复习题 | 用 | 不是生成知识，是检验理解 |
| AI 生成学习路线 | 用 | 告诉你该学啥，降低迷茫感 |
| AI 批量出面试题 | 用 | 面试题本身需要量大 |

### 成本策略：生成一次，存储永久

```
AI 调用场景          调用频率        成本控制
──────────────      ──────────     ──────────────────
导入内容提取知识点    一次性         结果存数据库，不重复调
生成复习卡片         一次性         每个知识点生成一次，存 review_cards 表
AI 面试评分          每次面试       实时调用，用便宜模型（DeepSeek）
学习路线生成         一次性         生成后存库，可手动刷新
复习时               0 次 API      直接读数据库里的卡片
```

所有 AI 调用记录写入 `ai_call_logs` 表，用于成本追踪和调试。

---

## 二、产品功能总览

### 2.0 用户系统（基础必备）

支持多用户使用，每人有独立的学习数据。

- 注册（用户名 + 密码）→ bcrypt 哈希存储
- 登录 → 返回 JWT access_token + refresh_token
- Token 刷新（access_token 30 分钟，refresh_token 7 天）
- 所有 API 需要登录（中间件校验 Token）
- 每个用户的数据完全隔离（所有表有 user_id）

面试关联："JWT 认证流程怎么设计？"——做完这个就能讲清楚。

### 2.1 知识管理（增强）

在原有笔记 CRUD 基础上增加：
- 掌握度标记（未学 / 学习中 / 已掌握）
- 知识点来源标记（manual / imported / ai_generated）
- 导入功能（URL / 文本 / 代码片段）+ 草稿确认流程
- **搜索筛选**：按标签、掌握度、来源、关键词、是否需复习
- **批量操作**：批量标记掌握度、批量删除

### 2.2 AI 对话（新增）

基于知识点内容的 RAG 问答：
- 流式输出（SSE）+ 引用来源
- 多轮对话上下文
- 可选择关联特定知识点进行针对性问答

### 2.3 间隔复习（核心特色）

类似不背单词的卡片复习：
- AI 根据知识点自动生成 3 种卡片（概念 / 代码 / 场景）
- **SM-2 状态在每张卡片上**（一张知识点有 3 张卡，每张掌握程度不同）
- 每日复习任务 + 连续学习天数
- **复习时不调 AI**，直接读数据库
- **卡片编辑**：用户可以修改 AI 生成的卡片
- **卡片反馈**：标记"这张卡片不好"
- **复习提醒**：浏览器 Notification API 推送

### 2.4 AI 模拟面试（核心特色）

- 一次面试包含多道题（session + questions 模型）
- 基于已学知识点生成面试题
- 每题独立评分 + 反馈
- 面试历史回放 + 薄弱知识点聚合分析

### 2.5 学习仪表盘

- 知识点掌握度分布（饼图）
- 每日学习曲线（折线图）
- 连续学习天数
- 待复习数量提醒

### 2.6 数据导出

- JSON（完整数据，可重新导入）
- Markdown（知识点，方便阅读）
- CSV（复习卡片，可导入 Anki）

### 2.7 移动端适配（后续优化）

复习卡片页面响应式布局优先做，其他页面先保证 PC 端可用。

---

## 三、数据库设计

### 3.1 新增 users 表

| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| username | VARCHAR(50) UNIQUE | 用户名 |
| email | VARCHAR(100) UNIQUE, nullable | 邮箱 |
| password_hash | VARCHAR(200) | bcrypt 哈希密码 |
| reminder_enabled | BOOLEAN, default false | 是否开启复习提醒 |
| reminder_time | TIME, nullable | 每日提醒时间 |
| created_at | TIMESTAMP | 注册时间 |

### 3.2 修改 notes 表

| 列名 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| user_id | UUID FK → users.id | 必填 | 所属用户 |
| mastery_level | INTEGER | 0 | 整体掌握度：0=未学, 1=学习中, 2=已掌握（汇总值） |
| source_type | VARCHAR(20) | 'manual' | 来源：manual / imported / ai_generated |
| source_url | TEXT, nullable | NULL | 来源 URL |

> 注意：SM-2 相关字段（next_review_at, ease_factor, review_count, interval_days）**不在 notes 表上**，而在 review_cards 表上。因为一个知识点有 3 张卡片，每张掌握程度不同。notes.mastery_level 是汇总值。

### 3.3 新增表

#### conversations（对话）

| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| user_id | UUID FK → users.id | 所属用户 |
| title | VARCHAR(200) | 对话标题 |
| note_id | UUID FK, nullable | 关联的知识点 |
| created_at / updated_at | TIMESTAMP | 时间戳 |

#### messages（消息）

| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| conversation_id | UUID FK | 所属对话 |
| role | VARCHAR(20) | user / assistant / system |
| content | TEXT | 消息内容 |
| sources | JSONB, nullable | AI 引用的知识点列表 |
| created_at | TIMESTAMP | 创建时间 |

#### note_chunks（文本分块 + 向量嵌入）

> 替代原 note_embeddings 设计。一条 note 可以有多个 chunk（长文分块），每个 chunk 一个向量。

| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| note_id | UUID FK → notes.id | 所属知识点 |
| chunk_index | INTEGER | 分块序号（0, 1, 2...） |
| chunk_text | TEXT | 分块文本 |
| content_hash | VARCHAR(64) | 内容 hash（去重用） |
| embedding | VECTOR(1536) | pgvector 向量 |
| updated_at | TIMESTAMP | 更新时间 |

索引：`(note_id, chunk_index)` UNIQUE

MVP 策略：短知识点（<500 字）只生成 1 个 chunk；长文导入自动按段落分块。

#### review_cards（复习卡片）

| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| note_id | UUID FK | 关联的知识点 |
| card_type | VARCHAR(20) | concept / code / scenario |
| question | TEXT | 问题（卡片正面） |
| answer | TEXT | 答案（卡片背面） |
| **next_review_at** | TIMESTAMP, nullable | **下次复习时间（SM-2 调度）** |
| **ease_factor** | FLOAT, default 2.5 | **SM-2 难度因子** |
| **interval_days** | INTEGER, default 0 | **当前间隔天数** |
| **review_count** | INTEGER, default 0 | **累计复习次数** |
| **last_reviewed_at** | TIMESTAMP, nullable | **上次复习时间** |
| is_user_edited | BOOLEAN, default false | 用户是否手动编辑过 |
| is_flagged | BOOLEAN, default false | 是否被标记为"不好" |
| created_at | TIMESTAMP | 创建时间 |

卡片类型：
- **concept** — "JWT 的三个组成部分是什么？"
- **code** — "补全 FastAPI 依赖注入的代码..."
- **scenario** — "你的 API 突然变慢，怎么排查？"

#### review_records（复习历史）

| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| card_id | UUID FK → review_cards.id | 复习的卡片 |
| quality | INTEGER | 评分：0=完全忘了, 3=勉强记得, 5=很熟悉 |
| reviewed_at | TIMESTAMP | 复习时间 |

#### import_jobs（导入任务）

| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| user_id | UUID FK → users.id | 所属用户 |
| source_type | VARCHAR(20) | url / text / code |
| source_url | TEXT, nullable | 来源 URL |
| source_text | TEXT | 原始文本 |
| status | VARCHAR(20) | pending / processing / draft / confirmed / failed |
| error_message | TEXT, nullable | 错误信息 |
| created_at / updated_at | TIMESTAMP | 时间戳 |

#### extraction_drafts（提取草稿）

| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| import_job_id | UUID FK → import_jobs.id | 所属导入任务 |
| title | VARCHAR(200) | 候选知识点标题 |
| content | TEXT | 候选知识点内容 |
| is_selected | BOOLEAN, default true | 用户是否勾选（默认全选） |
| note_id | UUID FK, nullable | 确认后生成的 note ID |
| created_at | TIMESTAMP | 创建时间 |

#### interview_sessions（面试场次）

| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| user_id | UUID FK → users.id | 所属用户 |
| title | VARCHAR(200) | 面试标题（如"后端面试 Round 1"） |
| scope | VARCHAR(50) | 范围：all / weak_points / specific_tags |
| total_score | INTEGER, nullable | 总分（所有题目评分汇总） |
| summary | TEXT, nullable | AI 面试总结 |
| status | VARCHAR(20) | in_progress / completed |
| created_at / finished_at | TIMESTAMP | 时间戳 |

#### interview_questions（面试题目）

| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| session_id | UUID FK → interview_sessions.id | 所属面试场次 |
| note_id | UUID FK, nullable | 关联的知识点 |
| question | TEXT | AI 出的面试题 |
| user_answer | TEXT, nullable | 用户回答 |
| ai_score | INTEGER, nullable | AI 评分（1-10） |
| ai_feedback | TEXT, nullable | AI 评价和改进建议 |
| question_order | INTEGER | 题目顺序（1, 2, 3...） |
| created_at | TIMESTAMP | 创建时间 |

#### learning_paths（学习路径）

| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| user_id | UUID FK → users.id | 所属用户 |
| name | VARCHAR(100) | 路径名称 |
| description | TEXT | 路径描述 |
| modules | JSONB | 模块列表（MVP 用 JSONB，V2.2 再拆表） |
| created_at | TIMESTAMP | 创建时间 |

modules JSON 结构：
```json
[
  {
    "name": "数据库",
    "topics": ["索引原理", "事务隔离级别", "慢SQL优化"],
    "priority": 1
  },
  {
    "name": "缓存",
    "topics": ["Redis数据结构", "缓存穿透", "缓存雪崩"],
    "priority": 2
  }
]
```

#### ai_call_logs（AI 调用日志）

| 列名 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| user_id | UUID FK, nullable | 触发用户 |
| provider | VARCHAR(20) | deepseek / glm / openai |
| model | VARCHAR(50) | 具体模型名 |
| purpose | VARCHAR(30) | extract / card_generate / chat / interview / path_generate |
| prompt_tokens | INTEGER | 输入 token 数 |
| completion_tokens | INTEGER | 输出 token 数 |
| estimated_cost | FLOAT | 预估费用（美元） |
| latency_ms | INTEGER | 响应时间 |
| status | VARCHAR(10) | success / error |
| error_message | TEXT, nullable | 错误信息 |
| created_at | TIMESTAMP | 调用时间 |

---

## 四、后端架构

### 4.1 整体架构

```
Frontend (React)
    │ REST + SSE
    ▼
FastAPI Routers
    ├── api/auth.py        → 认证
    ├── api/chat.py        → AI 对话
    ├── api/review.py      → 间隔复习
    ├── api/interview.py   → AI 面试
    ├── api/import.py      → 内容导入（草稿确认流程）
    ├── api/paths.py       → 学习路径
    ├── api/export.py      → 数据导出
    └── api/notes.py       → 知识点 CRUD（已有，增强）
    │
    ▼
Services
    ├── services/auth_service.py
    ├── services/chat_service.py
    ├── services/review_service.py      → SM-2 复习调度
    ├── services/interview_service.py   → 面试出题 + 评分
    ├── services/import_service.py      → 导入 + 草稿确认
    ├── services/path_service.py
    ├── services/export_service.py
    └── services/note_service.py        → 已有
    │
    ▼
RAG Pipeline (app/rag/)
    ├── llm.py             → LLM 客户端工厂
    ├── embedding.py       → 向量嵌入生成
    ├── retrieval.py       → 相似度搜索（基于 note_chunks）
    ├── prompts.py         → Prompt 模板
    ├── pipeline.py        → RAG 编排
    ├── card_generator.py  → AI 复习卡片生成
    ├── extractor.py       → 导入内容知识点提取
    └── interviewer.py     → AI 面试官
```

### 4.2 SM-2 间隔复习算法

```python
def calculate_next_review(quality: int, ease_factor: float, interval_days: int, review_count: int):
    """
    SM-2 算法（修正版）

    quality: 0-5（用户评分）
    ease_factor: 难度因子，初始 2.5
    interval_days: 当前间隔天数（从 card 上读取）
    review_count: 已复习次数

    返回: (next_review_at, new_ease_factor, new_interval_days, new_review_count)
    """
    if quality < 3:
        # 忘了 → 重来
        new_interval = 1
        new_review_count = 0
    else:
        if review_count == 0:
            new_interval = 1
        elif review_count == 1:
            new_interval = 6
        else:
            new_interval = round(interval_days * ease_factor)
        new_review_count = review_count + 1

    new_ease = max(1.3, ease_factor + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    next_review = datetime.utcnow() + timedelta(days=new_interval)
    return next_review, new_ease, new_interval, new_review_count
```

> 关键修正：`interval_days` 必须从 card 表读取并传入，不能凭空计算。`review_count > 1` 时用 `interval_days * ease_factor` 递增。

### 4.3 导入流程

```
POST /import/text
  ↓
创建 import_jobs (status=pending)
  ↓
后台调用 AI 提取 (status=processing)
  ↓
提取结果写入 extraction_drafts (status=draft)
  ↓
前端展示草稿列表，用户勾选/编辑/删除
  ↓
POST /import/{job_id}/confirm
  ↓
选中的草稿 → 生成 notes + review_cards + note_chunks (status=confirmed)
```

### 4.4 API 端点

#### Auth API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/register` | 注册 |
| POST | `/auth/login` | 登录 |
| POST | `/auth/refresh` | 刷新 Token |
| GET | `/auth/me` | 当前用户信息 |
| PUT | `/auth/reminder` | 设置复习提醒 |

> 以下 API 都需要 `Authorization: Bearer <access_token>`

#### Notes API（增强）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/notes` | 知识点列表（新增 mastery_level / source_type / need_review 筛选） |
| GET | `/notes/{id}` | 知识点详情 |
| POST | `/notes` | 创建知识点 |
| PUT | `/notes/{id}` | 更新知识点 |
| DELETE | `/notes/{id}` | 删除知识点 |

#### Chat API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/chat/conversations` | 对话列表 |
| POST | `/chat/conversations` | 创建对话 |
| GET | `/chat/conversations/{id}` | 对话 + 消息历史 |
| DELETE | `/chat/conversations/{id}` | 删除对话 |
| POST | `/chat/conversations/{id}/chat` | 发消息，SSE 流式返回 |

#### Review API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/review/today` | 今日待复习的卡片列表 |
| GET | `/review/cards/{note_id}` | 获取某知识点的复习卡片 |
| POST | `/review/submit` | 提交复习评分（更新 card 的 SM-2 状态） |
| GET | `/review/stats` | 学习统计 |
| POST | `/review/generate/{note_id}` | 生成复习卡片（一次性存库） |
| PUT | `/review/cards/{card_id}` | 编辑卡片内容 |
| POST | `/review/cards/{card_id}/flag` | 标记卡片"不好" |

#### Interview API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/interview/start` | 开始面试（创建 session + 生成 N 道题） |
| POST | `/interview/{session_id}/answer/{question_id}` | 提交单题回答，AI 评分 |
| POST | `/interview/{session_id}/finish` | 结束面试，AI 生成总结 |
| GET | `/interview/sessions` | 面试历史列表 |
| GET | `/interview/sessions/{id}` | 面试详情（所有题目 + 评分） |
| GET | `/interview/weak-points` | 薄弱知识点聚合分析 |

#### Import API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/import/text` | 导入文本，创建 job + AI 提取草稿 |
| POST | `/import/url` | 导入 URL（抓取内容后同 text 流程） |
| POST | `/import/code` | 导入代码片段，AI 解释技术点 |
| GET | `/import/jobs` | 导入任务列表 |
| GET | `/import/jobs/{id}/drafts` | 获取某任务的草稿列表 |
| PUT | `/import/drafts/{id}` | 编辑草稿内容 |
| POST | `/import/drafts/{id}/toggle` | 勾选/取消草稿 |
| POST | `/import/jobs/{id}/confirm` | 确认选中草稿 → 生成 notes |

#### Learning Path API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/paths` | 学习路径列表 |
| POST | `/paths/generate` | AI 生成学习路径 |
| GET | `/paths/{id}` | 路径详情 |

#### Export API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/export/json` | 导出全部数据为 JSON |
| GET | `/export/markdown` | 导出知识点为 Markdown |
| GET | `/export/anki` | 导出复习卡片为 CSV |

---

## 五、前端架构

### 5.1 路由

```
/login              → 登录页
/register           → 注册页
/                   → 学习仪表盘（需登录）
/notes              → 知识点列表
/notes/:id          → 知识点编辑
/chat               → AI 对话
/review             → 间隔复习
/interview          → AI 模拟面试
/import             → 内容导入（含草稿确认）
/paths              → 学习路径
/settings           → 设置（提醒、导出）
```

### 5.2 侧边栏

```
┌──────────────────┐
│    KnowBase      │
├──────────────────┤
│ 概览             │
│ 知识点           │
│ AI 对话          │
│ 间隔复习         │
│ 模拟面试         │
│ 导入知识         │
│ 学习路径         │
│ 设置             │
├──────────────────┤
│ 用户名  [退出]    │
└──────────────────┘
```

---

## 六、实施计划（三个版本）

不一次性做完，分三个可用版本逐步交付：

### V2.1 — 学习闭环 MVP（最核心）

> 目标：跑通"记知识点 → 间隔复习 → 掌握度提升"的完整循环

| 步骤 | 内容 | 文件 |
|------|------|------|
| 1 | Users 模型 + Alembic 迁移 | `models/user.py` |
| 2 | Auth 服务 + API + JWT 中间件 | `services/auth_service.py`、`api/auth.py`、`utils/deps.py` |
| 3 | notes 表新增字段 + 迁移（user_id, mastery_level, source_type） | 修改 `models/note.py` |
| 4 | 现有 API 加 user_id 过滤 | 修改 `services/note_service.py`、`api/notes.py` |
| 5 | review_cards + review_records 模型 + 迁移 | `models/review.py` |
| 6 | SM-2 算法 + 复习服务 | `services/review_service.py` |
| 7 | AI 卡片生成 | `rag/llm.py`、`rag/card_generator.py` |
| 8 | Review API（含卡片编辑/反馈） | `schemas/review.py`、`api/review.py` |
| 9 | 前端 Auth（登录/注册/路由守卫） | `store/authStore.ts`、`pages/Login.tsx`、`pages/Register.tsx`、`components/AuthRoute.tsx` |
| 10 | 前端 Review UI（翻卡片 + 评分） | `api/review.ts`、`pages/Review.tsx` |
| 11 | Dashboard 基础版（今日复习 + 掌握度统计） | `pages/Dashboard.tsx` |

**V2.1 交付物**：用户注册登录 → 手动创建知识点 → 自动生成复习卡片 → 每日复习 → 看到掌握度提升

### V2.2 — AI 导入 + 学习路径

> 目标：降低知识录入门槛，有学习路线指引

| 步骤 | 内容 | 文件 |
|------|------|------|
| 12 | import_jobs + extraction_drafts 模型 + 迁移 | `models/import_job.py` |
| 13 | AI 提取服务 | `rag/llm.py`（V2.1 已建）、`rag/extractor.py` |
| 14 | Import API（含草稿确认流程） | `schemas/import.py`、`services/import_service.py`、`api/import.py` |
| 15 | learning_paths 模型 + 迁移 | `models/path.py` |
| 16 | 学习路径服务 + API | `services/path_service.py`、`api/paths.py` |
| 17 | 前端 Import UI（草稿列表 + 勾选确认） | `pages/Import.tsx` |
| 18 | 前端 Paths UI | `pages/Paths.tsx` |

**V2.2 交付物**：粘贴博客/面经 → AI 提取草稿 → 用户确认 → 知识点入库 → 自动生成卡片

### V2.3 — RAG 对话 + 模拟面试

> 目标：AI 问答 + 面试模拟，完整学习闭环

| 步骤 | 内容 | 文件 |
|------|------|------|
| 19 | note_chunks 模型 + pgvector 迁移 | 修改 `models/note.py`（或新建 chunk 模型），Alembic 迁移 |
| 20 | 嵌入服务 + 向量检索 | `rag/embedding.py`、`rag/retrieval.py` |
| 21 | RAG 管线 + Prompt 模板 | `rag/prompts.py`、`rag/pipeline.py` |
| 22 | conversations/messages 模型 + 迁移 | `models/chat.py` |
| 23 | Chat 服务 + API（SSE 流式） | `schemas/chat.py`、`services/chat_service.py`、`api/chat.py` |
| 24 | 笔记创建时自动嵌入 | 修改 `services/note_service.py` |
| 25 | interview_sessions/questions 模型 + 迁移 | `models/interview.py` |
| 26 | AI 面试官 + 面试服务 | `rag/interviewer.py`、`services/interview_service.py` |
| 27 | Interview API | `schemas/interview.py`、`api/interview.py` |
| 28 | 数据导出服务 + API | `services/export_service.py`、`api/export.py` |
| 29 | 前端 Chat UI | `api/chat.ts`、`api/streamClient.ts`、`store/chatStore.ts`、`pages/Chat.tsx` |
| 30 | 前端 Interview UI | `api/interview.ts`、`pages/Interview.tsx` |
| 31 | 前端 Settings UI（导出 + 提醒） | `pages/Settings.tsx` |
| 32 | Dashboard 完整版（学习曲线 + 面试历史） | 更新 `pages/Dashboard.tsx` |

**V2.3 交付物**：基于知识点的 RAG 问答 → AI 模拟面试 → 薄弱分析 → 数据导出

---

## 七、文件清单

### 后端新增

**认证** (V2.1)
- `backend/app/models/user.py`
- `backend/app/schemas/auth.py`
- `backend/app/services/auth_service.py`
- `backend/app/api/auth.py`
- `backend/app/utils/deps.py`

**间隔复习** (V2.1)
- `backend/app/models/review.py`
- `backend/app/schemas/review.py`
- `backend/app/services/review_service.py`
- `backend/app/api/review.py`

**导入** (V2.2)
- `backend/app/models/import_job.py`
- `backend/app/schemas/import.py`
- `backend/app/services/import_service.py`
- `backend/app/api/import.py`

**学习路径** (V2.2)
- `backend/app/models/path.py`
- `backend/app/schemas/path.py`
- `backend/app/services/path_service.py`
- `backend/app/api/paths.py`

**RAG + Chat** (V2.3)
- `backend/app/models/chat.py`
- `backend/app/schemas/chat.py`
- `backend/app/services/chat_service.py`
- `backend/app/api/chat.py`

**AI 面试** (V2.3)
- `backend/app/models/interview.py`
- `backend/app/schemas/interview.py`
- `backend/app/services/interview_service.py`
- `backend/app/api/interview.py`

**导出** (V2.3)
- `backend/app/services/export_service.py`
- `backend/app/api/export.py`

**RAG 管线** (V2.3)
- `backend/app/rag/llm.py`
- `backend/app/rag/embedding.py`
- `backend/app/rag/retrieval.py`
- `backend/app/rag/prompts.py`
- `backend/app/rag/pipeline.py`
- `backend/app/rag/card_generator.py`
- `backend/app/rag/extractor.py`
- `backend/app/rag/interviewer.py`

### 后端修改
- `backend/app/models/note.py` — 新增字段 + chunk 关系
- `backend/app/models/__init__.py` — 注册新模型
- `backend/app/api/router.py` — 注册新路由
- `backend/app/services/note_service.py` — user_id 过滤 + 自动嵌入
- `backend/app/main.py` — APScheduler 定时任务

### 前端新增
- `frontend/src/api/auth.ts`、`review.ts`、`chat.ts`、`interview.ts`、`import.ts`、`paths.ts`、`export.ts`、`streamClient.ts`
- `frontend/src/store/authStore.ts`、`chatStore.ts`
- `frontend/src/pages/Login.tsx`、`Register.tsx`、`Chat.tsx`、`Review.tsx`、`Interview.tsx`、`Import.tsx`、`Paths.tsx`、`Dashboard.tsx`、`Settings.tsx`
- `frontend/src/components/AuthRoute.tsx`
- `frontend/src/components/chat/` (ConversationList, MessageBubble, ChatInput)

### 前端修改
- `frontend/src/App.tsx` — 路由 + 守卫
- `frontend/src/components/Layout.tsx` — 侧边栏 + 用户信息

---

## 八、验证方式

### V2.1 验证
1. 注册 → 登录 → Token 校验 → 数据隔离
2. 创建知识点 → 自动生成 3 张复习卡片
3. 复习评分 → SM-2 更新 card 上的 next_review_at / ease_factor / interval_days
4. 编辑卡片 / 标记"不好"
5. Dashboard 显示今日待复习数量 + 掌握度分布

### V2.2 验证
1. 粘贴文本 → 创建 import_job → AI 提取草稿
2. 草稿列表展示 → 用户勾选/编辑 → 确认 → 生成 notes
3. 生成学习路径 → 路径详情正确

### V2.3 验证
1. 知识点自动嵌入 → note_chunks 表有记录
2. Chat 对话 → SSE 流式输出 → 引用来源正确
3. 开始面试 → 多题作答 → 每题评分 → 结束面试 → 总结
4. 面试历史回放 → 薄弱知识点聚合
5. 导出 JSON / Markdown / Anki CSV 数据完整

---

## 九、面试场景关联

| 场景 | 项目中的体现 |
|------|------------|
| "JWT 认证流程怎么设计？" | 注册 → 登录 → Token 校验 → 刷新 |
| "密码怎么存储？" | bcrypt 哈希 |
| "怎么实现数据隔离？" | 每张表有 user_id，API 中间件自动过滤 |
| "FastAPI 依赖注入怎么用？" | Depends(get_db)、Depends(get_current_user) |
| "SSE vs WebSocket 怎么选？" | AI 回答单向流，SSE 更简单 |
| "SM-2 算法怎么实现？" | ease_factor / interval_days 递增 / quality 评分，状态存 card 而非 note |
| "RAG 检索效果不好怎么优化？" | note_chunks 分块 + HNSW 索引 + chunk_size 调参 |
| "多 LLM 怎么切换？" | 工厂模式 + 配置化 |
| "为什么用 pgvector 不用 Milvus？" | 个人项目够用，减少运维，trade-off 是规模上限 |
| "怎么控制 AI 调用成本？" | 生成一次存库 + ai_call_logs 追踪 + 复习不调 API |
| "定时任务怎么实现？" | APScheduler + FastAPI lifespan |
| "导入数据怎么保证质量？" | 草稿确认流程，AI 提取 → 用户筛选 → 再入库 |
