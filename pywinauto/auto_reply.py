"""微信智能自动回复 — 轮询 → LLM 判断 → LLM 生成回复 → pywinauto 发送"""

import json
import logging
import os
import subprocess
import time
import httpx

from datetime import datetime, timedelta
from typing import Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

# --------------- 日志 ---------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bot")


# --------------- 配置 ---------------

MONITOR_CHATS: list[str] = ["KL_邵翔", "KL_林啸虎"]
MY_NAMES: list[str] = ["话少"]
POLL_INTERVAL: int = 3
CONTEXT_LIMIT: int = 20

# --------------- LLM ---------------

llm = ChatOpenAI(
    model=os.environ.get("QWEN_CHAT_MODEL", "qwen3.5-plus"),
    api_key=os.environ["DASHSCOPE_API_KEY"],
    base_url=os.environ["DASHSCOPE_BASE_URL"],
    temperature=0.85,
    extra_body={"enable_thinking": False},
)

SYSTEM_PROMPT = r"""你是话少的微信分身。话少是一个 27 岁的程序员，成都人，平时喜欢骑车、打游戏、看数码评测。

性格：内向但熟了话多，吐槽型人格，爱用"确实""离谱""真实"这种词，偶尔发个狗头表情。

重要：现在是测试模式，收到任何消息都要回复！

规则：
1. 根据对方语气调整语气——
   - 对方正经 → 你简短正经回应
     例：对方"这个接口 QPS 上不去"→ 你"看看连接池配置，大概率没调优"
   - 对方开玩笑 → 你接梗调侃
     例：对方"我要瘦成闪电"→ 你"闪电也是要胖的先劈到"
   - 对方吐槽/烦躁 → 你共情，别硬搞笑
     例：对方"今天加班到 11 点"→ 你"离谱，这公司是真不当人"
   - 对方闲聊 → 随意接话，像朋友聊天
     例：对方"今天好热"→ 你"确实，出门直接融化"

2. 回复短小，1-3 句话。不知道怎么接的时候发个表情包文字或"确实""真实"

3. 不用"主人""机器人""AI""为您服务"等词。你就是话少本人

4. 可以适当用语气词：嗯、哎、确实、离谱、真实、草、哈哈、额"""


# --------------- wechat-cli ---------------


def _run_wechat_cli(*args: str, raw: bool = False) -> Any:
    """运行 wechat-cli 命令，返回 JSON 解析结果或原始文本。"""
    cmd = ["wechat-cli", *args]
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", timeout=30
        )
        lines = [l for l in r.stdout.splitlines() if not l.startswith("[解密]")]
        text = "\n".join(lines)
        if raw:
            return text
        return json.loads(text)
    except json.JSONDecodeError:
        log.error("wechat-cli 返回非 JSON 结果: %s", cmd)
    except subprocess.TimeoutExpired:
        log.error("wechat-cli 超时: %s", cmd)
    except FileNotFoundError:
        log.error("找不到 wechat-cli 命令，请确认已安装")
    return {} if not raw else ""


def get_new_messages() -> list[dict]:
    """通过 wechat-cli new-messages 获取增量新消息。"""
    data = _run_wechat_cli("new-messages")
    return data.get("messages", []) if isinstance(data, dict) else []


def get_context(chat_name: str, limit: int = CONTEXT_LIMIT) -> str:
    """取最近 5 分钟内的聊天记录作为 LLM 上下文。"""
    start = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M")
    return _run_wechat_cli(
        "history",
        chat_name,
        "--limit",
        str(limit),
        "--start-time",
        start,
        "--format",
        "text",
        raw=True,
    )


_is_group_cache: dict[str, bool] = {}


def is_group_chat(name: str) -> bool:
    """判断聊天名称是否是群聊（结果缓存避免重复查询）。"""
    if name in _is_group_cache:
        return _is_group_cache[name]
    data = _run_wechat_cli("sessions", "--limit", "200")
    if isinstance(data, list):
        for s in data:
            if s.get("chat") == name:
                _is_group_cache[name] = s.get("is_group", False)
                return _is_group_cache[name]
    _is_group_cache[name] = False
    return False


