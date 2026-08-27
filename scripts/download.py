# -*- coding: utf-8 -*-
"""BB 课件下载: python ai_warden.py download <课程关键词> [文件关键词]
例: download CSC3150            # 下载 CSC3150 全部文件
    download CSC3150 review     # 只下文件名含 review 的
"""
import subprocess, shutil, re, os, sys, tempfile, time
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
DL_DIR = os.path.join(ROOT, "downloads")
BASE = "https://bb.cuhk.edu.cn"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

CURL_CANDIDATES = [
    r"C:\Program Files\Git\mingw64\bin\curl.exe",
    r"C:\Program Files\Git\usr\bin\curl.exe",
    r"C:\Program Files\Git\bin\curl.exe",
    r"C:\Windows\System32\curl.exe",
]
curl = next((c for c in CURL_CANDIDATES if os.path.exists(c)), None) or shutil.which("curl")
if not curl:
    raise SystemExit("找不到 curl，请安装 Git for Windows")

def curl_get(args, timeout=120):
    cmd = [curl, "-s", "--max-time", str(timeout), "-A", UA] + args
    r = subprocess.run(cmd, capture_output=True, timeout=timeout + 20)
    return r.stdout

def get_location(headers):
    m = re.search(r"(?i)^Location:\s*(\S+)", headers.decode("utf-8", "replace"), re.M)
    return m.group(1).strip() if m else None

# ---------- 登录 ----------
cj = os.path.join(tempfile.gettempdir(), "aiw_dl_cookies.txt")
try:
    os.remove(cj)
except OSError:
    pass

html = curl_get(["-c", cj, sts_auth]).decode("utf-8", "replace")
m = re.search(r'action="(/adfs/oauth2/authorize[^"]*)"', html)
if not m:
    print("LOGIN_FAIL: 无法解析登录页")
    sys.exit(1)
action = m.group(1).replace("&amp;", "&")
login_url = "https://STS.cuhk.edu.cn" + action
username = domain + "\\" + stu
h1 = curl_get(["-b", cj, "-c", cj, "-D", "-", "-o", "NUL",
               "--data-urlencode", "UserName=" + username,
               "--data-urlencode", "Password=" + pw,
               "--data-urlencode", "AuthMethod=FormsAuthentication",
               "--data", "Kmsi=true",
               "-H", "Origin: https://STS.cuhk.edu.cn",
               "-H", "Referer: " + login_url, login_url])
loc1 = get_location(h1)
if not loc1:
    print("LOGIN_FAIL: 登录未跳转")
    sys.exit(1)
h2 = curl_get(["-b", cj, "-c", cj, "-D", "-", "-o", "NUL", loc1])
loc2 = get_location(h2)
if not loc2 or "code=" not in loc2:
    print("LOGIN_FAIL: 未获取授权码")
    sys.exit(1)
curl_get(["-b", cj, "-c", cj, "-o", "NUL", loc2])
print("登录成功")

# ---------- 参数 ----------
if len(sys.argv) < 2:
    print("用法: python ai_warden.py download <课程关键词> [文件关键词]")
    sys.exit(1)
keyword = sys.argv[1]
file_kw = sys.argv[2] if len(sys.argv) > 2 else ""

# ---------- 找课程 ----------
tab = curl_get(["-b", cj, "-c", cj, BASE + "/webapps/portal/execute/tabs/tabAction?tab_tab_group_id=_2_1"]).decode("utf-8", "replace")
course = None
for m in re.finditer(r'href="\s*(/webapps/blackboard/execute/launcher\?type=Course&id=(_?\d+_\d+)[^"]*)"[^>]*>\s*([^<]{2,80})\s*<', tab):
    name = m.group(3).strip()
    if name and keyword.lower() in name.lower():
        course = (m.group(2), name)
        break
