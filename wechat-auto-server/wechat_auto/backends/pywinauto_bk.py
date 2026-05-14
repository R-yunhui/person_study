"""pywinauto 后端 — 通过 pywinauto 操控微信 UI"""

import ctypes
import os
import subprocess
import time
from ctypes import wintypes
from typing import Sequence

import psutil
import pyperclip
from pywinauto import Application, Desktop, keyboard, mouse, timings

from wechat_auto.backends.base import WeChatBackend
from wechat_auto.config import settings


class PyWinAutoBackend(WeChatBackend):
    def __init__(self):
        self._attached = False
        self._app: Application | None = None
        self._main_win = None
        timings.Timings.window_find_timeout = 2
        timings.Timings.exists_timeout = 2
        timings.Timings.app_connect_timeout = 2

    # ---- 窗口 ----

    def _find_window(self):
        """枚举顶层窗口，找微信主窗口。"""
        top = Desktop(backend="uia").windows()
        for w in top:
            try:
                ei = w.element_info
                name = (ei.name or "").lower()
                pid = getattr(ei, "process_id", None)
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
        if self._attached:
            return
        win = self._find_window()
        if win is None and settings.launch_wechat:
            self._launch()
            win = self._find_window()
        if win is None:
            raise RuntimeError("微信未运行，请先启动微信")
        self._app = Application(backend="uia")
        self._app.connect(handle=win.handle, timeout=5)
        self._main_win = self._app.top_window().wrapper_object()
        if self._main_win.is_minimized():
            self._main_win.restore()
        self._main_win.set_focus()
        time.sleep(0.3)
        self._attached = True

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
        keyboard.send_keys("^f")
        time.sleep(0.3)
        keyboard.send_keys("^a{BS}")
        time.sleep(0.05)
        pyperclip.copy(name)
        keyboard.send_keys("^v")
        time.sleep(0.2)
        keyboard.send_keys("{ENTER}")
        time.sleep(settings.friend_delay)

    def _click_input(self):
        """点输入区域，确保焦点。"""
        r = self._main_win.element_info.rectangle
        cx = int((r.left + r.right) / 2)
        cy = int(r.bottom - 80)
        mouse.click(button="left", coords=(cx, cy))
        time.sleep(0.2)

    # ---- 发送 ----

    def send_text(self, contact: str, message: str) -> bool:
        self._ensure_attached()
        self._search_contact(contact)
        self._click_input()
        pyperclip.copy(message)
        keyboard.send_keys("^v")
        time.sleep(settings.message_delay)
        if settings.ctrl_enter:
            keyboard.send_keys("^{{ENTER}}")
        else:
            keyboard.send_keys("{ENTER}")
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
                keyboard.send_keys("^v")
                time.sleep(settings.message_delay)
                if settings.ctrl_enter:
                    keyboard.send_keys("^{{ENTER}}")
                else:
                    keyboard.send_keys("{ENTER}")
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
        keyboard.send_keys("^v")
        time.sleep(0.5)
        keyboard.send_keys("{ENTER}")
        time.sleep(0.3)
        return True

    # ---- 调试 ----

    def dump_controls(self, max_count: int = 30) -> list[dict]:
        self._ensure_attached()
        out = []
        for i, c in enumerate(self._main_win.descendants()[:max_count]):
            try:
                ei = c.element_info
                out.append({
                    "index": i,
                    "type": getattr(ei, "control_type", ""),
                    "name": getattr(ei, "name", ""),
                    "class": getattr(ei, "class_name", ""),
                })
            except Exception:
                pass
        return out
