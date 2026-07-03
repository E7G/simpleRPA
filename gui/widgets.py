from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QDialog, QApplication,
    QLabel, QRubberBand, QListWidgetItem, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QRect, QPoint
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QFont
from typing import Optional, Tuple, Dict
import sys

from qfluentwidgets import (
    BodyLabel, StrongBodyLabel, PushButton, PrimaryPushButton,
    SpinBox, DoubleSpinBox, ComboBox, LineEdit, CaptionLabel
)

from .fluent_theme import muted_caption_style


def get_physical_cursor_pos(fallback_point=None) -> Tuple[int, int]:
    """返回物理像素下的鼠标坐标，与 pyautogui 回放保持同一坐标系。

    开启高 DPI 缩放(AA_EnableHighDpiScaling)后，Qt 的 event.globalPos()
    返回的是逻辑像素；而 pyautogui / win32(ClientToScreen 等)都使用物理像素。
    在缩放比 ≠100% 的屏幕上直接用逻辑坐标拾取会按 DPI 比例偏移，
    因此拾取时改为在鼠标事件发生的瞬间直接读取系统物理光标坐标。
    """
    if sys.platform == 'win32':
        try:
            import win32api
            return win32api.GetCursorPos()
        except Exception:
            try:
                import ctypes
                from ctypes import wintypes
                pt = wintypes.POINT()
                if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
                    return (pt.x, pt.y)
            except Exception:
                pass
    if fallback_point is not None:
        return (fallback_point.x(), fallback_point.y())
    return (0, 0)


class CoordinateWidget(QWidget):
    coordinates_changed = pyqtSignal(int, int)
    
    def __init__(self, parent=None, title: str = "坐标", window_offset: Optional[Tuple[int, int]] = None):
        super().__init__(parent)
        self._title = title
        self._window_offset = window_offset
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        title_label = StrongBodyLabel(f"{self._title}")
        layout.addWidget(title_label)
        
        x_label = BodyLabel("X 坐标")
        layout.addWidget(x_label)
        
        self._x_spin = SpinBox()
        self._x_spin.setRange(0, 9999)
        self._x_spin.setValue(0)
        self._x_spin.setMinimumHeight(36)
        self._x_spin.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self._x_spin)
        
        y_label = BodyLabel("Y 坐标")
        layout.addWidget(y_label)
        
        self._y_spin = SpinBox()
        self._y_spin.setRange(0, 9999)
        self._y_spin.setValue(0)
        self._y_spin.setMinimumHeight(36)
        self._y_spin.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self._y_spin)
        
        self._pick_btn = PushButton("拾取坐标")
        self._pick_btn.setMinimumHeight(36)
        self._pick_btn.clicked.connect(self._start_pick)
        layout.addWidget(self._pick_btn)
        
        if self._window_offset:
            info_label = BodyLabel("💡 将拾取窗口内相对坐标")
            info_label.setStyleSheet(muted_caption_style("font-size: 11px;"))
            layout.addWidget(info_label)
    
    def set_window_offset(self, offset: Optional[Tuple[int, int]]):
        self._window_offset = offset
    
    def _on_value_changed(self):
        self.coordinates_changed.emit(self._x_spin.value(), self._y_spin.value())
    
    def _start_pick(self):
        self._pick_widget = ScreenPickWidget(window_offset=self._window_offset)
        self._pick_widget.position_picked.connect(self._on_position_picked)
        self._pick_widget.show()
    
    def _on_position_picked(self, x: int, y: int):
        self._x_spin.setValue(x)
        self._y_spin.setValue(y)
    
    def set_coordinates(self, x: int, y: int):
        self._x_spin.blockSignals(True)
        self._y_spin.blockSignals(True)
        self._x_spin.setValue(x)
        self._y_spin.setValue(y)
        self._x_spin.blockSignals(False)
        self._y_spin.blockSignals(False)
    
    def get_coordinates(self) -> Tuple[int, int]:
        return (self._x_spin.value(), self._y_spin.value())


