"""消息过滤 — 群聊/私聊、自己发的、已回复过的"""

import logging
from typing import Callable

log = logging.getLogger("wechat.agent")

SelfSentFn = Callable[[str, str, int], bool]


class MessageFilter:
    def __init__(self):
        self._replied: dict[str, list[str]] = {}

    def has_replied(self, chat: str, content: str) -> bool:
        prefix = content[:40]
        return any(c[:40] == prefix or c == content for c in self._replied.get(chat, []))

    def record(self, chat: str, reply: str):
        self._replied.setdefault(chat, []).append(reply)
        if len(self._replied[chat]) > 20:
            self._replied[chat].pop(0)

    def process_messages(
        self,
        chat_msgs: list[dict],
        is_group: bool,
        my_names: list[str],
        self_sent_fn: SelfSentFn | None = None,
        decoded_images: dict[int, str] | None = None,
    ) -> tuple[str, bool, list[str]]:
        """处理消息列表，返回 (合并文本, 是否被@, 多模态图片路径列表)。"""
        new_text = ""
        mentioned = False
        image_paths: list[str] = []
        skipped = 0

        for m in chat_msgs:
            sender: str = m.get("sender", "")
            content: str = m.get("last_message", "")
            msg_type: str = m.get("msg_type", "文本")
            msg_ts: int = m.get("timestamp", 0)
            wxid: str = m.get("username", "")

            if is_group:
                if sender in my_names:
                    continue
                display = sender
            else:
                if self.has_replied(m.get("chat", ""), content):
                    log.info("  跳过已回复过的私聊消息: %s", content[:40])
                    skipped += 1
                    continue
                if self_sent_fn and self_sent_fn(m.get("chat", ""), content, msg_ts):
                    log.info("  跳过自己手动发的私聊消息: %s", content[:40])
                    skipped += 1
                    continue
                display = m.get("chat", "")

            extra = ""
            if msg_type == "图片" and wxid and decoded_images and msg_ts in decoded_images:
                p = decoded_images[msg_ts]
                ext = p.rsplit(".", 1)[-1]
                if ext in ("jpg", "jpeg", "png", "gif", "bmp", "webp"):
                    image_paths.append(p)
                    extra = " (已解码)"
                else:
                    extra = f" (格式不支持: {ext})"

            new_text += f"[{display}]: {content}{extra}\n"
            if is_group and any(n in content for n in my_names):
                mentioned = True

        if skipped:
            log.info("  共跳过 %s 条", skipped)

        return new_text.strip(), mentioned, image_paths
