"""Windows per-user startup registration."""

import os
import subprocess
import sys
from typing import Optional


class StartupManager:
    APP_NAME = "SimpleRPA"
    RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

    @classmethod
    def command(cls) -> str:
        if getattr(sys, "frozen", False):
            args = [os.path.abspath(sys.executable)]
        else:
            root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            executable = os.path.abspath(sys.executable)
            if executable.lower().endswith("python.exe"):
                pythonw = executable[:-10] + "pythonw.exe"
                if os.path.exists(pythonw):
                    executable = pythonw
            args = [executable, os.path.join(root, "main.py")]
        return subprocess.list2cmdline(args)

    @classmethod
    def is_enabled(cls) -> bool:
        if sys.platform != "win32":
            return False
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.RUN_KEY) as key:
                winreg.QueryValueEx(key, cls.APP_NAME)
            return True
        except (FileNotFoundError, OSError):
            return False

    @classmethod
    def set_enabled(cls, enabled: bool) -> bool:
        if sys.platform != "win32":
            return False
        try:
            import winreg

            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER, cls.RUN_KEY, 0, winreg.KEY_SET_VALUE
            ) as key:
                if enabled:
                    winreg.SetValueEx(key, cls.APP_NAME, 0, winreg.REG_SZ, cls.command())
                else:
                    try:
                        winreg.DeleteValue(key, cls.APP_NAME)
                    except FileNotFoundError:
                        pass
            return True
        except OSError:
            return False
