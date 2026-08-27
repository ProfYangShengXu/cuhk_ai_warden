# cuhk_ai_warden · AI 导员

自动化你的学校事务：**Blackboard 通知 + QQ 邮箱播报**，新动态自动推送（配合 Hermes cron 或 Windows 任务计划程序）。

## 功能

| 命令 | 干什么 |
|------|--------|
| `python ai_warden.py check` | 检查 .env 配置是否完整 |
| `python ai_warden.py bb` | 扫描 Blackboard 通知/附件，输出新动态 |
| `python ai_warden.py mail` | 扫描 QQ 邮箱新邮件，输出摘要 |
| `python ai_warden.py all` | 两个都跑 |

- 首次运行只建立状态（不输出），之后有新内容才输出 → 适合挂定时任务，没新东西零打扰
- 状态文件在 `state/` 目录，删掉 = 重新从全量开始

## 安装（三分钟）

1. **装 Python 3.8+**（勾选 Add to PATH）：https://www.python.org/downloads/
2. **装 Git for Windows**（自带 curl，BB 登录要用）：https://git-scm.com/download/win
3. 复制 `.env.example` 为 `.env`，填你的信息（见下）

## 配置 .env

| 变量 | 怎么拿 |
|------|--------|
| `CUHK_STUDENT_ID` | 你的学号 |
| `CUHK_BB_PASSWORD` | 学校账号密码 |
| `QQ_EMAIL` | 你的 QQ 邮箱（收学校转发邮件用的） |
| `QQ_IMAP_AUTHCODE` | QQ 邮箱网页版 → 设置 → 账户 → 开启 IMAP/SMTP → 生成 16 位授权码 |

> 学校邮件需要先在 Outlook 网页版设置**转发规则**到你的 QQ 邮箱（设置 → 邮件 → 转发）。

## 定时运行

- **Hermes 用户**：脚本 stdout 非空才推送，配 no_agent cron（见技能 cuhk-bb-warden）
- **Windows 任务计划程序**：`python ai_warden.py bb` 每天早上 8 点；`python ai_warden.py mail` 每 30 分钟

## 常见问题

- **bb 报 LOGIN_FAIL**：检查学号/密码，或学校改登录方式了
- **mail 报 MAIL_SCAN_ERROR**：检查授权码是否有效（重新生成）
- **找不到 curl**：Git for Windows 没装，或没加 PATH

## 安全

- `.env` 含密码和授权码，**不要发给任何人、不要提交 git**（.gitignore 已排除）
- 脚本不上传任何数据，全部本地运行
