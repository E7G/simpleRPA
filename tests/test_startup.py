import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from utils.startup import StartupManager


class TestStartupManager(unittest.TestCase):
    def test_source_command_contains_python_and_main(self):
        with patch.object(sys, "executable", os.path.join("C:\\Python", "python.exe")), \
                patch.object(sys, "frozen", False, create=True), \
                patch("utils.startup.os.path.exists", return_value=False):
            command = StartupManager.command()
        self.assertIn("python.exe", command)
        self.assertIn("main.py", command)

    @patch("utils.startup.sys.platform", "win32")
    def test_enable_writes_current_user_run_key(self):
        key = MagicMock()
        key.__enter__.return_value = key
        winreg = MagicMock()
        winreg.HKEY_CURRENT_USER = object()
        winreg.KEY_SET_VALUE = 2
        winreg.REG_SZ = 1
        winreg.CreateKeyEx.return_value = key

        with patch.dict(sys.modules, {"winreg": winreg}), \
                patch.object(StartupManager, "command", return_value='"C:\\SimpleRPA.exe"'):
            self.assertTrue(StartupManager.set_enabled(True))

        winreg.SetValueEx.assert_called_once_with(
            key, StartupManager.APP_NAME, 0, winreg.REG_SZ, '"C:\\SimpleRPA.exe"'
        )

    @patch("utils.startup.sys.platform", "win32")
    def test_disable_is_idempotent(self):
        key = MagicMock()
        key.__enter__.return_value = key
        winreg = MagicMock()
        winreg.HKEY_CURRENT_USER = object()
        winreg.KEY_SET_VALUE = 2
        winreg.CreateKeyEx.return_value = key
        winreg.DeleteValue.side_effect = FileNotFoundError

        with patch.dict(sys.modules, {"winreg": winreg}):
            self.assertTrue(StartupManager.set_enabled(False))


if __name__ == "__main__":
    unittest.main()
