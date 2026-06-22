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
  5. 分两个 commit 提交全部未提交改动(commit 1: `82f9dc6` V5.0 重构 90 文件;commit 2: `ee3f756` 用户级 LLM 配置 3 文件)
  6. 验证无回归:后端 `pytest` 46 passed / 0 failed;前端 `npm run build` 通过(仅 chunk size 警告,已知问题)
- **未决/待确认**:
  - `docs/CONTEXT.md` 仍待补:§4 删除已移除 API 端点、§5 users 表加 `llm_provider/llm_api_key/llm_model`、§10 加更新日志(见下方待办 1)

---

## 待办(下次会话从这里接着干)

### 1. [高] 提交 V5.0 大重构 + 用户级 LLM 配置改动 ✅ 已完成(2026-06-22)

- **commit 1** `82f9dc6`: V5.0 精简重构(90 文件,+2350/-6316)——删 demo 模块、Dashboard 重写、侧边栏扁平化、复习三色按钮、Chat 保存为笔记、八股分类预设、HANDOFF 机制
- **commit 2** `ee3f756`: 用户级 LLM 配置(3 文件)——alembic `86386e2a8c02` + `df925bb28bcf` 加 users 三字段、`test_v41_security.py` email 校验
- **验证**:`pytest` → **46 passed / 0 failed**;`npm run build` → 通过(仅 chunk size 警告,已知问题)
- **当前状态**:分支 `feature/v3.0-polish`,工作区干净,**未 push**(AGENTS.md 禁止自动 push,等用户决定是否合并到 main 或继续开发)

### 2. [中] 同步 CONTEXT.md(下次会话做)

更新 CONTEXT.md:
- §4 API 端点表:删除 traces/workspace/eval/portfolio/paths 相关行(这些 router 已删)
- §5 数据库 Schema:补 users 表的 `llm_provider / llm_api_key / llm_model` 三字段
- §7 进度:V5.0 验证结果块已写
- §10 更新日志:加一条「2026-06-22 | 用户级 LLM 配置 + HANDOFF 机制 + 提交 V5.0」

### 3. [低] V5.0 重构后可能遗留的点 ✅ 已验证无问题(2026-06-22)
- ✅ `pytest` 46 passed
- ✅ `npm run build` 通过
- ⚠️ 未检查 `frontend/src/App.tsx` 路由是否还有指向已删页面的引用(但 build 通过说明无编译错误,运行时风险低)
- ✅ alembic 已在 `df925bb28bcf (head)`,数据库升级正常

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
