"""uiautomation 后端 — 通过 uiautomation 操控微信 UI"""

import ctypes
import os
import struct
import subprocess
import time
from ctypes import wintypes
from typing import Sequence

import psutil
import pyperclip
import uiautomation as auto

from wechat_auto.backends.base import WeChatBackend
from wechat_auto.config import settings

# ---------- Win32 剪贴板（64 位指针需 WINFUNCTYPE 显式签名） ----------

_GA = ctypes.WINFUNCTYPE(ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t)(("GlobalAlloc", ctypes.windll.kernel32))
_GLk = ctypes.WINFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p)(("GlobalLock", ctypes.windll.kernel32))
_GFree = ctypes.WINFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p)(("GlobalFree", ctypes.windll.kernel32))
_GUnl = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p)(("GlobalUnlock", ctypes.windll.kernel32))
_OCb = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p)(("OpenClipboard", ctypes.windll.user32))
_ECb = ctypes.WINFUNCTYPE(ctypes.c_int)(("EmptyClipboard", ctypes.windll.user32))
_SCb = ctypes.WINFUNCTYPE(ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p)(("SetClipboardData", ctypes.windll.user32))
_CCb = ctypes.WINFUNCTYPE(ctypes.c_int)(("CloseClipboard", ctypes.windll.user32))


def _addr(p):
    """c_void_p → 整数地址。"""
    return p.value if hasattr(p, "value") else p


def _set_cf_hdrop(filepath: str):
    """文件路径 → CF_HDROP + CF_UNICODETEXT 剪贴板（同资源管理器）。"""
    wpath = filepath.encode("utf-16-le") + b"\x00\x00\x00\x00"
    dropfiles = struct.pack("<I", 20) + struct.pack("<ii", 0, 0) + struct.pack("<II", 0, 1)
    buf_hdrop = dropfiles + wpath
    hmem_hdrop = _GA(0x0002, len(buf_hdrop))
    if not hmem_hdrop:
        raise RuntimeError("GlobalAlloc(CF_HDROP) 失败")
    ptr = _GLk(hmem_hdrop)
    if not ptr:
        _GFree(hmem_hdrop)
        raise RuntimeError("GlobalLock(CF_HDROP) 失败")
    try:
        ctypes.memmove(_addr(ptr), buf_hdrop, len(buf_hdrop))
    finally:
        _GUnl(hmem_hdrop)

    # CF_UNICODETEXT（文件路径文本）
    text_bytes = (filepath + "\0").encode("utf-16-le")
    hmem_text = _GA(0x0002, len(text_bytes))

    if not _OCb(0) or not _ECb():
        _GFree(hmem_hdrop)
        if hmem_text:
            _GFree(hmem_text)
        raise RuntimeError("Open/Empty 剪贴板失败")
    _SCb(15, hmem_hdrop)
    if hmem_text:
        _SCb(13, hmem_text)
    _CCb()


def _set_cf_dib(image_path: str):
    """图片文件 → CF_DIB 剪贴板。"""
    from PIL import Image
    import io

    img = Image.open(image_path)
    if img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="BMP")
    dib_data = buf.getvalue()[14:]

    hmem = _GA(0x0002, len(dib_data))
    if not hmem:
        raise RuntimeError("GlobalAlloc 失败")
    ptr = _GLk(hmem)
    if not ptr:
        _GFree(hmem)
        raise RuntimeError("GlobalLock 失败")
    try:
        ctypes.memmove(_addr(ptr), dib_data, len(dib_data))
    finally:
        _GUnl(hmem)
    if not _OCb(0) or not _ECb():
        _GFree(hmem)
        raise RuntimeError("Open/Empty 失败")
    if not _SCb(8, hmem):
        _GFree(hmem)
        _CCb()
        raise RuntimeError("SetClipboardData(CF_DIB) 失败")
    _CCb()


