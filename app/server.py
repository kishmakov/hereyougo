import hashlib
import hmac
import json
import os
import re
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


BOT_KEY = os.environ.get("HEREYOUGO_BOT_KEY", "")
NOTIFY_TOKEN = os.environ.get("NOTIFY_TOKEN")
PORT = int(os.environ.get("HEREYOUGO_BOT_PORT", "8080"))
REGISTRY_DB = os.environ.get("REGISTRY_DB", "/data/registry.sqlite3")
REGISTRY_SECRET = os.environ.get("REGISTRY_SECRET", "")
DELIVERY_RATE = float(os.environ.get("DELIVERY_RATE", "25"))
DELIVERY_WORKERS = int(os.environ.get("DELIVERY_WORKERS", "8"))

USER_ID_PATTERN = r"[A-Za-z0-9][A-Za-z0-9_-]{2,63}"
USER_ID_RE = re.compile(USER_ID_PATTERN)
QUEUE_EVENT = threading.Event()

MSG_ID_DESCRIPTION = (
    "Use 3-64 letters (case-sensitive), numbers, "
    f"underscores, or hyphens (regex: {USER_ID_PATTERN}). Remember it: server will only keep a hash of it."
)
MSG_HELP = "Choose/update your unique ID with /register <id>.\n\n" + MSG_ID_DESCRIPTION
MSG_PRIVATE_CHAT_ONLY = "Registration is only available in a private chat."
MSG_INVALID_ID = (
    "Invalid ID. Use 3-64 characters: letters, numbers, underscores, "
    "or hyphens; the first character must be a letter or number."
)
MSG_REGISTERED = "Registered."
MSG_ID_TAKEN = "That ID is already taken. Please choose another one."


class TelegramError(Exception):
    def __init__(self, description, error_code=None, retry_after=None):
        super().__init__(description)
        self.error_code = error_code
        self.retry_after = retry_after


