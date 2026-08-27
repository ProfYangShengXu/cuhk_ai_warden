# -*- coding: utf-8 -*-
"""读取 .env 配置（脚本同目录或父目录）"""
import os, io

def load_env():
    here = os.path.dirname(os.path.abspath(__file__))
    # 向上找 .env（scripts/ -> 项目根）
    candidates = [os.path.join(here, ".env"), os.path.join(os.path.dirname(here), ".env")]
    env_path = next((p for p in candidates if os.path.exists(p)), None)
    if not env_path:
        raise SystemExit("找不到 .env！请复制 .env.example 为 .env 并填写")
    kv = {}
    with io.open(env_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                kv[k.strip()] = v.strip().strip("'").strip('"')
    return kv

def require(kv, key):
    v = kv.get(key, "")
    if not v or v.startswith("你的"):
        raise SystemExit(f"缺少配置: {key}，请在 .env 中填写")
    return v
