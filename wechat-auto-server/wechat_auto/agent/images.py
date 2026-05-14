"""图片查找和解码 — 从 attach 目录定位 .dat + wechat-decrypt 解码"""

import glob
import hashlib
import logging
import os
from datetime import datetime

log = logging.getLogger("wechat.agent")


def _find_dat_files(username: str, timestamp: int) -> list[str]:
    """在微信 attach 目录下查找 .dat 图片。"""
    chat_hash = hashlib.md5(username.encode()).hexdigest()
    ym = datetime.fromtimestamp(timestamp).strftime("%Y-%m")
    pattern = os.path.expandvars(
        rf"%USERPROFILE%\xwechat_files\*\msg\attach\{chat_hash}\{ym}\Img\*.dat"
    )
    return sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)


def decode_image(username: str, timestamp: int, out_dir: str) -> str | None:
    """查找并解码图片，返回解码后的路径。"""
    if not out_dir:
        return None
    os.makedirs(out_dir, exist_ok=True)

    dat_files = _find_dat_files(username, timestamp)
    if not dat_files:
        return None

    dat_path = dat_files[0]
    with open(dat_path, "rb") as f:
        hdr = f.read(6)

    # 输出文件名用内容 MD5 前 12 位
    with open(dat_path, "rb") as f:
        md5 = hashlib.md5(f.read(65536)).hexdigest()[:12]
    out_path = os.path.join(out_dir, f"{md5}.jpg")
    if os.path.exists(out_path):
        return out_path

    # wechat-decrypt 解码
    try:
        import importlib.util
        wd_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "wechat-decrypt", "decode_image.py")
        if os.path.isfile(wd_path):
            spec = importlib.util.spec_from_file_location("_wd", wd_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            v2_decrypt = getattr(mod, "v2_decrypt_file", None)
            decrypt_dat = getattr(mod, "decrypt_dat_file", None)

            # 读取 AES key
            aes_key = None
            cfg_path = os.path.join(os.path.dirname(wd_path), "config.json")
            if os.path.isfile(cfg_path):
                import json
                with open(cfg_path) as f:
                    cfg = json.load(f)
                aes_key = cfg.get("image_aes_key", "").encode() if cfg.get("image_aes_key") else None
            xor_key = 0xED

            is_v2 = hdr == b"\x07\x08V2\x08\x07"
            if is_v2 and v2_decrypt and aes_key:
                result, fmt = v2_decrypt(dat_path, f"{out_path}.tmp", aes_key, xor_key)
            elif decrypt_dat:
                result, fmt = decrypt_dat(dat_path, f"{out_path}.tmp", aes_key, xor_key)
            else:
                return None

            if result:
                final = out_path.rsplit(".", 1)[0] + f".{fmt}"
                if os.path.exists(final):
                    os.unlink(final)
                os.rename(result, final)
                log.info("图片已解码: %s", final)
                return final
    except Exception as e:
        log.warning("图片解码失败: %s", e)

    return None
