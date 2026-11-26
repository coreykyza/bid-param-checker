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
import ssl
import time
import json
import os
import sys
import mimetypes
import threading
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent

# ---- TLS 信任根补充 ----
# 精简版 Windows Server 的根证书库常缺 Let's Encrypt 新根（ISRG Root X2），
# 访问使用 LE 新链的站点（如 tokenfuture.si）会报
# SSL: CERTIFICATE_VERIFY_FAILED / unable to get local issuer certificate。
# 这里在系统默认信任根之上「追加」两张 ISRG 根证书（不覆盖系统原有根），
# 火山（DigiCert Global Root G2）等其它链路完全不受影响。
# 证书来源：letsencrypt.org 官方，SHA256 指纹
#   X1 96:BC:EC:06:26:49:76:F3:74:60:77:9A:CF:28:C5:A7:CF:E8:A3:C0:AA:E1:1A:8F:FC:EE:05:C0:BD:DF:08:C6
#   X2 69:72:9B:8E:15:A8:6E:FC:17:7A:57:AF:B7:17:1D:FC:64:AD:D2:8C:2F:CA:8C:F1:50:7E:34:45:3C:CB:14:70
_ISRG_ROOTS = """-----BEGIN CERTIFICATE-----
MIIFazCCA1OgAwIBAgIRAIIQz7DSQONZRGPgu2OCiwAwDQYJKoZIhvcNAQELBQAw
TzELMAkGA1UEBhMCVVMxKTAnBgNVBAoTIEludGVybmV0IFNlY3VyaXR5IFJlc2Vh
cmNoIEdyb3VwMRUwEwYDVQQDEwxJU1JHIFJvb3QgWDEwHhcNMTUwNjA0MTEwNDM4
WhcNMzUwNjA0MTEwNDM4WjBPMQswCQYDVQQGEwJVUzEpMCcGA1UEChMgSW50ZXJu
ZXQgU2VjdXJpdHkgUmVzZWFyY2ggR3JvdXAxFTATBgNVBAMTDElTUkcgUm9vdCBY
MTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBAK3oJHP0FDfzm54rVygc
h77ct984kIxuPOZXoHj3dcKi/vVqbvYATyjb3miGbESTtrFj/RQSa78f0uoxmyF+
0TM8ukj13Xnfs7j/EvEhmkvBioZxaUpmZmyPfjxwv60pIgbz5MDmgK7iS4+3mX6U
A5/TR5d8mUgjU+g4rk8Kb4Mu0UlXjIB0ttov0DiNewNwIRt18jA8+o+u3dpjq+sW
T8KOEUt+zwvo/7V3LvSye0rgTBIlDHCNAymg4VMk7BPZ7hm/ELNKjD+Jo2FR3qyH
B5T0Y3HsLuJvW5iB4YlcNHlsdu87kGJ55tukmi8mxdAQ4Q7e2RCOFvu396j3x+UC
B5iPNgiV5+I3lg02dZ77DnKxHZu8A/lJBdiB3QW0KtZB6awBdpUKD9jf1b0SHzUv
KBds0pjBqAlkd25HN7rOrFleaJ1/ctaJxQZBKT5ZPt0m9STJEadao0xAH0ahmbWn
OlFuhjuefXKnEgV4We0+UXgVCwOPjdAvBbI+e0ocS3MFEvzG6uBQE3xDk3SzynTn
jh8BCNAw1FtxNrQHusEwMFxIt4I7mKZ9YIqioymCzLq9gwQbooMDQaHWBfEbwrbw
qHyGO0aoSCqI3Haadr8faqU9GY/rOPNk3sgrDQoo//fb4hVC1CLQJ13hef4Y53CI
rU7m2Ys6xt0nUW7/vGT1M0NPAgMBAAGjQjBAMA4GA1UdDwEB/wQEAwIBBjAPBgNV
HRMBAf8EBTADAQH/MB0GA1UdDgQWBBR5tFnme7bl5AFzgAiIyBpY9umbbjANBgkq
hkiG9w0BAQsFAAOCAgEAVR9YqbyyqFDQDLHYGmkgJykIrGF1XIpu+ILlaS/V9lZL
ubhzEFnTIZd+50xx+7LSYK05qAvqFyFWhfFQDlnrzuBZ6brJFe+GnY+EgPbk6ZGQ
3BebYhtF8GaV0nxvwuo77x/Py9auJ/GpsMiu/X1+mvoiBOv/2X/qkSsisRcOj/KK
NFtY2PwByVS5uCbMiogziUwthDyC3+6WVwW6LLv3xLfHTjuCvjHIInNzktHCgKQ5
ORAzI4JMPJ+GslWYHb4phowim57iaztXOoJwTdwJx4nLCgdNbOhdjsnvzqvHu7Ur
TkXWStAmzOVyyghqpZXjFaH3pO3JLF+l+/+sKAIuvtd7u+Nxe5AW0wdeRlN8NwdC
jNPElpzVmbUq4JUagEiuTDkHzsxHpFKVK7q4+63SM1N95R1NbdWhscdCb+ZAJzVc
oyi3B43njTOQ5yOf+1CceWxG1bQVs5ZufpsMljq4Ui0/1lvh+wjChP4kqKOJ2qxq
4RgqsahDYVvTH9w7jXbyLeiNdd8XM2w9U/t7y0Ff/9yi0GE44Za4rF2LN9d11TPA
mRGunUHBcnWEvgJBQl9nJEiU0Zsnvgc/ubhPgXRR4Xq37Z0j4r7g1SgEEzwxA57d
emyPxgcYxn/eR44/KJ4EBs+lVDR3veyJm+kXQ99b21/+jh5Xos1AnX5iItreGCc=
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIICGzCCAaGgAwIBAgIQQdKd0XLq7qeAwSxs6S+HUjAKBggqhkjOPQQDAzBPMQsw
CQYDVQQGEwJVUzEpMCcGA1UEChMgSW50ZXJuZXQgU2VjdXJpdHkgUmVzZWFyY2gg
R3JvdXAxFTATBgNVBAMTDElTUkcgUm9vdCBYMjAeFw0yMDA5MDQwMDAwMDBaFw00
MDA5MTcxNjAwMDBaME8xCzAJBgNVBAYTAlVTMSkwJwYDVQQKEyBJbnRlcm5ldCBT
ZWN1cml0eSBSZXNlYXJjaCBHcm91cDEVMBMGA1UEAxMMSVNSRyBSb290IFgyMHYw
EAYHKoZIzj0CAQYFK4EEACIDYgAEzZvVn4CDCuwJSvMWSj5cz3es3mcFDR0HttwW
+1qLFNvicWDEukWVEYmO6gbf9yoWHKS5xcUy4APgHoIYOIvXRdgKam7mAHf7AlF9
ItgKbppbd9/w+kHsOdx1ymgHDB/qo0IwQDAOBgNVHQ8BAf8EBAMCAQYwDwYDVR0T
AQH/BAUwAwEB/zAdBgNVHQ4EFgQUfEKWrt5LSDv6kviejM9ti6lyN5UwCgYIKoZI
zj0EAwMDaAAwZQIwe3lORlCEwkSHRhtFcP9Ymd70/aTSVaYgLXTWNLxBo1BfASdW
tL4ndQavEi51mI38AjEAi/V3bNTIZargCyzuFJ0nN6T5U6VR5CmD1/iQMVtCnwr1
/q4AaOeMSQ+2b1tbFfLn
-----END CERTIFICATE-----
"""

