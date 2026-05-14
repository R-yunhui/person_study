"""微信智能自动回复 — 轮询 → LLM 判断 → LLM 生成回复 → pywinauto 发送"""
import base64
import glob
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import time
import httpx

from datetime import datetime, timedelta
from typing import Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

# --------------- 日志 ---------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bot")


# --------------- 配置 ---------------

MONITOR_CHATS: list[str] = ["KL_邵翔", "KL_林啸虎", "文件传输助手", "ZY_卿平跃"]
MY_NAMES: list[str] = ["话少"]
POLL_INTERVAL: int = 3
CONTEXT_LIMIT: int = 20

# 图片解码后的输出目录
DECODED_IMG_DIR = os.path.join(os.path.dirname(__file__), "decoded_images")

# --------------- 密钥 ---------------

_WD_CONFIG: dict[str, Any] = {}
_wd_cfg_path = os.path.join(os.path.dirname(__file__), "..", "wechat-decrypt", "config.json")
if os.path.isfile(_wd_cfg_path):
    try:
        with open(_wd_cfg_path) as f:
            _WD_CONFIG = json.load(f)
    except Exception:
        pass

WECHAT_AES_KEY: str | None = _WD_CONFIG.get("image_aes_key")
WECHAT_XOR_KEY: int = _WD_CONFIG.get("image_xor_key", 0xED)

# --------------- LLM ---------------

llm = ChatOpenAI(
    model=os.environ.get("QWEN_CHAT_MODEL", "qwen3.5-plus"),
    api_key=os.environ["DASHSCOPE_API_KEY"],
    base_url=os.environ["DASHSCOPE_BASE_URL"],
    temperature=0.85,
    extra_body={"enable_thinking": False},
)

SYSTEM_PROMPT = r"""你是话少的微信分身。话少是一个 27 岁的程序员，成都人，平时喜欢骑车、打游戏、看数码评测。

性格：内向但熟了话多，吐槽型人格，爱用"确实""离谱""真实"这种词，偶尔发个狗头表情。

重要：现在是测试模式，收到任何消息都要回复！

规则：
1. 根据对方语气调整语气——
   - 对方正经 → 你简短正经回应
     例：对方"这个接口 QPS 上不去"→ 你"看看连接池配置，大概率没调优"
   - 对方开玩笑 → 你接梗调侃
     例：对方"我要瘦成闪电"→ 你"闪电也是要胖的先劈到"
   - 对方吐槽/烦躁 → 你共情，别硬搞笑
     例：对方"今天加班到 11 点"→ 你"离谱，这公司是真不当人"
   - 对方闲聊 → 随意接话，像朋友聊天
     例：对方"今天好热"→ 你"确实，出门直接融化"

2. 回复短小，1-3 句话。不知道怎么接的时候发个表情包文字或"确实""真实"

3. 不用"主人""机器人""AI""为您服务"等词。你就是话少本人

4. 可以适当用语气词：嗯、哎、确实、离谱、真实、草、哈哈、额"""


# --------------- wechat-cli ---------------


def _run_wechat_cli(*args: str, raw: bool = False) -> Any:
    """运行 wechat-cli 命令，返回 JSON 解析结果或原始文本。"""
    cmd = ["wechat-cli", *args]
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", timeout=30
        )
        lines = [l for l in r.stdout.splitlines() if not l.startswith("[解密]")]
        text = "\n".join(lines)
        if raw:
            return text
        return json.loads(text)
    except json.JSONDecodeError:
        log.error("wechat-cli 返回非 JSON 结果: %s", cmd)
    except subprocess.TimeoutExpired:
        log.error("wechat-cli 超时: %s", cmd)
    except FileNotFoundError:
        log.error("找不到 wechat-cli 命令，请确认已安装")
    return {} if not raw else ""


def get_new_messages() -> list[dict]:
    """通过 wechat-cli new-messages 获取增量新消息。"""
    data = _run_wechat_cli("new-messages")
    return data.get("messages", []) if isinstance(data, dict) else []


def get_context(chat_name: str, limit: int = CONTEXT_LIMIT) -> str:
    """取最近 5 分钟内的聊天记录作为 LLM 上下文。"""
    start = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M")
    return _run_wechat_cli(
        "history",
        chat_name,
        "--limit",
        str(limit),
        "--start-time",
        start,
        "--format",
        "text",
        raw=True,
    )


