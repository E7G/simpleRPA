import sys
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from typing import List, Optional, Tuple


user32 = ctypes.windll.user32 if sys.platform == 'win32' else None
GWL_EXSTYLE = -20
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


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

    def move_window_offscreen(self, hwnd: int) -> Optional[dict]:
        if not self._win32_available or not user32:
            return None

        import win32gui
        import win32con

        try:
            if not win32gui.IsWindow(hwnd):
                return None

            rect = win32gui.GetWindowRect(hwnd)
            placement = win32gui.GetWindowPlacement(hwnd)
            width = max(1, rect[2] - rect[0])
            height = max(1, rect[3] - rect[1])

            if win32gui.IsIconic(hwnd):
                # 离屏模式启动时不要把最小化窗口带到前台，否则会在运行开始瞬间抢焦点。
                win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)

            virtual_left = user32.GetSystemMetrics(76)
            virtual_top = user32.GetSystemMetrics(77)
            virtual_width = user32.GetSystemMetrics(78)
            virtual_height = user32.GetSystemMetrics(79)

            offscreen_x = virtual_left + virtual_width + 120
            max_top = virtual_top + max(0, virtual_height - height - 40)
            offscreen_y = min(max(rect[1], virtual_top + 40), max_top)

            win32gui.SetWindowPos(
                hwnd,
                None,
                offscreen_x,
                offscreen_y,
                width,
                height,
                win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE,
            )
            win32gui.UpdateWindow(hwnd)

            return {
                'rect': rect,
                'show_cmd': placement[1],
            }
        except Exception:
            return None

    def set_window_taskbar_visibility(self, hwnd: int, visible: bool) -> Optional[dict]:
        if not self._win32_available or not user32:
            return None

        import win32gui
        import win32con

        try:
            if not win32gui.IsWindow(hwnd):
                return None

            current_exstyle = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            desired_exstyle = current_exstyle
            if visible:
                desired_exstyle |= WS_EX_APPWINDOW
                desired_exstyle &= ~WS_EX_TOOLWINDOW
            else:
                desired_exstyle &= ~WS_EX_APPWINDOW
                desired_exstyle |= WS_EX_TOOLWINDOW

            if desired_exstyle != current_exstyle:
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, desired_exstyle)
                win32gui.SetWindowPos(
                    hwnd,
                    None,
                    0,
                    0,
                    0,
                    0,
                    win32con.SWP_NOMOVE
                    | win32con.SWP_NOSIZE
                    | win32con.SWP_NOZORDER
                    | win32con.SWP_NOACTIVATE
                    | win32con.SWP_FRAMECHANGED,
                )
                win32gui.UpdateWindow(hwnd)

            return {'exstyle': current_exstyle}
        except Exception:
            return None

    def restore_window_taskbar_visibility(self, hwnd: int, state: Optional[dict]) -> bool:
        if not self._win32_available or not user32 or not state:
            return False

        import win32gui
        import win32con

        try:
            if not win32gui.IsWindow(hwnd):
                return False

            original_exstyle = state.get('exstyle')
            if original_exstyle is None:
                return False

            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, int(original_exstyle))
            win32gui.SetWindowPos(
                hwnd,
                None,
                0,
                0,
                0,
                0,
                win32con.SWP_NOMOVE
                | win32con.SWP_NOSIZE
                | win32con.SWP_NOZORDER
                | win32con.SWP_NOACTIVATE
                | win32con.SWP_FRAMECHANGED,
            )
            win32gui.UpdateWindow(hwnd)
            return True
        except Exception:
            return False

    def restore_window_placement(self, hwnd: int, placement_info: Optional[dict]) -> bool:
        if not self._win32_available or not placement_info:
            return False

        import win32gui
        import win32con

        try:
            if not win32gui.IsWindow(hwnd):
                return False

            rect = placement_info.get('rect')
            show_cmd = placement_info.get('show_cmd', win32con.SW_SHOWNORMAL)
            if rect and len(rect) == 4:
                width = max(1, rect[2] - rect[0])
                height = max(1, rect[3] - rect[1])
                win32gui.SetWindowPos(
                    hwnd,
                    None,
                    rect[0],
                    rect[1],
                    width,
                    height,
                    win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE,
                )

            if show_cmd in (win32con.SW_SHOWMINIMIZED, win32con.SW_MINIMIZE, win32con.SW_SHOWMINNOACTIVE):
                win32gui.ShowWindow(hwnd, win32con.SW_SHOWMINNOACTIVE)
            elif show_cmd == win32con.SW_SHOWMAXIMIZED:
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            elif show_cmd == win32con.SW_HIDE:
                win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
            else:
                win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)

            return True
        except Exception:
            return False

    def force_foreground_window(self, hwnd: int) -> bool:
        """强制把窗口带到前台并激活。

        Windows 限制：当调用进程不是前台进程时（例如本程序在托盘后台触发），
        SetForegroundWindow 会被静默拒绝，窗口虽置顶却拿不到真正的前台焦点，
        导致目标窗口首帧不绘制而出现白屏。这里用 AttachThreadInput 把本线程
        临时挂到当前前台线程上，绕过该限制，并辅以 ShowWindow 触发重绘。
        """
        if not self._win32_available:
            return False

        import win32gui
        import win32con
        import win32process

        try:
            if not win32gui.IsWindow(hwnd):
                return False

            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            else:
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

            fg_hwnd = win32gui.GetForegroundWindow()
            if fg_hwnd == hwnd:
                return True

            cur_thread = win32process.GetCurrentThreadId()
            fg_thread = 0
            target_thread = 0
            try:
                if fg_hwnd:
                    fg_thread, _ = win32process.GetWindowThreadProcessId(fg_hwnd)
                target_thread, _ = win32process.GetWindowThreadProcessId(hwnd)
            except Exception:
                fg_thread = target_thread = 0

            attached_fg = attached_target = False
            try:
                if fg_thread and fg_thread != cur_thread:
                    attached_fg = bool(user32.AttachThreadInput(cur_thread, fg_thread, True))
                if target_thread and target_thread != cur_thread and target_thread != fg_thread:
                    attached_target = bool(user32.AttachThreadInput(cur_thread, target_thread, True))

                win32gui.BringWindowToTop(hwnd)
                win32gui.SetForegroundWindow(hwnd)
                win32gui.SetActiveWindow(hwnd)
            finally:
                if attached_fg:
                    user32.AttachThreadInput(cur_thread, fg_thread, False)
                if attached_target:
                    user32.AttachThreadInput(cur_thread, target_thread, False)

            try:
                win32gui.UpdateWindow(hwnd)
            except Exception:
                pass

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
    
    def screen_to_client_coords(self, hwnd: int, screen_x: int, screen_y: int) -> Optional[Tuple[int, int]]:
        """
        将屏幕坐标转换为窗口客户区坐标（使用 Windows API）
        
        这是唯一可靠的坐标转换方法，自动处理：
        - 窗口边框和标题栏
        - DPI 缩放
        - 多显示器设置
        - 不同窗口样式
        
        Args:
            hwnd: 窗口句柄
            screen_x: 屏幕X坐标
            screen_y: 屏幕Y坐标
        
        Returns:
            (client_x, client_y): 窗口客户区坐标
        """
        if not self._win32_available or not user32:
            return None
        
        try:
            point = POINT(screen_x, screen_y)
            if user32.ScreenToClient(hwnd, ctypes.byref(point)):
                return (point.x, point.y)
            return None
        except Exception:
            return None
    
    def client_to_screen_coords(self, hwnd: int, client_x: int, client_y: int) -> Optional[Tuple[int, int]]:
        """
        将窗口客户区坐标转换为屏幕坐标（使用 Windows API）
        
        Args:
            hwnd: 窗口句柄
            client_x: 客户区X坐标
            client_y: 客户区Y坐标
        
        Returns:
            (screen_x, screen_y): 屏幕坐标
        """
        if not self._win32_available or not user32:
            return None
        
        try:
            point = POINT(client_x, client_y)
            if user32.ClientToScreen(hwnd, ctypes.byref(point)):
                return (point.x, point.y)
            return None
        except Exception:
            return None
    
    def get_client_offset(self, hwnd: int) -> Optional[Tuple[int, int]]:
        """
        获取窗口客户区相对于窗口左上角的偏移量
        
        使用 ClientToScreen API 计算偏移量，这是最准确的方法
        
        Returns:
            (offset_x, offset_y): 客户区左上角相对于窗口左上角的偏移
        """
        if not self._win32_available or not user32:
            return None
        
        try:
            import win32gui
            window_rect = win32gui.GetWindowRect(hwnd)
            screen_point = self.client_to_screen_coords(hwnd, 0, 0)
            if screen_point:
                offset_x = screen_point[0] - window_rect[0]
                offset_y = screen_point[1] - window_rect[1]
                return (offset_x, offset_y)
            return None
        except Exception:
            return None
    
    def get_client_rect_screen(self, hwnd: int) -> Optional[Tuple[int, int, int, int]]:
        """
        获取窗口客户区在屏幕坐标系中的矩形
        
        Returns:
            (left, top, right, bottom): 客户区在屏幕坐标系中的矩形
        """
        if not self._win32_available:
            return None
        
        try:
            import win32gui
            client_rect = win32gui.GetClientRect(hwnd)
            top_left = self.client_to_screen_coords(hwnd, client_rect[0], client_rect[1])
            bottom_right = self.client_to_screen_coords(hwnd, client_rect[2], client_rect[3])
            if top_left and bottom_right:
                return (top_left[0], top_left[1], bottom_right[0], bottom_right[1])
            return None
        except Exception:
            return None
    
    def set_window_topmost(self, hwnd: int) -> bool:
        """
        设置窗口始终置顶
        
        Args:
            hwnd: 窗口句柄
        
        Returns:
            bool: 是否成功
        """
        if not self._win32_available:
            return False
        
        import win32gui
        import win32con
        
        try:
            if not win32gui.IsWindow(hwnd):
                return False
            
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_TOPMOST,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW
            )
            
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            win32gui.SetForegroundWindow(hwnd)
            
            return True
        except Exception:
            return False
    
    def remove_window_topmost(self, hwnd: int) -> bool:
        """
        取消窗口始终置顶
        
        Args:
            hwnd: 窗口句柄
        
        Returns:
            bool: 是否成功
        """
        if not self._win32_available:
            return False
        
        import win32gui
        import win32con
        
        try:
            if not win32gui.IsWindow(hwnd):
                return False
            
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_NOTOPMOST,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW
            )
            return True
        except Exception:
            return False