class ScreenPickWidget(QWidget):
    position_picked = pyqtSignal(int, int)
    
    def __init__(self, parent=None, window_offset: Optional[Tuple[int, int]] = None):
        super().__init__(parent)
        self._screen_pixmap = None
        self._screen_offset = (0, 0)
        self._window_offset = window_offset
        
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowState(Qt.WindowFullScreen)
        self.setCursor(Qt.CrossCursor)
        self.setAttribute(Qt.WA_OpaquePaintEvent, False)
        
        screen = QApplication.primaryScreen()
        if screen:
            self._screen_pixmap = screen.grabWindow(0)
            geometry = screen.geometry()
            self._screen_offset = (geometry.x(), geometry.y())
    
    def showEvent(self, event):
        super().showEvent(event)
        self.activateWindow()
        self.raise_()
        self.setFocus()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            
            if self._screen_pixmap:
                painter.drawPixmap(0, 0, self._screen_pixmap)
            
            painter.fillRect(self.rect(), QColor(0, 0, 0, 80))
            
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawText(20, 40, "点击屏幕获取坐标，按 ESC 取消")
        finally:
            painter.end()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 用物理像素光标坐标，与 pyautogui 回放及窗口偏移(ClientToScreen)同一坐标系，
            # 避免高 DPI 缩放下 event.globalPos() 的逻辑坐标导致拾取偏移。
            x, y = get_physical_cursor_pos(event.globalPos())

            if self._window_offset:
                x = x - self._window_offset[0]
                y = y - self._window_offset[1]

            self.position_picked.emit(x, y)
            self.close()
        elif event.button() == Qt.RightButton:
            self.close()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class DragCoordinateWidget(QWidget):
    coordinates_changed = pyqtSignal(int, int, int, int)
    
    def __init__(self, parent=None, title: str = "区域"):
        super().__init__(parent)
        self._title = title
        self._region: Tuple[int, int, int, int] = (0, 0, 0, 0)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        title_label = StrongBodyLabel(f"{self._title}")
        layout.addWidget(title_label)
        
        self._info_label = BodyLabel("未选择区域")
        self._info_label.setStyleSheet(muted_caption_style())
        layout.addWidget(self._info_label)
        
        self._pick_btn = PushButton("框选区域")
        self._pick_btn.setMinimumHeight(36)
        self._pick_btn.clicked.connect(self._start_pick)
        layout.addWidget(self._pick_btn)
    
    def _start_pick(self):
        self._pick_widget = CaptureWidget()
        self._pick_widget.captured.connect(self._on_region_captured)
        self._pick_widget.show()
    
    def _on_region_captured(self, rect: QRect):
        self._region = (rect.x(), rect.y(), rect.width(), rect.height())
        self._info_label.setText(f"区域: ({rect.x()}, {rect.y()}) {rect.width()}x{rect.height()}")
        self._info_label.setStyleSheet("")
        self.coordinates_changed.emit(rect.x(), rect.y(), rect.width(), rect.height())
    
    def set_region(self, x: int, y: int, width: int, height: int):
        self._region = (x, y, width, height)
        self._info_label.setText(f"区域: ({x}, {y}) {width}x{height}")
        self._info_label.setStyleSheet("")
    
    def get_region(self) -> Tuple[int, int, int, int]:
        return self._region


