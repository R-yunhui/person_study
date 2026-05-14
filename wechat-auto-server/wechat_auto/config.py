"""配置管理 — 环境变量 + 命令行"""

import os
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Settings:
    # 后端选择: pywinauto | uia
    backend: Literal["pywinauto", "uia"] = field(
        default_factory=lambda: os.environ.get("WECHAT_BACKEND", "uia")
    )
    # HTTP API
    host: str = field(default_factory=lambda: os.environ.get("WECHAT_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.environ.get("WECHAT_PORT", "8000")))
    # MCP
    mcp_name: str = "wechat-auto"
    mcp_version: str = "0.1.0"
    # 行为
    launch_wechat: bool = field(
        default_factory=lambda: os.environ.get("WECHAT_LAUNCH", "true").lower() == "true"
    )
    ctrl_enter: bool = field(
        default_factory=lambda: os.environ.get("WECHAT_CTRL_ENTER", "false").lower() == "true"
    )
    use_paste: bool = field(
        default_factory=lambda: os.environ.get("WECHAT_USE_PASTE", "true").lower() == "true"
    )
    friend_delay: float = field(
        default_factory=lambda: float(os.environ.get("WECHAT_FRIEND_DELAY", "0.5"))
    )
    message_delay: float = field(
        default_factory=lambda: float(os.environ.get("WECHAT_MSG_DELAY", "0.3"))
    )

    # Agent
    monitor_chats: str = field(
        default_factory=lambda: os.environ.get("WECHAT_MONITOR_CHATS", "文件传输助手")
    )
    my_names: str = field(
        default_factory=lambda: os.environ.get("WECHAT_MY_NAMES", "话少")
    )
    poll_interval: int = field(
        default_factory=lambda: int(os.environ.get("WECHAT_POLL_INTERVAL", "3"))
    )
    context_limit: int = field(
        default_factory=lambda: int(os.environ.get("WECHAT_CONTEXT_LIMIT", "20"))
    )

    # LLM
    llm_model: str = field(
        default_factory=lambda: os.environ.get("QWEN_CHAT_MODEL", "qwen3.5-plus")
    )
    llm_api_key: str = field(
        default_factory=lambda: os.environ.get("DASHSCOPE_API_KEY", "")
    )
    llm_base_url: str = field(
        default_factory=lambda: os.environ.get("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    )

    # 图片
    decoded_img_dir: str = field(
        default_factory=lambda: os.environ.get("WECHAT_DECODED_IMG_DIR", "")
    )
    wechat_decrypt_path: str = field(
        default_factory=lambda: os.environ.get("WECHAT_DECRYPT_PATH", "")
    )


settings = Settings()
