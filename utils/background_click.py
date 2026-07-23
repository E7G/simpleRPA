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
PW_CLIENTONLY = 0x00000001
PW_RENDERFULLCONTENT = 0x00000002


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
        self._dm_binding = None
        
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
        self._try_bind_dmsoft()
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
        self._try_bind_dmsoft()
        return True

    def _try_bind_dmsoft(self):
        try:
            from utils.dmsoft import DmSoftBinding
            self._dm_binding = DmSoftBinding.try_bind(self._main_hwnd)
        except Exception:
            self._dm_binding = None
    
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
        if self._dm_binding and self._dm_binding.dm:
            try:
                dm = self._dm_binding.dm
                dm.MoveTo(int(x), int(y))
                method = {'right': 'RightClick', 'middle': 'MiddleClick'}.get(button, 'LeftClick')
                getattr(dm, method)()
                return BackgroundClickResult(True, "后台点击成功(dmsoft)", True)
            except Exception:
                pass
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

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, background: bool = True) -> BackgroundClickResult:
        if not self._main_hwnd:
            return BackgroundClickResult(False, "未附加到窗口", False)
        if not background:
            return BackgroundClickResult(False, "仅支持后台拖拽", False)
        if self._dm_binding and self._dm_binding.dm:
            try:
                dm = self._dm_binding.dm
                dm.MoveTo(int(start_x), int(start_y))
                dm.LeftDown()
                dm.MoveTo(int(end_x), int(end_y))
                dm.LeftUp()
                return BackgroundClickResult(True, "后台拖拽成功(dmsoft)", True)
            except Exception:
                pass
        target = self._render_hwnd or self._main_hwnd
        try:
            user32.PostMessageW(target, WM_MOUSEMOVE, 0, self._make_lparam(start_x, start_y))
            user32.PostMessageW(target, WM_LBUTTONDOWN, MK_LBUTTON, self._make_lparam(start_x, start_y))
            user32.PostMessageW(target, WM_MOUSEMOVE, MK_LBUTTON, self._make_lparam(end_x, end_y))
            user32.PostMessageW(target, WM_LBUTTONUP, 0, self._make_lparam(end_x, end_y))
            return BackgroundClickResult(True, "后台拖拽成功", True)
        except Exception as e:
            return BackgroundClickResult(False, f"后台拖拽失败: {e}", True)
    
    def move(self, x: int, y: int, background: bool = True) -> BackgroundClickResult:
        """移动鼠标"""
        if not self._main_hwnd:
            return BackgroundClickResult(False, "未附加到窗口", False)
        
        if background:
            if self._dm_binding and self._dm_binding.dm:
                try:
                    self._dm_binding.dm.MoveTo(int(x), int(y))
                    return BackgroundClickResult(True, "后台移动成功(dmsoft)", True)
                except Exception:
                    pass
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
            return self.scroll_background(x, y, clicks)
        
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

    def key_press(self, key: str) -> BackgroundClickResult:
        if not self._main_hwnd:
            return BackgroundClickResult(False, "未附加到窗口", False)
        if self._dm_binding and self._dm_binding.dm:
            try:
                self._dm_binding.dm.KeyPress(self._vk_code(key))
                return BackgroundClickResult(True, "后台按键成功(dmsoft)", True)
            except Exception:
                pass
        try:
            import win32con
            target = self._render_hwnd or self._main_hwnd
            vk = self._vk_code(key)
            user32.PostMessageW(target, win32con.WM_KEYDOWN, vk, 0)
            user32.PostMessageW(target, win32con.WM_KEYUP, vk, 0)
            return BackgroundClickResult(True, "后台按键成功", True)
        except Exception as e:
            return BackgroundClickResult(False, f"后台按键失败: {e}", True)

    def type_text(self, text: str) -> BackgroundClickResult:
        if self._dm_binding and self._dm_binding.dm:
            try:
                self._dm_binding.dm.SendString(self._main_hwnd, str(text))
                return BackgroundClickResult(True, "后台输入成功(dmsoft)", True)
            except Exception:
                pass
        try:
            target = self._render_hwnd or self._main_hwnd
            for char in str(text):
                user32.PostMessageW(target, 0x0102, ord(char), 0)
            return BackgroundClickResult(True, "后台输入成功", True)
        except Exception as e:
            return BackgroundClickResult(False, f"后台输入失败: {e}", True)

    def hotkey(self, keys) -> BackgroundClickResult:
        keys = list(keys or [])
        if not keys:
            return BackgroundClickResult(True, "", True)
        try:
            if self._dm_binding and self._dm_binding.dm:
                dm = self._dm_binding.dm
                codes = [self._vk_code(key) for key in keys]
                for code in codes:
                    dm.KeyDown(code)
                for code in reversed(codes):
                    dm.KeyUp(code)
            else:
                import win32con
                target = self._render_hwnd or self._main_hwnd
                codes = [self._vk_code(key) for key in keys]
                for code in codes:
                    user32.PostMessageW(target, win32con.WM_KEYDOWN, code, 0)
                for code in reversed(codes):
                    user32.PostMessageW(target, win32con.WM_KEYUP, code, 0)
            return BackgroundClickResult(True, "后台快捷键成功", True)
        except Exception as e:
            return BackgroundClickResult(False, f"后台快捷键失败: {e}", True)

    @staticmethod
    def _vk_code(key: str) -> int:
        import win32con
        key_name = str(key or "").upper()
        aliases = {
            'ENTER': win32con.VK_RETURN, 'RETURN': win32con.VK_RETURN,
            'ESC': win32con.VK_ESCAPE, 'ESCAPE': win32con.VK_ESCAPE,
            'TAB': win32con.VK_TAB, 'SPACE': win32con.VK_SPACE,
            'BACKSPACE': win32con.VK_BACK, 'DELETE': win32con.VK_DELETE,
            'LEFT': win32con.VK_LEFT, 'RIGHT': win32con.VK_RIGHT,
            'UP': win32con.VK_UP, 'DOWN': win32con.VK_DOWN,
            'CTRL': win32con.VK_CONTROL, 'CONTROL': win32con.VK_CONTROL,
            'SHIFT': win32con.VK_SHIFT, 'ALT': win32con.VK_MENU,
        }
        if key_name in aliases:
            return aliases[key_name]
        if len(key_name) == 1:
            return ord(key_name)
        if key_name.startswith('F') and key_name[1:].isdigit():
            n = int(key_name[1:])
            if 1 <= n <= 24:
                return win32con.VK_F1 + n - 1
        return ord(key_name[:1] or "\0")

    def scroll_background(self, x: int, y: int, clicks: int) -> BackgroundClickResult:
        if not self._main_hwnd:
            return BackgroundClickResult(False, "未附加到窗口", True)
        try:
            if self._dm_binding and self._dm_binding.dm:
                dm = self._dm_binding.dm
                dm.MoveTo(int(x), int(y))
                method = 'WheelUp' if clicks > 0 else 'WheelDown'
                for _ in range(abs(int(clicks))):
                    getattr(dm, method)()
            else:
                import win32con
                target = self._render_hwnd or self._main_hwnd
                delta = int(clicks) * 120
                user32.PostMessageW(target, win32con.WM_MOUSEWHEEL, (delta << 16), self._make_lparam(x, y))
            return BackgroundClickResult(True, "后台滚动成功", True)
        except Exception as e:
            return BackgroundClickResult(False, f"后台滚动失败: {e}", True)

    def capture(self, background: bool = True):
        """截取目标窗口客户区图像。"""
        if not self._main_hwnd:
            return None

        target_hwnd = self._render_hwnd or self._main_hwnd
        if background:
            image = self._background_capture(target_hwnd)
            return image
        return self._foreground_capture(target_hwnd)

    def _background_capture(self, hwnd: int):
        try:
            import win32gui
            import win32ui
            from PIL import Image

            left, top, right, bottom = win32gui.GetClientRect(hwnd)
            width = right - left
            height = bottom - top
            if width <= 0 or height <= 0:
                return None

            if self._dm_binding and self._dm_binding.dm:
                image = self._dm_binding.capture(width, height)
                if image is not None:
                    return image

            hwnd_dc = win32gui.GetWindowDC(hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()
            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(bitmap)

            result = 0
            try:
                for flags in (PW_RENDERFULLCONTENT, PW_CLIENTONLY, 0):
                    result = user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), flags)
                    if result == 1:
                        break

                if result != 1:
                    return None

                bmp_info = bitmap.GetInfo()
                bmp_bytes = bitmap.GetBitmapBits(True)
                return Image.frombuffer(
                    'RGB',
                    (bmp_info['bmWidth'], bmp_info['bmHeight']),
                    bmp_bytes,
                    'raw',
                    'BGRX',
                    0,
                    1
                )
            finally:
                win32gui.DeleteObject(bitmap.GetHandle())
                save_dc.DeleteDC()
                mfc_dc.DeleteDC()
                win32gui.ReleaseDC(hwnd, hwnd_dc)
        except Exception:
            return None

    def _foreground_capture(self, hwnd: int):
        try:
            import pyautogui

            rect = self._get_client_rect_screen(hwnd)
            if not rect:
                return None

            return pyautogui.screenshot(region=rect)
        except Exception:
            return None

    def _get_client_rect_screen(self, hwnd: int) -> Optional[Tuple[int, int, int, int]]:
        try:
            import win32gui

            left, top, right, bottom = win32gui.GetClientRect(hwnd)
            top_left = self._client_to_screen(hwnd, left, top)
            bottom_right = self._client_to_screen(hwnd, right, bottom)
            if not top_left or not bottom_right:
                return None

            return (
                top_left[0],
                top_left[1],
                max(0, bottom_right[0] - top_left[0]),
                max(0, bottom_right[1] - top_left[1])
            )
        except Exception:
            return None

    def _client_to_screen(self, hwnd: int, x: int, y: int) -> Optional[Tuple[int, int]]:
        try:
            point = wintypes.POINT(x, y)
            if user32.ClientToScreen(hwnd, ctypes.byref(point)):
                return (point.x, point.y)
            return None
        except Exception:
            return None
    
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
