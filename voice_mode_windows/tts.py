"""
Windows 原生语音合成（TTS）
使用 pyttsx3 调用 Windows SAPI，完全离线，支持中文语音。
"""

import logging
import pyttsx3

logger = logging.getLogger(__name__)

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = pyttsx3.init()
        # 优先选择中文语音
        voices = _engine.getProperty("voices")
        for v in voices:
            if "Chinese" in v.name or any("zh" in lang for lang in getattr(v, "languages", [])):
                _engine.setProperty("voice", v.id)
                logger.info(f"选中语音: {v.name}")
                break
        # 语速稍微放慢一点，更自然
        rate = _engine.getProperty("rate")
        _engine.setProperty("rate", rate - 20)
    return _engine


def speak(text: str) -> None:
    """朗读指定文本（同步阻塞）。"""
    if not text:
        return
    engine = _get_engine()
    engine.say(text)
    engine.runAndWait()


def speak_async(text: str) -> None:
    """朗读指定文本（异步，不阻塞调用线程）。"""
    if not text:
        return
    engine = _get_engine()
    engine.say(text)
    engine.startLoop(False)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    speak("你好，我是 Windows 语音助手。有什么可以帮助你的吗？")
