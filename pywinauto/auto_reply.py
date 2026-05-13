"""微信智能自动回复 — 轮询 → LLM 判断 → LLM 生成回复 → pywinauto 发送"""
import subprocess
import json
import time
import os
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI

# --------------- 配置 ---------------

MONITOR_CHATS = [
    "CAP人才群",
    "文件传输助手",
]

MY_NAMES = ["话少"]

POLL_INTERVAL = 5
THROTTLE_SECONDS = 5
CONTEXT_LIMIT = 20
TEST_MODE = True  # 测试模式：每条消息都回复

# --------------- LLM ---------------

llm = ChatOpenAI(
    model=os.environ.get("QWEN_CHAT_MODEL", "qwen3.5-plus"),
    api_key=os.environ["DASHSCOPE_API_KEY"],
    base_url=os.environ["DASHSCOPE_BASE_URL"],
    temperature=0.85,
    extra_body={"enable_thinking": False},
)

SYSTEM_PROMPT_NORMAL = r"""你是话少的微信分身。性格轻松幽默，有点自嘲，爱开玩笑但不过分。

规则：
1. 私聊消息必须回复（别人找你就是有事）
2. 群聊里被 @话少 必须回复
3. 群聊里收到新消息，分析后觉得你该插话就回，觉得没必要就输出 [SKIP]
4. 技术话题（编程、AI、大模型、部署）你可以帮忙，语气随意带梗
5. 闲聊（吃饭、骑车、生活）适当参与，轻松接话
6. 回复短小精干，不超过 3 句话，像真人聊天
7. 你就是话少本人，不要用"主人""机器人"这类词

输出：直接回复内容，不需要就输出 [SKIP]"""

SYSTEM_PROMPT_TEST = r"""你是话少的微信分身。性格轻松幽默，有点自嘲，爱开玩笑但不过分。

重要：现在是测试模式，无论收到什么消息都必须回复！

规则：
1. 收到任何新消息都要回复，不能跳过
2. 技术话题（编程、AI、大模型、部署）你可以帮忙，语气随意带梗
3. 闲聊（吃饭、骑车、生活）适当参与，轻松接话
4. 即使是无聊消息或者你不了解的话题，也要接一句话
5. 回复短小精干，不超过 3 句话，像真人聊天
6. 你就是话少本人，不要用"主人""机器人"这类词"""

SYSTEM_PROMPT = SYSTEM_PROMPT_TEST if TEST_MODE else SYSTEM_PROMPT_NORMAL


# --------------- wechat-cli ---------------

def run_wechat_cli(*args, raw=False):
    cmd = ["wechat-cli"] + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=30)
    lines = [l for l in r.stdout.splitlines() if not l.startswith("[解密]")]
    text = "\n".join(lines)
    if raw:
        return text
    return json.loads(text)


def get_new_messages():
    data = run_wechat_cli("new-messages")
    return data.get("messages", []) if isinstance(data, dict) else []


def get_context(chat_name, limit=CONTEXT_LIMIT):
    from datetime import datetime, timedelta
    start = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M")
    return run_wechat_cli(
        "history", chat_name,
        "--limit", str(limit),
        "--start-time", start,
        "--format", "text",
        raw=True,
    )


_is_group_cache = {}

def is_group_chat(name):
    if name in _is_group_cache:
        return _is_group_cache[name]
    try:
        data = run_wechat_cli("sessions", "--limit", "200")
        if isinstance(data, list):
            for s in data:
                if s.get("chat") == name:
                    _is_group_cache[name] = s.get("is_group", False)
                    return _is_group_cache[name]
    except Exception:
        pass
    _is_group_cache[name] = False
    return False


# --------------- 发送 ---------------

def send_message(contact, message):
    import httpx
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
    except Exception as e:
        print(f"  发送失败: {e}")
        return False


# --------------- LLM 决策 ---------------

def should_reply(context, new_msgs, chat_type):
    prompt = f"""这是{chat_type}记录——

最近消息：
{context}

刚收到的新消息：
{new_msgs}

请决定是否回复。"""

    try:
        resp = llm.invoke([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ])
        text = resp.content.strip()
        if not TEST_MODE and "[SKIP]" in text:
            return None
        # 测试模式下忽略 SKIP，即使模型输出 SKIP 也返回内容
        return text.replace("[SKIP]", "").strip() or text
    except Exception as e:
        print(f"  LLM 失败: {e}")
        return None


# --------------- 主循环 ---------------

last_reply_time = {}


def main():
    print("🧠 智能回复机器人启动")
    print(f"  监控: {MONITOR_CHATS}")
    print(f"  身份: {MY_NAMES}")
    print(f"  轮询: {POLL_INTERVAL}s | 节流: {THROTTLE_SECONDS}s")
    print("  监听中...\n")

    get_new_messages()

    while True:
        try:
            msgs = get_new_messages()
            if not msgs:
                ts = time.strftime("%H:%M:%S")
                print(f"[{ts}] ·", end="\r")
                time.sleep(POLL_INTERVAL)
                continue

            by_chat = {}
            for m in msgs:
                chat = m.get("chat", "")
                if chat in MONITOR_CHATS and m.get("msg_type") == "文本":
                    by_chat.setdefault(chat, []).append(m)

            if not by_chat:
                time.sleep(POLL_INTERVAL)
                continue

            for chat, chat_msgs in by_chat.items():
                is_group = is_group_chat(chat)
                chat_type = "群聊" if is_group else "私聊"
                ts = time.strftime("%H:%M:%S")
                print(f"\n[{ts}] [{chat_type}] {chat} 收到 {len(chat_msgs)} 条")

                now = time.time()
                if chat in last_reply_time:
                    if now - last_reply_time[chat] < THROTTLE_SECONDS:
                        print(f"  ⏳ 节流中")
                        continue

                new_text = ""
                mentioned = False
                for m in chat_msgs:
                    sender = m.get("sender", "")
                    content = m.get("last_message", "")
                    if sender in MY_NAMES:
                        continue
                    new_text += f"[{sender}]: {content}\n"
                    if is_group and any(n in content for n in MY_NAMES):
                        mentioned = True

                if not new_text.strip():
                    continue

                if mentioned:
                    print(f"  🔔 被 @ 了")
                elif not is_group:
                    print(f"  📩 私聊消息")

                context = get_context(chat)
                print(f"  🤔 LLM 判断中...")
                reply = should_reply(context, new_text, chat_type)

                if reply is None:
                    print(f"  → [SKIP]")
                    continue

                print(f"  → 回复: {reply[:80]}")
                if send_message(chat, reply):
                    last_reply_time[chat] = time.time()

        except KeyboardInterrupt:
            print("\n已停止")
            break
        except Exception as e:
            print(f"\n  异常: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
