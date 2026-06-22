# 🤖 tgcodex-bot

**Telegram ↔ Codex AI 远程控制桥** — 在手机上通过 Telegram 遥控 Codex AI、执行终端命令、传输文件。

**Telegram Remote Control Bridge for Codex AI** — Control your Codex AI from your phone via Telegram: run shell commands, transfer files, chat with AI.

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen.svg)](requirements.txt)

---

## ✨ 功能 / Features

| 功能 | 说明 |
|------|------|
| 🎮 **远程命令** | 通过 Telegram 在手机端执行 Termux/Shell 命令 |
| 🤖 **AI 对话** | 直接聊天，消息自动转发给 Codex AI 回复 |
| 📁 **文件传输** | 发送文件/图片到 Telegram，自动保存到设备 |
| 📂 **项目切换** | 预设项目目录快速切换 |
| 🇨🇳 **中文支持** | 完全中文化命令别名 |
| 🔒 **用户认证** | 可设置 `allowed_users` 白名单 |
| ⚡ **异步处理** | 耗时操作后台执行，不阻塞消息接收 |
| 📦 **零依赖** | 纯 Python 3 标准库，开箱即用 |

> **典型场景**：你躺在床上 / 在外面，想用手机让手机上的 Codex 干活？打开 Telegram 跟 Bot 说话就行。

---

## 🚀 快速开始 / Quick Start

### 1. 创建 Telegram Bot

在 Telegram 中搜索 [@BotFather](https://t.me/BotFather)，发送 `/newbot`，按提示创建 Bot，拿到 **Token**（形如 `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`）。

### 2. 下载 / 克隆

```bash
git clone https://github.com/malaxiya20250530-glitch/tgcodex-bot.git
cd tgcodex-bot
```

### 3. 配置

```bash
cp config.example.json config.json
# 编辑 config.json，填入你的 Bot Token
```

```json
{
  "telegram_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
  "allowed_users": [],
  "home_dir": "/data/data/com.termux/files/home",
  "projects": {
    "home": "/data/data/com.termux/files/home",
    "project-a": "/data/data/com.termux/files/home/projects/a",
    "project-b": "/data/data/com.termux/files/home/projects/b"
  }
}
```

> ⚠️ `allowed_users` 设为空数组 `[]` 表示允许所有用户。建议填上你的 Telegram User ID 以启用白名单。

### 4. 运行

```bash
python3 bot.py
```

看到 `✅ @your_bot 已上线` 就成功了。

### 5. 在 Telegram 中使用

搜索你的 Bot，发送 `/start` 或 `/help` 查看可用命令。

---

## 📖 命令参考 / Commands

| 命令 | 中文别名 | 说明 |
|------|---------|------|
| `/cd [name]` | `/切换` | 切换到预设项目目录 |
| `/exec <cmd>` | `/执行` | 执行 Shell 命令 |
| `/files [path]` | `/文件` | 列出目录文件 |
| `/cat <file>` | `/查看` | 查看文件内容 |
| `/help` | `/帮助` | 显示帮助信息 |

**<任意文本>** → 自动发给 Codex AI 并返回回复。

---

## 🔧 配置详解 / Configuration

| 字段 | 类型 | 说明 |
|------|------|------|
| `telegram_token` | string | BotFather 给你的 Bot Token |
| `allowed_users` | int[] | Telegram User ID 白名单（空=全部允许） |
| `home_dir` | string | 默认工作目录 |
| `projects` | object | 项目名称 → 路径映射，用于 `/cd` 快速切换 |
| `upload_dir` | string | 文件上传保存目录（默认 `telegram_uploads/`） |

---

## 🏗️ 项目结构 / Project Structure

```
tgcodex-bot/
├── bot.py               # 👈 主程序
├── config.example.json  # 配置模板
├── config.json          # 实际配置（已 gitignore）
├── telegram_uploads/    # 上传文件保存目录
├── .gitignore
├── requirements.txt     # 无依赖 :)
└── README.md
```

---

## 🛡️ 安全提醒 / Security

- ⚠️ **Bot 具有 Shell 权限** — 请谨慎设置 `allowed_users`
- ⚠️ **Token 不要提交到 Git** — `config.json` 已在 `.gitignore` 中
- ⚠️ **Bot 使用 `--dangerously-bypass-approvals-and-sandbox`** 调用 Codex，请确保只有你可信用户能访问

---

## 🧩 与 Codex 配合使用

这个 Bot 的杀手锏：**你可以通过 Telegram 让 Codex 自己写代码、改代码、部署**。

典型流程：

```
你 (TG) → Bot → Codex AI → Codex 写代码 → Bot 发结果给你
```

结合 `/exec` 命令，可以实现完整的远程开发工作流。

---

## 📜 许可证 / License

MIT License — 随意使用、修改、分发。

---

## 🌟 给个 Star？

如果这个项目对你有帮助，欢迎 ⭐ —— 让更多人看到它！

---

<p align="center">
  <sub>Made with ❤️ by <a href="https://github.com/malaxiya20250530-glitch">malaxiya20250530-glitch</a></sub>
</p>
