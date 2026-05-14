"""LLM 决策 + 回复生成"""

import base64
import logging
import os
from typing import Any

from langchain_openai import ChatOpenAI

log = logging.getLogger("wechat.agent")

AGENT_PROMPT = r"""你是「话少」的微信分身。话少是一个 27 岁的程序员，成都人，喜欢骑车、打游戏、看数码评测。

性格：内向但熟了话多，吐槽型人格，用词随意（确实、离谱、真实），偶尔发狗头。

重要：现在是测试模式，收到任何消息都要回复！

规则：
1. 根据对方语气调整——
   - 正经 → 正经回应
   - 开玩笑 → 接梗调侃
   - 吐槽/烦躁 → 共情安慰
   - 闲聊 → 轻松接话
2. 回复短小，1-3 句。不知道咋回就发"确实""真实"
3. 不用"主人""机器人""AI"等词。你就是话少本人
4. 可以适当用语气词：确实、离谱、真实、草、哈哈、额"""


class LLMEngine:
    def __init__(self, model: str, api_key: str, base_url: str):
        self.llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=0.85,
            extra_body={"enable_thinking": False},
        ) if api_key else None

    def decide_and_reply(
        self, context: str, new_msgs: str, chat_type: str, image_paths: list[str] | None = None
    ) -> str | None:
        if not self.llm:
            log.warning("LLM 未配置，跳过回复")
            return None

        prompt = f"""这是{chat_type}记录——

最近消息：
{context}

刚收到的新消息：
{new_msgs}

请决定是否回复。"""

        try:
            if image_paths:
                content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
                for img in image_paths:
                    if not os.path.isfile(img):
                        continue
                    with open(img, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode()
                    ext = img.rsplit(".", 1)[-1]
                    content.append({"type": "image_url", "image_url": {"url": f"data:image/{ext};base64,{b64}"}})
                resp = self.llm.invoke([{"role": "system", "content": AGENT_PROMPT}, {"role": "user", "content": content}])
            else:
                resp = self.llm.invoke([{"role": "system", "content": AGENT_PROMPT}, {"role": "user", "content": prompt}])
            return resp.content.strip().replace("[SKIP]", "").strip() or resp.content.strip()
        except Exception as e:
            log.error("LLM 调用失败: %s", e)
            return None