class WindowSelector(QWidget):
    window_selected = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_window = None
        self._pick_mode = False
        self._listener = None
        self._setup_ui()
        self._check_win32()
    
    def _check_win32(self):
        if sys.platform == 'win32':
            try:
                import win32gui
                self._win32_available = True
            except ImportError:
                self._win32_available = False
        else:
            self._win32_available = False
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        self._window_combo = ComboBox()
        self._window_combo.setMinimumWidth(200)
        self._window_combo.setMinimumHeight(36)
        self._window_combo.currentIndexChanged.connect(self._on_combo_changed)
        layout.addWidget(self._window_combo)
        
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        
        self._refresh_btn = PushButton("刷新")
        self._refresh_btn.setMinimumHeight(32)
        self._refresh_btn.clicked.connect(self.refresh_windows)
        btn_row.addWidget(self._refresh_btn)
        
        self._pick_btn = PushButton("拾取")
        self._pick_btn.setCheckable(True)
        self._pick_btn.setMinimumHeight(32)
        self._pick_btn.clicked.connect(self._toggle_pick_mode)
        btn_row.addWidget(self._pick_btn)
        
        layout.addLayout(btn_row)
    
    def refresh_windows(self):
        current_hwnd = self._selected_window
        current_title = ""
        if current_hwnd and self._win32_available:
            try:
                import win32gui
                current_title = win32gui.GetWindowText(current_hwnd)
            except:
                pass
        
        self._window_combo.clear()
        self._window_combo.addItem("-- 选择窗口 --")
        
        if not self._win32_available:
            return
        
        try:
            import win32gui
            
            windows = []
            
            def enum_callback(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title:
                        windows.append((hwnd, title))
                return True
            
            win32gui.EnumWindows(enum_callback, None)
            
            found_index = -1
            for hwnd, title in windows:
                self._window_combo.addItem(title)
                self._window_combo.setItemData(self._window_combo.count() - 1, hwnd)
                if hwnd == current_hwnd:
                    found_index = self._window_combo.count() - 1
            
            if found_index > 0:
                self._window_combo.setCurrentIndex(found_index)
            else:
                self._selected_window = None
        except Exception as e:
            print(f"Refresh windows failed: {e}")
    
    def _on_combo_changed(self, index: int):
        if index > 0:
            hwnd = self._window_combo.itemData(index)
            if hwnd:
                self._selected_window = hwnd
                self.window_selected.emit(hwnd)
                self._ensure_window_exists(hwnd)
    
    def _ensure_window_exists(self, hwnd: int):
        if not self._win32_available:
            return
        
        try:
            import win32gui
            if not win32gui.IsWindow(hwnd):
                title = self._window_combo.currentText()
                self._try_launch_window(title)
        except Exception:
            pass
    
    def _try_launch_window(self, window_title: str):
        from core.command_manager import CommandManager
        cmd_manager = CommandManager.get_instance()
        
        commands = cmd_manager.get_all_commands()
        for cmd in commands:
            if cmd.window_title_pattern and cmd.window_title_pattern.lower() in window_title.lower():
                success, message, already_running = cmd_manager.check_and_launch(cmd.id)
                if success and not already_running:
                    from qfluentwidgets import InfoBar, InfoBarPosition
                    InfoBar.success(
                        title="窗口已启动",
                        content=f"已自动启动: {cmd.name}",
                        parent=self,
                        position=InfoBarPosition.TOP,
                        duration=2000
                    )
                break
    
    def _toggle_pick_mode(self, checked: bool):
        self._pick_mode = checked
        if checked:
            self.refresh_windows()
            self._pick_btn.setText("点击窗口")
            self._start_pick()
        else:
            self._pick_btn.setText("拾取")
            self._stop_pick()
    
    def _start_pick(self):
        from pynput import mouse
        
        def on_click(x, y, button, pressed):
            if pressed:
                self._select_window_at_point(int(x), int(y))
                return False
        
        self._listener = mouse.Listener(on_click=on_click)
        self._listener.start()
    
    def _stop_pick(self):
        if self._listener:
            self._listener.stop()
            self._listener = None
        self._pick_btn.setChecked(False)
        self._pick_btn.setText("拾取")
        self._pick_mode = False
    
    def _select_window_at_point(self, x: int, y: int):
        if not self._win32_available:
            return
        
        try:
            import win32gui
            
            hwnd = win32gui.WindowFromPoint((x, y))
            
            while hwnd:
                parent = win32gui.GetParent(hwnd)
                if parent == 0:
                    break
                hwnd = parent
            
            for i in range(self._window_combo.count()):
                if self._window_combo.itemData(i) == hwnd:
                    self._window_combo.setCurrentIndex(i)
                    break
            
            self._stop_pick()
        except Exception as e:
            print(f"Select window failed: {e}")
            self._stop_pick()
    
    def get_selected_window(self):
        return self._selected_window
    
    def get_window_rect(self) -> Optional[Tuple[int, int, int, int]]:
        if not self._selected_window or not self._win32_available:
            return None
        
        try:
            import win32gui
            return win32gui.GetWindowRect(self._selected_window)
        except Exception:
            return None
    
    def get_window_offset(self) -> Optional[Tuple[int, int]]:
        """
        获取窗口客户区左上角在屏幕上的坐标
        
        使用 ClientToScreen API 确保坐标准确，自动处理：
        - 窗口边框和标题栏
        - DPI 缩放
        - 多显示器设置
        """
        if not self._selected_window:
            return None
        
        from utils.window_utils import WindowUtils
        window_utils = WindowUtils()
        
        client_screen_pos = window_utils.client_to_screen_coords(self._selected_window, 0, 0)
        return client_screen_pos
    
    def _get_client_offset(self) -> Optional[Tuple[int, int]]:
        if not self._selected_window:
            return None
        
        from utils.window_utils import WindowUtils
        window_utils = WindowUtils()
        return window_utils.get_client_offset(self._selected_window)
    
    def screen_to_client(self, screen_x: int, screen_y: int) -> Optional[Tuple[int, int]]:
        """
        将屏幕坐标转换为窗口客户区坐标
        
        使用 Windows ScreenToClient API 确保转换准确
        """
        if not self._selected_window:
            return None
        
        from utils.window_utils import WindowUtils
        window_utils = WindowUtils()
        return window_utils.screen_to_client_coords(self._selected_window, screen_x, screen_y)
    
    def client_to_screen(self, client_x: int, client_y: int) -> Optional[Tuple[int, int]]:
        """
        将窗口客户区坐标转换为屏幕坐标
        
        使用 Windows ClientToScreen API 确保转换准确
        """
        if not self._selected_window:
            return None
        
        from utils.window_utils import WindowUtils
        window_utils = WindowUtils()
        return window_utils.client_to_screen_coords(self._selected_window, client_x, client_y)
    
    def get_selected_hwnd(self) -> int:
        return self._selected_window or 0
    
    def get_selected_title(self) -> str:
        if self._selected_window and self._win32_available:
            try:
                import win32gui
                return win32gui.GetWindowText(self._selected_window)
            except:
                pass
        return ""
    
    def set_selected_window(self, hwnd: int, title: str = ""):
        self._selected_window = hwnd
        if title:
            self._window_combo.addItem(title, hwnd)
            self._window_combo.setCurrentText(title)
    
    def validate_window(self) -> Tuple[bool, str, Optional[int]]:
        if not self._selected_window:
            return True, "", None
        
        if not self._win32_available:
            return True, "", self._selected_window
        
        try:
            import win32gui
            
            if not win32gui.IsWindow(self._selected_window):
                title = self.get_selected_title()
                return False, f"窗口已关闭或不存在\n窗口标题: {title}\n句柄: {self._selected_window}", self._selected_window
            
            current_title = win32gui.GetWindowText(self._selected_window)
            if not current_title:
                return False, f"窗口可能已无响应\n句柄: {self._selected_window}", self._selected_window
            
            return True, current_title, self._selected_window
            
        except Exception as e:
            return False, f"验证窗口失败: {str(e)}\n句柄: {self._selected_window}", self._selected_window
    
    def refresh_and_validate(self) -> Tuple[bool, str]:
        if not self._selected_window:
            return True, ""
        
        is_valid, message, _ = self.validate_window()
        
        if not is_valid:
            self._selected_window = None
            self._window_combo.setCurrentIndex(0)
        
        return is_valid, message
    
    def set_window_title(self, title: str):
        if not title:
            return
        
        for i in range(self._window_combo.count()):
            item_title = self._window_combo.itemText(i)
            if title.lower() in item_title.lower():
                self._window_combo.setCurrentIndex(i)
                self._selected_window = self._window_combo.itemData(i)
                return
        
        self._window_combo.insertItem(1, f"[未找到] {title}")
        self._window_combo.setCurrentIndex(1)


class WindowPickerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择窗口")
        self.setMinimumSize(400, 300)
        self._selected_window = None
        self._setup_ui()
        self._load_windows()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        from qfluentwidgets import SubtitleLabel, CaptionLabel
        
        title_label = SubtitleLabel("请选择目标窗口")
        layout.addWidget(title_label)
        
        tip_label = CaptionLabel("点击列表中的窗口或使用\"拾取\"按钮选择")
        tip_label.setStyleSheet(muted_caption_style())
        layout.addWidget(tip_label)
        
        from qfluentwidgets import ListWidget
        
        self._window_list = ListWidget()
        self._window_list.setMinimumHeight(200)
        self._window_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._window_list)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self._pick_btn = PushButton("拾取窗口")
        self._pick_btn.clicked.connect(self._start_pick)
        btn_layout.addWidget(self._pick_btn)
        
        self._ok_btn = PrimaryPushButton("确定")
        self._ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self._ok_btn)
        
        self._cancel_btn = PushButton("取消")
        self._cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def _load_windows(self):
        from utils.window_utils import WindowUtils
        window_utils = WindowUtils()
        windows = window_utils.get_all_windows()
        
        self._window_list.clear()
        for window in windows:
            if window.title and window.width > 100 and window.height > 100:
                item = QListWidgetItem(f"{window.title} (hwnd: {window.hwnd})")
                item.setData(Qt.UserRole, {
                    'hwnd': window.hwnd,
                    'title': window.title,
                    'rect': window.rect
                })
                self._window_list.addItem(item)
    
    def _on_item_double_clicked(self, item):
        self.accept()
    
    def _start_pick(self):
        self.hide()
        
        from pynput import mouse
        
        def on_click(x, y, button, pressed):
            if pressed:
                self._select_window_at_point(int(x), int(y))
                return False
        
        self._listener = mouse.Listener(on_click=on_click)
        self._listener.start()
    
    def _select_window_at_point(self, x: int, y: int):
        try:
            import win32gui
            
            hwnd = win32gui.WindowFromPoint((x, y))
            
            while hwnd:
                parent = win32gui.GetParent(hwnd)
                if parent == 0:
                    break
                hwnd = parent
            
            title = win32gui.GetWindowText(hwnd)
            
            self._selected_window = {
                'hwnd': hwnd,
                'title': title,
                'process': self._get_process_name(hwnd)
            }
            
            from PyQt5.QtCore import QMetaObject, Qt
            QMetaObject.invokeMethod(self, "accept", Qt.QueuedConnection)
            
        except Exception:
            self.show()
    
    def _get_process_name(self, hwnd: int) -> str:
        try:
            import win32process
            import psutil
            
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            return process.name()
        except:
            return ""
    
    def get_selected_window(self) -> Optional[Dict]:
        if self._selected_window:
            return self._selected_window
        
        current_item = self._window_list.currentItem()
        if current_item:
            data = current_item.data(Qt.UserRole)
            return {
                'hwnd': data['hwnd'],
                'title': data['title'],
                'process': self._get_process_name(data['hwnd'])
            }
        
        return None


