"""HTTP client for the HereYouGo notification service."""

import os
import urllib.request

try:
    from ._server import HOST, PORT  # generated at build time by setup.py
except ImportError:  # source checkout or editable install
    HOST = PORT = None


def notify(message: str, *, timeout: float = 10) -> None:
    """Send *message* through the HereYouGo server.

    The server address is baked in at build time from ``GC_VM_IP`` and
    ``HEREYOUGOBOT_PORT``; the same environment variables override it at run
    time. When ``NOTIFY_TOKEN`` is set, it is sent as a bearer token.

    Network and HTTP errors from :mod:`urllib` are intentionally propagated.
    """
    host = os.environ.get("GC_VM_IP") or HOST
    port = os.environ.get("HEREYOUGOBOT_PORT") or PORT
    if not host or not port:
        raise RuntimeError(
            "HereYouGo server is not configured: set GC_VM_IP and HEREYOUGOBOT_PORT"
        )

    headers = {"Content-Type": "text/plain; charset=utf-8"}
    token = os.environ.get("NOTIFY_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        f"http://{host}:{port}/notify",
        data=message.encode("utf-8"),
        headers=headers,
        method="POST",
    )
    urllib.request.urlopen(request, timeout=timeout).close()