def database():
    connection = sqlite3.connect(REGISTRY_DB, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def initialize_database():
    Path(REGISTRY_DB).parent.mkdir(parents=True, exist_ok=True)
    with database() as connection:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS registrations (
                telegram_user_id INTEGER PRIMARY KEY,
                telegram_chat_id INTEGER NOT NULL,
                user_id_hash BLOB NOT NULL UNIQUE,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                available_at REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'sending', 'failed')),
                last_error TEXT,
                created_at REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS notifications_pending
            ON notifications(status, available_at, id);
            """
        )
        connection.execute(
            "UPDATE notifications SET status = 'pending' WHERE status = 'sending'"
        )


def user_id_hash(user_id):
    return hmac.new(
        REGISTRY_SECRET.encode("utf-8"),
        user_id.encode("utf-8"),
        hashlib.sha256,
    ).digest()


def register_user(telegram_user_id, telegram_chat_id, user_id):
    """Register or rename a user. Return False when the ID belongs to another user."""
    now = time.time()
    try:
        with database() as connection:
            connection.execute(
                """
                INSERT INTO registrations (
                    telegram_user_id, telegram_chat_id, user_id_hash,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(telegram_user_id) DO UPDATE SET
                    telegram_chat_id = excluded.telegram_chat_id,
                    user_id_hash = excluded.user_id_hash,
                    updated_at = excluded.updated_at
                """,
                (
                    telegram_user_id,
                    telegram_chat_id,
                    user_id_hash(user_id),
                    now,
                    now,
                ),
            )
    except sqlite3.IntegrityError:
        return False
    return True


def resolve_chat_id(user_id):
    with database() as connection:
        row = connection.execute(
            "SELECT telegram_chat_id FROM registrations WHERE user_id_hash = ?",
            (user_id_hash(user_id),),
        ).fetchone()
    return None if row is None else row["telegram_chat_id"]


def enqueue_notification(chat_id, message):
    now = time.time()
    with database() as connection:
        cursor = connection.execute(
            """
            INSERT INTO notifications (chat_id, message, available_at, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (chat_id, message, now, now),
        )
        notification_id = cursor.lastrowid
    QUEUE_EVENT.set()
    return notification_id


def queue_counts():
    with database() as connection:
        rows = connection.execute(
            "SELECT status, count(*) AS count FROM notifications GROUP BY status"
        ).fetchall()
    counts = {"pending": 0, "sending": 0, "failed": 0}
    counts.update({row["status"]: row["count"] for row in rows})
    return counts


def telegram_api(method, parameters, timeout=10):
    url = f"https://api.telegram.org/bot{BOT_KEY}/{method}"
    data = urllib.parse.urlencode(parameters).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise TelegramError(str(exc.reason), exc.code) from exc
        response_parameters = payload.get("parameters") or {}
        raise TelegramError(
            payload.get("description", str(exc.reason)),
            payload.get("error_code", exc.code),
            response_parameters.get("retry_after"),
        ) from exc

    if not payload.get("ok"):
        response_parameters = payload.get("parameters") or {}
        raise TelegramError(
            payload.get("description", "Telegram API request failed"),
            payload.get("error_code"),
            response_parameters.get("retry_after"),
        )
    return payload.get("result")


def send_telegram_message(chat_id, text):
    telegram_api("sendMessage", {"chat_id": chat_id, "text": text})


def claim_notification():
    with database() as connection:
        connection.execute("BEGIN IMMEDIATE")
        notification = connection.execute(
            """
            SELECT id, chat_id, message, attempts
            FROM notifications
            WHERE status = 'pending' AND available_at <= ?
            ORDER BY id
            LIMIT 1
            """,
            (time.time(),),
        ).fetchone()
        if notification is not None:
            connection.execute(
                "UPDATE notifications SET status = 'sending' WHERE id = ?",
                (notification["id"],),
            )
        return notification


def retry_notification(notification_id, attempts, error, delay):
    with database() as connection:
        connection.execute(
            """
            UPDATE notifications
            SET attempts = ?, available_at = ?, status = 'pending', last_error = ?
            WHERE id = ?
            """,
            (attempts, time.time() + delay, str(error)[:500], notification_id),
        )


def fail_notification(notification_id, attempts, error):
    with database() as connection:
        connection.execute(
            """
            UPDATE notifications
            SET attempts = ?, status = 'failed', last_error = ?
            WHERE id = ?
            """,
            (attempts, str(error)[:500], notification_id),
        )


def delete_notification(notification_id):
    with database() as connection:
        connection.execute("DELETE FROM notifications WHERE id = ?", (notification_id,))


class DeliveryLimiter:
    def __init__(self, rate):
        self.minimum_interval = 1.0 / rate
        self.next_delivery = 0.0
        self.next_chat_delivery = {}
        self.lock = threading.Lock()

    def wait(self, chat_id):
        with self.lock:
            now = time.monotonic()
            send_at = max(
                now,
                self.next_delivery,
                self.next_chat_delivery.get(chat_id, 0.0),
            )
            self.next_delivery = send_at + self.minimum_interval
            self.next_chat_delivery[chat_id] = send_at + 1.0
            if len(self.next_chat_delivery) > 10_000:
                cutoff = now - 1.0
                self.next_chat_delivery = {
                    key: value
                    for key, value in self.next_chat_delivery.items()
                    if value >= cutoff
                }
        delay = send_at - now
        if delay:
            time.sleep(delay)

    def pause(self, delay):
        with self.lock:
            self.next_delivery = max(
                self.next_delivery,
                time.monotonic() + delay,
            )


DELIVERY_LIMITER = DeliveryLimiter(DELIVERY_RATE)


def delivery_loop():

    while True:
        try:
            notification = claim_notification()
        except sqlite3.Error as exc:
            print(f"Queue read failed: {exc}", flush=True)
            time.sleep(1)
            continue
        if notification is None:
            QUEUE_EVENT.clear()
            QUEUE_EVENT.wait(timeout=0.5)
            continue

        DELIVERY_LIMITER.wait(notification["chat_id"])

        attempts = notification["attempts"] + 1
        try:
            send_telegram_message(notification["chat_id"], notification["message"])
        except TelegramError as exc:
            if exc.error_code in (400, 403, 404):
                fail_notification(notification["id"], attempts, exc)
            else:
                delay = exc.retry_after or min(300, 2 ** min(attempts, 8))
                if exc.retry_after:
                    DELIVERY_LIMITER.pause(exc.retry_after)
                retry_notification(notification["id"], attempts, exc, delay)
            print(f"Telegram delivery failed: {exc}", flush=True)
        except (urllib.error.URLError, TimeoutError) as exc:
            delay = min(300, 2 ** min(attempts, 8))
            retry_notification(notification["id"], attempts, exc, delay)
            print(f"Telegram delivery failed: {exc}", flush=True)
        except Exception as exc:
            delay = min(300, 2 ** min(attempts, 8))
            retry_notification(notification["id"], attempts, exc, delay)
            print(f"Unexpected delivery failure: {exc}", flush=True)
        else:
            delete_notification(notification["id"])


def registration_reply(update):
    message = update.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("text"), str):
        return

    chat = message.get("chat") or {}
    sender = message.get("from") or {}
    chat_id = chat.get("id")
    telegram_user_id = sender.get("id")
    if chat_id is None or telegram_user_id is None:
        return

    if chat.get("type") != "private":
        enqueue_notification(chat_id, MSG_PRIVATE_CHAT_ONLY)
        return

    text = message["text"].strip()
    command, separator, argument = text.partition(" ")
    command = command.split("@", 1)[0].lower()
    user_id = argument.strip() if separator else ""

    if command == "/register":
        if not USER_ID_RE.fullmatch(user_id):
            reply = MSG_INVALID_ID
        elif register_user(telegram_user_id, chat_id, user_id):
            reply = MSG_REGISTERED.format(user_id=user_id)
        else:
            reply = MSG_ID_TAKEN
    else: # "/start", "/help"
        reply = MSG_HELP

    enqueue_notification(chat_id, reply)


