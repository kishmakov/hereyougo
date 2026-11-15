# HereYouGo

A tiny, dependency-free client for sending messages directly from your Python
code:

```python
import hereyougo

hereyougo.notify("Training finished")
```

Network and HTTP errors are raised to the caller. The default request timeout is
10 seconds and can be changed with `hereyougo.notify(message, timeout=30)`.

