"""
后台点击工具 - 基于 SendNotifyMessage
适用于 Chrome 渲染的小程序窗口
"""
import ctypes
from ctypes import wintypes
import win32gui
from typing import Optional, Tuple

user32 = ctypes.windll.user32

WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MOUSEMOVE = 0x0200
MK_LBUTTON = 0x0001
MK_RBUTTON = 0x0002


class BackgroundClicker:
    """后台点击器 - 支持向 Chrome 渲染窗口发送点击"""
    
    def __init__(self, window_title: str = None, hwnd: int = None):
        self._main_hwnd: Optional[int] = None
        self._render_hwnd: Optional[int] = None
        self._title: str = ""
        
        if hwnd:
            self.attach_by_hwnd(hwnd)
        elif window_title:
            self.attach(window_title)
    
    def attach(self, title_keyword: str) -> bool:
        """通过窗口标题关键字附加到窗口"""
        result = []
        def enum_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title_keyword in title:
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
        if not win32gui.IsWindow(hwnd):
            return False
        
        self._main_hwnd = hwnd
        self._title = win32gui.GetWindowText(hwnd)
        self._find_render_window()
        return True
    
    def _find_render_window(self):
        """查找 Chrome 渲染子窗口"""
        self._render_hwnd = None
        
        children = []
        def enum_child(child_hwnd, _):
            class_name = win32gui.GetClassName(child_hwnd)
            children.append((child_hwnd, class_name))
            return True
        win32gui.EnumChildWindows(self._main_hwnd, enum_child, None)
        
        for child_hwnd, class_name in children:
            if 'Chrome_RenderWidgetHostHWND' in class_name:
                self._render_hwnd = child_hwnd
                return
    
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
        return win32gui.GetWindowRect(self._main_hwnd)
    
    def click(self, x: int, y: int, button: str = 'left') -> bool:
        """
        后台点击
        
        Args:
            x: 窗口内相对X坐标
            y: 窗口内相对Y坐标
            button: 'left' 或 'right'
        
        Returns:
            是否成功发送
        """
        if not self._main_hwnd:
            return False
        
        target_hwnd = self._render_hwnd or self._main_hwnd
        lParam = (y << 16) | (x & 0xFFFF)
        
        if button == 'right':
            user32.SendNotifyMessageW(target_hwnd, WM_MOUSEMOVE, 0, lParam)
            user32.SendNotifyMessageW(target_hwnd, WM_RBUTTONDOWN, MK_RBUTTON, lParam)
            user32.SendNotifyMessageW(target_hwnd, WM_RBUTTONUP, 0, lParam)
        else:
            user32.SendNotifyMessageW(target_hwnd, WM_MOUSEMOVE, 0, lParam)
            user32.SendNotifyMessageW(target_hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lParam)
            user32.SendNotifyMessageW(target_hwnd, WM_LBUTTONUP, 0, lParam)
        
        return True
    
    def double_click(self, x: int, y: int) -> bool:
        """后台双击"""
        self.click(x, y)
        import time
        time.sleep(0.1)
        return self.click(x, y)
    
    def __repr__(self):
        return f"BackgroundClicker(hwnd={self._main_hwnd:08X}, render={self._render_hwnd:08X}, title='{self._title}')"


def background_click(window_title: str, x: int, y: int, button: str = 'left') -> bool:
    """
    便捷函数：后台点击指定窗口
    
    Args:
        window_title: 窗口标题关键字
        x: 窗口内相对X坐标
        y: 窗口内相对Y坐标
        button: 'left' 或 'right'
    
    Returns:
        是否成功
    """
    clicker = BackgroundClicker(window_title)
    if not clicker.hwnd:
        return False
    return clicker.click(x, y, button)


if __name__ == "__main__":
    import time
    
    print("=" * 50)
    print("后台点击工具测试")
    print("=" * 50)
    
    clicker = BackgroundClicker("三国杀")
    
    if clicker.hwnd:
        print(f"已附加: {clicker}")
        print(f"窗口位置: {clicker.rect}")
        
        print("\n3秒后点击 (417, 156)...")
        time.sleep(3)
        clicker.click(417, 156)
        print("完成!")
    else:
        print("未找到窗口")