def _make_ssl_context():
    try:
        ctx = ssl.create_default_context()
        ctx.load_verify_locations(cadata=_ISRG_ROOTS)
        # 精简系统/框架 Python 常缺 CA 根证书库（macOS 框架版、Windows 精简版），
        # 火山（DigiCert 链）会报 CERTIFICATE_VERIFY_FAILED。certifi 可用时追加加载。
        try:
            import certifi
            ctx.load_verify_locations(certifi.where())
        except Exception:
            pass
        return ctx
    except Exception as e:
        sys.stderr.write(f"[tls] 构建 TLS 上下文失败，回退系统默认: {e}\n")
        return None

_SSL_CTX = _make_ssl_context()

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


# ---- 多 provider 配置 ----
# 主 provider（默认/旧 .env）：火山方舟。模型池里不带前缀的条目走这里。
API_KEY = _cfg("LLM_API_KEY", "DEEPSEEK_API_KEY", "ZHIPU_API_KEY")
MODEL = _cfg("LLM_MODEL", "DEEPSEEK_MODEL", "ZHIPU_MODEL", default="glm-4-flash")
PROVIDER = _cfg("LLM_PROVIDER", default="").lower()

_DEFAULT_URLS = {
    "deepseek": "https://api.deepseek.com/v1/chat/completions",
    "zhipu": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
}
if not PROVIDER:
    if MODEL.startswith("deepseek"):
        PROVIDER = "deepseek"
    elif MODEL.startswith("glm") or MODEL.startswith("charglm"):
        PROVIDER = "zhipu"
    else:
        PROVIDER = "custom"

API_URL = _cfg("LLM_BASE_URL") or _DEFAULT_URLS.get(PROVIDER) or _DEFAULT_URLS["zhipu"]
if API_URL and not API_URL.rstrip("/").endswith("/chat/completions"):
    API_URL = API_URL.rstrip("/") + "/chat/completions"

# 可选：DeepSeek 支持关闭思考模式提速（"disabled" / "enabled"）
THINKING = _cfg("LLM_THINKING", default="")

