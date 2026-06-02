# L1 HelpDesk Copilot

> ⚠️ **个人作品 / Lab 专用，绝非生产系统。**
> 所有 LLM 调用走 Anthropic API；所有 Microsoft Graph 调用只针对一个**免费 M365 开发者租户**，
> 默认 `GRAPH_DRY_RUN=true`（只演练、不改租户）。请勿接入任何真实 / 生产凭据或数据。

一个面向 **IT Support (L1 / Help Desk)** 岗位的求职作品：把一条支持工单
→ 用 Claude 分类 → 对 markdown 知识库做 RAG 生成带引用的回复 →
对账号类请求调用 Microsoft Graph 在 lab 租户里真的执行 → 全程审计。

## 功能
1. **导入工单**：粘贴文本，或从样例 CSV 读。
2. **分类（Claude）**：类别、优先级、incident vs request、是否命中 KB 文章。
3. **RAG 回复**：检索 markdown 知识库，生成引用了相关文章的 L1 回复草稿。
4. **执行动作（Microsoft Graph，lab 租户）**：建用户 / 重置密码 / 加入组 / 分配许可。
5. **审计日志**：每次分类 + 执行的动作都落盘（`audit_log.jsonl`）。
6. **评测**：对 40–60 条标注工单跑评测，得到诚实的分类准确率。

## 技术栈
Python · FastAPI · Anthropic SDK (Claude) · Microsoft Graph REST (`azure-identity` + `httpx`)
· markdown KB + 轻量检索 · 极简 HTML UI。

## 快速开始
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # 按需填 key；不填也能用规则基线跑起来
uvicorn app.main:app --reload
# 单页 UI:   http://127.0.0.1:8000/
# API 文档:  http://127.0.0.1:8000/docs
```
不填任何 key 时，`USE_MOCK_LLM=true` 会用**本地规则基线**分类——方便离线 demo，
也是评测时和 Claude 对比的 baseline。

## 路线图（周末 MVP）
- [x] 阶段 0 · 脚手架（配置 / 数据模型 / 可跑的 FastAPI + 规则基线分类）
- [x] 阶段 1 · Claude 结构化分类 + CSV 导入
- [x] 阶段 2 · KB + RAG 带引用回复
- [x] 阶段 3 · 50 条标注测试集 + 评测脚本（`python -m eval.run_eval`）
- [x] 阶段 4 · Microsoft Graph 账号动作 + 审计日志 → 配置见 [`docs/m365-setup.md`](docs/m365-setup.md)
  - **已在真实免费 Entra 租户 live 验证**：`create_user → 201` · `reset_password → 204` · `add_to_group → 204`（应用授 User Administrator 角色，最小权限；密码脱敏审计）。`assign_license` 因免费租户无 SKU 保持 dry-run。
- [x] 阶段 5 · 极简单页 UI（`/`）：分类 + 引用回复 + 建议动作(dry-run执行) + 审计面板
- [x] 扩展 · **置信度阈值护栏**（分类置信度 < 阈值则拦截真实动作，需人工复核）+ **回复反馈按钮**（已解决/需升级，写入审计，形成人在环闭环）

> 求职/面试讲稿见 [`docs/pitch.md`](docs/pitch.md)；录 demo 的分镜脚本见 [`docs/demo-script.md`](docs/demo-script.md)。

## 评测结果（真实数字）

在 **50 条手工标注**工单上，对比规则基线（关键词计数）与 Claude（Haiku 4.5，
strict 结构化输出，`temperature=0` 可复现）：

| 字段 | 关键词基线 | Claude | 提升 |
|---|---|---|---|
| category（类别） | 80% | **92%** | +12 |
| incident vs request | 84% | **98%** | +14 |
| priority（优先级） | 54% | **74%** | +20 |
| kb_hit（KB 命中） | 60% | **72%** | +12 |
| category macro-F1 | 61% | **81%** | +20 |

复现：`python -m eval.run_eval --engine both --show-errors`

**诚实的方法说明 / 局限：**
- 测试集仅 **50 条、单人标注**——数字用于作品演示，非严谨基准；`temperature=0` 让结果可复现，但样本小，几个点的差异不应过度解读。
- **priority** 起初仅 54%（与基线持平），诊断后发现是提示词 rubric 与标注口径不一致——**收紧 rubric + 加 few-shot 校准**后升到 74%；它本质主观，人类标注一致性也有限。
- **kb_hit** 是标注最粗的字段：约 11/14 个"错误"其实是"我标 NONE、Claude 给了合理 KB"的口径分歧，而非模型错误。
- 回复用的 KB 检索（BM25）与分类器的 kb_hit 字段**相互独立**——即使分类器选错，检索仍常能命中对的文章（见 demo 中钓鱼工单一例）。

> **CV 表述（可直接用）**：*"在 50 条手工标注的 IT 工单测试集上，基于 Claude（Haiku 4.5）+ strict 结构化输出的分类器，将类别准确率从 80%（关键词基线）提升到 92%、incident-vs-request 84%→98%、优先级经 rubric+few-shot 校准后 54%→74%、类别 macro-F1 61%→81%。"*

## 目录结构
```
app/        FastAPI 应用 (config / models / classifier / kb / responder / graph / audit / main)
kb/         markdown 知识库文章
data/       样例工单 CSV（含标注）
eval/       评测脚本（结果写入 eval/last_results.json，已 gitignore）
```
