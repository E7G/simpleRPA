import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class WindowInfo:
    hwnd: int
    title: str
    rect: Tuple[int, int, int, int]
    width: int
    height: int
    x: int
    y: int
    
    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)


class WindowUtils:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._win32_available = self._check_win32()
    
    def _check_win32(self) -> bool:
        if sys.platform != 'win32':
            return False
        try:
            import win32gui
            import win32con
            return True
        except ImportError:
            return False
    
    def is_win32_available(self) -> bool:
        return self._win32_available
    
    def get_all_windows(self) -> List[WindowInfo]:
        if not self._win32_available:
            return []
        
        import win32gui
        
        windows = []
        
        def enum_windows_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    rect = win32gui.GetWindowRect(hwnd)
                    x, y, right, bottom = rect
                    width = right - x
                    height = bottom - y
                    windows.append(WindowInfo(
                        hwnd=hwnd,
                        title=title,
                        rect=rect,
                        width=width,
                        height=height,
                        x=x,
                        y=y
                    ))
            return True
        
        win32gui.EnumWindows(enum_windows_callback, None)
        return windows
    
    def get_window_by_title(self, title: str) -> Optional[WindowInfo]:
        windows = self.get_all_windows()
        for window in windows:
            if title.lower() in window.title.lower():
                return window
        return None
    
    def get_window_by_hwnd(self, hwnd: int) -> Optional[WindowInfo]:
        if not self._win32_available:
            return None
        
        import win32gui
        
        try:
            if not win32gui.IsWindow(hwnd):
                return None
            
            title = win32gui.GetWindowText(hwnd)
            rect = win32gui.GetWindowRect(hwnd)
            x, y, right, bottom = rect
            width = right - x
            height = bottom - y
            
            return WindowInfo(
                hwnd=hwnd,
                title=title,
                rect=rect,
                width=width,
                height=height,
                x=x,
                y=y
            )
        except Exception:
            return None
    
    def get_foreground_window(self) -> Optional[WindowInfo]:
        if not self._win32_available:
            return None
        
        import win32gui
        
        try:
            hwnd = win32gui.GetForegroundWindow()
            return self.get_window_by_hwnd(hwnd)
        except Exception:
            return None
    
    def activate_window(self, hwnd: int) -> bool:
        if not self._win32_available:
            return False
        
        import win32gui
        import win32con
        
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            return True
        except Exception:
            return False
    
    def get_window_at_point(self, x: int, y: int) -> Optional[WindowInfo]:
        if not self._win32_available:
            return None
        
        import win32gui
        
        try:
            hwnd = win32gui.WindowFromPoint((x, y))
            while hwnd:
                parent = win32gui.GetParent(hwnd)
                if parent == 0:
                    break
                hwnd = parent
            return self.get_window_by_hwnd(hwnd)
        except Exception:
            return None
    
    def screen_to_window_coords(self, screen_x: int, screen_y: int, window_info: WindowInfo) -> Tuple[int, int]:
        return (screen_x - window_info.x, screen_y - window_info.y)
    
    def window_to_screen_coords(self, window_x: int, window_y: int, window_info: WindowInfo) -> Tuple[int, int]:
        return (window_x + window_info.x, window_y + window_info.y)
    
    def get_client_rect(self, hwnd: int) -> Optional[Tuple[int, int, int, int]]:
        if not self._win32_available:
            return None
        
        import win32gui
        
        try:
            return win32gui.GetClientRect(hwnd)
        except Exception:
            return None
    
    def get_window_rect(self, hwnd: int) -> Optional[Tuple[int, int, int, int]]:
        if not self._win32_available:
            return None
        
        import win32gui
        
        try:
            return win32gui.GetWindowRect(hwnd)
        except Exception:
            return None
