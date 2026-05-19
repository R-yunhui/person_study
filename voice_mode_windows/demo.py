"""
语音交互演示：按 Enter 录音，再按 Enter 停止识别，TTS 朗读。
说"退出"结束程序。
"""

import logging
from voice_mode_windows import recognize_from_mic, speak

logging.basicConfig(level=logging.INFO, format="%(message)s")


def main():
    speak("语音助手已启动")
    print("=" * 40)
    print("  按 Enter 开始录音，再按 Enter 停止")
    print("  说退出结束程序")
    print("=" * 40)

    while True:
        text = recognize_from_mic()
        if not text:
            speak("没有听到声音，请再说一遍")
            continue

        print(f"\n你说: {text}")

        if "退出" in text or "结束" in text:
            speak("再见")
            break

        speak(f"你说的是：{text}")
        print()


if __name__ == "__main__":
    main()