class UiaBackend(WeChatBackend):
    def __init__(self):
        self._window = None

    # ---- 窗口 ----

    def _find_window(self):
        for w in auto.GetRootControl().GetChildren():
            try:
                name = (w.Name or "").lower()
                pid = w.ProcessId
                pn = ""
                if pid:
                    try:
                        pn = (psutil.Process(pid).name() or "").lower()
                    except Exception:
                        pass
                if any(k in name for k in ("微信", "wechat", "weixin")) and pn in (
                    "weixin.exe", "wechat.exe"
                ):
                    return w
            except Exception:
                continue
        return None

    def _ensure_attached(self):
        if self._window:
            return
        w = self._find_window()
        if w is None and settings.launch_wechat:
            self._launch()
            w = self._find_window()
        if w is None:
            raise RuntimeError("微信未运行")
        w.SetActive()
        w.SetTopmost(True)
        time.sleep(0.2)
        w.SetTopmost(False)
        time.sleep(0.2)
        self._window = w

    def _launch(self):
        for exe in [
            os.path.expandvars(r"%PROGRAMFILES%\Tencent\Weixin\Weixin.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Tencent\WeChat\WeChat.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Tencent\WeChat\WeChat.exe"),
        ]:
            if os.path.isfile(exe):
                subprocess.Popen([exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(5)
                return

    # ---- 搜索 ----

    def _search_contact(self, name: str):
        auto.SendKeys("{Ctrl}f", waitTime=0.01)
        time.sleep(0.3)
        auto.SendKeys("{Ctrl}a", waitTime=0.01)
        auto.SendKeys("{Back}", waitTime=0.01)
        time.sleep(0.05)
        pyperclip.copy(name)
        auto.SendKeys("{Ctrl}v", waitTime=0.01)
        time.sleep(0.2)
        auto.SendKeys("{Enter}", waitTime=0.01)
        time.sleep(settings.friend_delay)

    def _click_input(self):
        if not self._window:
            return
        try:
            r = self._window.BoundingRectangle
            auto.Click(int((r.left + r.right) / 2), int(r.bottom - 80))
            time.sleep(0.2)
        except Exception:
            pass

    # ---- 发送 ----

    def send_text(self, contact: str, message: str) -> bool:
        self._ensure_attached()
        self._search_contact(contact)
        self._click_input()
        pyperclip.copy(message)
        auto.SendKeys("{Ctrl}v", waitTime=0.01)
        time.sleep(settings.message_delay)
        auto.SendKeys("{Enter}", waitTime=0.01)
        time.sleep(0.2)
        return True

    def send_text_with_mention(
        self, group: str, mentions: list[str], message: str
    ) -> bool:
        self._ensure_attached()
        self._search_contact(group)
        self._click_input()
        for name in mentions:
            auto.SendKeys("@", waitTime=0.01)
            time.sleep(0.4)
            pyperclip.copy(name)
            auto.SendKeys("{Ctrl}v", waitTime=0.01)
            time.sleep(0.5)
            auto.SendKeys("{Enter}", waitTime=0.01)
            time.sleep(0.3)
        pyperclip.copy(message)
        auto.SendKeys("{Ctrl}v", waitTime=0.01)
        time.sleep(settings.message_delay)
        auto.SendKeys("{Enter}", waitTime=0.01)
        time.sleep(0.2)
        return True

    def send_messages(self, friends: Sequence[str], messages: Sequence[str]) -> list[dict]:
        self._ensure_attached()
        results = []
        for friend in friends:
            self._search_contact(friend)
            self._click_input()
            for msg in messages:
                pyperclip.copy(msg)
                auto.SendKeys("{Ctrl}v", waitTime=0.01)
                time.sleep(settings.message_delay)
                auto.SendKeys("{Enter}", waitTime=0.01)
                time.sleep(0.2)
                results.append({"friend": friend, "message": msg, "ok": True})
        return results

    def send_file(self, contact: str, filepath: str) -> bool:
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"文件不存在: {filepath}")
        self._ensure_attached()
        self._search_contact(contact)
        self._click_input()
        _set_cf_hdrop(filepath)  # 必须在 _search_contact 之后（它会覆盖剪贴板）
        auto.SendKeys("{Ctrl}v", waitTime=0.01)
        time.sleep(0.5)
        auto.SendKeys("{Enter}", waitTime=0.01)
        time.sleep(0.3)
        return True

    def send_image(self, contact: str, image_path: str) -> bool:
        if not os.path.isfile(image_path):
            raise FileNotFoundError(f"图片不存在: {image_path}")
        self._ensure_attached()
        self._search_contact(contact)
        self._click_input()
        _set_cf_dib(image_path)  # 必须在 _search_contact 之后
        auto.SendKeys("{Ctrl}v", waitTime=0.01)
        time.sleep(0.5)
        auto.SendKeys("{Enter}", waitTime=0.01)
        time.sleep(0.3)
        return True

    # ---- 调试 ----

    def dump_controls(self, max_count: int = 30) -> list[dict]:
        self._ensure_attached()
        out = []
        try:
            items = self._window.GetChildren()
        except Exception:
            return out
        for i, c in enumerate(items[:max_count]):
            try:
                out.append({
                    "index": i,
                    "type": c.ControlTypeName,
                    "name": c.Name or "",
                    "class": c.ClassName or "",
                })
            except Exception:
                pass
        return out