class KeySequenceDialog(QDialog):
    def __init__(self, parent=None, current_keys=None):
        super().__init__(parent)
        self.setWindowTitle("设置快捷键")
        self.setMinimumWidth(350)
        self._keys = list(current_keys) if current_keys else []
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        tip_label = StrongBodyLabel("按下快捷键组合:")
        layout.addWidget(tip_label)
        
        self._key_label = BodyLabel(self._get_key_string())
        self._key_label.setAlignment(Qt.AlignCenter)
        self._key_label.setMinimumHeight(60)
        layout.addWidget(self._key_label)
        
        self._clear_btn = PushButton("清除")
        self._clear_btn.clicked.connect(self._clear_keys)
        layout.addWidget(self._clear_btn)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self._ok_btn = PrimaryPushButton("确定")
        self._ok_btn.setMinimumHeight(36)
        self._ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self._ok_btn)
        
        self._cancel_btn = PushButton("取消")
        self._cancel_btn.setMinimumHeight(36)
        self._cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._cancel_btn)
        layout.addLayout(btn_layout)
        
        self._start_listening()
    
    def _start_listening(self):
        from pynput import keyboard
        
        self._listener = keyboard.Listener(on_press=self._on_key_press)
        self._listener.start()
    
    def _on_key_press(self, key):
        try:
            key_name = None
            
            if hasattr(key, 'char') and key.char:
                key_name = key.char.upper()
            elif hasattr(key, 'name'):
                name_map = {
                    'ctrl_l': 'Ctrl', 'ctrl_r': 'Ctrl',
                    'alt_l': 'Alt', 'alt_r': 'Alt',
                    'shift_l': 'Shift', 'shift_r': 'Shift',
                    'cmd': 'Win', 'cmd_l': 'Win', 'cmd_r': 'Win',
                }
                key_name = name_map.get(key.name.lower(), key.name.lower().capitalize())
            
            if key_name and key_name not in self._keys:
                modifier_keys = ['Ctrl', 'Alt', 'Shift', 'Win']
                if key_name in modifier_keys:
                    self._keys.insert(0, key_name)
                else:
                    self._keys.append(key_name)
                
                self._key_label.setText(self._get_key_string())
        except Exception:
            pass
    
    def _clear_keys(self):
        self._keys = []
        self._key_label.setText("按下快捷键组合")
    
    def _get_key_string(self) -> str:
        return ' + '.join(self._keys) if self._keys else "按下快捷键组合"
    
    def get_keys(self):
        return self._keys
    
    def closeEvent(self, event):
        if hasattr(self, '_listener'):
            self._listener.stop()
        super().closeEvent(event)


