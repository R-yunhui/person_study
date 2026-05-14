"""FastAPI 服务 — 提供 HTTP 接口操控微信"""

from typing import Sequence

from fastapi import FastAPI
from pydantic import BaseModel, Field

from wechat_auto.backends import create_backend

app = FastAPI(title="WeChat Auto", version="0.1.0")
_backend = None


def get_backend():
    global _backend
    if _backend is None:
        _backend = create_backend()
    return _backend


# ---------- 模型 ----------


class SendRequest(BaseModel):
    friends: Sequence[str] = Field(..., description="好友/群聊名称列表")
    messages: Sequence[str] = Field(..., description="消息列表")
    ctrl_enter: bool = Field(False, description="使用 Ctrl+Enter 发送")
    friend_delay: float | None = Field(None, description="切换聊天等待秒数")
    message_delay: float | None = Field(None, description="每条消息等待秒数")


class DumpRequest(BaseModel):
    max_count: int = Field(30, description="控件数量上限")


class BatchRequest(BaseModel):
    friends: Sequence[str] = Field(..., description="好友/群聊列表")
    filepath: str = Field(..., description="文件路径")


# ---------- 路由 ----------


@app.post("/send")
def send_messages(req: SendRequest):
    """向好友/群聊发送消息。"""
    try:
        results = get_backend().send_messages(req.friends, req.messages)
        return {"ok": True, "results": results}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/send-text")
def send_text(contact: str, message: str):
    """向单个联系人发送文本消息。"""
    try:
        ok = get_backend().send_text(contact, message)
        return {"ok": ok}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/send-file")
def send_file(contact: str, filepath: str):
    """向联系人发送文件。"""
    try:
        ok = get_backend().send_file(contact, filepath)
        return {"ok": ok}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/dump")
def dump_controls(req: DumpRequest):
    """导出控件树（调试用）。"""
    try:
        controls = get_backend().dump_controls(req.max_count)
        return {"ok": True, "controls": controls}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/health")
def health():
    """健康检查。"""
    return {"ok": True}