# 附加 provider（如阿里云百炼、TokenFuture）：每个 provider 有自己的 key/url/thinking。
# 模型池条目用 `tag:model` 指定 provider（如 tf:gpt-6.2-sol），无前缀走主 provider。
# 启用的 tag 由 LLM_EXTRA_TAGS 列出（逗号分隔），配置变量：LLM_<TAG>_API_KEY / LLM_<TAG>_BASE_URL / LLM_<TAG>_THINKING
_EXTRA_PROVIDERS = {}
for _tag in [t.strip().upper() for t in _cfg("LLM_EXTRA_TAGS", default="BAILIAN,BAILIAN_KIMI").split(",") if t.strip()]:
    _k = _cfg(f"LLM_{_tag}_API_KEY", default="")
    _u = _cfg(f"LLM_{_tag}_BASE_URL", default="")
    if not _k and _tag == "BAILIAN_KIMI":
        # kimi 专属 tag 未单独配 key 时，继承百炼主 key（只是 thinking 规则不同）
        _k = _cfg("LLM_BAILIAN_API_KEY", default="")
        _u = _cfg("LLM_BAILIAN_BASE_URL", default="")
    if _k and _u:
        if not _u.rstrip("/").endswith("/chat/completions"):
            _u = _u.rstrip("/") + "/chat/completions"
        _EXTRA_PROVIDERS[_tag.lower()] = {
            "key": _k, "url": _u,
            "thinking": _cfg(f"LLM_{_tag}_THINKING", default=""),
        }


def _resolve(model):
    """池条目 → (真实模型名, key, url, thinking)。支持 `bailian:qwen4-max` 前缀。"""
    tag, real = "", model
    if ":" in model:
        tag, real = model.split(":", 1)
        tag = tag.lower()
    if tag and tag in _EXTRA_PROVIDERS:
        p = _EXTRA_PROVIDERS[tag]
        return real, p["key"], p["url"], p["thinking"]
    return real, API_KEY, API_URL, THINKING


# AI 核验专家用独立模型（异构盲核，避免同一个模型复核自己）。未配置则回退到初判模型。
VERIFY_MODEL = _cfg("LLM_VERIFY_MODEL", default="") or MODEL

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
# 模型选择（前端「上传与配置」枚举，请求体带 poolMode）：
#   gpt（默认，慢但准）——初判走 MODEL_POOL（tf:gpt 优先），核验走 VERIFY_POOL（国内优先）
#   cn（快，国内火山）——初判走 MODEL_POOL 剔除 tf: 后的国内池，核验走 tf: 池，仍保持异构复核
_TF_SUBPOOL = [m for m in MODEL_POOL if str(m).startswith("tf:")]
_CN_SUBPOOL = [m for m in MODEL_POOL if not str(m).startswith("tf:")]


def _pick_pool(role, pool_mode):
    if pool_mode == "cn":
        if role == "verify":
            return _TF_SUBPOOL if _TF_SUBPOOL else VERIFY_POOL
        return _CN_SUBPOOL if _CN_SUBPOOL else MODEL_POOL
    return VERIFY_POOL if role == "verify" else MODEL_POOL

DEAD_FILE = BASE / "model_deadlist.json"
_dead_lock = threading.Lock()
# 黑名单自动复活：任何拉黑都有有效期，到点自动重试。
# 避免「一次瞬时并发 429」把高优先级模型永久钉死（第三方中转常见 RPM 限制，
# 与账户额度无关；旧版把 429 一律当额度耗尽且重启不清）。
DEAD_TTL_SEC = int(_cfg("LLM_DEAD_TTL_SEC", default="1800"))  # 默认 30 分钟


def _load_dead():
    """读取黑名单；已过期条目自动移除复活。旧格式（无 until）一律视为过期清除。"""
    try:
        with _dead_lock:
            if not DEAD_FILE.is_file():
                return {}
            d = json.loads(DEAD_FILE.read_text(encoding="utf-8"))
            now = time.time()
            alive = {m: v for m, v in d.items()
                     if isinstance(v, dict) and float(v.get("until", 0)) > now}
            if len(alive) != len(d):
                DEAD_FILE.write_text(json.dumps(alive, ensure_ascii=False, indent=2), encoding="utf-8")
            return alive
    except Exception:
        pass
    return {}


def _save_dead(d):
    try:
        with _dead_lock:
            DEAD_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        sys.stderr.write(f"[route] 无法保存模型黑名单: {e}\n")


def _mark_dead(model, reason, ttl=None):
    d = _load_dead()
    d[model] = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "until": time.time() + (DEAD_TTL_SEC if ttl is None else ttl),
        "reason": str(reason)[:160],
    }
    _save_dead(d)
    sys.stderr.write(f"[route] 模型 {model} 已拉黑 {DEAD_TTL_SEC if ttl is None else ttl}s（到期自动复活）：{str(reason)[:100]}\n")