# --------------- 图片查找和解码 ---------------


def _find_dat_files(username: str, timestamp: int) -> list[str]:
    """在微信 attach 目录下查找对应时间附近的 .dat 图片文件。

    路径规则：attach/<md5(username)>/<YYYY-MM>/Img/*.dat
    """
    chat_hash = hashlib.md5(username.encode()).hexdigest()
    ym = datetime.fromtimestamp(timestamp).strftime("%Y-%m")
    # 在 xwechat_files 下找所有 wxid 目录
    search_root = os.path.expandvars(
        r"%USERPROFILE%\xwechat_files\*"  # 所有微信账号
    )
    pattern = os.path.join(search_root, "msg", "attach", chat_hash, ym, "Img", "*.dat")
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    return files


def decode_image(username: str, timestamp: int) -> str | None:
    """查找并解码图片 .dat 文件，返回解码后的路径。"""
    os.makedirs(DECODED_IMG_DIR, exist_ok=True)

    dat_files = _find_dat_files(username, timestamp)
    if not dat_files:
        log.info("未找到图片文件: username=%s timestamp=%s", username[:12], timestamp)
        return None

    dat_path = dat_files[0]  # 最新的那个
    # 用 .dat 的 MD5 作为输出文件名（稳定可复现）
    with open(dat_path, "rb") as f:
        file_md5 = hashlib.md5(f.read(65536)).hexdigest()[:12]

    out_path = os.path.join(DECODED_IMG_DIR, f"{file_md5}.jpg")
    if os.path.exists(out_path):
        return out_path

    # 尝试用 wechat-decrypt 解码（目录名带连字符，用 importlib 加载）
    try:
        import importlib.util
        _wd_decoder = os.path.join(
            os.path.dirname(__file__), "..", "wechat-decrypt", "decode_image.py"
        )
        if os.path.isfile(_wd_decoder):
            _spec = importlib.util.spec_from_file_location("_wd_decoder", _wd_decoder)
            _mod = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_mod)
            decrypt_dat_file = _mod.decrypt_dat_file
            is_v2_format = _mod.is_v2_format
            v2_decrypt_file = getattr(_mod, "v2_decrypt_file", None)

        aes_key = WECHAT_AES_KEY.encode() if WECHAT_AES_KEY else None

        # 检查文件格式
        with open(dat_path, "rb") as f:
            hdr = f.read(6)
        v2 = hdr == b"\x07\x08V2\x08\x07"
        v1 = hdr == b"\x07\x08V1\x08\x07"
        log.info("图片格式检测: V2=%s V1=%s XOR=%s AES key=%s", v2, v1, not(v2 or v1), bool(aes_key))

        if v2 and not aes_key:
            log.warning("V2 图片需要 AES key")
            return None
        if v2:
            result, fmt = v2_decrypt_file(
                dat_path, f"{out_path}.tmp", aes_key, WECHAT_XOR_KEY
            )
        else:
            result, fmt = decrypt_dat_file(dat_path, f"{out_path}.tmp", aes_key, 0x88)

        if result:
            final = out_path.rsplit(".", 1)[0] + f".{fmt}"
            if os.path.exists(final):
                os.unlink(final)
            os.rename(result, final)
            log.info("图片已解码: %s", final)
            return final
        else:
            log.warning("wechat-decrypt 解码返回空结果 (result=%s fmt=%s)", result, fmt)
    except ImportError:
        log.warning("wechat-decrypt 未安装，回退到 XOR 解码")
    except Exception as e:
        log.warning("wechat-decrypt 解码失败: %s", e)
        import traceback
        log.warning(traceback.format_exc())

    # 回退：自带的 XOR 解码
    return _xor_decode(dat_path, out_path)


_xor_key: int | None = None


