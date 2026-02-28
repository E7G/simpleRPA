from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QDialog, QApplication,
    QLabel, QRubberBand
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QRect, QPoint
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QFont
from typing import Optional, Tuple
import sys

from qfluentwidgets import (
    BodyLabel, StrongBodyLabel, PushButton, PrimaryPushButton,
    SpinBox, DoubleSpinBox, ComboBox, LineEdit
)


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
            info_label.setStyleSheet("color: #666; font-size: 11px;")
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
            global_pos = event.globalPos()
            x = global_pos.x()
            y = global_pos.y()
            
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
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        title_label = StrongBodyLabel(f"{self._title}")
        layout.addWidget(title_label)
        
        self._info_label = BodyLabel("未选择区域")
        self._info_label.setStyleSheet("color: gray;")
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
        self._info_label.setText(f"区域: ({rect.x()}, {rect.y()}) {rect.width()}x{rect.height()}")
        self._info_label.setStyleSheet("")
        self.coordinates_changed.emit(rect.x(), rect.y(), rect.width(), rect.height())
    
    def set_region(self, x: int, y: int, width: int, height: int):
        self._info_label.setText(f"区域: ({x}, {y}) {width}x{height}")
        self._info_label.setStyleSheet("")
    
    def get_region(self) -> Tuple[int, int, int, int]:
        return (0, 0, 0, 0)


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
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        self._window_combo = ComboBox()
        self._window_combo.setMinimumWidth(200)
        self._window_combo.setMinimumHeight(40)
        self._window_combo.currentIndexChanged.connect(self._on_combo_changed)
        layout.addWidget(self._window_combo)
        
        self._refresh_btn = PushButton("刷新")
        self._refresh_btn.setMinimumWidth(60)
        self._refresh_btn.setMinimumHeight(40)
        self._refresh_btn.clicked.connect(self.refresh_windows)
        layout.addWidget(self._refresh_btn)
        
        self._pick_btn = PushButton("拾取")
        self._pick_btn.setCheckable(True)
        self._pick_btn.setMinimumWidth(60)
        self._pick_btn.setMinimumHeight(40)
        self._pick_btn.clicked.connect(self._toggle_pick_mode)
        layout.addWidget(self._pick_btn)
    
    def refresh_windows(self):
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
            
            for hwnd, title in windows:
                self._window_combo.addItem(title)
                self._window_combo.setItemData(self._window_combo.count() - 1, hwnd)
        except Exception as e:
            print(f"Refresh windows failed: {e}")
    
    def _on_combo_changed(self, index: int):
        if index > 0:
            hwnd = self._window_combo.itemData(index)
            self._selected_window = hwnd
            self.window_selected.emit(hwnd)
    
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
        rect = self.get_window_rect()
        if rect:
            return (rect[0], rect[1])
        return None
    
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
            self.update()
        elif event.button() == Qt.RightButton:
            self.close()
    
    def mouseMoveEvent(self, event):
        if self._start_pos:
            self._end_pos = event.globalPos()
            self.update()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._start_pos and self._end_pos:
            rect = QRect(self._start_pos, self._end_pos).normalized()
            
            if rect.width() > 10 and rect.height() > 10:
                self.captured.emit(rect)
            
            self.close()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
