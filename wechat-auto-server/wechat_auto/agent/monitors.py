"""消息监控 — 通过 wechat-cli 轮询新消息"""

import json
import logging
import re
import subprocess
from datetime import datetime, timedelta

log = logging.getLogger("wechat.agent")


def _run_cli(*args: str, raw: bool = False) -> dict | str:
    """运行 wechat-cli 命令。"""
    cmd = ["wechat-cli", *args]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=30)
        lines = [l for l in r.stdout.splitlines() if not l.startswith("[解密]")]
        text = "\n".join(lines)
        if raw:
            return text
        return json.loads(text)
    except Exception as e:
        log.error("wechat-cli 失败: %s", e)
        return {} if not raw else ""


def get_new_messages() -> list[dict]:
    """获取增量新消息。"""
    data = _run_cli("new-messages")
    return data.get("messages", []) if isinstance(data, dict) else []


def get_context(chat_name: str, limit: int = 20) -> str:
    """取最近 5 分钟聊天记录作为 LLM 上下文。"""
    start = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M")
    return _run_cli(
        "history", chat_name,
        "--limit", str(limit),
        "--start-time", start,
        "--format", "text",
        raw=True,
    )


def is_self_sent(chat: str, content: str, timestamp: int, my_names: list[str]) -> bool:
    """通过 history 查私聊消息发送者。"""
    start = datetime.fromtimestamp(timestamp - 60).strftime("%Y-%m-%d %H:%M")
    text = _run_cli(
        "history", chat, "--limit", "3",
        "--start-time", start, "--format", "text", raw=True,
    )
    first_line = content.split("\n")[0]
    for line in text.splitlines() if isinstance(text, str) else []:
        m = re.match(r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] (.+?): (.+)", line)
        if m and (m.group(2).strip() == content or m.group(2).strip() == first_line):
            return m.group(1).strip() in my_names
    return False