def _active_model(pool):
    """返回本次请求应使用的模型；如全部拉黑则清空黑名单从头再来（带 TTL 自动复活）。"""
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
            dead_now = _load_dead()
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
                "providers": {"primary": PROVIDER, "extra": sorted(_EXTRA_PROVIDERS.keys())},
                "cn_grade_pool": _CN_SUBPOOL,
                "cn_verify_pool": _TF_SUBPOOL,
                "dead_models": list(dead_now.keys()),
                "dead_details": dead_now,
                "dead_ttl_sec": DEAD_TTL_SEC,
            })
            return
        if self.path.startswith("/api/admin/clear-dead"):
            # 远程清空黑名单（无需连服务器重启）：口令与 /api/grade 一致
            supplied = self.headers.get("X-Access-Token", "")
            if not supplied and "?" in self.path:
                from urllib.parse import parse_qs, urlsplit
                supplied = parse_qs(urlsplit(self.path).query).get("t", [""])[0]
            if ACCESS_TOKEN and supplied != ACCESS_TOKEN:
                self._json(401, {"error": "UNAUTHORIZED", "message": "访问口令错误或缺失"})
                return
            cleared = list(_load_dead().keys())
            _save_dead({})
            self._json(200, {"ok": True, "cleared": cleared,
                             "message": "黑名单已清空，下轮请求重新按池优先级选择模型"})
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
        if not MODEL_POOL:
            self._json(400, {"error": "NO_KEY", "message": "服务器未配置任何模型池，请在 .env 中填写 LLM_MODEL_POOL"})
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
            pool_mode = data.get("poolMode") or "gpt"
        except Exception as e:
            self._json(400, {"error": "BAD_REQUEST", "message": str(e)})
            return

        # 按池顺序调用；429 / 模型未开通即拉黑该模型并自动切下一个，直到成功或全部耗尽。
        pool = _pick_pool(role, pool_mode)
        candidates = [m for m in pool if m not in _load_dead()]
        if not candidates:
            _save_dead({})
            sys.stderr.write("[route] 池内模型全部拉黑，清空黑名单重试一轮\n")
            candidates = list(pool)
        last_error = None
        for entry in candidates:
            real_model, use_key, use_url, use_thinking = _resolve(entry)
            payload = {
                "model": real_model,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": int(_cfg("LLM_MAX_TOKENS", default="8192")),
                "response_format": {"type": "json_object"},
            }
            # 关思考：DeepSeek V4 / 百炼部分模型默认开思考会吃光 max_tokens 导致空返回。
            # kimi 系列 temperature 必须是 0.6（见 _resolve 对应 provider 配置）。
            if use_thinking in ("enabled", "disabled"):
                payload["thinking"] = {"type": use_thinking}
            elif use_thinking == "kimi":
                payload["temperature"] = 0.6
                payload["thinking"] = {"type": "disabled"}
            elif use_thinking == "qwen-no-think":
                payload["enable_thinking"] = False
            req = urllib.request.Request(
                use_url,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {use_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=130, context=_SSL_CTX) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    self._json(200, result)
                    return
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "ignore")[:500]
                last_error = (e.code, detail)
                low = detail.lower()
                quota_gone = any(k in low for k in (
                    "quota", "insufficient", "balance", "exhausted", "expired",
                    "out of credit", "no credit", "额度", "余额", "欠费", "用尽", "已用完"))
                never_on = any(k in low for k in (
                    "not activated", "not enabled", "model not found", "does not exist",
                    "未开通", "未启用", "模型不存在"))
                if e.code == 429 and not quota_gone:
                    # 瞬时并发限流 / RPM 限制：只在本轮跳过，绝不写持久黑名单。
                    # 下一轮请求仍从池首位（tf）开始尝试。
                    sys.stderr.write(f"[route] {entry} 瞬时 429 限流，本轮跳过（不拉黑）\n")
                    continue
                if e.code == 429 or (e.code in (401, 403) and (quota_gone or never_on)):
                    _mark_dead(entry, f"HTTP {e.code}: {detail}")
                    sys.stderr.write(f"[route] {entry} 额度/权限不可用，拉黑 {DEAD_TTL_SEC}s 后自动复活\n")
                    continue
                # 其它上游错误（5xx 等）：同样跳过该模型，不让单次故障拖垮整轮
                sys.stderr.write(f"[route] {entry} 上游 HTTP {e.code}，切下一个模型\n")
                continue
            except Exception as e:
                # 连接级故障（证书链 / DNS / 超时 / 连接重置）同样跳过当前模型，
                # 继续尝试池内下一个；不写持久黑名单，故障恢复后自动回到高优先级。
                last_error = (502, str(e))
                sys.stderr.write(f"[route] {entry} 连接失败，切下一个模型: {e}\n")
                continue
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
