# HereYouGo

This is tiny Telegram bot, which resides on VM, listens for incoming messages
(sent by finished jobs), and re-sends them via Telegram.

## Instructions for reporting

On my VM in Google Cloud there is a service listening on the port and redirecting
incoming messages to Telegram. It can be used from Python as following:
- `POST` request to the bot's `/notify` endpoint.
- plain text for simple messages, or JSON with `text`/`message`;

```python
import os
import urllib.request

url = f"http://{os.environ['GC_VM_IP']}:{os.environ['HEREYOUGOBOT_PORT']}/notify"
headers = {"Content-Type": "text/plain"}

request = urllib.request.Request(
    url,
    data=b"Job finished",
    headers=headers,
    method="POST",
)
with urllib.request.urlopen(request, timeout=10) as response:
    response.read()
```
