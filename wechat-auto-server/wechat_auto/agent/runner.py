"""Agent 主循环 — 轮询 → 过滤 → LLM → 发送"""

import logging
import os
import sys
import time

from wechat_auto.agent.filters import MessageFilter
from wechat_auto.agent.images import decode_image
from wechat_auto.agent.llm import LLMEngine
from wechat_auto.agent.monitors import get_new_messages, get_context, is_self_sent, resolve_file_path, read_file_content
from wechat_auto.backends import create_backend
from wechat_auto.config import settings

log = logging.getLogger("wechat.agent")


def run():
    """启动 Agent：连接微信 → 轮询 → 自动回复。"""
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S")
    monitor_chats = [c.strip() for c in settings.monitor_chats.split(",") if c.strip()]
    my_names = [n.strip() for n in settings.my_names.split(",") if n.strip()]
    llm = LLMEngine(settings.llm_model, settings.llm_api_key, settings.llm_base_url)
    backend = create_backend()
    mfilter = MessageFilter()

    log.info(
        "Agent 启动 | 监控: %s | 身份: %s | 轮询: %ss",
        monitor_chats, my_names, settings.poll_interval,
    )

    # 建立 new-messages 基线
    get_new_messages()

    while True:
        try:
            msgs = get_new_messages()
            if not msgs:
                time.sleep(settings.poll_interval)
                continue

            # 按聊天分组
            by_chat: dict[str, list[dict]] = {}
            chat_group: dict[str, bool] = {}
            chat_name: dict[str, str] = {}
            for m in msgs:
                c = m.get("chat", "")
                if c not in monitor_chats:
                    continue
                by_chat.setdefault(c, []).append(m)
                if c not in chat_group:
                    chat_group[c] = m.get("is_group", False)
                if c not in chat_name:
                    chat_name[c] = m.get("username", "")

            if not by_chat:
                time.sleep(settings.poll_interval)
                continue

            for chat, chat_msgs in by_chat.items():
                is_group = chat_group.get(chat, False)
                ct = "群聊" if is_group else "私聊"
                log.info("[%s] %s 收到 %s 条", ct, chat, len(chat_msgs))

                # 预解码图片
                decoded_images: dict[int, str] = {}
                for m in chat_msgs:
                    if m.get("msg_type") == "图片" and m.get("username", ""):
                        img = decode_image(m["username"], m.get("timestamp", 0), settings.decoded_img_dir)
                        if img:
                            decoded_images[m["timestamp"]] = img

                # 预解析文件消息
                file_contents: dict[int, str] = {}
                for m in chat_msgs:
                    if m.get("msg_type") == "链接/文件":
                        chat_name = m.get("chat", "")
                        fp = resolve_file_path(chat_name, m.get("timestamp", 0))
                        if fp:
                            content = read_file_content(fp)
                            if content:
                                file_contents[m["timestamp"]] = f"[文件: {os.path.basename(fp)}]\n{content[:600]}"
                                log.info("文件已解析: %s (%d 字符)", fp, len(content))

                # 过滤消息
                new_text, mentioned, image_paths = mfilter.process_messages(
                    chat_msgs, is_group, my_names,
                    self_sent_fn=lambda c, t, ts: is_self_sent(c, t, ts, my_names),
                    decoded_images=decoded_images,
                    file_contents=file_contents,
                )

                if not new_text:
                    continue

                if mentioned:
                    log.info("  @了")
                elif not is_group:
                    log.info("  私聊消息")
                if image_paths:
                    log.info("  %s 张图片", len(image_paths))

                context = get_context(chat, settings.context_limit)
                reply = llm.decide_and_reply(context, new_text, ct, image_paths or None)

                if not reply:
                    log.info("  → 跳过")
                    continue

                log.info("  → %s", reply[:80])
                backend.send_text(chat, reply)
                mfilter.record(chat, reply)

        except KeyboardInterrupt:
            log.info("已停止")
            break
        except Exception as e:
            log.exception("异常: %s", e)
            time.sleep(settings.poll_interval)
