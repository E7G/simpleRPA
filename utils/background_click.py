"""
后台点击工具 - 支持后台模式和普通模式一键切换
基于 SendNotifyMessage 实现后台点击，适用于 Chrome 渲染的小程序窗口
"""
import sys
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from typing import Optional, Tuple, List

user32 = ctypes.windll.user32

WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MOUSEMOVE = 0x0200
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
MK_LBUTTON = 0x0001
MK_RBUTTON = 0x0002
MK_MBUTTON = 0x0010


@dataclass
class BackgroundClickResult:
    success: bool
    message: str = ""
    used_background: bool = False


class BackgroundClicker:
    """后台点击器 - 支持后台模式和普通模式"""
    
    def __init__(self, window_title: str = None, hwnd: int = None):
        self._main_hwnd: Optional[int] = None
        self._render_hwnd: Optional[int] = None
        self._title: str = ""
        self._win32_available = self._check_win32()
        
        if hwnd:
            self.attach_by_hwnd(hwnd)
        elif window_title:
            self.attach(window_title)
    
    def _check_win32(self) -> bool:
        if sys.platform != 'win32':
            return False
        try:
            import win32gui
            return True
        except ImportError:
            return False
    
    @property
    def is_available(self) -> bool:
        return self._win32_available and self._main_hwnd is not None
    
    @property
    def hwnd(self) -> int:
        return self._main_hwnd
    
    @property
    def render_hwnd(self) -> int:
        return self._render_hwnd or self._main_hwnd
    
    @property
    def title(self) -> str:
        return self._title
    
    @property
    def rect(self) -> Tuple[int, int, int, int]:
        if not self._win32_available or not self._main_hwnd:
            return (0, 0, 0, 0)
        import win32gui
        return win32gui.GetWindowRect(self._main_hwnd)
    
    def attach(self, title_keyword: str) -> bool:
        """通过窗口标题关键字附加到窗口"""
        if not self._win32_available:
            return False
        
        import win32gui
        
        result = []
        def enum_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title_keyword.lower() in title.lower():
                    result.append((hwnd, title))
            return True
        win32gui.EnumWindows(enum_callback, None)
        
        if not result:
            return False
        
        self._main_hwnd, self._title = result[0]
        self._find_render_window()
        return True
    
    def attach_by_hwnd(self, hwnd: int) -> bool:
        """通过窗口句柄附加"""
        if not self._win32_available:
            return False
        
        import win32gui
        
        if not win32gui.IsWindow(hwnd):
            return False
        
        self._main_hwnd = hwnd
        self._title = win32gui.GetWindowText(hwnd)
        self._find_render_window()
        return True
    
    def _find_render_window(self):
        """查找 Chrome 渲染子窗口"""
        if not self._win32_available:
            return
        
        import win32gui
        
        self._render_hwnd = None
        
        children = []
        def enum_child(child_hwnd, _):
            try:
                class_name = win32gui.GetClassName(child_hwnd)
                children.append((child_hwnd, class_name))
            except Exception:
                pass
            return True
        win32gui.EnumChildWindows(self._main_hwnd, enum_child, None)
        
        for child_hwnd, class_name in children:
            if 'Chrome_RenderWidgetHostHWND' in class_name:
                self._render_hwnd = child_hwnd
                return
    
    def click(self, x: int, y: int, button: str = 'left', background: bool = True) -> BackgroundClickResult:
        """
        点击窗口内指定位置
        
        Args:
            x: 窗口内相对X坐标
            y: 窗口内相对Y坐标
            button: 'left', 'right' 或 'middle'
            background: 是否使用后台模式
        
        Returns:
            BackgroundClickResult: 点击结果
        """
        if not self._main_hwnd:
            return BackgroundClickResult(False, "未附加到窗口", False)
        
        if background:
            return self._background_click(x, y, button)
        else:
            return self._foreground_click(x, y, button)
    
    def _background_click(self, x: int, y: int, button: str) -> BackgroundClickResult:
        """后台模式点击"""
        target_hwnd = self._render_hwnd or self._main_hwnd
        lParam = self._make_lparam(x, y)
        
        try:
            if button == 'right':
                user32.SendNotifyMessageW(target_hwnd, WM_MOUSEMOVE, 0, lParam)
                user32.SendNotifyMessageW(target_hwnd, WM_RBUTTONDOWN, MK_RBUTTON, lParam)
                user32.SendNotifyMessageW(target_hwnd, WM_RBUTTONUP, 0, lParam)
            elif button == 'middle':
                user32.SendNotifyMessageW(target_hwnd, WM_MOUSEMOVE, 0, lParam)
                user32.SendNotifyMessageW(target_hwnd, WM_MBUTTONDOWN, MK_MBUTTON, lParam)
                user32.SendNotifyMessageW(target_hwnd, WM_MBUTTONUP, 0, lParam)
            else:
                user32.SendNotifyMessageW(target_hwnd, WM_MOUSEMOVE, 0, lParam)
                user32.SendNotifyMessageW(target_hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lParam)
                user32.SendNotifyMessageW(target_hwnd, WM_LBUTTONUP, 0, lParam)
            
            return BackgroundClickResult(True, "后台点击成功", True)
        except Exception as e:
            return BackgroundClickResult(False, f"后台点击失败: {str(e)}", True)
    
    def _foreground_click(self, x: int, y: int, button: str) -> BackgroundClickResult:
        """普通模式点击（前台）"""
        try:
            import pyautogui
            
            rect = self.rect
            screen_x = rect[0] + x
            screen_y = rect[1] + y
            
            if button == 'right':
                pyautogui.rightClick(x=screen_x, y=screen_y)
            elif button == 'middle':
                pyautogui.click(x=screen_x, y=screen_y, button='middle')
            else:
                pyautogui.click(x=screen_x, y=screen_y)
            
            return BackgroundClickResult(True, "前台点击成功", False)
        except Exception as e:
            return BackgroundClickResult(False, f"前台点击失败: {str(e)}", False)
    
    def double_click(self, x: int, y: int, background: bool = True) -> BackgroundClickResult:
        """双击"""
        import time
        
        result = self.click(x, y, 'left', background)
        if not result.success:
            return result
        
        time.sleep(0.1)
        return self.click(x, y, 'left', background)
    
    def move(self, x: int, y: int, background: bool = True) -> BackgroundClickResult:
        """移动鼠标"""
        if not self._main_hwnd:
            return BackgroundClickResult(False, "未附加到窗口", False)
        
        if background:
            target_hwnd = self._render_hwnd or self._main_hwnd
            lParam = self._make_lparam(x, y)
            try:
                user32.SendNotifyMessageW(target_hwnd, WM_MOUSEMOVE, 0, lParam)
                return BackgroundClickResult(True, "后台移动成功", True)
            except Exception as e:
                return BackgroundClickResult(False, f"后台移动失败: {str(e)}", True)
        else:
            try:
                import pyautogui
                rect = self.rect
                screen_x = rect[0] + x
                screen_y = rect[1] + y
                pyautogui.moveTo(x=screen_x, y=screen_y)
                return BackgroundClickResult(True, "前台移动成功", False)
            except Exception as e:
                return BackgroundClickResult(False, f"前台移动失败: {str(e)}", False)
    
    def scroll(self, x: int, y: int, clicks: int, background: bool = True) -> BackgroundClickResult:
        """滚动鼠标滚轮"""
        if not self._main_hwnd:
            return BackgroundClickResult(False, "未附加到窗口", False)
        
        if background:
            return BackgroundClickResult(False, "后台模式暂不支持滚轮操作", True)
        else:
            try:
                import pyautogui
                rect = self.rect
                screen_x = rect[0] + x
                screen_y = rect[1] + y
                pyautogui.scroll(clicks, x=screen_x, y=screen_y)
                return BackgroundClickResult(True, "前台滚动成功", False)
            except Exception as e:
                return BackgroundClickResult(False, f"前台滚动失败: {str(e)}", False)
    
    @staticmethod
    def _make_lparam(x: int, y: int):
        """创建 lParam 参数"""
        return wintypes.LPARAM((y << 16) | (x & 0xFFFF))
    
    def __repr__(self):
        hwnd_hex = self._main_hwnd if self._main_hwnd else 0
        render_hex = self._render_hwnd if self._render_hwnd else 0
        return f"BackgroundClicker(hwnd={hwnd_hex:08X}, render={render_hex:08X}, title='{self._title}')"


