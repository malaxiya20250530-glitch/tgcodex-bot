#!/usr/bin/env python3
"""
tgcodex-bot — Telegram ↔ Codex AI 远程控制桥
==============================================
在手机上通过 Telegram 遥控 Codex AI、执行终端命令、传输文件。

零外部依赖，仅用 Python 3 标准库。
"""

import subprocess
import urllib.request
import json
import os
import sys
import time
import threading
import logging

# ── 日志 ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("tgcodex")

# ── 配置 ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
UPLOAD_DIR_NAME = "telegram_uploads"  # 会被 cfg 覆盖

cfg = None
current_dir = None
upload_dir = None


# ══════════════════════════════════════════════════
#  配置加载
# ══════════════════════════════════════════════════

def load_config():
    """加载配置。如文件不存在，从 example 模板生成一份。"""
    if not os.path.exists(CONFIG_PATH):
        example = CONFIG_PATH.replace("config.json", "config.example.json")
        if os.path.exists(example):
            log.warning("config.json 不存在，已从 config.example.json 复制")
            import shutil
            shutil.copy(example, CONFIG_PATH)
        else:
            log.error("config.json 和 config.example.json 都不存在！")
            sys.exit(1)

    with open(CONFIG_PATH) as f:
        return json.load(f)


def init():
    """初始化全局状态"""
    global cfg, current_dir, upload_dir

    cfg = load_config()

    home = cfg.get("home_dir", os.path.expanduser("~"))
    projects = cfg.get("projects", {"home": home})
    current_dir = home

    upload_dir_name = cfg.get("upload_dir", UPLOAD_DIR_NAME)
    upload_dir = os.path.join(SCRIPT_DIR, upload_dir_name)
    os.makedirs(upload_dir, exist_ok=True)

    return home, projects


# ══════════════════════════════════════════════════
#  Telegram API 封装
# ══════════════════════════════════════════════════

def tg_api(method, data=None):
    """调用 Telegram Bot API"""
    url = f"https://api.telegram.org/bot{cfg['telegram_token']}/{method}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        log.warning("API %s: %s", method, e)
        return None


def download_file(file_id, save_path):
    """从 Telegram 下载文件"""
    r = tg_api("getFile", {"file_id": file_id})
    if not r or not r.get("ok"):
        return False
    file_url = (
        f"https://api.telegram.org/file/bot{cfg['telegram_token']}"
        f"/{r['result']['file_path']}"
    )
    try:
        with urllib.request.urlopen(file_url, timeout=120) as resp:
            with open(save_path, "wb") as f:
                f.write(resp.read())
        return True
    except Exception as e:
        log.warning("下载失败: %s", e)
        return False


def send_raw(chat_id, text, reply_to=None):
    """发送消息，返回 message_id"""
    if not text:
        return None
    data = {"chat_id": chat_id, "text": text[:4000]}
    if reply_to:
        data["reply_to_message_id"] = reply_to
    r = tg_api("sendMessage", data)
    if r and r.get("ok"):
        return r["result"]["message_id"]
    return None


def send(chat_id, text, reply_to=None):
    """发送可能较长的消息（自动分片 4000 字符）"""
    if not text:
        return
    for i in range(0, len(text), 4000):
        chunk = text[i : i + 4000]
        data = {"chat_id": chat_id, "text": chunk}
        if reply_to and i == 0:
            data["reply_to_message_id"] = reply_to
        tg_api("sendMessage", data)


def send_action(chat_id, action="typing"):
    """发送打字中…状态"""
    tg_api("sendChatAction", {"chat_id": chat_id, "action": action})


# ══════════════════════════════════════════════════
#  用户认证
# ══════════════════════════════════════════════════

def is_allowed(user_id):
    """检查用户是否被允许"""
    allowed = cfg.get("allowed_users", [])
    if not allowed:
        return True  # 空列表 = 允许所有用户
    return user_id in allowed


# ══════════════════════════════════════════════════
#  核心功能
# ══════════════════════════════════════════════════

def run_cmd(cmd, timeout=30):
    """执行终端命令"""
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(current_dir),
        )
        out = proc.stdout.strip() or "(无输出)"
        err = proc.stderr.strip()
        if err:
            out += "\n[stderr]\n" + err
        return out[:4000]
    except subprocess.TimeoutExpired:
        return "⏰ 命令执行超时（%ds）" % timeout
    except Exception as e:
        return "⚠️ 执行错误: %s" % e


