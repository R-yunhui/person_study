"""uiautomation 后端 — 通过 uiautomation 操控微信 UI"""

import ctypes
import os
import subprocess
import time
from ctypes import wintypes
from typing import Sequence

import psutil
import pyperclip
import uiautomation as auto

from wechat_auto.backends.base import WeChatBackend
from wechat_auto.config import settings


class UiaBackend(WeChatBackend):
    def __init__(self):
        self._window = None

    # ---- 窗口 ----

    def _find_window(self):
        """枚举顶层窗口，找微信主窗口。"""
        for w in auto.GetRootControl().GetChildren():
            try:
                name = (w.Name or "").lower()
                pid = w.ProcessId
                proc_name = ""
                if pid:
                    try:
                        proc_name = (psutil.Process(pid).name() or "").lower()
                    except Exception:
                        pass
                if any(k in name for k in ("微信", "wechat", "weixin")) and proc_name in (
                    "weixin.exe",
                    "wechat.exe",
                ):
                    return w
            except Exception:
                continue
        return None

    def _ensure_attached(self):
        """确保已连接到微信窗口。"""
        if self._window:
            return
        w = self._find_window()
        if w is None and settings.launch_wechat:
            self._launch()
            w = self._find_window()
        if w is None:
            raise RuntimeError("微信未运行，请先启动微信")
        w.SetActive()
        w.SetTopmost(True)
        time.sleep(0.2)
        w.SetTopmost(False)
        time.sleep(0.2)
        self._window = w

    def _launch(self):
        """启动微信。"""
        paths = [
            os.path.expandvars(r"%PROGRAMFILES%\Tencent\Weixin\Weixin.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Tencent\WeChat\WeChat.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Tencent\WeChat\WeChat.exe"),
        ]
        for exe in paths:
            if os.path.isfile(exe):
                subprocess.Popen([exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(5)
                return

    # ---- 搜索 ----

    def _search_contact(self, name: str):
        """Ctrl+F → 搜索联系人 → 回车打开聊天。"""
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
        """点击窗口底部输入区域。"""
        if not self._window:
            return
        try:
            r = self._window.BoundingRectangle
            x = int((r.left + r.right) / 2)
            y = int(r.bottom - 80)
            auto.Click(x, y)
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
        if settings.ctrl_enter:
            auto.SendKeys("{Ctrl}{Enter}", waitTime=0.01)
        else:
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
                if settings.ctrl_enter:
                    auto.SendKeys("{Ctrl}{Enter}", waitTime=0.01)
                else:
                    auto.SendKeys("{Enter}", waitTime=0.01)
                time.sleep(0.2)
                results.append({"friend": friend, "message": msg, "ok": True})
        return results

    def send_file(self, contact: str, filepath: str) -> bool:
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"文件不存在: {filepath}")

        # CF_HDROP 入剪贴板
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        offset = ctypes.sizeof(wintypes.DWORD) * 3
        wpath = filepath.encode("utf-16-le") + b"\x00\x00"
        size = offset + len(wpath)
        user32.OpenClipboard(0)
        user32.EmptyClipboard()
        hmem = kernel32.GlobalAlloc(0x0002, size)
        buf = kernel32.GlobalLock(hmem)
        ctypes.memmove(buf, ctypes.byref(wintypes.DWORD(offset)), 4)
        ctypes.memmove(buf + 8, ctypes.byref(wintypes.DWORD(1)), 4)
        ctypes.memmove(buf + offset, wpath, len(wpath))
        kernel32.GlobalUnlock(hmem)
        user32.SetClipboardData(15, hmem)
        user32.CloseClipboard()

        self._ensure_attached()
        self._search_contact(contact)
        self._click_input()
        auto.SendKeys("{Ctrl}v", waitTime=0.01)
        time.sleep(0.5)
        auto.SendKeys("{Enter}", waitTime=0.01)
        time.sleep(0.3)
        return True

    # ---- 调试 ----

    def dump_controls(self, max_count: int = 30) -> list[dict]:
        self._ensure_attached()
        out = []
        items = []
        try:
            items = self._window.GetChildren()
        except Exception:
            pass
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
