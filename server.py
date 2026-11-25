#!/usr/bin/env python3
"""
招投标参数对照工具 — 零依赖本地代理
仅用于转发浏览器请求到智谱 API，API Key 只存在于本机 .env，不进前端源码。
用法：python3 server.py
"""
import http.server
import socketserver
import urllib.request
import urllib.error
import json
import os
import sys
import mimetypes
from pathlib import Path

BASE = Path(__file__).resolve().parent

def load_dotenv(path):
    env = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env

ENV = load_dotenv(BASE / ".env")


def _cfg(*keys, default=""):
    """按顺序取配置：环境变量 > .env > 默认值。支持新旧两套变量名。"""
    for k in keys:
        v = os.environ.get(k) or ENV.get(k)
        if v:
            return v.strip()
    return default


# ---- 模型无关配置 ----
# 优先读通用变量（LLM_*），回退到旧的 ZHIPU_*，保证老 .env 仍能跑。
API_KEY = _cfg("LLM_API_KEY", "DEEPSEEK_API_KEY", "ZHIPU_API_KEY")
MODEL = _cfg("LLM_MODEL", "DEEPSEEK_MODEL", "ZHIPU_MODEL", default="glm-4-flash")
PROVIDER = _cfg("LLM_PROVIDER", default="").lower()

# 按 provider 或模型名推断 base url
_DEFAULT_URLS = {
    "deepseek": "https://api.deepseek.com/v1/chat/completions",
    "zhipu": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
}
if not PROVIDER:
    if MODEL.startswith("deepseek"):
        PROVIDER = "deepseek"
    elif MODEL.startswith("glm") or MODEL.startswith("charglm"):
        PROVIDER = "zhipu"
    elif MODEL.startswith("qwen"):
        PROVIDER = "qwen"
    else:
        PROVIDER = "zhipu"

API_URL = _cfg("LLM_BASE_URL") or _DEFAULT_URLS.get(PROVIDER) or _DEFAULT_URLS["zhipu"]
if API_URL and not API_URL.rstrip("/").endswith("/chat/completions"):
    API_URL = API_URL.rstrip("/") + "/chat/completions"

# 可选：DeepSeek 支持关闭思考模式提速（"disabled" / "enabled"）
THINKING = _cfg("LLM_THINKING", default="")

PORT = int(_cfg("PORT", default="8765"))

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}

class Handler(http.server.BaseHTTPRequestHandler):
    def _json(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/health"):
            self._json(200, {
                "ok": True,
                "key_configured": bool(API_KEY and not API_KEY.startswith("your_")),
                "model": MODEL,
                "provider": PROVIDER,
                "thinking": THINKING or None,
            })
            return
        # 托管静态文件（index.html / vendor 等）
        rel = self.path.split("?", 1)[0].lstrip("/") or "index.html"
        # 浏览器会自动请求 /favicon.ico。没有就返回 204，
        # 免得控制台常驻一条 404 干扰真正的问题排查。
        if rel == "favicon.ico" and not (BASE / rel).is_file():
            self.send_response(204)
            for k, v in CORS_HEADERS.items():
                self.send_header(k, v)
            self.end_headers()
            return
        target = (BASE / rel).resolve()
        if not str(target).startswith(str(BASE)) or not target.is_file():
            self._json(404, {"error": "not found"})
            return
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        body = target.read_bytes()
        self.send_response(200)
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text/") or ctype == "application/javascript" else ""))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if not self.path.startswith("/api/grade"):
            self._json(404, {"error": "not found"})
            return
        if not API_KEY or API_KEY.startswith("your_"):
            self._json(400, {"error": "NO_KEY", "message": "服务器未配置 API Key，请在 .env 中填写 LLM_API_KEY"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            data = json.loads(raw.decode("utf-8"))
            messages = data.get("messages")
            if not messages:
                self._json(400, {"error": "BAD_REQUEST", "message": "缺少 messages"})
                return
        except Exception as e:
            self._json(400, {"error": "BAD_REQUEST", "message": str(e)})
            return

        payload = {
            "model": MODEL,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": int(_cfg("LLM_MAX_TOKENS", default="8192")),
            "response_format": {"type": "json_object"},
        }
        # DeepSeek 默认开启思考模式，逐条判定这种任务不需要推理，关掉快很多。
        # 通过 .env 里 LLM_THINKING=disabled 控制；智谱等不支持该参数的服务不要设置。
        if THINKING in ("enabled", "disabled"):
            payload["thinking"] = {"type": THINKING}
        req = urllib.request.Request(
            API_URL,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=130) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                self._json(200, result)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "ignore")[:500]
            self._json(e.code, {"error": "UPSTREAM_HTTP_ERROR", "status": e.code, "detail": detail})
        except Exception as e:
            self._json(502, {"error": "UPSTREAM_ERROR", "message": str(e)})

    def log_message(self, fmt, *args):
        # 静默日志，避免刷屏；错误仍输出
        if args and len(args) > 1 and str(args[1]).startswith(("4", "5")):
            sys.stderr.write("[proxy] %s\n" % (fmt % args))


class ReusableTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    configured = bool(API_KEY and not API_KEY.startswith("your_"))
    print(f"[bid-checker proxy] provider={PROVIDER} model={MODEL} thinking={THINKING or '-'} key_configured={configured} port={PORT}")
    if not configured:
        print("[bid-checker proxy] WARNING: .env 未配置 ZHIPU_API_KEY，真实核验不可用（HTML 会走演示模式）")
    print(f"[bid-checker proxy] 打开 http://localhost:{PORT}/index.html 使用工具")
    with ReusableTCPServer(("127.0.0.1", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[bid-checker proxy] 已停止")