def create_background_clicker(window_title: str = None, hwnd: int = None) -> Optional[BackgroundClicker]:
    """创建后台点击器的便捷函数"""
    clicker = BackgroundClicker(window_title=window_title, hwnd=hwnd)
    if clicker.is_available:
        return clicker
    return None


def background_click(window_title: str, x: int, y: int, button: str = 'left', background: bool = True) -> BackgroundClickResult:
    """
    便捷函数：点击指定窗口
    
    Args:
        window_title: 窗口标题关键字
        x: 窗口内相对X坐标
        y: 窗口内相对Y坐标
        button: 'left', 'right' 或 'middle'
        background: 是否使用后台模式
    
    Returns:
        BackgroundClickResult: 点击结果
    """
    clicker = BackgroundClicker(window_title)
    if not clicker.is_available:
        return BackgroundClickResult(False, f"未找到窗口: {window_title}", False)
    return clicker.click(x, y, button, background)


if __name__ == "__main__":
    import time
    
    print("=" * 50)
    print("后台点击工具测试")
    print("=" * 50)
    
    clicker = BackgroundClicker("记事本")
    
    if clicker.is_available:
        print(f"已附加: {clicker}")
        print(f"窗口位置: {clicker.rect}")
        
        print("\n3秒后点击 (100, 100)...")
        time.sleep(3)
        result = clicker.click(100, 100, background=True)
        print(f"结果: {result}")
    else:
        print("未找到窗口，请打开一个记事本窗口")
