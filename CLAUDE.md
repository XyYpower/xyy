# CLAUDE.md — Claude Code 项目指令

> 本文件是 Claude Code 启动时自动读取的项目指令文件。

## 快速上手

开始工作前，**先读 `docs/CONTEXT.md`** 了解项目全貌和最新进度。

## 项目简介

KnowBase — AI 驱动的个人知识库。FastAPI 后端 + React 前端 + PostgreSQL (pgvector)。

## 行为规范

### 通用
- 使用中文与用户交流
- 代码注释使用中文
- 修改代码前先理解上下文，遵循现有代码风格
- 每次完成重要阶段后，更新 `docs/CONTEXT.md` 对应章节
- 不要删除或覆盖其他 Agent 的文档，除非明确指示

### 后端 (Python / FastAPI)
- 异步优先，所有数据库操作使用 `async/await`
- 新增 API 端点必须在 `schemas/` 定义 Pydantic 模型
- 业务逻辑放在 `services/` 层，API 路由只做参数校验和调用
- 数据库变更必须通过 Alembic 迁移，不要手动改表

### 前端 (React / TypeScript)
- 函数组件 + Hooks，不使用 class 组件
- 新页面添加到 `src/pages/`，路由在 `App.tsx` 注册
- API 调用统一通过 `src/api/client.ts` 的 Axios 实例
- UI 组件优先使用 Ant Design，样式辅助用 Tailwind CSS

### Git
- 不要自动 commit 或 push，除非用户明确要求
- Commit message 使用英文，格式：`feat: / fix: / docs: / chore:`
- 功能开发应在独立分支 `feature/xxx` 上进行

### 多 Agent 协作
- 开始任务前先 `git status`，确认是否有其他 Agent 未提交的修改
- 如果有未提交的修改，先阅读理解再继续，**不要覆盖未理解的改动**
- 每次完成重要阶段后，更新 `docs/CONTEXT.md` 中对应章节（进度、已知问题、更新日志）
- 如果修改了 API 接口或数据库结构，同步更新 `docs/CONTEXT.md` 中的 API 端点和 Schema 章节

### 测试
- 后端测试放在 `backend/tests/`
- 前端暂无测试要求，后续按需添加

## 文件引用

- 共享项目上下文：`docs/CONTEXT.md`（两个 Agent 共用，保持同步）
- Codex 指令：`AGENTS.md`（与本文件同级）
