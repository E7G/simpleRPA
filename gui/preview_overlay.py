from PyQt5.QtWidgets import QWidget, QApplication, QDesktopWidget
from PyQt5.QtCore import Qt, QTimer, QRect, QPoint
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QGuiApplication, QScreen
from typing import Optional, Tuple, List
import os


class PreviewOverlay(QWidget):
    def __init__(self, duration: int = 2000):
        super().__init__()
        self._duration = duration
        self._preview_type = None
        self._preview_data = {}
        
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timer)
        self._blink_state = True
        self._blink_count = 0
        
        self._setup_geometry()
    
    def _setup_geometry(self):
        screens = QGuiApplication.screens()
        if screens:
            virtual_geometry = screens[0].geometry()
            for screen in screens[1:]:
                virtual_geometry = virtual_geometry.united(screen.geometry())
            self.setGeometry(virtual_geometry)
        else:
            self.showFullScreen()
    
    def show_click_position(self, x: int, y: int, label: str = ""):
        self._preview_type = 'click'
        self._preview_data = {'x': x, 'y': y, 'label': label}
        self._start_preview()
    
    def show_drag_line(self, start_x: int, start_y: int, end_x: int, end_y: int):
        self._preview_type = 'drag'
        self._preview_data = {
            'start_x': start_x, 'start_y': start_y,
            'end_x': end_x, 'end_y': end_y
        }
        self._start_preview()
    
    def show_region(self, x: int, y: int, width: int, height: int, label: str = ""):
        self._preview_type = 'region'
        self._preview_data = {'x': x, 'y': y, 'width': width, 'height': height, 'label': label}
        self._start_preview()
    
    def show_scroll_position(self, x: int, y: int, clicks: int):
        self._preview_type = 'scroll'
        self._preview_data = {'x': x, 'y': y, 'clicks': clicks}
        self._start_preview()
    
    def show_image_match(self, image_path: str, confidence: float = 0.9):
        self._preview_type = 'image'
        self._preview_data = {'image_path': image_path, 'confidence': confidence}
        self._start_preview()
    
    def show_text_preview(self, text: str, title: str = "文本预览"):
        self._preview_type = 'text'
        self._preview_data = {'text': text, 'title': title}
        self._start_preview()
    
    def show_hotkey_preview(self, keys: List[str]):
        self._preview_type = 'hotkey'
        self._preview_data = {'keys': keys}
        self._start_preview()
    
    def show_action_group_preview(self, group_name: str, action_count: int, description: str = ""):
        self._preview_type = 'action_group'
        self._preview_data = {
            'group_name': group_name,
            'action_count': action_count,
            'description': description
        }
        self._start_preview()
    
    def _start_preview(self):
        self._blink_state = True
        self._blink_count = 0
        self.show()
        self.raise_()
        self._timer.start(200)
    
    def _on_timer(self):
        self._blink_state = not self._blink_state
        self._blink_count += 1
        self.update()
        
        if self._blink_count >= self._duration // 200:
            self._timer.stop()
            self.hide()
    
    def stop_preview(self):
        self._timer.stop()
        self.hide()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self._preview_type == 'click':
            self._draw_click_marker(painter)
        elif self._preview_type == 'drag':
            self._draw_drag_line(painter)
        elif self._preview_type == 'region':
            self._draw_region(painter)
        elif self._preview_type == 'scroll':
            self._draw_scroll_marker(painter)
        elif self._preview_type == 'image':
            self._draw_image_match(painter)
        elif self._preview_type == 'text':
            self._draw_text_preview(painter)
        elif self._preview_type == 'hotkey':
            self._draw_hotkey_preview(painter)
        elif self._preview_type == 'action_group':
            self._draw_action_group_preview(painter)
    
    def _draw_click_marker(self, painter: QPainter):
        x = self._preview_data.get('x', 0)
        y = self._preview_data.get('y', 0)
        label = self._preview_data.get('label', '')
        
        radius = 20
        color = QColor(255, 50, 50, 200) if self._blink_state else QColor(255, 100, 100, 150)
        
        painter.setPen(QPen(color, 3))
        painter.setBrush(QBrush(QColor(255, 50, 50, 80)))
        painter.drawEllipse(QPoint(x, y), radius, radius)
        
        painter.setPen(QPen(QColor(255, 50, 50), 2))
        painter.drawLine(x - 10, y, x + 10, y)
        painter.drawLine(x, y - 10, x, y + 10)
        
        if label:
            font = QFont()
            font.setPointSize(12)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QPen(QColor(255, 255, 255)))
            
            text_rect = QRect(x + radius + 5, y - 15, 200, 30)
            painter.fillRect(text_rect, QColor(0, 0, 0, 180))
            painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, label)
    
    def _draw_drag_line(self, painter: QPainter):
        start_x = self._preview_data.get('start_x', 0)
        start_y = self._preview_data.get('start_y', 0)
        end_x = self._preview_data.get('end_x', 0)
        end_y = self._preview_data.get('end_y', 0)
        
        color = QColor(50, 150, 255, 200) if self._blink_state else QColor(100, 180, 255, 150)
        
        painter.setPen(QPen(color, 3))
        painter.drawLine(start_x, start_y, end_x, end_y)
        
        painter.setBrush(QBrush(color))
        
        dx = end_x - start_x
        dy = end_y - start_y
        length = (dx * dx + dy * dy) ** 0.5
        if length > 0:
            dx /= length
            dy /= length
            
            arrow_size = 15
            p1 = QPoint(end_x, end_y)
            p2 = QPoint(int(end_x - arrow_size * (dx + dy * 0.5)),
                       int(end_y - arrow_size * (dy - dx * 0.5)))
            p3 = QPoint(int(end_x - arrow_size * (dx - dy * 0.5)),
                       int(end_y - arrow_size * (dy + dx * 0.5)))
            
            painter.drawPolygon(p1, p2, p3)
        
        painter.setPen(QPen(QColor(50, 200, 50), 3))
        painter.setBrush(QBrush(QColor(50, 200, 50, 100)))
        painter.drawEllipse(QPoint(start_x, start_y), 10, 10)
        
        painter.setPen(QPen(QColor(255, 50, 50), 3))
        painter.setBrush(QBrush(QColor(255, 50, 50, 100)))
        painter.drawEllipse(QPoint(end_x, end_y), 10, 10)
        
        font = QFont()
        font.setPointSize(10)
        painter.setFont(font)
        painter.setPen(QPen(QColor(255, 255, 255)))
        
        start_text = f"({start_x}, {start_y})"
        end_text = f"({end_x}, {end_y})"
        
        painter.fillRect(start_x - 40, start_y - 30, 80, 20, QColor(0, 0, 0, 180))
        painter.drawText(start_x - 40, start_y - 15, start_text)
        
        painter.fillRect(end_x - 40, end_y + 10, 80, 20, QColor(0, 0, 0, 180))
        painter.drawText(end_x - 40, end_y + 25, end_text)
    
    def _draw_region(self, painter: QPainter):
        x = self._preview_data.get('x', 0)
        y = self._preview_data.get('y', 0)
        width = self._preview_data.get('width', 100)
        height = self._preview_data.get('height', 100)
        label = self._preview_data.get('label', '')
        
        color = QColor(50, 200, 50, 200) if self._blink_state else QColor(100, 230, 100, 150)
        
        pen = QPen(color, 2, Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(50, 200, 50, 30)))
        painter.drawRect(x, y, width, height)
        
        font = QFont()
        font.setPointSize(11)
        painter.setFont(font)
        painter.setPen(QPen(QColor(255, 255, 255)))
        
        text = label if label else f"区域: {width}x{height}"
        text_rect = QRect(x, y - 25, len(text) * 10 + 20, 25)
        painter.fillRect(text_rect, QColor(50, 200, 50, 200))
        painter.drawText(text_rect, Qt.AlignCenter, text)
    
    def _draw_scroll_marker(self, painter: QPainter):
        x = self._preview_data.get('x', 0)
        y = self._preview_data.get('y', 0)
        clicks = self._preview_data.get('clicks', 0)
        
        color = QColor(255, 150, 50, 200) if self._blink_state else QColor(255, 180, 100, 150)
        
        painter.setPen(QPen(color, 3))
        painter.setBrush(QBrush(QColor(255, 150, 50, 80)))
        painter.drawEllipse(QPoint(x, y), 15, 15)
        
        direction = "↑" if clicks > 0 else "↓"
        abs_clicks = abs(clicks)
        
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(QColor(255, 255, 255)))
        
        painter.drawText(x - 7, y + 5, direction)
        
        text = f"滚动: {abs_clicks} 格 {'向上' if clicks > 0 else '向下'}"
        text_rect = QRect(x + 20, y - 15, 150, 30)
        painter.fillRect(text_rect, QColor(0, 0, 0, 180))
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, text)
    
    def _draw_image_match(self, painter: QPainter):
        image_path = self._preview_data.get('image_path', '')
        confidence = self._preview_data.get('confidence', 0.9)
        
        try:
            import pyautogui
            try:
                location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            except pyautogui.ImageNotFoundException:
                location = None
            
            if location:
                color = QColor(50, 200, 50, 200) if self._blink_state else QColor(100, 230, 100, 150)
                
                pen = QPen(color, 3)
                painter.setPen(pen)
                painter.setBrush(QBrush(QColor(50, 200, 50, 50)))
                painter.drawRect(location.left, location.top, location.width, location.height)
                
                painter.setPen(QPen(color, 2))
                painter.drawLine(location.left, location.top, location.left + 15, location.top)
                painter.drawLine(location.left, location.top, location.left, location.top + 15)
                painter.drawLine(location.left + location.width, location.top, location.left + location.width - 15, location.top)
                painter.drawLine(location.left + location.width, location.top, location.left + location.width, location.top + 15)
                painter.drawLine(location.left, location.top + location.height, location.left + 15, location.top + location.height)
                painter.drawLine(location.left, location.top + location.height, location.left, location.top + location.height - 15)
                painter.drawLine(location.left + location.width, location.top + location.height, location.left + location.width - 15, location.top + location.height)
                painter.drawLine(location.left + location.width, location.top + location.height, location.left + location.width, location.top + location.height - 15)
                
                font = QFont()
                font.setPointSize(10)
                font.setBold(True)
                painter.setFont(font)
                painter.setPen(QPen(QColor(255, 255, 255)))
                
                line1 = f"✓ 匹配成功"
                line2 = f"位置: ({location.left}, {location.top})"
                line3 = f"尺寸: {location.width}x{location.height}"
                line4 = f"置信度: {confidence}"
                
                info_x = location.left
                info_y = location.top - 80
                if info_y < 10:
                    info_y = location.top + location.height + 10
                
                info_width = 160
                info_height = 75
                info_rect = QRect(info_x, info_y, info_width, info_height)
                painter.fillRect(info_rect, QColor(50, 200, 50, 230))
                
                painter.drawText(info_x + 10, info_y + 18, line1)
                painter.drawText(info_x + 10, info_y + 35, line2)
                painter.drawText(info_x + 10, info_y + 52, line3)
                painter.drawText(info_x + 10, info_y + 69, line4)
                
                center_x = location.left + location.width // 2
                center_y = location.top + location.height // 2
                painter.setPen(QPen(QColor(255, 255, 255), 2))
                painter.drawLine(center_x - 10, center_y, center_x + 10, center_y)
                painter.drawLine(center_x, center_y - 10, center_x, center_y + 10)
            else:
                font = QFont()
                font.setPointSize(12)
                font.setBold(True)
                painter.setFont(font)
                painter.setPen(QPen(QColor(255, 100, 100)))
                
                screen_center = self.rect().center()
                
                info_width = 200
                info_height = 60
                info_rect = QRect(
                    screen_center.x() - info_width // 2,
                    screen_center.y() - info_height // 2,
                    info_width,
                    info_height
                )
                painter.fillRect(info_rect, QColor(0, 0, 0, 220))
                
                painter.drawText(info_rect.adjusted(10, 10, -10, -30), Qt.AlignCenter, "✗ 未找到匹配图片")
                painter.setFont(QFont("", 10))
                painter.drawText(info_rect.adjusted(10, 35, -10, -10), Qt.AlignCenter, f"置信度: {confidence}")
        except Exception as e:
            font = QFont()
            font.setPointSize(12)
            painter.setFont(font)
            painter.setPen(QPen(QColor(255, 100, 100)))
            
            screen_center = self.rect().center()
            error_msg = str(e)[:50] if str(e) else "未知错误"
            text = f"预览错误: {error_msg}"
            text_rect = QRect(screen_center.x() - 200, screen_center.y() - 20, 400, 40)
            painter.fillRect(text_rect, QColor(0, 0, 0, 200))
            painter.drawText(text_rect, Qt.AlignCenter, text)
    
    def _draw_text_preview(self, painter: QPainter):
        text = self._preview_data.get('text', '')
        title = self._preview_data.get('title', '文本预览')
        
        screen_center = self.rect().center()
        
        font = QFont()
        font.setPointSize(12)
        painter.setFont(font)
        
        display_text = text[:100] + "..." if len(text) > 100 else text
        text_width = len(display_text) * 12 + 40
        text_height = 80
        
        text_rect = QRect(
            screen_center.x() - text_width // 2,
            screen_center.y() - text_height // 2,
            text_width,
            text_height
        )
        
        color = QColor(50, 100, 200, 230) if self._blink_state else QColor(70, 120, 220, 200)
        painter.fillRect(text_rect, color)
        
        painter.setPen(QPen(QColor(255, 255, 255)))
        
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(text_rect.adjusted(10, 10, -10, -text_height + 30), Qt.AlignLeft, title)
        
        content_font = QFont()
        content_font.setPointSize(10)
        painter.setFont(content_font)
        painter.drawText(text_rect.adjusted(10, 35, -10, -10), Qt.AlignLeft | Qt.TextWordWrap, display_text)
    
    def _draw_hotkey_preview(self, painter: QPainter):
        keys = self._preview_data.get('keys', [])
        
        screen_center = self.rect().center()
        
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        painter.setFont(font)
        
        key_texts = []
        key_width = 0
        for key in keys:
            key_display = key.upper()
            if len(key_display) == 1:
                key_display = key_display
            key_texts.append(key_display)
            key_width += len(key_display) * 15 + 30
        
        total_width = key_width + 40
        total_height = 60
        
        bg_rect = QRect(
            screen_center.x() - total_width // 2,
            screen_center.y() - total_height // 2,
            total_width,
            total_height
        )
        
        color = QColor(100, 50, 200, 230) if self._blink_state else QColor(120, 70, 220, 200)
        painter.fillRect(bg_rect, color)
        
        painter.setPen(QPen(QColor(255, 255, 255)))
        
        x_offset = bg_rect.left() + 20
        for i, key_text in enumerate(key_texts):
            key_rect = QRect(x_offset, bg_rect.top() + 15, len(key_text) * 15 + 20, 30)
            
            painter.fillRect(key_rect, QColor(255, 255, 255, 50))
            painter.drawRect(key_rect)
            painter.drawText(key_rect, Qt.AlignCenter, key_text)
            
            x_offset += key_rect.width() + 5
            
            if i < len(key_texts) - 1:
                plus_rect = QRect(x_offset, bg_rect.top() + 20, 15, 20)
                painter.drawText(plus_rect, Qt.AlignCenter, "+")
                x_offset += 20
    
    def _draw_action_group_preview(self, painter: QPainter):
        group_name = self._preview_data.get('group_name', '未知')
        action_count = self._preview_data.get('action_count', 0)
        description = self._preview_data.get('description', '')
        
        screen_center = self.rect().center()
        
        font = QFont()
        font.setPointSize(12)
        painter.setFont(font)
        
        title_text = f"📁 动作组: {group_name}"
        count_text = f"包含 {action_count} 个动作"
        desc_text = description[:50] + "..." if len(description) > 50 else description
        
        max_width = max(len(title_text) * 12, len(count_text) * 10, len(desc_text) * 10) + 60
        total_width = max(max_width, 300)
        total_height = 120 if description else 90
        
        bg_rect = QRect(
            screen_center.x() - total_width // 2,
            screen_center.y() - total_height // 2,
            total_width,
            total_height
        )
        
        color = QColor(76, 175, 80, 230) if self._blink_state else QColor(100, 200, 100, 200)
        painter.fillRect(bg_rect, color)
        
        painter.setPen(QPen(QColor(255, 255, 255)))
        
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(bg_rect.adjusted(15, 15, -15, -total_height + 40), Qt.AlignLeft, title_text)
        
        content_font = QFont()
        content_font.setPointSize(11)
        painter.setFont(content_font)
        painter.drawText(bg_rect.adjusted(15, 45, -15, -total_height + 70), Qt.AlignLeft, count_text)
        
        if description:
            desc_font = QFont()
            desc_font.setPointSize(10)
            painter.setFont(desc_font)
            painter.setPen(QPen(QColor(220, 220, 220)))
            painter.drawText(bg_rect.adjusted(15, 75, -15, -10), Qt.AlignLeft | Qt.TextWordWrap, desc_text)
