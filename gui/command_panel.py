from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QSpacerItem, QSizePolicy, QScrollArea, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QColor
from typing import Optional, List

from qfluentwidgets import (
    CardWidget, ElevatedCardWidget, BodyLabel, StrongBodyLabel, 
    PushButton, PrimaryPushButton, LineEdit, TransparentToolButton, 
    FluentIcon, InfoBar, InfoBarPosition, MessageBox, IconWidget,
    SubtitleLabel, CaptionLabel, ScrollArea, SimpleCardWidget,
    isDarkTheme, themeColor
)

from core.command_manager import CommandManager, LaunchCommand


class CommandCard(ElevatedCardWidget):
    execute_requested = pyqtSignal(str)
    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    
    def __init__(self, command: LaunchCommand, parent=None):
        super().__init__(parent)
        self._command = command
        self._hover_animation = None
        self._setup_ui()
    
    def _setup_ui(self):
        self._update_style()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)
        
        icon_widget = IconWidget(FluentIcon.APPLICATION)
        icon_widget.setFixedSize(40, 40)
        layout.addWidget(icon_widget)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)
        
        name_label = StrongBodyLabel(self._command.name)
        info_layout.addWidget(name_label)
        
        cmd_container = QHBoxLayout()
        cmd_container.setSpacing(4)
        
        cmd_icon = IconWidget(FluentIcon.CODE)
        cmd_icon.setFixedSize(14, 14)
        cmd_container.addWidget(cmd_icon)
        
        self._cmd_label = CaptionLabel(self._command.command)
        self._cmd_label.setWordWrap(True)
        cmd_container.addWidget(self._cmd_label, 1)
        
        info_layout.addLayout(cmd_container)
        
        if self._command.description:
            self._desc_label = CaptionLabel(self._command.description)
            self._desc_label.setWordWrap(True)
            info_layout.addWidget(self._desc_label)
        else:
            self._desc_label = None
        
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)
        
        from datetime import datetime
        self._time_label = None
        self._count_label = None
        
        if self._command.last_used:
            try:
                last_used = datetime.fromisoformat(self._command.last_used)
                time_str = last_used.strftime("%m-%d %H:%M")
                self._time_label = CaptionLabel(f"最近使用: {time_str}")
                stats_layout.addWidget(self._time_label)
            except:
                pass
        
        if self._command.use_count > 0:
            self._count_label = CaptionLabel(f"使用 {self._command.use_count} 次")
            stats_layout.addWidget(self._count_label)
        
        stats_layout.addStretch()
        info_layout.addLayout(stats_layout)
        
        layout.addLayout(info_layout, 1)
        
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)
        
        self._run_btn = PrimaryPushButton("  启动  ")
        self._run_btn.setFixedHeight(36)
        self._run_btn.clicked.connect(lambda: self.execute_requested.emit(self._command.id))
        btn_layout.addWidget(self._run_btn)
        
        action_btn_layout = QHBoxLayout()
        action_btn_layout.setSpacing(4)
        
        self._edit_btn = TransparentToolButton(FluentIcon.EDIT)
        self._edit_btn.setFixedSize(28, 28)
        self._edit_btn.clicked.connect(lambda: self.edit_requested.emit(self._command.id))
        action_btn_layout.addWidget(self._edit_btn)
        
        self._delete_btn = TransparentToolButton(FluentIcon.DELETE)
        self._delete_btn.setFixedSize(28, 28)
        self._delete_btn.clicked.connect(lambda: self.delete_requested.emit(self._command.id))
        action_btn_layout.addWidget(self._delete_btn)
        
        btn_layout.addLayout(action_btn_layout)
        
        layout.addLayout(btn_layout)
    
    def _update_style(self):
        if isDarkTheme():
            self.setStyleSheet("""
                CommandCard {
                    background-color: rgba(45, 45, 45, 0.9);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 12px;
                }
            """)
        else:
            self.setStyleSheet("""
                CommandCard {
                    background-color: rgba(255, 255, 255, 0.9);
                    border: 1px solid rgba(0, 0, 0, 0.05);
                    border-radius: 12px;
                }
            """)
    
    def paintEvent(self, event):
        self._update_style()
        super().paintEvent(event)
    
    def get_command_id(self) -> str:
        return self._command.id


