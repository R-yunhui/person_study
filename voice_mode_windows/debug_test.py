"""分步定位问题：录音质量 + SAPI 识别。"""

import subprocess
import sys
import threading
import time
import wave

import numpy as np
import sounddevice as sd

WAV_PATH = r"D:\ryh\personal\study\voice_mode_windows\test_debug.wav"

# === Step 1: 录音（用线程分离录音和按键等待）===
print("=" * 50)
print("Step 1: 录音测试")
print("按 Enter 开始录音，说几句话，再按 Enter 停止...")
input()

audio_data = []
recording = True

def callback(indata, frames, time, status):
    if recording:
        audio_data.append(indata.copy())

stream = sd.InputStream(samplerate=16000, channels=1, dtype="int16", callback=callback)
stream.start()
print("[INFO] 录音线程已启动")

input()
recording = False

# 等一会确保最后的音频回调完成
time.sleep(0.5)
stream.stop()
stream.close()

if not audio_data:
    print("[FAIL] 未捕获到音频数据")
    # 试试不加 callback 的方式
    print("尝试用 sd.rec() 方式...")
    input("按 Enter 开始录音（sd.rec 方式，录 5 秒）...")
    audio2 = sd.rec(int(5 * 16000), samplerate=16000, channels=1, dtype='int16')
    sd.wait()
    max_val = np.max(np.abs(audio2))
    print(f"sd.rec: 采样数={len(audio2)}, 最大振幅={max_val}")
    if max_val < 100:
        print("[FAIL] sd.rec 也无有效音频信号")
        sys.exit(1)
    data = audio2
else:
    data = np.concatenate(audio_data, axis=0)

duration = len(data) / 16000
max_val = np.max(np.abs(data))
rms = np.sqrt(np.mean(data.astype(float) ** 2))
print(f"[OK] 录音完成: {duration:.1f} 秒")
print(f"[INFO] 最大振幅: {max_val} (0-32767)")
print(f"[INFO] RMS: {rms:.1f}")

if max_val < 500:
    print("[WARN] 最大振幅很低，可能是静音")
else:
    print("[OK] 录音有有效信号")

with wave.open(WAV_PATH, "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(16000)
    wf.writeframes(data.tobytes())
print(f"[OK] WAV 已保存: {WAV_PATH}")

# === Step 2: SAPI 从文件识别 ===
print("\n" + "=" * 50)
print("Step 2: SAPI 文件识别测试")
PS_SCRIPT = f'''
$path = "{WAV_PATH}"
Add-Type -AssemblyName System.Speech
$recognizer = New-Object System.Speech.Recognition.SpeechRecognitionEngine("zh-CN")
if (-not $recognizer) {{ $recognizer = New-Object System.Speech.Recognition.SpeechRecognitionEngine("en-US") }}
$recognizer.SetInputToWaveFile($path)
$grammar = New-Object System.Speech.Recognition.DictationGrammar
$recognizer.LoadGrammar($grammar)
try {{
    $result = $recognizer.Recognize()
    if ($result) {{ Write-Output $result.Text }} else {{ Write-Output "" }}
}} finally {{ $recognizer.Dispose() }}
'''
result = subprocess.run(
    ["powershell", "-NoProfile", "-Command", PS_SCRIPT],
    capture_output=True, text=True, timeout=30,
)
print(f"stdout: [{result.stdout.strip()}]")
if result.stderr:
    print(f"stderr: [{result.stderr.strip()}]")

# === Step 3: SAPI 直接麦克风识别 ===
print("\n" + "=" * 50)
print("Step 3: SAPI 直接麦克风识别（说完等 2 秒静音自动结束）")
PS_DIRECT = '''
Add-Type -AssemblyName System.Speech
$recognizer = New-Object System.Speech.Recognition.SpeechRecognitionEngine("zh-CN")
if (-not $recognizer) { $recognizer = New-Object System.Speech.Recognition.SpeechRecognitionEngine("en-US") }
$recognizer.SetInputToDefaultAudioDevice()
$recognizer.InitialSilenceTimeout = [TimeSpan]::FromSeconds(5)
$recognizer.EndSilenceTimeout = [TimeSpan]::FromMilliseconds(1000)
$grammar = New-Object System.Speech.Recognition.DictationGrammar
$recognizer.LoadGrammar($grammar)
try {
    $result = $recognizer.Recognize()
    if ($result) { Write-Output $result.Text } else { Write-Output "" }
} finally { $recognizer.Dispose() }
'''
result = subprocess.run(
    ["powershell", "-NoProfile", "-Command", PS_DIRECT],
    capture_output=True, text=True, timeout=60,
)
print(f"stdout: [{result.stdout.strip()}]")
if result.stderr:
    print(f"stderr: [{result.stderr.strip()}]")
if result.stdout.strip():
    print("[OK] SAPI 直接麦克风识别成功!")
else:
    print("[FAIL] SAPI 直接麦克风也无结果")
