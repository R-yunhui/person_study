"""uiautomation 版微信操控 — 找窗口 → 搜索联系人 → 发送消息/文件"""
import time
import psutil
import pyperclip

import uiautomation as auto


# --------------- 实用 ---------------

def _log(msg: str) -> None:
    clean = msg.encode("gbk", errors="replace").decode("gbk", errors="replace")
    print(f"[{time.strftime('%H:%M:%S')}] {clean}")


# --------------- 窗口 ---------------

def find_weixin():
    """枚举所有顶层窗口，找到微信主窗口（比对 pid 进程名）。"""
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
            if any(k in name for k in ("微信", "wechat", "weixin")) and proc_name in ("weixin.exe", "wechat.exe"):
                _log(f"找到微信: {w.Name} (pid={pid})")
                return w
        except Exception:
            continue
    return None


def activate_wechat():
    """找到并激活微信主窗口。"""
    win = find_weixin()
    if not win:
        raise RuntimeError("微信未运行")
    win.SetActive()
    win.SetTopmost(True)
    time.sleep(0.3)
    win.SetTopmost(False)
    _log(f"窗口已激活: {win.Name}")
    return win


# --------------- 搜索 & 输入 ---------------

def search_contact(contact: str):
    """Ctrl+F → 输入联系人名 → 回车打开聊天。"""
    auto.SendKeys("{Ctrl}f", waitTime=0.01)
    time.sleep(0.3)
    auto.SendKeys("{Ctrl}a", waitTime=0.01)
    auto.SendKeys("{Back}", waitTime=0.01)
    time.sleep(0.05)
    pyperclip.copy(contact)
    auto.SendKeys("{Ctrl}v", waitTime=0.01)
    time.sleep(0.2)
    auto.SendKeys("{Enter}", waitTime=0.01)
    time.sleep(0.8)


# --------------- 发送消息 ---------------

def _click_window_bottom():
    """点击当前窗口底部（输入区域附近）。"""
    win = find_weixin()
    if not win:
        return
    try:
        r = win.BoundingRectangle
        x = int((r.left + r.right) / 2)
        y = int(r.bottom - 80)
        auto.Click(x, y)
        time.sleep(0.2)
    except Exception:
        pass


def send_text(contact: str, message: str):
    """搜索联系人并发送文本消息（剪贴板粘贴）。"""
    _log(f"发送给: {contact}")
    search_contact(contact)
    _click_window_bottom()

    pyperclip.copy(message)
    auto.SendKeys("{Ctrl}v", waitTime=0.05)
    time.sleep(0.2)
    auto.SendKeys("{Enter}", waitTime=0.05)
    _log(f"已发送: {message[:60]}")
    time.sleep(0.3)


def send_file(contact: str, filepath: str):
    """发送文件（CF_HDROP 入剪贴板 + Ctrl+V）。"""
    import os, ctypes
    from ctypes import wintypes

    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    # CF_HDROP 格式
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

    _log(f"发送文件: {filepath}")
    search_contact(contact)
    _click_window_bottom()
    auto.SendKeys("{Ctrl}v", waitTime=0.05)
    time.sleep(0.5)
    auto.SendKeys("{Enter}", waitTime=0.05)
    time.sleep(0.3)


# --------------- 批量 ---------------

def broadcast(contacts: list[str], message: str, *, interval: float = 2.0):
    """向多个联系人群发同一条消息。"""
    total = len(contacts)
    for i, name in enumerate(contacts, 1):
        _log(f"[{i}/{total}] {name}")
        send_text(name, message)
        time.sleep(interval)
    _log("完成")


# --------------- 调试 ---------------

def dump_controls(max_count: int = 30):
    """打印微信窗口的控件树（调试用）。"""
    win = find_weixin()
    if not win:
        _log("未找到微信窗口")
        return
    wc = auto.WindowControl(Name=win.Name)
    _log(f"控件树 ({wc.Name}):")
    items = []
    try:
        items = wc.GetChildren()
    except Exception:
        pass
    for i, c in enumerate(items[:max_count]):
        try:
            _log(f"  [{i}] ControlType={c.ControlTypeName} Name={c.Name or ''} Class={c.ClassName or ''}")
        except Exception:
            pass


# --------------- Demo ---------------

def demo():
    activate_wechat()
    send_text("文件传输助手", "uiautomation 测试消息")
    # dump_controls()


if __name__ == "__main__":
    demo()
