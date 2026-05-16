"""抽象后端接口 — 所有操控后端必须实现"""

from abc import ABC, abstractmethod
from typing import Sequence


class WeChatBackend(ABC):
    """微信自动化后端抽象类。"""

    @abstractmethod
    def send_messages(
        self,
        friends: Sequence[str],
        messages: Sequence[str],
    ) -> list[dict]:
        """向一个或多个联系人发送消息。返回每条消息的结果。"""
        ...

    @abstractmethod
    def send_text(self, contact: str, message: str) -> bool:
        """向单个联系人发送文本消息。"""
        ...

    @abstractmethod
    def send_text_with_mention(
        self, group: str, mentions: list[str], message: str
    ) -> bool:
        """在群聊中发送 @提及 消息。"""
        ...

    @abstractmethod
    def send_file(self, contact: str, filepath: str) -> bool:
        """向单个联系人发送文件。"""
        ...

    @abstractmethod
    def send_image(self, contact: str, image_path: str) -> bool:
        """向单个联系人发送图片（CF_DIB 剪贴板，显示为图片缩略图）。"""
        ...

    @abstractmethod
    def dump_controls(self, max_count: int = 30) -> list[dict]:
        """导出控件树（调试用）。"""
        ...
