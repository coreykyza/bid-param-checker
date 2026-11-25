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
import threading
from datetime import datetime
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
# AI 核验专家用独立模型（异构盲核，避免同一个模型复核自己）。未配置则回退到初判模型。
VERIFY_MODEL = _cfg("LLM_VERIFY_MODEL", default="") or MODEL
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

# 可选访问口令：配置后，/api/grade 必须带正确 token 才放行（防公网白嫖 API Key）。
# /health 与静态页面不受保护，便于探测和访问。token 从 URL ?t= 或 X-Access-Token 头读取。
ACCESS_TOKEN = _cfg("ACCESS_TOKEN", default="")

# ---- 模型自动路由（免费额度场景）----
# LLM_MODEL_POOL / LLM_VERIFY_POOL 是按优先级排列的模型列表，逗号分隔。
# 某模型返回 429（额度耗尽 / 被暂停）即自动拉黑并切下一个，拉黑结果写入 model_deadlist.json，
# 服务重启后依然有效。全部拉黑时清空黑名单重试一轮（防止用户换了 key 后永久卡死）。
# 未配置 pool 时回退到单模型 LLM_MODEL / LLM_VERIFY_MODEL，行为与旧版一致。
# 火山默认池：当 .env 未显式配置 pool 且 base_url 指向火山时自动启用。
# 这样旧 .env 里已失效的 LLM_MODEL 也不会拖垮服务，客户更新只需换 server.py + index.html。
_VOLC_DEFAULT_POOL = "deepseek-v4-1-flash-economy-261017,deepseek-v4-flash-ga-260731,glm-5-3-flash-260828,deepseek-v4-pro-ga-260813,glm-5-2-260617,doubao-seed-evolving"
_VOLC_DEFAULT_VERIFY_POOL = "doubao-seed-evolving,deepseek-v4-pro-ga-260813,glm-5-3-flash-260828"


def _pool(key, fallback):
    raw = _cfg(key, default="")
    if raw:
        return [x.strip() for x in raw.split(",") if x.strip()]
    if "volces.com" in API_URL:
        if key == "LLM_MODEL_POOL":
            return [x.strip() for x in _VOLC_DEFAULT_POOL.split(",") if x.strip()]
        if key == "LLM_VERIFY_POOL":
            return [x.strip() for x in _VOLC_DEFAULT_VERIFY_POOL.split(",") if x.strip()]
    return [fallback] if fallback else []

MODEL_POOL = _pool("LLM_MODEL_POOL", MODEL)
VERIFY_POOL = _pool("LLM_VERIFY_POOL", VERIFY_MODEL) or MODEL_POOL
DEAD_FILE = BASE / "model_deadlist.json"
_dead_lock = threading.Lock()


