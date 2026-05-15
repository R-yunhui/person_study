"""MCP Server — 将微信操控暴露为 Claude Code 工具"""

from typing import Sequence

from fastmcp import FastMCP

from wechat_auto.backends import create_backend
from wechat_auto.config import settings

app = FastMCP(name=settings.mcp_name, version=settings.mcp_version)
_backend = None


def get_backend():
    global _backend
    if _backend is None:
        _backend = create_backend()
    return _backend


@app.tool()
def send_messages(
    friends: Sequence[str],
    messages: Sequence[str],
    ctrl_enter: bool = False,
    friend_delay: float | None = None,
    message_delay: float | None = None,
) -> dict:
    """向好友/群聊发送消息。

    Args:
        friends: 好友或群聊名称列表
        messages: 要发送的消息列表
        ctrl_enter: 是否使用 Ctrl+Enter 发送
        friend_delay: 切换聊天后的等待秒数（默认 config 值）
        message_delay: 每条消息的等待秒数（默认 config 值）
    """
    from wechat_auto.config import settings as s

    if friend_delay is not None:
        s.friend_delay = friend_delay
    if message_delay is not None:
        s.message_delay = message_delay
    if ctrl_enter:
        s.ctrl_enter = ctrl_enter

    try:
        results = get_backend().send_messages(friends, messages)
        return {"ok": True, "results": results}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.tool()
def dump_controls(max_count: int = 30) -> dict:
    """导出微信主窗口控件树（调试用）。

    Args:
        max_count: 控件数量上限
    """
    try:
        controls = get_backend().dump_controls(max_count)
        return {"ok": True, "controls": controls}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.tool()
def send_file(
    contact: str,
    filepath: str,
) -> dict:
    """向指定联系人发送文件（显示为文件图标）。

    Args:
        contact: 好友或群聊名称
        filepath: 文件路径（绝对路径）
    """
    try:
        ok = get_backend().send_file(contact, filepath)
        return {"ok": ok}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.tool()
def send_image(
    contact: str,
    image_path: str,
) -> dict:
    """向指定联系人发送图片（显示为图片缩略图，非文件图标）。

    Args:
        contact: 好友或群聊名称
        image_path: 图片路径（绝对路径，支持 jpg/png/gif/bmp 等格式）
    """
    try:
        ok = get_backend().send_image(contact, image_path)
        return {"ok": ok}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def run():
    """通过 CLI 启动 MCP 服务器。"""
    app.run()
