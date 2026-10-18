#!/usr/bin/env python3
"""生成 Home Assistant 集成用的授权码。

用法：

    # 1. 准备 session.json（与 get_tokens.py 相同格式）
    # 2. 生成授权码
    python export_auth.py

输出一串字符，粘贴到 Home Assistant 里「方太洗碗机」集成的配置框即可。
授权码里已经包含续期所需的全部信息，填一次就好。

注意：授权码等同于账号凭证，不要发给别人。
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SESSION_FILE = HERE / "session.json"

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


def main() -> None:
    if not SESSION_FILE.exists():
        sys.exit(f"找不到 {SESSION_FILE}\n请先准备好账号信息（格式见 get_tokens.py 顶部说明）。")

    data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    missing = [k for k in ("user_id", "phone", "access_token", "refresh_token") if not data.get(k)]
    if missing:
        sys.exit(f"session.json 缺少字段: {', '.join(missing)}")

    payload = {
        "u": str(data["user_id"]),
        "p": str(data["phone"]),
        "a": data["access_token"],
        "r": data["refresh_token"],
    }
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    code = base64.urlsafe_b64encode(raw).decode().rstrip("=")

    print("授权码（复制整行，粘贴到 Home Assistant）：\n")
    print(code)
    print(f"\n长度 {len(code)} 字符")


if __name__ == "__main__":
    main()
