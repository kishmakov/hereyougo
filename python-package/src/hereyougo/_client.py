"""HTTP client for the HereYouGo notification service."""

import json
import os
from typing import Optional
import urllib.request

try:
    from ._server import HOST, PORT  # generated at build time by setup.py
except ImportError:  # source checkout or editable install
    HOST = PORT = None


def notify(message: str, *, user_id: Optional[str] = None, timeout: float = 10) -> None:
    """Send *message* through the HereYouGo server.

    The server address is baked in at build time from ``HEREYOUGO_VM_IP`` and
    ``HEREYOUGO_BOT_PORT``; the same environment variables override it at run
    time. The recipient ID can be passed explicitly or read from
    ``HEREYOUGO_USER_ID``. When ``NOTIFY_TOKEN`` is set, it is sent as a
    bearer token.

    Network and HTTP errors from :mod:`urllib` are intentionally propagated.
    """
    host = os.environ.get("HEREYOUGO_VM_IP") or HOST
    port = os.environ.get("HEREYOUGO_BOT_PORT") or PORT
    if not host or not port:
        raise RuntimeError(
            "HereYouGo server is not configured: set HEREYOUGO_VM_IP and "
            "HEREYOUGO_BOT_PORT"
        )

    user_id = user_id or os.environ.get("HEREYOUGO_USER_ID")
    if not user_id:
        raise RuntimeError(
            "HereYouGo recipient is not configured: pass user_id or set "
            "HEREYOUGO_USER_ID"
        )

    headers = {"Content-Type": "application/json"}
    token = os.environ.get("NOTIFY_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        f"http://{host}:{port}/notify",
        data=json.dumps({"user_id": user_id, "text": message}).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    urllib.request.urlopen(request, timeout=timeout).close()
