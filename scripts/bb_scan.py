# -*- coding: utf-8 -*-
"""BB 通知扫描：登录 Blackboard → 抓通知 → 新动态输出（cron 用，无新则静默）"""
import subprocess, shutil, re, json, os, io, sys, hashlib, tempfile
from common import load_env, require

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

env = load_env()
stu = require(env, "CUHK_STUDENT_ID")
pw = require(env, "CUHK_BB_PASSWORD")
domain = env.get("CUHK_BB_DOMAIN", "cuhksz")
sts_auth = require(env, "CUHK_STS_AUTH_URL")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STATE_DIR = os.path.join(ROOT, "state")
os.makedirs(STATE_DIR, exist_ok=True)
STATE = os.path.join(STATE_DIR, "bb_notify_state.json")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
CURL_CANDIDATES = [
    r"C:\Program Files\Git\mingw64\bin\curl.exe",
    r"C:\Program Files\Git\usr\bin\curl.exe",
    r"C:\Program Files\Git\bin\curl.exe",
    r"C:\Windows\System32\curl.exe",
]
curl = next((c for c in CURL_CANDIDATES if os.path.exists(c)), None) or shutil.which("curl")
if not curl:
    raise SystemExit("找不到 curl，请安装 Git for Windows（自带 curl）")

def curl_run(args, timeout=60):
    cmd = [curl, "-s", "--max-time", str(timeout), "-A", UA] + args
    r = subprocess.run(cmd, capture_output=True, timeout=timeout + 15)
    return r.stdout

def get_location(headers_bytes):
    text = headers_bytes.decode("utf-8", errors="replace")
    m = re.search(r"(?i)^Location:\s*(\S+)", text, re.M)
    return m.group(1).strip() if m else None

def get_code(url):
    m = re.search(r"code=([A-Za-z0-9_-]{8,})", url)
    return m.group(1) if m else None

tmp = tempfile.gettempdir()
cj = os.path.join(tmp, "aiw_cookies.txt")

# 1. GET AD FS 登录页
html = curl_run(["-c", cj, sts_auth]).decode("utf-8", "replace")
m = re.search(r'action="(/adfs/oauth2/authorize[^"]*)"', html)
if not m:
    print("LOGIN_FAIL: 无法解析登录页")
    sys.exit(1)
action = m.group(1).replace("&amp;", "&")
login_url = "https://STS.cuhk.edu.cn" + action

# 2. POST 登录（域\学号）
username = domain + "\\" + stu
h1 = curl_run(["-b", cj, "-c", cj, "-D", "-", "-o", "NUL",
               "--data-urlencode", "UserName=" + username,
               "--data-urlencode", "Password=" + pw,
               "--data-urlencode", "AuthMethod=FormsAuthentication",
               "--data", "Kmsi=true",
               "-H", "Origin: https://STS.cuhk.edu.cn",
               "-H", "Referer: " + login_url,
               login_url])
loc1 = get_location(h1)
if not loc1:
    print("LOGIN_FAIL: 登录未跳转")
    sys.exit(1)

# 3. 跟随跳转拿授权码
h2 = curl_run(["-b", cj, "-c", cj, "-D", "-", "-o", "NUL", loc1])
loc2 = get_location(h2)
code = get_code(loc2 or "")
if not code:
    print("LOGIN_FAIL: 未获取授权码")
    sys.exit(1)

# 4. 兑换 BB 会话
curl_run(["-b", cj, "-c", cj, "-o", "NUL", loc2])

# 5. 抓通知页
ann = curl_run(["-b", cj, "-c", cj,
                "https://bb.cuhk.edu.cn/webapps/blackboard/execute/announcement?method=search&context=mybb&handle=my_announcements"]).decode("utf-8", "replace")
if len(ann) < 5000:
    print("FETCH_FAIL: 通知页过小，可能登录失败")
    sys.exit(1)

# 6. 解析
plain = re.sub(r"<script[\s\S]*?</script>", " ", ann)
items = []
for m in re.finditer(r'href="(/bbcswebdav/[^"]+)"[^>]*>\s*([^<]{2,80})\s*<', plain):
    name = m.group(2).strip()
    if name and not name.startswith("&"):
        items.append(("attachment", name))
for m in re.finditer(r'href="([^"]*announcement[^"]*)"[^>]*>\s*([^<]{2,100})\s*<', plain, re.I):
    name = m.group(2).strip()
    if name and "javascript" not in m.group(1) and not re.search(r"\.(docx?|pdf|xlsx?|zip|ppt)$", name, re.I):
        items.append(("announcement", name))

# 7. 状态对比
first_run = not os.path.exists(STATE)
seen = set()
if os.path.exists(STATE):
    try:
        with io.open(STATE, encoding="utf-8") as fh:
            seen = set(json.load(fh))
    except Exception:
        seen = set()

new_items = []
for typ, name in items:
    key = hashlib.md5((typ + name).encode()).hexdigest()[:12]
    if key not in seen:
        new_items.append((typ, name))
        seen.add(key)

with io.open(STATE, "w", encoding="utf-8") as fh:
    json.dump(sorted(seen), fh, ensure_ascii=False)

if first_run:
    sys.exit(0)
if new_items:
    print("【BB 新动态】" + str(len(new_items)) + " 条")
    for typ, name in new_items[:8]:
        tag = "附件" if typ == "attachment" else "通知"
        print("  " + tag + ": " + name[:60])
    if len(new_items) > 8:
        print("  ...共 " + str(len(new_items)) + " 条")