# --------------- 发送 ---------------


def send_message(contact: str, message: str) -> bool:
    """通过本地 HTTP API 发送消息（剪贴板粘贴模式避免 IME 吞字）。"""

    try:
        resp = httpx.post(
            "http://127.0.0.1:8000/send",
            json={
                "friends": [contact],
                "messages": [message],
                "use_paste": True,
                "friend_delay": 0.5,
                "message_delay": 0.3,
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        return True
    except httpx.RequestError as e:
        log.error("发送请求失败: %s", e)
    except httpx.HTTPStatusError as e:
        log.error("发送接口返回 %s: %s", e.response.status_code, e.response.text)
    return False


# --------------- LLM 决策 ---------------


def should_reply(context: str, new_msgs: str, chat_type: str) -> str | None:
    """调用 LLM 判断是否回复，返回回复内容或 None。"""
    prompt = f"""这是{chat_type}记录——

最近消息：
{context}

刚收到的新消息：
{new_msgs}

请决定是否回复。"""

    try:
        resp = llm.invoke(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
        )
        text = resp.content.strip()
        return text.replace("[SKIP]", "").strip() or text
    except Exception as e:
        log.error("LLM 调用失败: %s", e)
        return None


# --------------- 主循环 ---------------

_last_reply_time: dict[str, float] = {}  # chat → 最后回复时间戳


def main() -> None:
    """主循环，轮询获取新消息，判断是否回复，发送回复"""
    log.info(
        "智能回复机器人启动 | 监控: %s | 身份: %s | 轮询: %ss",
        MONITOR_CHATS,
        MY_NAMES,
        POLL_INTERVAL,
    )

    get_new_messages()  # 建立增量基线

    while True:
        try:
            msgs = get_new_messages()
            if not msgs:
                log.info("·")
                time.sleep(POLL_INTERVAL)
                continue

            # 按聊天分组，只保留监控列表中的文本消息
            by_chat: dict[str, list[dict]] = {}
            for m in msgs:
                chat: str = m.get("chat", "")
                if chat in MONITOR_CHATS and m.get("msg_type") == "文本":
                    by_chat.setdefault(chat, []).append(m)

            if not by_chat:
                time.sleep(POLL_INTERVAL)
                continue

            for chat, chat_msgs in by_chat.items():
                is_group = is_group_chat(chat)
                chat_type = "群聊" if is_group else "私聊"
                log.info("[%s] %s 收到 %s 条消息", chat_type, chat, len(chat_msgs))

                # 合并新消息文本
                new_text = ""
                mentioned = False
                for m in chat_msgs:
                    sender: str = m.get("sender", "")  # 群聊有 sender，私聊为空
                    content: str = m.get("last_message", "")
                    msg_ts: int = m.get("timestamp", 0)

                    if is_group:
                        if sender in MY_NAMES:
                            continue  # 群聊跳过自己发的
                        display = sender
                    else:
                        # 私聊：通过时间戳判断是否为自己刚发的消息
                        last_ts = _last_reply_time.get(chat, 0)
                        if last_ts > 0 and abs(msg_ts - last_ts) <= 2:
                            log.info(
                                "  ⏭ 跳过私聊消息（时间戳 %s 在上次回复 %s 附近）",
                                msg_ts, last_ts,
                            )
                            continue
                        display = chat  # 私聊用聊天名称作为发送者

                    new_text += f"[{display}]: {content}\n"
                    if is_group and any(n in content for n in MY_NAMES):
                        mentioned = True

                if not new_text.strip():
                    continue

                if mentioned:
                    log.info("🔔 被 @ 了")
                elif not is_group:
                    log.info("📩 私聊消息")

                context = get_context(chat)
                log.info("🤔 LLM 决策中...")
                reply = should_reply(context, new_text, chat_type)

                if reply is None:
                    log.info("→ 跳过")
                    continue

                log.info("→ 回复: %s", reply[:80])
                if send_message(chat, reply):
                    _last_reply_time[chat] = time.time()

        except KeyboardInterrupt:
            log.info("用户中断，已停止")
            break
        except Exception as e:
            log.exception("主循环异常: %s", e)
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
