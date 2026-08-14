import urllib.request, json, time, urllib.parse
from datetime import datetime, timezone

PROXY = "http://127.0.0.1:3456"
NOW = datetime.now(timezone.utc)
MAX_AGE_DAYS = 45

def post(path, data, params=None):
    url = PROXY + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, data=data.encode('utf-8'), method='POST')
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.read().decode('utf-8', 'ignore')
    except Exception as e:
        return '{"error":"%s"}' % str(e)

def new_tab(url):
    res = post("/new", url)
    try:
        return json.loads(res).get('targetId')
    except:
        return None

def eval_js(target, js):
    res = post("/eval", js, {"target": target})
    try:
        return json.loads(res).get('value')
    except:
        return res

# 提取：链接 + 正文 + ISO 时间戳（X 的 <time datetime> 属性）
JS = """JSON.stringify([...document.querySelectorAll('article')].slice(0,20).map(a=>{
  const st=a.querySelector('a[href*="/status/"]');
  const te=a.querySelector('time');
  return {h:st?st.getAttribute('href'):'', t:a.innerText.slice(0,420),
          d:te?te.getAttribute('datetime'):''};
}))"""

KEYWORDS = [
    "client voice note",
    "freelancer voice message",
    "virtual assistant voice note",
    "client sends voice note",
    "voice notes from clients",
    "designer client voice note",
]

SPAM = ['hire me', 'dm me', 'link in bio', 'book a call', 'book a free', 'my services',
        'i help', 'we help', 'agency', 'virtual assistant services', 'click the link',
        'sign up', 'join my', 'enroll', 'course', 'coaching', 'let me handle', 'i offer',
        'krispcall', 'nobl', 'locul', 'use my']

EMOTION = ['her voice', 'his voice', 'i miss', 'miss her', 'miss him', 'boyfriend',
           'girlfriend', 'crush', 'my ex', 'ex ', 'breakup', 'heart', 'love you',
           'drowning in memories', 'drown in memories']

WORK = ['client', 'freelance', 'virtual assistant', 'my boss', 'customer', 'inbox',
        'business', 'bookkeep', 'real estate', 'my coach', 'admin', 'designer', 'brand']

PAIN = ['exhaust', 'tired', 'hate', 'drown', 'too many', 'overwhelm', 'struggl',
        'annoy', 'frustrat', "can't keep up", 'falling behind', 'need to transcrib',
        'how to transcrib', 'what tool', 'recommend', 'help me', 'any tool',
        'so many', 'pile up', 'behind on', 'spend hours', 'waste time', 'listen to',
        're-listen', 'relisten', 'transcrib', 'simple', 'just need something']

def days_old(d_str):
    if not d_str:
        return 999
    try:
        dt = datetime.fromisoformat(d_str.replace('Z', '+00:00'))
        return (NOW - dt).days
    except:
        return 999

all_tweets = []
seen = set()
for kw in KEYWORDS:
    # 用 f=live（最新排序）而不是 f=top（历史高赞，会混入老帖）
    url = "https://x.com/search?q=" + urllib.parse.quote(kw) + "&f=live"
    tid = new_tab(url)
    if not tid:
        continue
    time.sleep(9)
    raw = eval_js(tid, JS)
    try:
        arr = json.loads(raw)
    except:
        arr = []
    for a in arr:
        h = a.get('h', '')
        t = a.get('t', '')
        d = a.get('d', '')
        if not h or h in seen:
            continue
        age = days_old(d)
        if age > MAX_AGE_DAYS:
            continue  # 过滤超过 45 天的老帖
        seen.add(h)
        tl = t.lower()
        has_voice = any(w in tl for w in ['voice', 'audio', 'voicemail'])
        if not has_voice:
            continue
        if any(s in tl for s in SPAM):
            continue
        if any(e in tl for e in EMOTION):
            continue
        if not any(w in tl for w in WORK):
            continue
        strong = any(p in tl for p in PAIN)
        all_tweets.append({'h': h, 't': t, 'strong': strong, 'kw': kw, 'age': age})
    time.sleep(1)

all_tweets.sort(key=lambda x: (not x['strong'], x['age']))

lines = ["# X 痛点帖回复清单（AI 抓取，你手动回）", "",
         "抓取时间：" + time.strftime('%Y-%m-%d %H:%M'),
         "只抓最近 %d 天内、工作场景+语音痛点的推文（已去重过滤）：%d 条" % (MAX_AGE_DAYS, len(all_tweets)),
         "其中强痛点（抱怨/问工具）：%d 条" % sum(1 for x in all_tweets if x['strong']),
         "", "操作：点链接 → 登录你 X → 粘贴对应话术 → 发。回完喊【下一批】我再来一轮。", "", "---", ""]

for i, p in enumerate(all_tweets, 1):
    link = "https://x.com" + p['h']
    tag = "【强痛点】" if p['strong'] else "【相关】"
    lines.append("## %d. %s %s  (约 %d 天前)" % (i, tag, link, p['age']))
    lines.append("**对方原话（节选）：** " + p['t'][:320])
    lines.append("")
    lines.append("**复制即用回复（按对方语气选一条）：**")
    lines.append("")
    lines.append("> A（共情型，对方在抱怨）：honestly the voice-note pileup from clients is the worst part of this job. I built myself a tiny thing that turns client audio into a task list + a reply draft so I stopped re-listening 5x. happy to share if useful")
    lines.append("")
    lines.append("> B（工具型，对方问怎么转写）：for transcribing client voice notes I use a small tool that spits out action items + a draft reply from the audio. want the link?")
    lines.append("")
    lines.append("> C（轻推型，对方描述具体痛点）：that exact problem (client drops a 2-min voice note, you re-listen 3x to catch the tasks) is why I made a tool that turns the audio into a checklist + reply draft. dm me if you want it")
    lines.append("")
    lines.append("---")
    lines.append("")

with open("X_REPLY_LIST.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("TOTAL_RELEVANT", len(all_tweets), "STRONG", sum(1 for x in all_tweets if x['strong']))