def _xor_decode(dat_path: str, out_path: str) -> str | None:
    """XOR 解码 .dat 文件（自带回退方案）。"""
    global _xor_key

    if os.path.exists(out_path):
        return out_path

    try:
        with open(dat_path, "rb") as f:
            data = bytearray(f.read())
    except Exception as e:
        log.warning("读文件失败 %s: %s", dat_path, e)
        return None
    if len(data) < 2:
        return None

    _MAGIC: dict[bytes, str] = {b"\xff\xd8": "jpg", b"\x89\x50": "png", b"BM": "bmp", b"GIF": "gif"}
    _COMMON_KEYS = [0x1F, 0xAB, 0xAC, 0xAD, 0xAE, 0xAF, 0xD5]

    if _xor_key is not None:
        key = _xor_key
    else:
        candidates = [k for k in _COMMON_KEYS if (data[0] ^ k) == 0xff and (data[1] ^ k) == 0xd8]
        if not candidates:
            for k in range(256):
                if (data[0] ^ k) == 0xff and (data[1] ^ k) == 0xd8:
                    candidates.append(k)
                    break
        if not candidates:
            log.warning("无法确定 XOR 密钥: %s", dat_path)
            return None
        key = candidates[0]
        _xor_key = key
        log.info("XOR 密钥 0x%02X 已缓存", key)

    ext = "jpg"
    for magic, fmt in _MAGIC.items():
        if (data[0] ^ key) == magic[0] and (data[1] ^ key) == magic[1]:
            ext = fmt
            break
    for i in range(len(data)):
        data[i] ^= key

    final = out_path.rsplit(".", 1)[0] + f".{ext}"
    with open(final, "wb") as f:
        f.write(data)
    log.info("XOR 解码完成: %s", final)
    return final


# --------------- 文件路径查询 ---------------


def get_media_path(chat_name: str, create_time: int) -> str | None:
    """通过 history --media 查文件/图片的磁盘路径（兜底方案）。"""
    start = datetime.fromtimestamp(create_time)
    start_str = start.strftime("%Y-%m-%d %H:%M")
    text = _run_wechat_cli(
        "history", chat_name,
        "--limit", "5",
        "--start-time", start_str,
        "--format", "text",
        "--media",
        raw=True,
    )
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("D:\\", "C:\\", "/")) and os.path.exists(stripped):
            return stripped
        if not stripped.startswith("[") and stripped and "\\" in stripped:
            full = os.path.abspath(stripped)
            if os.path.exists(full):
                return full
    return None


# --------------- 发送 ---------------

_replied_contents: dict[str, list[str]] = {}


def _is_self_sent(chat: str, content: str, timestamp: int) -> bool:
    """通过 history 查私聊消息是否是自己发的（手动发微信时区分）。"""
    start = datetime.fromtimestamp(timestamp - 60).strftime("%Y-%m-%d %H:%M")
    text = _run_wechat_cli(
        "history", chat, "--limit", "3",
        "--start-time", start, "--format", "text", raw=True,
    )
    content_first_line = content.split("\n")[0]
    for line in text.splitlines():
        m = re.match(r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] (.+?): (.+)", line)
        if m and (m.group(2).strip() == content or m.group(2).strip() == content_first_line):
            return m.group(1).strip() in MY_NAMES
    return False


def _has_replied(chat: str, content: str) -> bool:
    """检查内容是否近期回复过，支持 40 字前缀匹配应对截断。"""
    prefix = content[:40]
    return any(c[:40] == prefix or c == content for c in _replied_contents.get(chat, []))


