from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QSpacerItem, QSizePolicy, QScrollArea, QFrame, QStackedWidget
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QColor, QFont
from typing import Optional, List

from qfluentwidgets import (
    CardWidget, ElevatedCardWidget, BodyLabel, StrongBodyLabel, 
    PushButton, PrimaryPushButton, LineEdit, TransparentToolButton, 
    FluentIcon, InfoBar, InfoBarPosition, MessageBox, IconWidget,
    SubtitleLabel, CaptionLabel, ScrollArea, SimpleCardWidget,
    TitleLabel, isDarkTheme, themeColor, HeaderCardWidget
)

from core.command_manager import CommandManager, LaunchCommand


class CommandCard(CardWidget):
    execute_requested = pyqtSignal(str)
    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    
    def __init__(self, command: LaunchCommand, parent=None):
        super().__init__(parent)
        self._command = command
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 20, 20, 20)
        layout.setSpacing(20)
        
        icon_container = QWidget()
        icon_container.setFixedSize(56, 56)
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        
        icon_widget = IconWidget(FluentIcon.APPLICATION)
        icon_widget.setFixedSize(36, 36)
        icon_layout.addWidget(icon_widget, 0, Qt.AlignCenter)
        
        layout.addWidget(icon_container)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)
        
        name_row = QHBoxLayout()
        name_label = SubtitleLabel(self._command.name)
        name_row.addWidget(name_label)
        name_row.addStretch()
        info_layout.addLayout(name_row)
        
        cmd_row = QHBoxLayout()
        cmd_row.setSpacing(8)
        
        cmd_icon = IconWidget(FluentIcon.CODE)
        cmd_icon.setFixedSize(14, 14)
        cmd_row.addWidget(cmd_icon)
        
        cmd_text = self._command.command
        if len(cmd_text) > 50:
            cmd_text = cmd_text[:47] + "..."
        self._cmd_label = StrongBodyLabel(cmd_text)
        self._cmd_label.setStyleSheet("color: #666;")
        cmd_row.addWidget(self._cmd_label)
        cmd_row.addStretch()
        info_layout.addLayout(cmd_row)
        
        if self._command.description or self._command.window_title_pattern:
            extra_row = QHBoxLayout()
            extra_row.setSpacing(12)
            
            if self._command.window_title_pattern:
                window_icon = IconWidget(FluentIcon.SETTING)
                window_icon.setFixedSize(14, 14)
                extra_row.addWidget(window_icon)
                window_label = StrongBodyLabel(self._command.window_title_pattern[:30])
                window_label.setStyleSheet("color: #888;")
                extra_row.addWidget(window_label)
            
            if self._command.description and self._command.window_title_pattern:
                sep = StrongBodyLabel("·")
                sep.setStyleSheet("color: #888;")
                extra_row.addWidget(sep)
            
            if self._command.description:
                desc_label = StrongBodyLabel(self._command.description[:30])
                desc_label.setStyleSheet("color: #888;")
                extra_row.addWidget(desc_label)
            
            extra_row.addStretch()
            info_layout.addLayout(extra_row)
        
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)
        
        if self._command.use_count > 0:
            count_icon = IconWidget(FluentIcon.PIN)
            count_icon.setFixedSize(14, 14)
            stats_row.addWidget(count_icon)
            count_label = StrongBodyLabel(f"使用 {self._command.use_count} 次")
            count_label.setStyleSheet("color: #888;")
            stats_row.addWidget(count_label)
        
        if self._command.last_used:
            from datetime import datetime
            try:
                last_used = datetime.fromisoformat(self._command.last_used)
                time_str = last_used.strftime("%m-%d %H:%M")
                time_icon = IconWidget(FluentIcon.STOP_WATCH)
                time_icon.setFixedSize(14, 14)
                stats_row.addWidget(time_icon)
                time_label = StrongBodyLabel(f"最近 {time_str}")
                time_label.setStyleSheet("color: #888;")
                stats_row.addWidget(time_label)
            except:
                pass
        
        stats_row.addStretch()
        info_layout.addLayout(stats_row)
        
        layout.addLayout(info_layout, 1)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self._run_btn = PrimaryPushButton(FluentIcon.PLAY, "启动")
        self._run_btn.setFixedHeight(44)
        self._run_btn.clicked.connect(lambda: self.execute_requested.emit(self._command.id))
        btn_layout.addWidget(self._run_btn)
        
        self._edit_btn = TransparentToolButton(FluentIcon.EDIT)
        self._edit_btn.setFixedSize(44, 44)
        self._edit_btn.clicked.connect(lambda: self.edit_requested.emit(self._command.id))
        btn_layout.addWidget(self._edit_btn)
        
        self._delete_btn = TransparentToolButton(FluentIcon.DELETE)
        self._delete_btn.setFixedSize(44, 44)
        self._delete_btn.clicked.connect(lambda: self.delete_requested.emit(self._command.id))
        btn_layout.addWidget(self._delete_btn)
        
        layout.addLayout(btn_layout)
        
        self.setMinimumHeight(120)
    
    def get_command_id(self) -> str:
        return self._command.id


