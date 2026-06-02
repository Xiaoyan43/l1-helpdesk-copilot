# Entra / M365 lab 租户 + Graph 应用注册（逐步指南）

> ⚠️ **只在免费的测试租户上做。** 用 `*.onmicrosoft.com` 的测试用户。
> client secret 只放进 `.env`（已被 `.gitignore` 忽略），**绝不提交、绝不用生产租户**。
> 全程保持 `GRAPH_DRY_RUN=true`，等你亲眼确认请求无误，再切 `false` 真正执行。

整个过程约 15–20 分钟。完成后，应用就能在你的 lab 租户里真的**建用户 / 重置密码 / 加入组**。

---

## 1) 建一个免费的 Microsoft Entra (Azure AD) 租户
> **2026 现状**：免费 E5 开发者沙箱已限定 Visual Studio 订阅 / 微软合作伙伴；普通人走
> **免费 Entra 租户**最省事。它免费（绑卡仅验证身份、**不扣费**），足以真跑
> **建用户 / 改密 / 加组**——这三个是纯 Entra 操作，无需任何 M365 许可。
> `assign_license`（分配许可）因免费租户没有付费 SKU，继续保持 dry-run。

1. 用任意微软账号登录 **https://entra.microsoft.com**
2. 左侧 **Identity → Overview → Manage tenants → ＋ Create**
3. Tenant type 选 **Microsoft Entra ID** → Next
4. 填 **Organization name**、**Initial domain name**（→ `<你的域名>.onmicrosoft.com`）、
   **Country/Region** → **Review + create**（首次可能要求手机/信用卡验证身份——不扣费）
5. 创建完成后，右上角**切换到这个新租户**，记下租户域名 `<xxx>.onmicrosoft.com`。

> 想让 `assign_license` 也真跑？可临时开一个 M365 E5 / Entra ID P2 免费试用（绑卡、记得取消），
> 后续步骤完全一样，只是多了可分配的 SKU。本作品默认不需要。

## 2) 注册一个应用（拿 client id / secret）
进入 **https://entra.microsoft.com** → 用管理员账号登录 → 左侧 **Identity → Applications → App registrations**：
1. **New registration** → 名字填 `HelpDesk Copilot (lab)` → Supported account types 选 **Single tenant** → **Register**。
2. 在 **Overview** 页复制两个值：
   - **Application (client) ID** → `.env` 的 `AZURE_CLIENT_ID`
   - **Directory (tenant) ID** → `.env` 的 `AZURE_TENANT_ID`
3. 左侧 **Certificates & secrets** → **New client secret** → 描述随意、有效期选最短 → **Add** →
   **立刻复制 Value 列**（不是 Secret ID，且只显示这一次）→ `.env` 的 `AZURE_CLIENT_SECRET`。

## 3) 给应用授予 Graph 权限（Application 权限，app-only）
左侧 **API permissions** → **Add a permission** → **Microsoft Graph** → **Application permissions**，
搜索并勾选下面这些，然后 **Add permissions**：

| 权限 | 用途 |
|---|---|
| `User.ReadWrite.All` | 建用户、重置密码、分配许可 |
| `Group.ReadWrite.All` | 把用户加入组 |
| `Directory.Read.All` | 读取用户/组列表（发现 id） |
| `Organization.Read.All` | 读取可用许可 SKU（`/graph/skus`） |

最后一定要点 **Grant admin consent for \<租户\>** → 状态变成绿色对勾。
（app-only 权限必须管理员同意，否则所有调用会 403。）

## 4) 填 `.env` 并先用 dry-run 自检
```env
AZURE_TENANT_ID=<Directory (tenant) ID>
AZURE_CLIENT_ID=<Application (client) ID>
AZURE_CLIENT_SECRET=<刚复制的 secret Value>
GRAPH_DRY_RUN=true          # 先保持 true
```
重启服务，打开 `/docs`：
- `GET /healthz` 应显示 `"graph_creds_ready": true`。
- `GET /graph/skus`：能列出租户里的许可（拿到 `skuId` 备用）。
- `GET /graph/groups`：拿到目标组的 `id`。
- 试 `POST /actions/create-user`，看返回的 `request` 是不是你预期的 Graph 调用（密码会脱敏）。

## 5) 真正执行（确认无误后）
把 `.env` 改成 `GRAPH_DRY_RUN=false`，重启。然后建议的最小验证顺序：
1. `POST /actions/create-user`（body 只需 `display_name` + `user_principal_name`，UPN 用 `xxx@<你的租户>.onmicrosoft.com`）→ 记下返回的 `generated_password`。
2. `GET /graph/users` 确认新用户出现，拿到其 `id`。
3. `POST /actions/assign-license`（`user`=新用户 UPN，`sku`=第 4 步拿到的 `skuId`）。
4. `POST /actions/add-to-group`（`user`=用户 `id`，`group`=组 `id`）。
5. `POST /actions/reset-password`（`user`=UPN）。
6. `GET /audit` 复核每一步都被记录、且无明文密码。

## 常见报错
- **403 / insufficient privileges**：第 3 步漏了某个权限，或忘了 **Grant admin consent**。
- **assignLicense 报 usageLocation 缺失**：建用户时已默认设 `US`，老用户可重建或先 PATCH。
- **重置密码 403**：app-only 不能重置“管理员”用户的密码——用普通测试用户。
- **认证失败**：tenant/client id 或 secret 填错，或 secret 已过期（重建一个）。

> CV 表述建议：*“在隔离的 M365 开发者租户上，通过 Microsoft Graph（app-only / client-credentials）实现 L1 账号操作（建号/改密/加组/发许可），默认 dry-run、密码脱敏审计。”*
