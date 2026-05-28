import json
import os
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


BOT_KEY = os.environ["HEREYOUGOBOT_KEY"]
CHAT_ID = os.environ["CHAT_ID"]
NOTIFY_TOKEN = os.environ.get("NOTIFY_TOKEN")
PORT = int(os.environ["HEREYOUGOBOT_PORT"])


class Handler(BaseHTTPRequestHandler):
    server_version = "HereYouGo/0.1"

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "ok"})
            return
        self._respond(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/notify":
            self._respond(404, {"error": "not found"})
            return

        if NOTIFY_TOKEN:
            auth = self.headers.get("Authorization", "")
            expected = f"Bearer {NOTIFY_TOKEN}"
            if auth != expected:
                self._respond(401, {"error": "unauthorized"})
                return

        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length)
        text = self._notification_text(raw_body)
        if not text:
            self._respond(400, {"error": "empty notification"})
            return

        try:
            send_telegram_message(text)
        except urllib.error.HTTPError as exc:
            self._respond(exc.code, {"error": exc.reason})
            return
        except urllib.error.URLError as exc:
            self._respond(502, {"error": str(exc.reason)})
            return

        self._respond(202, {"status": "sent"})

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}", flush=True)

    def _notification_text(self, raw_body):
        if not raw_body:
            return ""

        content_type = self.headers.get("Content-Type", "")
        if "application/json" in content_type:
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except json.JSONDecodeError:
                return ""
            if isinstance(payload, dict):
                return str(payload.get("text") or payload.get("message") or "").strip()
            return ""

        return raw_body.decode("utf-8", errors="replace").strip()

    def _respond(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_KEY}/sendMessage"
    data = urllib.parse.urlencode(
        {
            "chat_id": CHAT_ID,
            "text": text,
        }
    ).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(request, timeout=10) as response:
        response.read()


def main():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Listening on :{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
