import os
import unittest
from unittest.mock import patch

import hereyougo


class NotifyTests(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    @patch("hereyougo._client.PORT", 8080)
    @patch("hereyougo._client.HOST", "192.0.2.1")
    @patch("urllib.request.urlopen")
    def test_notify_posts_json_to_baked_server(self, urlopen):
        result = hereyougo.notify("Val accuracy = 0.95", user_id="alice")

        self.assertIsNone(result)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://192.0.2.1:8080/notify")
        self.assertEqual(request.method, "POST")
        self.assertEqual(
            request.data,
            b'{"user_id": "alice", "text": "Val accuracy = 0.95"}',
        )
        self.assertEqual(request.get_header("Content-type"), "application/json")
        self.assertIsNone(request.get_header("Authorization"))
        self.assertEqual(urlopen.call_args.kwargs, {"timeout": 10})
        urlopen.return_value.close.assert_called_once_with()

    @patch.dict(
        os.environ,
        {
            "HEREYOUGO_VM_IP": "example.test",
            "HEREYOUGO_BOT_PORT": "9000",
            "NOTIFY_TOKEN": "secret",
            "HEREYOUGO_USER_ID": "bob",
        },
        clear=True,
    )
    @patch("hereyougo._client.HOST", "192.0.2.1")
    @patch("urllib.request.urlopen")
    def test_environment_overrides_server_and_sends_token(self, urlopen):
        hereyougo.notify("done", timeout=2.5)

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://example.test:9000/notify")
        self.assertEqual(request.get_header("Authorization"), "Bearer secret")
        self.assertEqual(request.data, b'{"user_id": "bob", "text": "done"}')
        self.assertEqual(urlopen.call_args.kwargs, {"timeout": 2.5})

    @patch.dict(os.environ, {}, clear=True)
    @patch("hereyougo._client.HOST", None)
    @patch("hereyougo._client.PORT", None)
    def test_notify_reports_missing_configuration(self):
        with self.assertRaisesRegex(RuntimeError, "HEREYOUGO_VM_IP"):
            hereyougo.notify("done", user_id="alice")

    @patch.dict(os.environ, {}, clear=True)
    @patch("hereyougo._client.PORT", 8080)
    @patch("hereyougo._client.HOST", "192.0.2.1")
    def test_notify_reports_missing_recipient(self):
        with self.assertRaisesRegex(RuntimeError, "user_id"):
            hereyougo.notify("done")


if __name__ == "__main__":
    unittest.main()
