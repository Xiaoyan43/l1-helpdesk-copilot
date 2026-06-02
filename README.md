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
# 打开 http://127.0.0.1:8000/docs
```
不填任何 key 时，`USE_MOCK_LLM=true` 会用**本地规则基线**分类——方便离线 demo，
也是评测时和 Claude 对比的 baseline。

## 路线图（周末 MVP）
- [x] 阶段 0 · 脚手架（配置 / 数据模型 / 可跑的 FastAPI + 规则基线分类）
- [x] 阶段 1 · Claude 结构化分类 + CSV 导入
- [x] 阶段 2 · KB + RAG 带引用回复
- [x] 阶段 3 · 50 条标注测试集 + 评测脚本（`python -m eval.run_eval`）
- [ ] 阶段 4 · Microsoft Graph 账号动作（默认 dry-run）
- [ ] 阶段 5 · 极简 UI + 审计日志页

## 目录结构
```
app/        FastAPI 应用 (config / models / classifier / kb / responder / graph / audit / main)
kb/         markdown 知识库文章
data/       样例工单 CSV（含标注）
eval/       评测脚本
```
