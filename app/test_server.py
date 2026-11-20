import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import server


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.database_patch = patch.object(
            server,
            "REGISTRY_DB",
            str(Path(self.temporary_directory.name, "registry.sqlite3")),
        )
        self.secret_patch = patch.object(server, "REGISTRY_SECRET", "test-secret")
        self.token_patch = patch.object(server, "NOTIFY_TOKEN", None)
        self.database_patch.start()
        self.secret_patch.start()
        self.token_patch.start()
        self.addCleanup(self.database_patch.stop)
        self.addCleanup(self.secret_patch.stop)
        self.addCleanup(self.token_patch.stop)
        server.initialize_database()

    def test_registration_is_bidirectional_and_unique(self):
        self.assertTrue(server.register_user(100, 200, "alice"))
        self.assertEqual(server.resolve_chat_id("alice"), 200)

        with server.database() as connection:
            stored_hash = connection.execute(
                "SELECT user_id_hash FROM registrations WHERE telegram_user_id = 100"
            ).fetchone()["user_id_hash"]
        self.assertEqual(len(stored_hash), 32)
        self.assertNotIn(b"alice", stored_hash)

        self.assertFalse(server.register_user(101, 201, "alice"))
        self.assertEqual(server.resolve_chat_id("alice"), 200)

        self.assertTrue(server.register_user(100, 202, "alice-new"))
        self.assertIsNone(server.resolve_chat_id("alice"))
        self.assertEqual(server.resolve_chat_id("alice-new"), 202)

    def test_notifications_are_persisted(self):
        notification_id = server.enqueue_notification(200, "Job finished")

        notification = server.claim_notification()
        self.assertEqual(notification["id"], notification_id)
        self.assertEqual(notification["chat_id"], 200)
        self.assertEqual(notification["message"], "Job finished")
        self.assertIsNone(server.claim_notification())
        self.assertEqual(
            server.queue_counts(),
            {"pending": 0, "sending": 1, "failed": 0},
        )

    def test_register_command_queues_confirmation(self):
        server.registration_reply(
            {
                "message": {
                    "text": "/register research-job",
                    "chat": {"id": 200, "type": "private"},
                    "from": {"id": 100},
                }
            }
        )

        self.assertEqual(server.resolve_chat_id("research-job"), 200)
        self.assertIn("Registered", server.claim_notification()["message"])

    def test_duplicate_id_queues_rejection(self):
        self.assertTrue(server.register_user(100, 200, "research-job"))
        server.registration_reply(
            {
                "message": {
                    "text": "/register research-job",
                    "chat": {"id": 201, "type": "private"},
                    "from": {"id": 101},
                }
            }
        )

        self.assertEqual(server.resolve_chat_id("research-job"), 200)
        self.assertIn("already taken", server.claim_notification()["message"])

class RequestParsingTests(unittest.TestCase):
    def handler(self, content_type, user_id=None):
        handler = object.__new__(server.Handler)
        handler.headers = {"Content-Type": content_type}
        if user_id is not None:
            handler.headers["X-HereYouGo-User-ID"] = user_id
        return handler

    def test_json_notification(self):
        handler = self.handler("application/json")
        self.assertEqual(
            handler._notification(b'{"user_id":"alice","text":"done"}'),
            ("alice", "done"),
        )

    def test_plain_text_notification(self):
        handler = self.handler("text/plain", "alice")
        self.assertEqual(
            handler._notification(b"done"),
            ("alice", "done"),
        )


if __name__ == "__main__":
    unittest.main()