def send_message(contact: str, message: str) -> bool:
    """通过本地 HTTP API 发送消息（剪贴板粘贴模式避免 IME 吞字）。"""
    try:
        resp = httpx.post(
            "http://127.0.0.1:8000/send",
            json={
                "friends": [contact],
                "messages": [message],
                "use_paste": True,
                "friend_delay": 0.5,
                "message_delay": 0.3,
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        return True
    except httpx.RequestError as e:
        log.error("发送请求失败: %s", e)
    except httpx.HTTPStatusError as e:
        log.error("发送接口返回 %s: %s", e.response.status_code, e.response.text)
    return False


# --------------- LLM 决策 ---------------


def should_reply(context: str, new_msgs: str, chat_type: str, image_paths: list[str] | None = None) -> str | None:
    """调用 LLM 判断是否回复，返回回复内容或 None。支持传入图片路径进行多模态分析。"""
    prompt = f"""这是{chat_type}记录——

最近消息：
{context}

刚收到的新消息：
{new_msgs}

请决定是否回复。"""

    try:
        if image_paths:
            content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
            for img in image_paths:
                if not os.path.isfile(img):
                    continue
                with open(img, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                ext = img.rsplit(".", 1)[-1]
                content.append({"type": "image_url", "image_url": {"url": f"data:image/{ext};base64,{b64}"}})
            resp = llm.invoke([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ])
        else:
            resp = llm.invoke([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ])
        text = resp.content.strip()
        return text.replace("[SKIP]", "").strip() or text
    except Exception as e:
        log.error("LLM 调用失败: %s", e)
        return None


# --------------- 主循环 ---------------


def main() -> None:
    """主循环，轮询获取新消息，判断是否回复，发送回复"""
    log.info(
        "智能回复机器人启动 | 监控: %s | 身份: %s | 轮询: %ss",
        MONITOR_CHATS, MY_NAMES, POLL_INTERVAL,
    )
    if WECHAT_AES_KEY:
        log.info("V2 图片 AES key 已配置")

    get_new_messages()

    while True:
        try:
            msgs = get_new_messages()
            if not msgs:
                log.info("·")
                time.sleep(POLL_INTERVAL)
                continue

            by_chat: dict[str, list[dict]] = {}
            chat_is_group: dict[str, bool] = {}
            chat_username: dict[str, str] = {}
            for m in msgs:
                chat: str = m.get("chat", "")
                if chat not in MONITOR_CHATS:
                    continue
                by_chat.setdefault(chat, []).append(m)
                if chat not in chat_is_group:
                    chat_is_group[chat] = m.get("is_group", False)
                if chat not in chat_username:
                    chat_username[chat] = m.get("username", "")

            if not by_chat:
                time.sleep(POLL_INTERVAL)
                continue

            for chat, chat_msgs in by_chat.items():
                is_group = chat_is_group.get(chat, False)
                chat_type = "群聊" if is_group else "私聊"
                log.info("[%s] %s 收到 %s 条消息", chat_type, chat, len(chat_msgs))

                new_text = ""
                mentioned = False
                skipped = 0
                image_paths: list[str] = []
                for m in chat_msgs:
                    sender: str = m.get("sender", "")
                    content: str = m.get("last_message", "")
                    msg_type: str = m.get("msg_type", "文本")
                    msg_ts: int = m.get("timestamp", 0)
                    wxid: str = m.get("username", "")

                    if is_group:
                        if sender in MY_NAMES:
                            continue
                        display = sender
                    else:
                        if _has_replied(chat, content):
                            log.info("  ⏭ 跳过已回复过的私聊消息: %s", content[:40])
                            skipped += 1
                            continue
                        if _is_self_sent(chat, content, msg_ts):
                            log.info("  ⏭ 跳过自己手动发的私聊消息: %s", content[:40])
                            skipped += 1
                            continue
                        display = chat

                    extra = ""
                    if msg_type == "图片" and wxid:
                        decoded = decode_image(wxid, msg_ts)
                        if decoded:
                            extra = f" (已解码: {decoded})"
                            # .hevc/.bin 不是标准图片，LLM 不支持，跳过多模态
                            if decoded.rsplit(".", 1)[-1] in ("jpg", "jpeg", "png", "gif", "bmp", "webp"):
                                image_paths.append(decoded)
                            else:
                                log.info("  跳过多模态: 格式不支持 %s", decoded.rsplit(".", 1)[-1])
                        else:
                            extra = f" (图片文件未找到)"
                    elif msg_type in ("链接/文件", "文件", "视频", "语音"):
                        path = get_media_path(chat, msg_ts)
                        if path:
                            extra = f" (路径: {path})"

                    new_text += f"[{display}]: {content}{extra}\n"
                    if is_group and any(n in content for n in MY_NAMES):
                        mentioned = True

                if skipped:
                    log.info("  ⏭ 共跳过 %s 条自己发的消息", skipped)

                if not new_text.strip():
                    continue

                if mentioned:
                    log.info("🔔 被 @ 了")
                elif not is_group:
                    log.info("📩 私聊消息")

                context = get_context(chat)
                log.info("🤔 LLM 决策中...（%s 张图片）", len(image_paths) if image_paths else "")
                reply = should_reply(context, new_text, chat_type, image_paths or None)

                if reply is None:
                    log.info("→ 跳过")
                    continue

                log.info("→ 回复: %s", reply[:80])
                if not send_message(chat, reply):
                    time.sleep(5)

                _replied_contents.setdefault(chat, []).append(reply)
                if len(_replied_contents[chat]) > 20:
                    _replied_contents[chat].pop(0)

        except KeyboardInterrupt:
            log.info("用户中断，已停止")
            break
        except Exception as e:
            log.exception("主循环异常: %s", e)
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
