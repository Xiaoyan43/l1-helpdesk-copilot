# Demo 分镜脚本 / Screen-recording shot list

> 目标：录一段 **60–90 秒**的作品集 demo。
> Mac 录屏：**Cmd + Shift + 5** 选区域录制（或用 QuickTime「新建屏幕录制」）。

## 录制前
1. 终端：`source .venv/bin/activate && uvicorn app.main:app --reload`，浏览器开 `http://127.0.0.1:8000/`
2. `.env`：`USE_MOCK_LLM=false`（用真 Claude，顶部徽章应是 `llm: claude`）
3. 想演示**真实 Graph 执行**：临时把 `.env` 的 `GRAPH_DRY_RUN=false`（录完改回 `true`）
4. 清掉旧审计让画面干净：`rm -f audit_log.jsonl`

## 分镜（顺序 + 建议字幕）
| 时间 | 画面 | 字幕 |
|---|---|---|
| 0:00 | README 顶部 / 标题 | "L1 HelpDesk Copilot — classify · cited RAG reply · real Microsoft Graph actions" |
| 0:08 | 下拉选 *Suspicious email…(T006)* → 点「分类+生成回复」，停在分类 chips + Claude 引用回复 | "Claude classifies and drafts a citation-grounded L1 reply" |
| 0:25 | 点「↑ 需升级」→ 审计面板出现 feedback 条 | "Human-in-the-loop feedback is audited" |
| 0:35 | 输入含糊工单（如 subject `help` / body `idk something is weird…`）→ other/0.4 → 动作面板黄色护栏 → 点执行被拦 | "Low-confidence triage blocks real actions until human review" |
| 0:50 | （需 `GRAPH_DRY_RUN=false`）选 *New hire setup(T002)* → 建议 create_user → 填 Maria → 执行 → 201 + 临时密码 + Graph 请求(密码脱敏) | "One click provisions a real account via Microsoft Graph" |
| 1:05 | **切到 Entra 门户 → 用户 → Maria Chen**（只有你能拍） | "Verified live in Microsoft Entra" |
| 1:15 | 终端 `python -m eval.run_eval --engine both` 跑出对比 | "92% category accuracy on a 50-ticket labeled set" |

## 只有你能拍的镜头
- **第 1:05 帧：Entra 门户里的 Maria / Sales Team**——这是你的微软账号，我无法登录你的浏览器会话。
- 任何需要你账号登录的画面。

## 我（助手）已截好、可直接用的静态图（在对话里，右键保存）
1. 分类 + Claude 引用回复 + 反馈按钮 + 审计面板
2. 置信度护栏拦住执行（other/0.4）
3. 建用户 dry-run 结果 + 将发送的 Graph 请求体（密码 `***REDACTED***`）

> 想把静态图放进 README：截上面几帧存到 `docs/img/` 再在 README 用 `![](docs/img/xxx.png)` 引用。

## 录完别忘
- `.env` 的 `GRAPH_DRY_RUN` 改回 `true`（安全默认）。