def codex_ask(prompt):
    """将消息发给 Codex AI 并返回回复"""
    try:
        proc = subprocess.run(
            [
                "codex",
                "exec",
                "--dangerously-bypass-approvals-and-sandbox",
                "-",
            ],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(current_dir),
        )
        # 提取最后一次 "codex" 标记后的内容
        parts = proc.stdout.split("\ncodex\n")
        if len(parts) > 1:
            reply = parts[-1].strip()
            lines = [
                l
                for l in reply.split("\n")
                if not l.startswith("tokens used")
            ]
            return "\n".join(lines).strip()
        return proc.stdout[-3000:].strip() or "(无输出)"
    except subprocess.TimeoutExpired:
        return "⏰ Codex 响应超时（120s）"
    except Exception as e:
        return "⚠️ Codex 错误: %s" % e


def arg(text):
    """提取命令后的参数"""
    parts = text.split(None, 1)
    return parts[1].strip() if len(parts) > 1 else ""


# ══════════════════════════════════════════════════
#  消息处理
# ══════════════════════════════════════════════════

def handle(msg):
    """处理单条消息"""
    global current_dir

    chat_id = msg["chat"]["id"]
    user = msg.get("from", {})
    user_id = user.get("id")
    username = user.get("username", user.get("first_name", "?"))
    msg_id = msg["message_id"]

    # ── 认证 ──
    if not is_allowed(user_id):
        log.warning("拒绝未授权用户: %s (id=%s)", username, user_id)
        return

    home_dir, projects = init()  # 重新读取 projects 配置

    # ── 文件接收 ──
    doc = msg.get("document")
    if doc:
        fn = doc.get("file_name", f"file_{doc['file_id'][:8]}")
        size_mb = doc.get("file_size", 0) / 1024 / 1024
        save_path = os.path.join(upload_dir, fn)
        # 避免重名
        base, ext = os.path.splitext(fn)
        counter = 1
        while os.path.exists(save_path):
            save_path = os.path.join(upload_dir, f"{base}_{counter}{ext}")
            counter += 1

        send(chat_id, f"📥 收到文件: {fn} ({size_mb:.1f}MB)", msg_id)
        if download_file(doc["file_id"], save_path):
            rel = os.path.relpath(save_path, SCRIPT_DIR)
            send(chat_id, f"✅ 已保存 → `{rel}`", msg_id)
        else:
            send(chat_id, "❌ 文件下载失败", msg_id)
        return

    photos = msg.get("photo")
    if photos:
        fid = photos[-1]["file_id"]
        fn = f"photo_{fid[:8]}.jpg"
        save_path = os.path.join(upload_dir, fn)
        send(chat_id, "📸 收到图片…", msg_id)
        if download_file(fid, save_path):
            rel = os.path.relpath(save_path, SCRIPT_DIR)
            send(chat_id, f"✅ 已保存 → `{rel}`", msg_id)
        else:
            send(chat_id, "❌ 下载失败", msg_id)
        return

    # ── 文本消息 ──
    text = msg.get("text", "").strip()
    if not text:
        return

    log.info("💬 [%s] %s", username, text[:80])

    # 解析命令
    raw_cmd = text.split()[0].lstrip("/") if text.startswith("/") else ""
    cmd_map = {
        "cd": "/cd",
        "切换": "/cd",
        "exec": "/exec",
        "执行": "/exec",
        "files": "/files",
        "文件": "/files",
        "ls": "/files",
        "cat": "/cat",
        "查看": "/cat",
        "help": "/help",
        "帮助": "/help",
        "start": "/help",
    }
    cmd = cmd_map.get(raw_cmd, raw_cmd)

    # ── /cd 切换项目目录 ──
    if cmd in ("/cd",):
        target = arg(text)
        if not target:
            proj_list = "\n".join(f"  /cd {k}  → {v}" for k, v in projects.items())
            send(
                chat_id,
                f"📂 当前目录: `{current_dir}`\n\n可用项目:\n{proj_list}",
                msg_id,
            )
        elif target in projects:
            current_dir = projects[target]
            send(chat_id, f"✅ 已切换到: `{target}`\n`{current_dir}`", msg_id)
        else:
            send(chat_id, f"❌ 未知项目: `{target}`\n可用: {', '.join(projects.keys())}", msg_id)

    # ── /exec 执行命令 ──
    elif cmd in ("/exec",):
        shell_cmd = arg(text)
        if not shell_cmd:
            send(chat_id, "用法: `/exec <命令>` 或 `/执行 <命令>`", msg_id)
            return

        send(chat_id, f"⏳ 正在执行…\n💻 `{shell_cmd}`\n📂 `{current_dir}`", msg_id)
        send_action(chat_id)

        def worker(cmd, cid, mid):
            result = run_cmd(cmd)
            send(cid, f"💻 `{cmd}`\n📂 `{current_dir}`\n\n{result}", mid)

        threading.Thread(target=worker, args=(shell_cmd, chat_id, msg_id), daemon=True).start()

    # ── /files 列出文件 ──
    elif cmd in ("/files",):
        path = arg(text) or "."
        full = (
            os.path.join(str(current_dir), path)
            if not path.startswith("/")
            else path
        )
        output = run_cmd(f'ls -la "{full}" 2>&1 | head -40')
        send(chat_id, f"📂 `{path}`\n\n{output}", msg_id)

    # ── /cat 查看文件内容 ──
    elif cmd in ("/cat",):
        path = arg(text)
        if not path:
            send(chat_id, "用法: `/cat <文件名>` 或 `/查看 <文件名>`", msg_id)
            return
        full = (
            os.path.join(str(current_dir), path)
            if not path.startswith("/")
            else path
        )
        if os.path.isfile(full):
            try:
                with open(full, encoding="utf-8", errors="replace") as f:
                    content = f.read()[:3500]
                send(chat_id, f"📄 `{path}`\n\n{content}", msg_id)
            except Exception as e:
                send(chat_id, f"❌ 读取失败: {e}", msg_id)
        else:
            send(chat_id, f"❌ 文件不存在: `{path}`", msg_id)

    # ── /help ──
    elif cmd in ("/help",):
        help_text = (
            f"📂 当前: `{current_dir}`\n\n"
            "**🔧 命令**\n"
            "`/cd [项目名]` — 切换项目目录\n"
            "`/exec <命令>` — 执行终端命令\n"
            "`/files [路径]` — 列出文件\n"
            "`/cat <文件>` — 查看文件内容\n\n"
            "**📎 文件传输**\n"
            "发送文件/图片 → 保存到服务器\n\n"
            "**🤖 AI 对话**\n"
            "直接发文字消息 → Codex AI 回复\n\n"
            "**💡 支持中文别名**\n"
            "`/切换` `/执行` `/文件` `/查看` `/帮助`"
        )
        send(chat_id, help_text, msg_id)

    # ── AI 对话 ──
    else:
        ack = send_raw(chat_id, "🤔 思考中…（约 30-60 秒）", msg_id)
        send_action(chat_id)

        def ai_worker(txt, cid, mid):
            log.info("  → Codex 请求 (%d 字)", len(txt))
            reply = codex_ask(txt)
            log.info("  ← %d 字回复", len(reply))
            send(cid, reply, mid)

        threading.Thread(
            target=ai_worker, args=(text, chat_id, msg_id), daemon=True
        ).start()