class CaptureWidget(QWidget):
    captured = pyqtSignal(QRect)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._start_pos = None
        self._end_pos = None
        # 物理像素坐标：用于输出截图区域，与 pyautogui.screenshot(region=...) 同一坐标系。
        # _start_pos/_end_pos 仍用逻辑坐标，仅用于在本控件上绘制选框。
        self._start_phys = None
        self._end_phys = None
        self._screen_pixmap = None
        
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowState(Qt.WindowFullScreen)
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_OpaquePaintEvent, False)
        
        screen = QApplication.primaryScreen()
        if screen:
            self._screen_pixmap = screen.grabWindow(0)
    
    def showEvent(self, event):
        super().showEvent(event)
        self.activateWindow()
        self.raise_()
        self.setFocus()
    
    def paintEvent(self, event):
        from PyQt5.QtGui import QPen, QBrush
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            
            if self._screen_pixmap:
                painter.drawPixmap(0, 0, self._screen_pixmap)
            
            painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
            
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawText(20, 40, "拖动鼠标框选区域，按 ESC 取消")
            
            if self._start_pos and self._end_pos:
                rect = QRect(self._start_pos, self._end_pos).normalized()
                
                if self._screen_pixmap:
                    painter.drawPixmap(rect, self._screen_pixmap, rect)
                
                painter.setPen(QPen(QColor(0, 120, 215), 2))
                painter.setBrush(QBrush(Qt.NoBrush))
                painter.drawRect(rect)
                
                size_text = f"{rect.width()} x {rect.height()}"
                painter.drawText(rect.x() + 5, rect.y() - 5, size_text)
        finally:
            painter.end()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._start_pos = event.globalPos()
            self._end_pos = event.globalPos()
            self._start_phys = get_physical_cursor_pos(event.globalPos())
            self._end_phys = self._start_phys
            self.update()
        elif event.button() == Qt.RightButton:
            self.close()

    def mouseMoveEvent(self, event):
        if self._start_pos:
            self._end_pos = event.globalPos()
            self._end_phys = get_physical_cursor_pos(event.globalPos())
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._start_pos and self._end_pos:
            rect = QRect(self._start_pos, self._end_pos).normalized()

            if rect.width() > 10 and rect.height() > 10:
                # 输出物理像素区域，与 pyautogui.screenshot(region=...) 同一坐标系，
                # 避免高 DPI 缩放下逻辑坐标导致截图区域错位/尺寸不符。
                sx, sy = self._start_phys or (rect.x(), rect.y())
                ex, ey = self._end_phys or (rect.x() + rect.width(), rect.y() + rect.height())
                phys_rect = QRect(QPoint(sx, sy), QPoint(ex, ey)).normalized()
                self.captured.emit(phys_rect)

            self.close()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class WindowPreview(QWidget):
    """窗口实时预览组件，用于在离屏模式下显示目标窗口状态。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hwnd = None
        self._pixmap = None
        self._paused = False
        self._setup_ui()

    def set_paused(self, paused: bool):
        self._paused = paused

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel()
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setMinimumSize(200, 150)
        self._label.setStyleSheet(
            "border: 1px solid rgba(128,128,128,0.3);"
            "background-color: rgba(0,0,0,0.05);"
        )
        layout.addWidget(self._label, 1)

        self._info_label = CaptionLabel("")
        self._info_label.setStyleSheet(muted_caption_style("font-size: 11px;"))
        layout.addWidget(self._info_label)

    def set_hwnd(self, hwnd):
        self._hwnd = hwnd
        if self.isVisible():
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(200, self._safe_update)

    def _safe_update(self):
        try:
            self.update_preview()
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        if self._hwnd:
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(300, self._safe_update)

    def update_preview(self):
        if not self._hwnd:
            self._pixmap = None
            self._label.clear()
            self._label.setText("未选择窗口")
            self._info_label.setText("")
            return

        label_size = self._label.size()
        if label_size.width() <= 0 or label_size.height() <= 0:
            return

        pixmap = self._capture_window()
        if pixmap and not pixmap.isNull():
            label_size = self._label.size()
            if label_size.width() > 0 and label_size.height() > 0:
                scaled = pixmap.scaled(
                    label_size,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self._pixmap = scaled
                self._label.setPixmap(scaled)
                self._info_label.setText(
                    f"{pixmap.width()}×{pixmap.height()}"
                )
            self._pixmap = scaled
            self._label.setPixmap(scaled)
            self._info_label.setText(
                f"{pixmap.width()}×{pixmap.height()}"
            )
        else:
            self._pixmap = None
            self._label.clear()
            self._label.setText("无法获取窗口")
            self._info_label.setText("")

    def _capture_window(self):
        if not self._hwnd:
            return None
        try:
            import win32gui
            import win32ui
            import ctypes

            if not win32gui.IsWindow(self._hwnd):
                return None

            left, top, right, bottom = win32gui.GetClientRect(self._hwnd)
            width = right - left
            height = bottom - top
            if width <= 0 or height <= 0:
                return None

            hwnd_dc = win32gui.GetWindowDC(self._hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()
            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(bitmap)

            try:
                user32 = ctypes.windll.user32
                PW_CLIENTONLY = 1
                PW_RENDERFULLCONTENT = 2
                result = 0
                for flags in (PW_RENDERFULLCONTENT, PW_CLIENTONLY, 0):
                    try:
                        result = user32.PrintWindow(
                            self._hwnd, save_dc.GetSafeHdc(), flags
                        )
                    except OSError:
                        result = 0
                    if result == 1:
                        break

                if result != 1:
                    return None

                bmp_info = bitmap.GetInfo()
                bmp_bytes = bitmap.GetBitmapBits(True)

                width = bmp_info["bmWidth"]
                height = bmp_info["bmHeight"]

                from PIL import Image
                from PyQt5.QtGui import QImage
                img = Image.frombuffer(
                    "RGB",
                    (width, height),
                    bmp_bytes,
                    "raw",
                    "BGRX",
                    0,
                    1,
                )
                data = img.tobytes("raw", "RGB")
                bytes_per_line = width * 3
                qimg = QImage(
                    data,
                    width,
                    height,
                    bytes_per_line,
                    QImage.Format_RGB888,
                )
                return QPixmap.fromImage(qimg.copy())
            finally:
                try:
                    win32gui.DeleteObject(bitmap.GetHandle())
                except Exception:
                    pass
                try:
                    save_dc.DeleteDC()
                except Exception:
                    pass
                try:
                    mfc_dc.DeleteDC()
                except Exception:
                    pass
                win32gui.ReleaseDC(self._hwnd, hwnd_dc)
        except Exception:
            return None