class FormCard(ElevatedCardWidget):
    save_requested = pyqtSignal(str, str, str, str)
    cancel_requested = pyqtSignal()
    pick_window_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._editing_id: Optional[str] = None
        self._setup_ui()
    
    def _setup_ui(self):
        self._update_style()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        header_layout = QHBoxLayout()
        
        self._form_icon = IconWidget(FluentIcon.ADD)
        self._form_icon.setFixedSize(24, 24)
        header_layout.addWidget(self._form_icon)
        
        self._form_title = SubtitleLabel("添加新命令")
        header_layout.addWidget(self._form_title)
        
        header_layout.addStretch()
        
        self._cancel_btn = TransparentToolButton(FluentIcon.CANCEL)
        self._cancel_btn.setFixedSize(28, 28)
        self._cancel_btn.clicked.connect(self.cancel_requested.emit)
        header_layout.addWidget(self._cancel_btn)
        
        layout.addLayout(header_layout)
        
        form_grid = QGridLayout()
        form_grid.setSpacing(12)
        form_grid.setColumnStretch(1, 1)
        
        labels = ["名称", "命令", "窗口标识", "描述"]
        placeholders = [
            "输入命令名称，如：记事本",
            "输入启动命令或程序路径，如：notepad.exe",
            "窗口标题关键字（用于检测是否已启动）",
            "可选描述信息"
        ]
        
        self._label_widgets = []
        self._edits = []
        
        for i, (label, placeholder) in enumerate(zip(labels, placeholders)):
            label_widget = BodyLabel(f"{label}:")
            label_widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            form_grid.addWidget(label_widget, i, 0)
            self._label_widgets.append(label_widget)
            
            if i == 2:
                row_layout = QHBoxLayout()
                row_layout.setSpacing(8)
                
                edit = LineEdit()
                edit.setPlaceholderText(placeholder)
                edit.setClearButtonEnabled(True)
                edit.setMinimumHeight(36)
                row_layout.addWidget(edit, 1)
                
                self._pick_btn = PushButton("拾取窗口")
                self._pick_btn.setFixedHeight(36)
                self._pick_btn.clicked.connect(self.pick_window_requested.emit)
                row_layout.addWidget(self._pick_btn)
                
                form_grid.addLayout(row_layout, i, 1)
            else:
                edit = LineEdit()
                edit.setPlaceholderText(placeholder)
                edit.setClearButtonEnabled(True)
                edit.setMinimumHeight(36)
                form_grid.addWidget(edit, i, 1)
            
            self._edits.append(edit)
        
        layout.addLayout(form_grid)
        
        tip_label = CaptionLabel("提示：点击\"拾取窗口\"可自动获取窗口标题作为窗口标识")
        tip_label.setStyleSheet("color: #888;")
        layout.addWidget(tip_label)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self._save_btn = PrimaryPushButton("  保存  ")
        self._save_btn.setFixedHeight(36)
        self._save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self._save_btn)
        
        layout.addLayout(btn_layout)
    
    def _update_style(self):
        if isDarkTheme():
            self.setStyleSheet("""
                FormCard {
                    background-color: rgba(45, 45, 45, 0.95);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 12px;
                }
            """)
        else:
            self.setStyleSheet("""
                FormCard {
                    background-color: rgba(255, 255, 255, 0.95);
                    border: 1px solid rgba(0, 120, 212, 0.15);
                    border-radius: 12px;
                }
            """)
    
    def paintEvent(self, event):
        self._update_style()
        super().paintEvent(event)
    
    def _on_save(self):
        name = self._edits[0].text().strip()
        command = self._edits[1].text().strip()
        pattern = self._edits[2].text().strip()
        description = self._edits[3].text().strip()
        self.save_requested.emit(name, command, pattern, description)
    
    def set_editing(self, cmd: LaunchCommand):
        self._editing_id = cmd.id
        self._form_icon.setIcon(FluentIcon.EDIT)
        self._form_title.setText("编辑命令")
        self._edits[0].setText(cmd.name)
        self._edits[1].setText(cmd.command)
        self._edits[2].setText(cmd.window_title_pattern)
        self._edits[3].setText(cmd.description)
    
    def set_adding(self):
        self._editing_id = None
        self._form_icon.setIcon(FluentIcon.ADD)
        self._form_title.setText("添加新命令")
        for edit in self._edits:
            edit.clear()
    
    def get_editing_id(self) -> Optional[str]:
        return self._editing_id
    
    def clear(self):
        for edit in self._edits:
            edit.clear()
        self._editing_id = None