# ══════════════════════════════════════════════════
#  轮询循环
# ══════════════════════════════════════════════════

def get_latest_offset():
    """获取最新 update_id，避免重复处理旧消息"""
    r = tg_api("getUpdates", {"offset": -1, "limit": 1, "timeout": 1})
    if r and r.get("ok") and r["result"]:
        return r["result"][-1]["update_id"] + 1
    return 0


def poll_forever():
    """持续轮询 Telegram 新消息"""
    offset = get_latest_offset()
    log.info("🔁 开始轮询 (initial offset=%d)", offset)

    while True:
        try:
            r = tg_api("getUpdates", {"offset": offset, "timeout": 30})
            if r and r.get("ok"):
                for update in r["result"]:
                    offset = max(offset, update["update_id"] + 1)
                    if "message" in update:
                        threading.Thread(
                            target=handle,
                            args=(update["message"],),
                            daemon=True,
                        ).start()
        except KeyboardInterrupt:
            raise
        except Exception as e:
            log.warning("轮询异常: %s", e)
            time.sleep(5)


# ══════════════════════════════════════════════════
#  入口
# ══════════════════════════════════════════════════

def main():
    # 初始化
    home_dir, projects = init()

    # 验证机器人 Token
    me = tg_api("getMe")
    if not me or not me.get("ok"):
        log.error("❌ 无法连接 Telegram API，请检查 config.json 中的 token")
        sys.exit(1)

    bot_username = me["result"]["username"]
    log.info("✅ @%s 已上线 (home=%s)", bot_username, home_dir)
    log.info("   项目列表: %s", list(projects.keys()))

    # 开始轮询
    try:
        poll_forever()
    except KeyboardInterrupt:
        log.info("👋 收到中断信号，退出")
        print()


if __name__ == "__main__":
    main()
