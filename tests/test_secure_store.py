import os
import tempfile
import unittest
from pathlib import Path

from utils.secure_store import WindowsSecretStore


@unittest.skipUnless(os.name == "nt", "Windows DPAPI test")
class SecureStoreTests(unittest.TestCase):
    def test_dpapi_round_trip_without_plaintext_on_disk(self):
        secret = "agnes-test-secret-DO-NOT-STORE-PLAINTEXT"

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "secrets.json"
            store = WindowsSecretStore(path)

            store.save("agnes_api_key", secret)

            self.assertTrue(path.exists())
            raw = path.read_text(encoding="utf-8")
            self.assertNotIn(secret, raw)
            self.assertEqual(store.load("agnes_api_key"), secret)

            store.delete("agnes_api_key")
            self.assertFalse(path.exists())

    def test_missing_secret_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "secrets.json"
            store = WindowsSecretStore(path)
            self.assertIsNone(store.load("agnes_api_key"))


if __name__ == "__main__":
    unittest.main()