class CommandManagerWidget(QWidget):
    command_executed = pyqtSignal(bool, str)
    _window_picked = pyqtSignal(int, str, str)  # hwnd, title, process
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._command_manager = CommandManager.get_instance()
        self._win32_available = self._check_win32()
        self._listener = None
        self._selected_window = None
        self._setup_ui()
        self._load_commands()
        
        self._window_picked.connect(self._on_window_picked)
    
    def _check_win32(self) -> bool:
        try:
            import win32gui
            return True
        except ImportError:
            return False
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self._header_card = SimpleCardWidget()
        self._update_header_style()
        
        header_layout = QHBoxLayout(self._header_card)
        header_layout.setContentsMargins(24, 16, 24, 16)
        header_layout.setSpacing(16)
        
        title_icon = IconWidget(FluentIcon.APPLICATION)
        title_icon.setFixedSize(28, 28)
        header_layout.addWidget(title_icon)
        
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        
        title_label = SubtitleLabel("启动命令管理")
        title_layout.addWidget(title_label)
        
        self._subtitle_label = CaptionLabel("管理常用程序和窗口的启动命令")
        title_layout.addWidget(self._subtitle_label)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        self._add_btn = PrimaryPushButton("  添加命令  ")
        self._add_btn.setFixedHeight(40)
        self._add_btn.clicked.connect(self._show_add_form)
        header_layout.addWidget(self._add_btn)
        
        layout.addWidget(self._header_card)
        
        self._form_card = FormCard()
        self._form_card.setVisible(False)
        self._form_card.save_requested.connect(self._save_command)
        self._form_card.cancel_requested.connect(self._hide_form)
        self._form_card.pick_window_requested.connect(self._on_pick_window)
        layout.addWidget(self._form_card)
        
        scroll_area = ScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        self._list_layout = QVBoxLayout(scroll_content)
        self._list_layout.setContentsMargins(24, 16, 24, 24)
        self._list_layout.setSpacing(12)
        self._list_layout.addStretch()
        
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area, 1)
        
        self._empty_widget = QWidget()
        self._empty_widget.setStyleSheet("background-color: transparent;")
        empty_layout = QVBoxLayout(self._empty_widget)
        empty_layout.setContentsMargins(24, 60, 24, 60)
        empty_layout.setSpacing(16)
        
        empty_icon = IconWidget(FluentIcon.APPLICATION)
        empty_icon.setFixedSize(64, 64)
        empty_layout.addWidget(empty_icon, 0, Qt.AlignCenter)
        
        self._empty_title = StrongBodyLabel("暂无启动命令")
        self._empty_title.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(self._empty_title)
        
        self._empty_desc = CaptionLabel("点击上方\"添加命令\"按钮创建新命令\n用于快速启动常用程序和窗口")
        self._empty_desc.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(self._empty_desc)
        
        empty_layout.addStretch()
        
        self._list_layout.insertWidget(0, self._empty_widget)
    
    def _update_header_style(self):
        if isDarkTheme():
            self._header_card.setStyleSheet("""
                SimpleCardWidget {
                    background-color: rgba(40, 40, 40, 0.95);
                    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
                }
            """)
        else:
            self._header_card.setStyleSheet("""
                SimpleCardWidget {
                    background-color: rgba(248, 249, 250, 0.95);
                    border-bottom: 1px solid rgba(0, 0, 0, 0.08);
                }
            """)
    
    def paintEvent(self, event):
        self._update_header_style()
        super().paintEvent(event)
    
    def _load_commands(self):
        commands = self._command_manager.get_all_commands()
        
        while self._list_layout.count() > 2:
            item = self._list_layout.takeAt(1)
            if item.widget() and item.widget() != self._empty_widget:
                item.widget().deleteLater()
        
        self._empty_widget.setVisible(len(commands) == 0)
        
        for cmd in sorted(commands, key=lambda x: x.use_count, reverse=True):
            card = CommandCard(cmd)
            card.execute_requested.connect(self._on_execute)
            card.edit_requested.connect(self._on_edit)
            card.delete_requested.connect(self._on_delete)
            self._list_layout.insertWidget(self._list_layout.count() - 1, card)
    
    def _show_add_form(self):
        self._form_card.set_adding()
        self._form_card.setVisible(True)
        self._form_card._edits[0].setFocus()
    
    def _hide_form(self):
        self._form_card.setVisible(False)
        self._form_card.clear()
    
    def _on_pick_window(self):
        self._form_card._pick_btn.setText("拾取中...")
        self._form_card._pick_btn.setChecked(True)
        self._start_pick()
    
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
        self._form_card._pick_btn.setChecked(False)
        self._form_card._pick_btn.setText("拾取窗口")
    
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
            
            title = win32gui.GetWindowText(hwnd)
            process = self._get_process_name(hwnd)
            
            self._window_picked.emit(hwnd, title, process)
            
        except Exception:
            pass
    
    def _on_window_picked(self, hwnd: int, title: str, process: str):
        self._selected_window = {
            'hwnd': hwnd,
            'title': title,
            'process': process
        }
        
        self._form_card._edits[0].setText(title)
        self._form_card._edits[1].setText(process)
        self._form_card._edits[2].setText(title)
        
        InfoBar.success(
            title="窗口已选择",
            content=f"已选择窗口: {title}",
            parent=self,
            position=InfoBarPosition.TOP,
        )
        
        self._stop_pick()
    
    def _get_process_name(self, hwnd: int) -> str:
        try:
            import win32process
            import psutil
            
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            return process.name()
        except:
            return ""
    
    def _save_command(self, name: str, command: str, pattern: str, description: str):
        if not name:
            InfoBar.warning(
                title="请输入名称",
                content="命令名称不能为空",
                parent=self,
                position=InfoBarPosition.TOP
            )
            return
        
        if not command:
            InfoBar.warning(
                title="请输入命令",
                content="启动命令不能为空",
                parent=self,
                position=InfoBarPosition.TOP
            )
            return
        
        editing_id = self._form_card.get_editing_id()
        
        if editing_id:
            success = self._command_manager.update_command(
                editing_id,
                name=name,
                command=command,
                window_title_pattern=pattern,
                description=description
            )
            if success:
                InfoBar.success(
                    title="更新成功",
                    content=f"命令 \"{name}\" 已更新",
                    parent=self,
                    position=InfoBarPosition.TOP
                )
        else:
            cmd = self._command_manager.add_command(name, command, pattern, description)
            if cmd:
                InfoBar.success(
                    title="添加成功",
                    content=f"命令 \"{name}\" 已添加",
                    parent=self,
                    position=InfoBarPosition.TOP
                )
        
        self._hide_form()
        self._load_commands()
    
    def _on_execute(self, cmd_id: str):
        success, message, already_running = self._command_manager.check_and_launch(cmd_id)
        
        cmd = self._command_manager.get_command(cmd_id)
        cmd_name = cmd.name if cmd else "命令"
        
        if already_running:
            InfoBar.info(
                title="窗口已运行",
                content=f"{cmd_name} 的窗口已在运行中",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000
            )
        elif success:
            InfoBar.success(
                title="启动成功",
                content=f"{cmd_name} 已启动",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000
            )
        else:
            InfoBar.error(
                title="启动失败",
                content=message,
                parent=self,
                position=InfoBarPosition.TOP
            )
        
        self.command_executed.emit(success, message)
    
    def _on_edit(self, cmd_id: str):
        cmd = self._command_manager.get_command(cmd_id)
        if not cmd:
            return
        
        self._form_card.set_editing(cmd)
        self._form_card.setVisible(True)
        self._form_card._edits[0].setFocus()
    
    def _on_delete(self, cmd_id: str):
        cmd = self._command_manager.get_command(cmd_id)
        if not cmd:
            return
        
        box = MessageBox('确认删除', f'确定要删除命令 "{cmd.name}" 吗？', self)
        box.yesButton.setText('确定')
        box.cancelButton.setText('取消')
        
        if box.exec():
            self._command_manager.delete_command(cmd_id)
            InfoBar.success(
                title="删除成功",
                content=f"命令 \"{cmd.name}\" 已删除",
                parent=self,
                position=InfoBarPosition.TOP
            )
            self._load_commands()
    
    def refresh(self):
        self._load_commands()