def _load_dead():
    try:
        with _dead_lock:
            if DEAD_FILE.is_file():
                return json.loads(DEAD_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_dead(d):
    try:
        with _dead_lock:
            DEAD_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        sys.stderr.write(f"[route] 无法保存模型黑名单: {e}\n")


def _mark_dead(model, reason):
    d = _load_dead()
    d[model] = {"ts": datetime.now().isoformat(timespec="seconds"), "reason": str(reason)[:160]}
    _save_dead(d)
    sys.stderr.write(f"[route] 模型 {model} 已拉黑：{str(reason)[:100]}\n")


def _active_model(pool):
    """返回本次请求应使用的模型；如全部拉黑则清空黑名单从头再来。"""
    dead = _load_dead()
    for m in pool:
        if m not in dead:
            return m
    _save_dead({})
    sys.stderr.write("[route] 池内模型全部拉黑，清空黑名单重试一轮\n")
    return pool[0] if pool else ""

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-Access-Token",
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
                "model": _active_model(MODEL_POOL),
                "verify_model": _active_model(VERIFY_POOL),
                "provider": PROVIDER,
                "thinking": THINKING or None,
                "route": "auto" if len(MODEL_POOL) > 1 else "single",
                "model_pool": MODEL_POOL,
                "verify_pool": VERIFY_POOL,
                "dead_models": list(_load_dead().keys()),
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
        # 访问口令校验：仅保护花钱的 /api/grade，静态页面与 /health 公开。
        if ACCESS_TOKEN:
            supplied = self.headers.get("X-Access-Token", "")
            if not supplied and "?" in self.path:
                from urllib.parse import parse_qs, urlsplit
                supplied = parse_qs(urlsplit(self.path).query).get("t", [""])[0]
            if supplied != ACCESS_TOKEN:
                self._json(401, {"error": "UNAUTHORIZED", "message": "访问口令错误或缺失"})
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
            role = data.get("role") or ""
        except Exception as e:
            self._json(400, {"error": "BAD_REQUEST", "message": str(e)})
            return

        # 按池顺序调用；429 / 模型未开通即拉黑该模型并自动切下一个，直到成功或全部耗尽。
        pool = VERIFY_POOL if role == "verify" else MODEL_POOL
        candidates = [m for m in pool if m not in _load_dead()]
        if not candidates:
            _save_dead({})
            sys.stderr.write("[route] 池内模型全部拉黑，清空黑名单重试一轮\n")
            candidates = list(pool)
        last_error = None
        for use_model in candidates:
            payload = {
                "model": use_model,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": int(_cfg("LLM_MAX_TOKENS", default="8192")),
                "response_format": {"type": "json_object"},
            }
            # DeepSeek V4 默认开启思考，结构化判定不需要，关掉更快且不空返回。
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
                    return
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "ignore")[:500]
                last_error = (e.code, detail)
                if e.code == 429 or (e.code == 403 and ("not activated" in detail.lower() or "未开通" in detail)):
                    _mark_dead(use_model, f"HTTP {e.code}: {detail}")
                    sys.stderr.write(f"[route] {use_model} 额度耗尽/不可用，切换下一个模型\n")
                    continue
                self._json(e.code, {"error": "UPSTREAM_HTTP_ERROR", "status": e.code, "detail": detail})
                return
            except Exception as e:
                self._json(502, {"error": "UPSTREAM_ERROR", "message": str(e)})
                return
        status = last_error[0] if last_error else 429
        self._json(status, {
            "error": "ALL_MODELS_EXHAUSTED",
            "message": "模型池内所有模型均不可用，请补充免费额度或换新 key",
            "detail": last_error[1] if last_error else "",
        })

    def log_message(self, fmt, *args):
        # 静默日志，避免刷屏；错误仍输出
        if args and len(args) > 1 and str(args[1]).startswith(("4", "5")):
            sys.stderr.write("[proxy] %s\n" % (fmt % args))


class ReusableTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    configured = bool(API_KEY and not API_KEY.startswith("your_"))
    print(f"[bid-checker proxy] provider={PROVIDER} model={_active_model(MODEL_POOL)} verify_model={_active_model(VERIFY_POOL)} thinking={THINKING or '-'} key_configured={configured} port={PORT}")
    print(f"[bid-checker proxy] 自动路由={'开' if len(MODEL_POOL) > 1 else '关'} 初判池={len(MODEL_POOL)}个 核验池={len(VERIFY_POOL)}个 已拉黑={len(_load_dead())}个")
    if not configured:
        print("[bid-checker proxy] WARNING: .env 未配置 LLM_API_KEY，真实核验不可用（HTML 会走演示模式）")
    print(f"[bid-checker proxy] 本机打开 http://localhost:{PORT}/index.html；外网访问请用 http://<服务器公网IP>:{PORT}/index.html")
    print("[bid-checker proxy] 注意：监听 0.0.0.0 后，任何能访问该端口的人都能调用你的 API Key，务必用安全组限制来源 IP")
    with ReusableTCPServer(("0.0.0.0", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[bid-checker proxy] 已停止")
