# 项目讲稿 / Interview Pitch — L1 HelpDesk Copilot

> 给求职用：怎么在简历、面试里介绍这个作品。数字都来自真实评测 / live 运行，可如实陈述。

## 一句话（elevator）
> 一个 L1 Help Desk 助手：把一条 IT 工单自动**分类**（类别 / 优先级 / incident-vs-request / KB 命中），
> 对 markdown 知识库做 **RAG** 生成带引用的回复草稿，并对账号类请求通过 **Microsoft Graph**
> 在隔离的 Entra 租户里**真的执行**（建用户 / 重置密码 / 加入组），全程**审计、密码脱敏**。

## 为什么做
针对 IT support / help desk 岗位：用一个能跑的作品证明我**既懂 L1 工作流，又会用现代工具把它自动化**——
而不是简历上空写"熟悉 AI / 自动化"。

## 2–3 分钟讲稿（STAR）
- **背景**：L1 的日常是分流工单、查知识库、做账号操作（建号/改密/加组）。我想把这套流程用 Claude + Graph 自动化。
- **做法**：Python/FastAPI 后端；Claude(Haiku 4.5) 用 **strict 结构化输出** 做分类；对 6 篇 markdown KB 做 **BM25 检索 + 引用式作答**；账号操作走 **Microsoft Graph（app-only / client-credentials）**，默认 dry-run、可一键切真跑；每次分类和动作都写**追加式审计日志**（明文密码绝不入库）。
- **怎么证明它有效**：我建了一个 **50 条手工标注**的测试集，写了评测脚本，和一个关键词基线逐字段对比。
- **结果**：类别 80%→**92%**、incident-vs-request 84%→**98%**、优先级 54%→**74%**、macro-F1 61%→**81%**；Graph 三个动作在真实 Entra 租户 **live 验证**：建用户 201、改密 204、加组 204。

## 关键数字（背下来）
| 指标 | 基线 | Claude |
|---|---|---|
| category | 80% | 92% |
| incident vs request | 84% | 98% |
| priority | 54% | 74% |
| kb_hit | 60% | 72% |
| macro-F1 | 61% | 81% |

Graph live：`create_user → 201` · `reset_password → 204` · `add_to_group → 204`（lab Entra 租户）。

## 最能加分的部分：我怎么排错的（面试官爱听）
1. **优先级一开始没提升**：诊断发现是我的提示词 rubric 和标注口径互相矛盾 → 收紧 rubric + 加 few-shot 校准 → priority 54%→74%。（体现：会做误差分析，不是调参碰运气。）
2. **改密报 403**：发现 app-only 建用户够，但**重置密码是特权操作**，需给应用分配 **User Administrator** 目录角色——这正是真实 L1 的最小权限模型。
3. **改密报 404**：Entra 复制延迟，刚建的用户按 UPN 查不到 → 改用对象 id 重试。
4. **个人 Gmail 账号建不了租户**：个人 MSA 只有占位目录 → 改用 Azure 免费账户建出真租户。
5. **配置被空环境变量盖住**：调整了 settings 源优先级，让 `.env` 优先。

## 怎么现场 demo（3 分钟）
1. `uvicorn app.main:app --reload` → 打开 `http://127.0.0.1:8000/`
2. 下拉选一条样例工单 → **分类 + 生成回复**：展示类别/优先级/引用的 KB / 回复草稿。
3. 打开 `/docs` 展示 API；讲 strict tool-use 结构化输出。
4. （可选真跑）把 `.env` 的 `GRAPH_DRY_RUN=false` → UI 里执行 create-user → 回 Entra 门户看新用户 → 看审计面板（密码脱敏）。
5. 终端 `python -m eval.run_eval --engine both` 现场跑出准确率。

## 诚实的边界（主动说，显得可信）
- 测试集仅 **50 条、单人标注**——用于作品演示，非严谨基准。
- 只跑在**样例工单 + 免费 lab 租户**上，**非生产**。
- `assign_license` 因免费 Entra 无付费 SKU，保持 dry-run（代码就绪、可展示请求体）。
- 没做多用户登录 / 向量数据库 / 真实工单系统集成——这些是刻意控制的 scope。

## 简历 bullet（英文，可直接用）
- Built an L1 help-desk copilot (Python/FastAPI + Claude): classifies tickets (category, priority, incident-vs-request, KB hit) with strict structured tool-use; on a 50-ticket hand-labeled set, improved category accuracy 80%→92%, incident-vs-request 84%→98%, priority 54%→74% (via rubric + few-shot calibration), macro-F1 61%→81% vs. a keyword baseline.
- Added BM25 retrieval over a markdown KB to generate citation-grounded L1 reply drafts (RAG).
- Integrated Microsoft Graph (app-only / client-credentials, azure-identity) to provision/manage accounts in an isolated Entra tenant — live-verified create-user (201), reset-password (204), add-to-group (204) — with the app granted the User Administrator role (least privilege), default dry-run, and an append-only, password-redacting audit log.
