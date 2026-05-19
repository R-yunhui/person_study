"""
Windows 原生语音识别（ASR）
按 Enter 开始/停止录音，自动识别。完全离线。
"""

import logging
import os
import subprocess
import tempfile
import wave

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)

RECOGNIZE_PS = r'''
Add-Type -AssemblyName System.Speech
$recognizer = New-Object System.Speech.Recognition.SpeechRecognitionEngine("zh-CN")
if (-not $recognizer) {
    $recognizer = New-Object System.Speech.Recognition.SpeechRecognitionEngine("en-US")
}
$recognizer.SetInputToWaveFile($path)
$grammar = New-Object System.Speech.Recognition.DictationGrammar
$recognizer.LoadGrammar($grammar)
try {
    $result = $recognizer.Recognize()
    if ($result) { Write-Output $result.Text } else { Write-Output "" }
} finally {
    $recognizer.Dispose()
}
'''


def _record_to_file(samplerate: int = 16000) -> str | None:
    """录音到临时 WAV 文件，按 Enter 停止。返回路径。"""
    audio_data = []

    def callback(indata, frames, time, status):
        audio_data.append(indata.copy())

    stream = sd.InputStream(samplerate=samplerate, channels=1, dtype="int16", callback=callback)
    stream.start()

    input()  # 等待按 Enter 停止

    stream.stop()
    stream.close()

    if not audio_data:
        return None

    data = np.concatenate(audio_data, axis=0)
    if len(data) < 1600:  # 少于 0.1 秒视为无效
        return None

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(tmp.name, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)
        wf.writeframes(data.tobytes())
    return tmp.name


def recognize_from_mic() -> str:
    """按 Enter 开始/停止录音，自动识别。返回文本。"""
    input("按 Enter 开始录音...")
    logger.info("录音中... (按 Enter 停止)")
    print()  # input() 会占用一行提示

    wav_path = _record_to_file()
    if not wav_path:
        logger.warning("录音太短或无效")
        return ""

    logger.info("识别中...")
    ps_script = f'$path = "{wav_path}"\n{RECOGNIZE_PS}'
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    text = result.stdout.strip()

    os.unlink(wav_path)

    if not text:
        logger.warning("未识别到语音")
        return ""
    logger.info(f"识别结果: {text}")
    return text


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    text = recognize_from_mic()
    print(f">> {text}" if text else ">> (未识别)")
