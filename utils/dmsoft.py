"""Optional dmsoft (大漠) window binding."""

import os
import tempfile
from typing import Optional


class DmSoftBinding:
    """Adapter around dmsoft.BindWindowEx; missing plugin is supported."""

    def __init__(self, hwnd: int):
        self.hwnd = int(hwnd)
        self.dm = None
        self.bound = False

    @classmethod
    def try_bind(cls, hwnd: int) -> Optional["DmSoftBinding"]:
        if not hwnd or os.environ.get("SIMPLERPA_DM_BIND", "auto").lower() in {"0", "false", "off", "no"}:
            return None
        binding = cls(hwnd)
        return binding if binding.bind() else None

    def bind(self) -> bool:
        try:
            import win32com.client
            self.dm = win32com.client.Dispatch("dm.dmsoft")
            result = self.dm.BindWindowEx(
                self.hwnd,
                os.environ.get("SIMPLERPA_DM_DISPLAY", "gdi"),
                os.environ.get("SIMPLERPA_DM_MOUSE", "windows3"),
                os.environ.get("SIMPLERPA_DM_KEYPAD", "windows"),
                os.environ.get("SIMPLERPA_DM_PUBLIC", "normal"),
                int(os.environ.get("SIMPLERPA_DM_MODE", "0")),
            )
            self.bound = bool(result)
            if not self.bound:
                self.dm = None
            return self.bound
        except Exception:
            self.dm = None
            self.bound = False
            return False

    def unbind(self) -> None:
        if self.dm is not None and self.bound:
            try:
                self.dm.UnBindWindow()
            except Exception:
                pass
        self.bound = False
        self.dm = None

    def capture(self, width: int, height: int):
        if not self.dm or not self.bound or width <= 0 or height <= 0:
            return None
        path = None
        try:
            from PIL import Image

            fd, path = tempfile.mkstemp(suffix=".bmp")
            os.close(fd)
            if not self.dm.Capture(0, 0, int(width), int(height), path):
                return None
            with Image.open(path) as image:
                return image.convert("RGB").copy()
        except Exception:
            return None
        finally:
            if path:
                try:
                    os.unlink(path)
                except OSError:
                    pass

    def __del__(self):
        self.unbind()