def bot_polling_loop():
    offset = None
    while True:
        parameters = {
            "timeout": 30,
            "allowed_updates": json.dumps(["message"]),
        }
        if offset is not None:
            parameters["offset"] = offset
        try:
            updates = telegram_api("getUpdates", parameters, timeout=35)
            for update in updates:
                registration_reply(update)
                offset = update["update_id"] + 1
        except (TelegramError, urllib.error.URLError, TimeoutError) as exc:
            print(f"Telegram polling failed: {exc}", flush=True)
            time.sleep(2)
        except Exception as exc:
            print(f"Unexpected polling failure: {exc}", flush=True)
            time.sleep(2)


class Handler(BaseHTTPRequestHandler):
    server_version = "HereYouGo/0.2"

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "ok", "notifications": queue_counts()})
            return
        self._respond(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/notify":
            self._respond(404, {"error": "not found"})
            return

        if NOTIFY_TOKEN:
            auth = self.headers.get("Authorization", "")
            expected = f"Bearer {NOTIFY_TOKEN}"
            if not hmac.compare_digest(auth, expected):
                self._respond(401, {"error": "unauthorized"})
                return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._respond(400, {"error": "invalid content length"})
            return
        if length < 0:
            self._respond(400, {"error": "invalid content length"})
            return
        if length > 64 * 1024:
            self._respond(413, {"error": "request too large"})
            return

        raw_body = self.rfile.read(length)
        user_id, text = self._notification(raw_body)
        if not user_id or not USER_ID_RE.fullmatch(user_id):
            self._respond(400, {"error": "invalid or missing user_id"})
            return
        if not text:
            self._respond(400, {"error": "empty notification"})
            return
        if len(text) > 4096:
            self._respond(400, {"error": "notification exceeds 4096 characters"})
            return

        try:
            chat_id = resolve_chat_id(user_id)
        except sqlite3.Error as exc:
            print(f"Registry lookup failed: {exc}", flush=True)
            self._respond(503, {"error": "registry unavailable"})
            return
        if chat_id is None:
            self._respond(404, {"error": "unknown user_id"})
            return

        try:
            notification_id = enqueue_notification(chat_id, text)
        except sqlite3.Error as exc:
            print(f"Queue write failed: {exc}", flush=True)
            self._respond(503, {"error": "queue unavailable"})
            return
        self._respond(
            202,
            {"status": "queued", "notification_id": notification_id},
        )

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}", flush=True)

    def _notification(self, raw_body):
        if not raw_body:
            return "", ""

        content_type = self.headers.get("Content-Type", "")
        if "application/json" in content_type:
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return "", ""
            if not isinstance(payload, dict):
                return "", ""
            user_id = str(payload.get("user_id") or "").strip()
            text = str(payload.get("text") or payload.get("message") or "").strip()
            return user_id, text

        user_id = self.headers.get("X-HereYouGo-User-ID", "").strip()
        text = raw_body.decode("utf-8", errors="replace").strip()
        return user_id, text

    def _respond(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    if not BOT_KEY:
        raise RuntimeError("HEREYOUGO_BOT_KEY is not set")
    if not REGISTRY_SECRET:
        raise RuntimeError("REGISTRY_SECRET is not set")
    if DELIVERY_RATE <= 0 or DELIVERY_RATE > 30:
        raise RuntimeError("DELIVERY_RATE must be greater than 0 and at most 30")
    if DELIVERY_WORKERS <= 0 or DELIVERY_WORKERS > 32:
        raise RuntimeError("DELIVERY_WORKERS must be between 1 and 32")

    initialize_database()
    for worker_id in range(DELIVERY_WORKERS):
        threading.Thread(
            target=delivery_loop,
            name=f"delivery-{worker_id}",
            daemon=True,
        ).start()
    threading.Thread(target=bot_polling_loop, name="bot-polling", daemon=True).start()

    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Listening on :{PORT}; database: {REGISTRY_DB}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
