"""系统空闲时间检测（Windows）。"""

import sys


def get_idle_seconds() -> float:
    """返回距离上次键鼠输入的空闲秒数。

    仅在 Windows 上有效；其他平台返回 0.0（视为始终活跃，不触发空闲执行）。
    """
    if sys.platform != 'win32':
        return 0.0

    try:
        import ctypes
        from ctypes import Structure, c_uint, sizeof, byref

        class LASTINPUTINFO(Structure):
            _fields_ = [('cbSize', c_uint), ('dwTime', c_uint)]

        lii = LASTINPUTINFO()
        lii.cbSize = sizeof(LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(byref(lii)):
            tick = ctypes.windll.kernel32.GetTickCount()
            millis = tick - lii.dwTime
            if millis < 0:
                return 0.0
            return millis / 1000.0
    except Exception:
        pass
    return 0.0
