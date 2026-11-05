import json, os, re
from collections import Counter
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
import paywall

PRICE = 0.01
STOP = set("the a an and or but of to in on for with is are was were be it this that as at by from i you he she we they not".split())

def analyze(text):
    words = re.findall(r"[A-Za-z0-9']+", text)
    sents = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    syll = sum(max(1, len(re.findall(r"[aeiouy]+", w.lower()))) for w in words)
    nw, ns = len(words), max(1, len(sents))
    fk = round(0.39 * nw / ns + 11.8 * syll / max(1, nw) - 15.59, 2) if nw else 0
    kw = Counter(w.lower() for w in words if w.lower() not in STOP and len(w) > 2).most_common(5)
    slug = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", " ".join(w.lower() for w in words[:8]))).strip("-")
    return {"words": nw, "characters": len(text), "sentences": len(sents),
            "reading_time_minutes": round(nw / 238, 2), "flesch_kincaid_grade": fk,
            "top_keywords": kw, "slug": slug,
            "summary_snippet": text.strip()[:155],
            "ai_disclosure": "Computed by software built and run by an AI automaton (earn-or-die)."}

class H(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if urlparse(self.path).path == "/stats":
            b = paywall.stats_json()
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
            return
        if urlparse(self.path).path == "/":
            return self._send(200, {"service": "textstats", "usage": "POST /analyze with JSON {\"text\": ...}; $0.01 USDC on Base per call, send X-Payment-Tx header", "ai_disclosure": "Built by an AI automaton."})
        self._send(404, {"error": "not found"})
    def do_POST(self):
        if urlparse(self.path).path != "/analyze":
            return self._send(404, {"error": "not found"})
        ok, code, body = paywall.check({k: v for k, v in self.headers.items()}, PRICE, "text analysis")
        if not ok:
            return self._send(code, body)
        n = int(self.headers.get("Content-Length", 0))
        if n > 200000: return self._send(413, {"error": "too large"})
        try: text = json.loads(self.rfile.read(n))["text"]
        except Exception: return self._send(400, {"error": "need JSON {\"text\": str}"})
        self._send(200, analyze(str(text)))
    def log_message(self, *a): pass

if __name__ == "__main__":
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 8000))), H).serve_forever()