class FormCard(CardWidget):
    save_requested = pyqtSignal(str, str, str, str)
    cancel_requested = pyqtSignal()
    pick_window_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._editing_id: Optional[str] = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(24)
        
        header_layout = QHBoxLayout()
        
        self._form_icon = IconWidget(FluentIcon.ADD)
        self._form_icon.setFixedSize(32, 32)
        header_layout.addWidget(self._form_icon)
        
        self._form_title = SubtitleLabel("添加新命令")
        header_layout.addWidget(self._form_title)
        
        header_layout.addStretch()
        
        self._cancel_btn = TransparentToolButton(FluentIcon.CANCEL)
        self._cancel_btn.setFixedSize(40, 40)
        self._cancel_btn.clicked.connect(self.cancel_requested.emit)
        header_layout.addWidget(self._cancel_btn)
        
        layout.addLayout(header_layout)
        
        form_layout = QVBoxLayout()
        form_layout.setSpacing(20)
        
        name_row = QHBoxLayout()
        name_label = BodyLabel("名称")
        name_label.setFixedWidth(100)
        name_row.addWidget(name_label)
        self._name_edit = LineEdit()
        self._name_edit.setPlaceholderText("输入命令名称，如：记事本")
        self._name_edit.setClearButtonEnabled(True)
        self._name_edit.setMinimumHeight(44)
        name_row.addWidget(self._name_edit)
        form_layout.addLayout(name_row)
        
        cmd_row = QHBoxLayout()
        cmd_label = BodyLabel("命令")
        cmd_label.setFixedWidth(100)
        cmd_row.addWidget(cmd_label)
        self._cmd_edit = LineEdit()
        self._cmd_edit.setPlaceholderText("输入启动命令或程序路径，如：notepad.exe")
        self._cmd_edit.setClearButtonEnabled(True)
        self._cmd_edit.setMinimumHeight(44)
        cmd_row.addWidget(self._cmd_edit)
        form_layout.addLayout(cmd_row)
        
        window_row = QHBoxLayout()
        window_label = BodyLabel("窗口标识")
        window_label.setFixedWidth(100)
        window_row.addWidget(window_label)
        self._window_edit = LineEdit()
        self._window_edit.setPlaceholderText("窗口标题关键字（用于检测是否已启动）")
        self._window_edit.setClearButtonEnabled(True)
        self._window_edit.setMinimumHeight(44)
        window_row.addWidget(self._window_edit)
        
        self._pick_btn = PushButton(FluentIcon.SETTING, "拾取")
        self._pick_btn.setFixedHeight(44)
        self._pick_btn.clicked.connect(self.pick_window_requested.emit)
        window_row.addWidget(self._pick_btn)
        form_layout.addLayout(window_row)
        
        desc_row = QHBoxLayout()
        desc_label = BodyLabel("描述")
        desc_label.setFixedWidth(100)
        desc_row.addWidget(desc_label)
        self._desc_edit = LineEdit()
        self._desc_edit.setPlaceholderText("可选描述信息")
        self._desc_edit.setClearButtonEnabled(True)
        self._desc_edit.setMinimumHeight(44)
        desc_row.addWidget(self._desc_edit)
        form_layout.addLayout(desc_row)
        
        layout.addLayout(form_layout)
        
        tip_label = StrongBodyLabel("提示：点击\"拾取\"按钮可自动获取窗口信息")
        tip_label.setStyleSheet("color: #888;")
        layout.addWidget(tip_label)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self._save_btn = PrimaryPushButton(FluentIcon.SAVE, "保存")
        self._save_btn.setFixedHeight(44)
        self._save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self._save_btn)
        
        layout.addLayout(btn_layout)
    
    def _on_save(self):
        name = self._name_edit.text().strip()
        command = self._cmd_edit.text().strip()
        pattern = self._window_edit.text().strip()
        description = self._desc_edit.text().strip()
        self.save_requested.emit(name, command, pattern, description)
    
    def set_editing(self, cmd: LaunchCommand):
        self._editing_id = cmd.id
        self._form_icon.setIcon(FluentIcon.EDIT)
        self._form_title.setText("编辑命令")
        self._name_edit.setText(cmd.name)
        self._cmd_edit.setText(cmd.command)
        self._window_edit.setText(cmd.window_title_pattern)
        self._desc_edit.setText(cmd.description)
    
    def set_adding(self):
        self._editing_id = None
        self._form_icon.setIcon(FluentIcon.ADD)
        self._form_title.setText("添加新命令")
        self._name_edit.clear()
        self._cmd_edit.clear()
        self._window_edit.clear()
        self._desc_edit.clear()
    
    def get_editing_id(self) -> Optional[str]:
        return self._editing_id
    
    def clear(self):
        self._name_edit.clear()
        self._cmd_edit.clear()
        self._window_edit.clear()
        self._desc_edit.clear()
        self._editing_id = None


