"""VoiceBrief 处理端点（Vercel Python Serverless）。

前端把音频读成 base64 -> POST JSON {"audio": <base64>, "name": <可选>} 到这里
-> 转写（智谱 GLM-ASR-2512 或免费 Groq whisper-large-v3）
-> 智谱 glm-4.5-flash 提取任务清单 + 起草回复
-> 返回 JSON {transcript, action_items, reply_draft}

无数据库、无后台定时、纯无状态，适合 Vercel 免费档（不绑卡）。
部署：仓库根放 index.html，本文件放 api/process.py。
环境变量（部署时必填，不要写进代码）：ZHIPU_API_KEY（智谱出稿 key）、GROQ_KEY（Groq 免费 whisper 转写 key）。两者都缺失时返回 500 提示。
"""
import json
import os
import base64
import tempfile
import urllib.request
from http.server import BaseHTTPRequestHandler

ZHIPU_KEY = os.environ.get('ZHIPU_API_KEY', '')
GROQ_KEY = os.environ.get('GROQ_KEY', '')
CHAT_URL = 'https://open.bigmodel.cn/api/paas/v4/chat/completions'
ASR_URL = 'https://open.bigmodel.cn/api/paas/v4/audio/transcriptions'
GROQ_URL = 'https://api.groq.com/openai/v1/audio/transcriptions'


def _multipart(fields, file_tuple):
    boundary = '----vb' + os.urandom(8).hex()
    body = []
    for k, v in fields.items():
        body.append(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (boundary, k, v)).encode())
    fn, data = file_tuple
    body.append(('--%s\r\nContent-Disposition: form-data; name="file"; filename="%s"\r\nContent-Type: application/octet-stream\r\n\r\n' % (boundary, fn)).encode() + data + b'\r\n')
    body.append(('--%s--\r\n' % boundary).encode())
    return b''.join(body), boundary


def _http_json(url, key, payload, timeout=20):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data,
                                 headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def transcribe(path):
    """返回转写文本。优先 Groq 免费 whisper，否则智谱 ASR。"""
    with open(path, 'rb') as f:
        data = f.read()
    if GROQ_KEY:
        body, boundary = _multipart({'model': 'whisper-large-v3'}, ('audio.webm', data))
        req = urllib.request.Request(GROQ_URL, data=body,
                                     headers={'Authorization': 'Bearer ' + GROQ_KEY,
                                              'Content-Type': 'multipart/form-data; boundary=' + boundary,
                                              'User-Agent': 'curl/8.0'})
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode('utf-8')).get('text', '')
    body, boundary = _multipart({'model': 'glm-asr-2512', 'stream': 'false'}, ('audio', data))
    req = urllib.request.Request(ASR_URL, data=body,
                                 headers={'Authorization': 'Bearer ' + ZHIPU_KEY,
                                          'Content-Type': 'multipart/form-data; boundary=' + boundary})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode('utf-8')).get('text', '')


def draft(transcript):
    prompt = (
        "You help a freelancer / consultant turn a client voice message into action.\n"
        "Transcript:\n\"\"\"" + transcript + "\"\"\"\n\n"
        "Return STRICTLY valid JSON (no markdown, no extra text):\n"
        '{"action_items":["specific to-do: who / what / when"],'
        '"reply_draft":"a professional reply to the client, ready to send, in a natural human tone, not robotic"}'
    )
    resp = _http_json(CHAT_URL, ZHIPU_KEY, {
        'model': 'glm-4.5-flash',
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0.3,
        'response_format': {'type': 'json_object'},
    })
    return resp['choices'][0]['message']['content']


class handler(BaseHTTPRequestHandler):
    def _json(self, obj, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(obj, ensure_ascii=False).encode('utf-8'))

    def do_GET(self):
        self._json({'ok': True, 'service': 'VoiceBrief'})

    def do_POST(self):
        try:
            n = int(self.headers.get('Content-Length', 0))
            payload = json.loads(self.rfile.read(n).decode('utf-8'))
            audio = base64.b64decode(payload.get('audio', ''))
            if not audio:
                self._json({'error': 'no audio received'}, 400)
                return
            fd, path = tempfile.mkstemp(suffix='.webm')
            with os.fdopen(fd, 'wb') as f:
                f.write(audio)
            txt = transcribe(path)
            os.remove(path)
            if not txt or not txt.strip():
                self._json({'error': 'transcription came back empty (audio too long / unclear?)'}, 422)
                return
            out = draft(txt)
            try:
                parsed = json.loads(out)
            except Exception:
                parsed = {'action_items': [], 'reply_draft': out}
            parsed['transcript'] = txt
            self._json(parsed)
        except Exception as e:  # noqa
            self._json({'error': str(e)}, 500)

    def log_message(self, *a):
        pass
