"""pywinauto 打开微信，搜索联系人，发送文本/文件"""
import ctypes
from ctypes import wintypes
import time
import psutil
from pywinauto import Application, Desktop
from pywinauto import keyboard, mouse
import pyperclip


# --------------- 剪贴板文件 ---------------

def copy_file_to_clipboard(filepath: str) -> None:
    """将文件路径以 CF_HDROP 格式放入剪贴板，微信 Ctrl+V 粘贴即可发文件"""
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    offset = ctypes.sizeof(wintypes.DWORD) * 3  # pFiles + pt + fNC + fWide
    wpath = filepath.encode("utf-16-le") + b"\x00\x00"
    size = offset + len(wpath)

    user32.OpenClipboard(0)
    user32.EmptyClipboard()
    hmem = kernel32.GlobalAlloc(0x0002, size)  # GMEM_MOVEABLE
    buf = kernel32.GlobalLock(hmem)

    ctypes.memmove(buf, ctypes.byref(wintypes.DWORD(offset)), 4)  # pFiles = offset
    ctypes.memmove(buf + 8, ctypes.byref(wintypes.DWORD(1)), 4)   # fWide = True
    ctypes.memmove(buf + offset, wpath, len(wpath))

    kernel32.GlobalUnlock(hmem)
    user32.SetClipboardData(15, hmem)  # CF_HDROP = 15
    user32.CloseClipboard()
    print(f"文件已放入剪贴板: {filepath}")


# --------------- 窗口/聊天 ---------------

def find_weixin_window():
    """枚举顶层窗口，找到微信主窗口"""
    top = Desktop(backend="uia").windows()
    window = None
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
            if (any(k in name for k in ("微信", "wechat", "weixin"))
                    and proc_name in ("weixin.exe", "wechat.exe")):
                print(f"找到微信窗口: {ei.name} (pid={pid})")
                window = w
            if name and len(name) > 0:
                print(f"窗口名称：{name} 进程名称：{proc_name}")
        except Exception:
            continue
    return window


def connect_wechat():
    """连接微信并返回 wrapper_object"""
    win = find_weixin_window()
    if win is None:
        raise RuntimeError("微信未运行，请先启动微信")
    app = Application(backend="uia")
    app.connect(handle=win.handle, timeout=5)
    main_win = app.top_window().wrapper_object()
    print(f"窗口标题: {main_win.element_info.name}")
    if main_win.is_minimized():
        main_win.restore()
    main_win.set_focus()
    time.sleep(0.3)
    return main_win


def open_chat(main_win, contact: str):
    """Ctrl+F 搜索并打开联系人聊天"""
    print(f"搜索并打开: {contact}")
    keyboard.send_keys("^f")
    time.sleep(0.3)
    keyboard.send_keys(f"{contact}{{ENTER}}")
    time.sleep(0.8)

    # 点一下底部输入区域，确保焦点在输入框
    rect = main_win.element_info.rectangle
    cx = int((rect.left + rect.right) / 2)
    input_y = int(rect.bottom - 80)
    mouse.click(button="left", coords=(cx, input_y))
    time.sleep(0.3)


def click_input_area(main_win):
    """点一下输入区域，确保焦点就位"""
    rect = main_win.element_info.rectangle
    cx = int((rect.left + rect.right) / 2)
    input_y = int(rect.bottom - 80)
    mouse.click(button="left", coords=(cx, input_y))
    time.sleep(0.2)


# --------------- 发送 ---------------

def send_text(main_win, message: str):
    """发送文本消息（剪贴板粘贴，避免 IME 问题）"""
    click_input_area(main_win)
    print(f"发送文本: {message}")
    pyperclip.copy(message)
    keyboard.send_keys("^v")
    time.sleep(0.3)
    keyboard.send_keys("{ENTER}")
    time.sleep(0.3)


def send_file(main_win, filepath: str):
    """发送文件（CF_HDROP 入剪贴板 + Ctrl+V 粘贴）"""
    import os
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")

    click_input_area(main_win)
    copy_file_to_clipboard(filepath)
    print(f"发送文件: {filepath}")
    keyboard.send_keys("^v")
    time.sleep(0.5)
    keyboard.send_keys("{ENTER}")
    time.sleep(0.3)


# --------------- 批量群发 ---------------

def broadcast(contacts: list[str], message: str, *, interval: float = 2.0):
    """向多个联系人群发同一条消息"""
    main_win = connect_wechat()
    total = len(contacts)
    for i, name in enumerate(contacts, 1):
        print(f"[{i}/{total}] 发送给: {name}")
        open_chat(main_win, name)
        send_text(main_win, message)
        time.sleep(interval)
    print("群发完成")


# --------------- 入口 ---------------

def demo():
    broadcast(
        contacts=["文件传输助手", "邵翔"],
        message="大家好，这是一条群发测试消息",
        interval=2.0,
    )

    # 发送文件示例（取消注释并改路径即可）
    # main_win = connect_wechat()
    # open_chat(main_win, "文件传输助手")
    # send_file(main_win, r"C:\Users\Admin\Desktop\docker-compose.yml")


if __name__ == "__main__":
    demo()