class CommandManagerWidget(QWidget):
    command_executed = pyqtSignal(bool, str)
    _window_picked = pyqtSignal(int, str, str)
    
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
        
        header = QWidget()
        header.setFixedHeight(100)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(32, 0, 32, 0)
        
        title_section = QVBoxLayout()
        title_section.setSpacing(8)
        
        title_row = QHBoxLayout()
        title_icon = IconWidget(FluentIcon.COMMAND_PROMPT)
        title_icon.setFixedSize(32, 32)
        title_row.addWidget(title_icon)
        
        title_label = TitleLabel("启动命令")
        title_row.addWidget(title_label)
        title_section.addLayout(title_row)
        
        subtitle = StrongBodyLabel("管理常用程序和窗口的快速启动命令")
        subtitle.setStyleSheet("color: #666;")
        title_section.addWidget(subtitle)
        
        header_layout.addLayout(title_section)
        header_layout.addStretch()
        
        self._add_btn = PrimaryPushButton(FluentIcon.ADD, "添加命令")
        self._add_btn.setFixedHeight(44)
        self._add_btn.clicked.connect(self._show_add_form)
        header_layout.addWidget(self._add_btn)
        
        layout.addWidget(header)
        
        self._form_card = FormCard()
        self._form_card.setVisible(False)
        self._form_card.save_requested.connect(self._save_command)
        self._form_card.cancel_requested.connect(self._hide_form)
        self._form_card.pick_window_requested.connect(self._on_pick_window)
        
        form_container = QWidget()
        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(32, 0, 32, 20)
        form_layout.addWidget(self._form_card)
        layout.addWidget(form_container)
        
        scroll_area = ScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(scroll_content)
        self._list_layout.setContentsMargins(32, 10, 32, 32)
        self._list_layout.setSpacing(10)
        
        self._empty_widget = self._create_empty_widget()
        self._list_layout.addWidget(self._empty_widget)
        self._list_layout.addStretch()
        
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area, 1)
    
    def _create_empty_widget(self) -> QWidget:
        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(40, 60, 40, 60)
        layout.setSpacing(18)
        
        icon = IconWidget(FluentIcon.APPLICATION)
        icon.setFixedSize(64, 64)
        layout.addWidget(icon, 0, Qt.AlignCenter)
        
        title = SubtitleLabel("暂无启动命令")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        desc = StrongBodyLabel("点击上方\"添加命令\"按钮创建新命令\n用于快速启动常用程序和窗口")
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("color: #888;")
        layout.addWidget(desc)
        
        return widget
    
    def _load_commands(self):
        while self._list_layout.count() > 2:
            item = self._list_layout.takeAt(1)
            if item.widget() and item.widget() != self._empty_widget:
                item.widget().deleteLater()
        
        commands = self._command_manager.get_all_commands()
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
        self._form_card._name_edit.setFocus()
    
    def _hide_form(self):
        self._form_card.setVisible(False)
        self._form_card.clear()
    
    def _on_pick_window(self):
        self._form_card._pick_btn.setText("拾取中...")
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
        self._form_card._pick_btn.setText("拾取")
    
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
        
        self._form_card._name_edit.setText(title)
        self._form_card._cmd_edit.setText(process)
        self._form_card._window_edit.setText(title)
        
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
        self._form_card._name_edit.setFocus()
    
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
