# -*- coding: utf-8 -*-
"""QQ 邮箱扫描：IMAP 拉新邮件 → 摘要输出（cron 用，无新则静默）"""
import imaplib, email, json, io, os, sys
from email.header import decode_header
from common import load_env, require

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

env = load_env()
account = require(env, "QQ_EMAIL")
code = require(env, "QQ_IMAP_AUTHCODE")
host = env.get("QQ_IMAP_HOST", "imap.qq.com")
port = int(env.get("QQ_IMAP_PORT", "993"))

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STATE_DIR = os.path.join(ROOT, "state")
os.makedirs(STATE_DIR, exist_ok=True)
STATE = os.path.join(STATE_DIR, "mail_state.json")

def dec(s):
    if not s:
        return ""
    out = []
    for p, c in decode_header(s):
        if isinstance(p, bytes):
            try:
                out.append(p.decode(c or "utf-8", errors="replace"))
            except Exception:
                out.append(p.decode("utf-8", errors="replace"))
        else:
            out.append(p)
    return "".join(out)

first_run = not os.path.exists(STATE)
seen = set()
if os.path.exists(STATE):
    try:
        with io.open(STATE, encoding="utf-8") as fh:
            seen = set(json.load(fh))
    except Exception:
        seen = set()

try:
    conn = imaplib.IMAP4_SSL(host, port, timeout=30)
    conn.login(account, code)
    conn.select("INBOX")
    st, data = conn.uid("search", None, "ALL")
    if st != "OK" or not data[0]:
        sys.exit(0)
    uids = data[0].split()[-30:]
    new_items = []
    for u in uids:
        uid_str = u.decode()
        if uid_str in seen:
            continue
        st, mdata = conn.uid("fetch", u, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
        if st != "OK" or not mdata or mdata[0] is None:
            continue
        raw = mdata[0][1].decode("utf-8", errors="replace")
        msg = email.message_from_string(raw)
        subj = dec(msg.get("Subject", "")) or "(no subject)"
        frm = dec(msg.get("From", ""))[:40]
        date = (msg.get("Date", "") or "")[:22]
        new_items.append((uid_str, date, frm, subj))
    all_seen = seen | set(u.decode() for u in uids)
    with io.open(STATE, "w", encoding="utf-8") as fh:
        json.dump(sorted(all_seen), fh, ensure_ascii=False)
    conn.logout()
    if first_run:
        sys.exit(0)
    for uid_str, date, frm, subj in new_items[:5]:
        print(f"[新邮件] {date} {frm} | {subj[:50]}")
except Exception as e:
    print("MAIL_SCAN_ERROR: " + str(e)[:200])
    sys.exit(1)
