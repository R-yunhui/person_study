"""后端工厂 — 根据配置选择 pywinauto 或 uiautomation"""

from wechat_auto.config import settings
from wechat_auto.backends.base import WeChatBackend


def create_backend() -> WeChatBackend:
    if settings.backend == "pywinauto":
        from wechat_auto.backends.pywinauto_bk import PyWinAutoBackend
        return PyWinAutoBackend()
    elif settings.backend == "uia":
        from wechat_auto.backends.uia_bk import UiaBackend
        return UiaBackend()
    raise ValueError(f"未知后端: {settings.backend}")