if not course:
    print("没找到课程关键词: " + keyword)
    for m in re.finditer(r'<a[^>]*href="[^"]*launcher\?type=Course&id=(_?\d+_\d+)[^"]*"[^>]*>([^<]{2,80})<', tab):
        print("  " + m.group(2).strip())
    sys.exit(1)
course_id, course_name = course
print("课程: " + course_name + " (" + course_id + ")")

# ---------- 爬内容 ----------
files = []  # (文件夹, 文件名, url)
visited = set()

def crawl(cid, folder, depth):
    if depth > 4 or cid in visited:
        return
    visited.add(cid)
    url = BASE + "/webapps/blackboard/content/listContent.jsp?course_id=" + course_id
    if cid:
        url += "&content_id=" + cid
    try:
        body = curl_get(["-L", "-b", cj, "-c", cj, url]).decode("utf-8", "replace")
    except Exception:
        return
    if len(body) < 3000:
        return
    tm = re.search(r"<title>([^<]+?) &ndash;", body)
    cur_folder = tm.group(1).strip() if tm else folder
    for m in re.finditer(r'<a href="(/bbcswebdav/[^"]+)"[^>]*>(.*?)</a>', body, re.S):
        fname = re.sub(r"<[^>]+>|&nbsp;|&amp;|&#x27;|&#39;", "", m.group(2)).strip()
        if fname and len(fname) >= 2:
            files.append((cur_folder, fname, BASE + m.group(1)))
    for m in re.finditer(r'href="([^"]*listContent[^"]*)"', body):
        sm = re.search(r"content_id=(_?\d+_\d+)", m.group(1))
        if sm:
            crawl(sm.group(1), cur_folder, depth + 1)

crawl(None, "", 0)
if not files:
    print("课程内容里没找到文件")
    sys.exit(0)
print("找到文件 " + str(len(files)) + " 个")
if file_kw:
    files = [f for f in files if file_kw.lower() in f[1].lower()]
    print("关键词 '" + file_kw + "' 匹配 " + str(len(files)) + " 个")
    if not files:
        sys.exit(0)

# ---------- 下载 ----------
MAGIC = [(b"%PDF", ".pdf"), (b"PK\x03\x04", ".zip"), (b"\x89PNG", ".png"),
         (b"\xff\xd8\xff", ".jpg"), (b"GIF8", ".gif"), (b"ftyp", ".mp4"),
         (b"ID3", ".mp3"), (b"\x1f\x8b", ".gz")]

def detect_ext(tmp):
    try:
        with open(tmp, "rb") as fh:
            head = fh.read(16)
        for magic, ext in MAGIC:
            if head.startswith(magic):
                return ext
    except OSError:
        pass
    return ""

os.makedirs(DL_DIR, exist_ok=True)
done = failed = 0
for folder, fname, url in files:
    safe_course = re.sub(r'[\\/:*?<>|]', '_', course_name)[:40]
    subdir = re.sub(r'[\\/:*?<>|]', '_', folder) if folder else ''
    dest_dir = os.path.join(DL_DIR, safe_course, subdir)
    os.makedirs(dest_dir, exist_ok=True)
    tmp = os.path.join(dest_dir, fname + ".part")
    ok = False
    for attempt in range(3):
        subprocess.run([curl, "-sL", "-C", "-", "-A", UA, "-b", cj, "-o", tmp, url],
                       capture_output=True, timeout=1500)
        if os.path.exists(tmp) and os.path.getsize(tmp) > 0:
            ok = True
            break
        time.sleep(2)
    if not ok:
        print("  失败: " + fname)
        failed += 1
        continue
    ext = detect_ext(tmp)
    final = os.path.join(dest_dir, fname + ext)
    os.rename(tmp, final)
    print("  [OK] " + (folder + "/" if folder else "") + fname + ext + " (" + str(os.path.getsize(final) // 1024) + " KB)")
    done += 1

print("\n完成: " + str(done) + " 个下载, " + str(failed) + " 个失败")
print("位置: " + DL_DIR)
