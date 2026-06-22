# HANDOFF.md — Agent 会话交接便签

> **用途**:轻量级增量交接文件。每次会话**开始前读**,**结束前写**。
> 与 `docs/CONTEXT.md` 的分工:
> - `CONTEXT.md` = 项目全量档案(架构/进度/API/Schema/已知问题),稳定,低频改动
> - `HANDOFF.md` = 当前工作便签(上次干到哪 / 下次该干啥 / 未决问题),高频改动
>
> **写法约定**:最新一次会话放在最上面(倒序),只保留最近 ~5 次记录,更早的归档进 CONTEXT.md 更新日志。

---

## 最近一次会话

- **日期**:2026-06-22
- **Agent / 工具**:ZCode (builtin: GLM-5.2)
- **做了什么**:
  1. 建立跨工具会话交接机制:新增本文件 `docs/HANDOFF.md`
  2. 在 `CLAUDE.md` / `AGENTS.md` 加入「开始前读 HANDOFF、结束前写 HANDOFF」规则
  3. 梳理当前未提交改动(见下方「待办」第 1 项)
  4. 清理误创建的 `nul` 垃圾文件
- **未决/待确认**:无

---

## 待办(下次会话从这里接着干)

### 1. [高] 提交 V5.0 大重构 + 用户级 LLM 配置改动

当前 `feature/v3.0-polish` 分支有大批未提交改动,分两类:

**A. V5.0 精简重构**(CONTEXT.md 已记录,见 §7 Phase 5)
- 删除 demo 模块:backend `agents/`(8 文件)、`mcp/`(2 文件)、`api/{eval,paths,portfolio,traces,workspace}.py`、`models/{agent,eval,path}.py`、`schemas/path.py`、`services/{eval,path,portfolio}_service.py`、`rag/hybrid_retrieval.py`
- 删除前端:`pages/{AgentWorkspace,Paths,Portfolio,TraceLab}.tsx`、`api/{eval,paths,portfolio,traces,workspace}.ts`、`constants/agent.ts`
- main.py / router.py / models/__init__.py 清理引用
- Dashboard 重写、侧边栏扁平化、复习三色按钮、笔记快速输入、Chat 保存为笔记、八股分类预设等 UX 改进
- 涉及测试改动,目标 46 passed

**B. 用户级 LLM 配置**(CONTEXT.md **未记录**,需补)
- 新增 alembic 迁移:`86386e2a8c02`(加 `users.llm_provider / llm_api_key`)+ `df925bb28bcf`(加 `users.llm_model`)
- `models/user.py` 同步加了三字段
- 新增测试 `backend/tests/test_v41_security.py`(email 校验单元测试)
- 新增 `docs/V4.1-quality-ux-redesign.md`

**建议提交方式**(分两个 commit 更清晰):
```
commit 1: feat: V5.0 simplify refactor - drop demo modules, refocus as daily learning tool
commit 2: feat: per-user LLM provider/key/model configuration
```
或合并为一个。等用户确认后再执行 `git add` + `git commit`,**不要自动 push**(网络不稳 + AGENTS.md 禁止自动 push)。

### 2. [中] 同步 CONTEXT.md

提交后更新 CONTEXT.md:
- §4 API 端点表:删除 traces/workspace/eval/portfolio/paths 相关行(这些 router 已删)
- §5 数据库 Schema:补 users 表的 `llm_provider / llm_api_key / llm_model` 三字段
- §7 进度:确认 V5.0 验证结果块已写(已写,但未提交)
- §10 更新日志:加一条「用户级 LLM 配置」

### 3. [低] V5.0 重构后可能遗留的点(下次跑一遍确认)
- 跑 `D:\Python\venvs\knowbase\Scripts\python.exe -m pytest -q` 确认 46 passed
- 跑 `npm run build` 确认前端通过
- 检查 `frontend/src/App.tsx` 路由是否还有指向已删页面的引用
- 检查 `docker compose up -d` 后 alembic 能升级到 `df925bb28bcf`

---

## 如何使用本文件(给任意 Agent 的操作说明)

**会话开始时**:
1. 读 `docs/CONTEXT.md`(项目全貌)
2. 读本文件(最近工作 + 待办)
3. `git status` 确认工作区是否干净,理解未提交改动

**会话结束时(强制)**:
1. 把本次会话内容加到「最近一次会话」(旧的往下移或归档)
2. 更新「待办」:完成的标记完成,新发现的待办加进去
3. 如有重要架构/接口/Schema 变更,**同时**更新 `docs/CONTEXT.md`
