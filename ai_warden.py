# -*- coding: utf-8 -*-
"""AI 导员统一入口
用法:
  python ai_warden.py check   # 检查配置
  python ai_warden.py bb      # 扫描 BB 通知
  python ai_warden.py mail    # 扫描 QQ 邮箱
  python ai_warden.py all     # 全跑
"""
import sys, os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "scripts")
sys.path.insert(0, SCRIPTS)

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    py = sys.executable
    if cmd == "check":
        from common import load_env, require
        env = load_env()
        ok = True
        for key in ["CUHK_STUDENT_ID", "CUHK_BB_PASSWORD", "QQ_EMAIL", "QQ_IMAP_AUTHCODE"]:
            try:
                require(env, key)
                print("  ✓ " + key)
            except SystemExit as e:
                print("  ✗ " + str(e))
                ok = False
        print("配置" + ("完整 ✓" if ok else "不完整，请检查 .env"))
    elif cmd in ("bb", "mail"):
        subprocess.run([py, os.path.join(SCRIPTS, cmd + "_scan.py")])
    elif cmd == "all":
        for c in ("bb", "mail"):
            subprocess.run([py, os.path.join(SCRIPTS, c + "_scan.py")])
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
