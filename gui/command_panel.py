import subprocess
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLayout
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from typing import Optional

from qfluentwidgets import (
    CardWidget, BodyLabel, StrongBodyLabel,
    PushButton, PrimaryPushButton, LineEdit, TransparentToolButton,
    FluentIcon, InfoBar, InfoBarPosition, MessageBox, IconWidget,
    SubtitleLabel, CaptionLabel, ScrollArea,
    TitleLabel, RoundMenu, Action,
)

from core.command_manager import CommandManager, LaunchCommand
from .fluent_theme import (
    muted_caption_style,
    list_item_card_style, setting_form_style,
    create_compact_float_spin, SettingFormGrid,
)


class CommandCard(CardWidget):
    execute_requested = pyqtSignal(str)
    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)

    def __init__(self, command: LaunchCommand, parent=None):
        super().__init__(parent)
        self._command = command
        self.setStyleSheet(list_item_card_style())
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 12, 10)
        layout.setSpacing(12)

        icon_widget = IconWidget(FluentIcon.APPLICATION)
        icon_widget.setFixedSize(32, 32)
        layout.addWidget(icon_widget)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name_label = StrongBodyLabel(self._command.name)
        info_layout.addWidget(name_label)

        cmd_text = self._command.command
        if len(cmd_text) > 56:
            cmd_text = cmd_text[:53] + "..."
        cmd_label = CaptionLabel(cmd_text)
        cmd_label.setStyleSheet(muted_caption_style())
        info_layout.addWidget(cmd_label)

        meta_parts = []
        if self._command.window_title_pattern:
            meta_parts.append(self._command.window_title_pattern[:24])
        if self._command.description:
            meta_parts.append(self._command.description[:24])
        if self._command.use_count > 0:
            meta_parts.append(f"使用 {self._command.use_count} 次")
        if self._command.last_used:
            from datetime import datetime
            try:
                last_used = datetime.fromisoformat(self._command.last_used)
                meta_parts.append(last_used.strftime("%m-%d %H:%M"))
            except ValueError:
                pass
        if meta_parts:
            meta_label = CaptionLabel(" · ".join(meta_parts))
            meta_label.setStyleSheet(muted_caption_style("font-size: 11px;"))
            info_layout.addWidget(meta_label)

        layout.addLayout(info_layout, 1)

        self._run_btn = PrimaryPushButton(FluentIcon.PLAY, "启动")
        self._run_btn.setFixedHeight(28)
        self._run_btn.clicked.connect(lambda: self.execute_requested.emit(self._command.id))
        layout.addWidget(self._run_btn)

        self._more_btn = TransparentToolButton(FluentIcon.MORE)
        self._more_btn.setFixedSize(24, 24)
        self._more_btn.clicked.connect(self._show_menu)
        layout.addWidget(self._more_btn)

        self.setMinimumHeight(64)
        self.setMaximumHeight(80)

    def _show_menu(self):
        menu = RoundMenu(parent=self)
        menu.addAction(Action(
            FluentIcon.EDIT, "编辑", self,
            triggered=lambda: self.edit_requested.emit(self._command.id),
        ))
        menu.addAction(Action(
            FluentIcon.DELETE, "删除", self,
            triggered=lambda: self.delete_requested.emit(self._command.id),
        ))
        menu.exec(self._more_btn.mapToGlobal(self._more_btn.rect().bottomLeft()))

    def get_command_id(self) -> str:
        return self._command.id


class FormCard(CardWidget):
    save_requested = pyqtSignal(str, str, str, str, float)
    cancel_requested = pyqtSignal()
    pick_window_requested = pyqtSignal()
    test_command_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._editing_id: Optional[str] = None
        self._timer_seconds = 0.0
        self._timer_active = False
        self._test_process = None
        self.setObjectName("settingFormCard")
        self.setStyleSheet(setting_form_style())
        self._setup_ui()

    def _field_host(self, layout: QHBoxLayout) -> QWidget:
        host = QWidget()
        host.setLayout(layout)
        lay = layout
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        return host

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

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

        form_grid = SettingFormGrid()

        self._name_edit = LineEdit()
        self._name_edit.setPlaceholderText("命令名称，如：记事本")
        self._name_edit.setClearButtonEnabled(True)
        self._name_edit.setFixedHeight(32)
        form_grid.add_row("名称", self._name_edit)

        self._cmd_edit = LineEdit()
        self._cmd_edit.setPlaceholderText("启动命令或路径，如：notepad.exe")
        self._cmd_edit.setClearButtonEnabled(True)
        self._cmd_edit.setFixedHeight(32)
        form_grid.add_row("命令", self._cmd_edit)

        window_row = QHBoxLayout()
        self._window_edit = LineEdit()
        self._window_edit.setPlaceholderText("窗口标题关键字（检测是否已启动）")
        self._window_edit.setClearButtonEnabled(True)
        self._window_edit.setFixedHeight(32)
        window_row.addWidget(self._window_edit, 1)
        self._pick_btn = PushButton(FluentIcon.SETTING, "拾取")
        self._pick_btn.setFixedHeight(32)
        self._pick_btn.clicked.connect(self.pick_window_requested.emit)
        window_row.addWidget(self._pick_btn)
        form_grid.add_row("窗口", self._field_host(window_row))

        delay_row = QHBoxLayout()
        self._delay_spin = create_compact_float_spin(0, 300, 0, step=0.5, suffix="s", width=88)
        delay_row.addWidget(self._delay_spin)
        self._test_btn = PushButton(FluentIcon.PLAY, "测试计时")
        self._test_btn.setFixedHeight(28)
        self._test_btn.clicked.connect(self._test_command)
        delay_row.addWidget(self._test_btn)
        delay_row.addStretch()
        form_grid.add_row("延迟", self._field_host(delay_row))

        self._desc_edit = LineEdit()
        self._desc_edit.setPlaceholderText("可选描述")
        self._desc_edit.setClearButtonEnabled(True)
        self._desc_edit.setFixedHeight(32)
        form_grid.add_row("描述", self._desc_edit)

        layout.addWidget(form_grid)

        tip_label = CaptionLabel("测试计时：执行命令后再次点击可停止并自动填入延迟")
        tip_label.setStyleSheet(muted_caption_style())
        layout.addWidget(tip_label)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._save_btn = PrimaryPushButton(FluentIcon.SAVE, "保存")
        self._save_btn.setFixedHeight(32)
        self._save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self._save_btn)
        layout.addLayout(btn_layout)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_timer)

    def _test_command(self):
        command = self._cmd_edit.text().strip()
        if not command:
            InfoBar.warning(
                title="请输入命令",
                content="请先输入启动命令",
                parent=self,
                position=InfoBarPosition.TOP,
            )
            return

        if self._timer_active:
            self._timer.stop()
            self._timer_active = False
            self._test_btn.setText("测试计时")
            if self._test_process:
                try:
                    self._test_process.terminate()
                except OSError:
                    pass
                self._test_process = None
            self._delay_spin.setValue(self._timer_seconds)
            InfoBar.success(
                title="计时完成",
                content=f"已记录延迟: {self._timer_seconds:.1f} 秒",
                parent=self,
                position=InfoBarPosition.TOP,
            )
            return

        self._timer_seconds = 0.0
        self._test_process = subprocess.Popen(command, shell=True)
        self._timer_active = True
        self._test_btn.setText("停止")
        self._timer.start(100)

    def _update_timer(self):
        self._timer_seconds += 0.1

    def _on_save(self):
        name = self._name_edit.text().strip()
        command = self._cmd_edit.text().strip()
        pattern = self._window_edit.text().strip()
        description = self._desc_edit.text().strip()
        delay = self._delay_spin.value()
        self.save_requested.emit(name, command, pattern, description, delay)

    def set_editing(self, cmd: LaunchCommand):
        self._editing_id = cmd.id
        self._form_icon.setIcon(FluentIcon.EDIT)
        self._form_title.setText("编辑命令")
        self._name_edit.setText(cmd.name)
        self._cmd_edit.setText(cmd.command)
        self._window_edit.setText(cmd.window_title_pattern)
        self._desc_edit.setText(cmd.description)
        self._delay_spin.setValue(cmd.delay_after_launch)

    def set_adding(self):
        self._editing_id = None
        self._form_icon.setIcon(FluentIcon.ADD)
        self._form_title.setText("添加新命令")
        self._name_edit.clear()
        self._cmd_edit.clear()
        self._window_edit.clear()
        self._desc_edit.clear()
        self._delay_spin.setValue(0)

    def get_editing_id(self) -> Optional[str]:
        return self._editing_id

    def clear(self):
        self._name_edit.clear()
        self._cmd_edit.clear()
        self._window_edit.clear()
        self._desc_edit.clear()
        self._delay_spin.setValue(0)
        self._editing_id = None
        if self._timer_active:
            self._timer.stop()
            self._timer_active = False
            self._test_btn.setText("测试计时")


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
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_row = QHBoxLayout()
        title_icon = IconWidget(FluentIcon.COMMAND_PROMPT)
        title_icon.setFixedSize(22, 22)
        title_row.addWidget(title_icon)
        title_row.addWidget(TitleLabel("启动命令"))
        title_col.addLayout(title_row)
        subtitle = CaptionLabel("管理常用程序与窗口的快速启动")
        subtitle.setStyleSheet(muted_caption_style())
        title_col.addWidget(subtitle)
        header.addLayout(title_col)
        header.addStretch()

        self._add_btn = PrimaryPushButton(FluentIcon.ADD, "添加")
        self._add_btn.setFixedHeight(32)
        self._add_btn.clicked.connect(self._show_add_form)
        header.addWidget(self._add_btn)
        layout.addLayout(header)

        self._form_card = FormCard()
        self._form_card.setVisible(False)
        self._form_card.save_requested.connect(self._save_command)
        self._form_card.cancel_requested.connect(self._hide_form)
        self._form_card.pick_window_requested.connect(self._on_pick_window)
        layout.addWidget(self._form_card)

        scroll_area = ScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(scroll_content)
        self._list_layout.setContentsMargins(0, 4, 0, 8)
        self._list_layout.setSpacing(8)

        self._empty_widget = self._create_empty_widget()
        self._list_layout.addWidget(self._empty_widget)
        self._list_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area, 1)

    def _create_empty_widget(self) -> QWidget:
        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 48, 24, 48)
        layout.setSpacing(12)

        icon = IconWidget(FluentIcon.APPLICATION)
        icon.setFixedSize(48, 48)
        layout.addWidget(icon, 0, Qt.AlignCenter)

        title = SubtitleLabel("暂无启动命令")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        desc = CaptionLabel("点击「添加」创建命令，用于快速启动常用程序")
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet(muted_caption_style())
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
        self._selected_window = {'hwnd': hwnd, 'title': title, 'process': process}
        self._form_card._name_edit.setText(title)
        self._form_card._cmd_edit.setText(process)
        self._form_card._window_edit.setText(title)
        InfoBar.success(
            title="窗口已选择",
            content=f"已选择: {title}",
            parent=self,
            position=InfoBarPosition.TOP,
        )
        self._stop_pick()

    def _get_process_name(self, hwnd: int) -> str:
        try:
            import win32process
            import psutil
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return psutil.Process(pid).name()
        except Exception:
            return ""

    def _save_command(self, name: str, command: str, pattern: str, description: str, delay: float):
        if not name:
            InfoBar.warning(
                title="请输入名称",
                content="命令名称不能为空",
                parent=self,
                position=InfoBarPosition.TOP,
            )
            return
        if not command:
            InfoBar.warning(
                title="请输入命令",
                content="启动命令不能为空",
                parent=self,
                position=InfoBarPosition.TOP,
            )
            return

        editing_id = self._form_card.get_editing_id()
        if editing_id:
            success = self._command_manager.update_command(
                editing_id,
                name=name,
                command=command,
                window_title_pattern=pattern,
                description=description,
                delay_after_launch=delay,
            )
            if success:
                InfoBar.success(
                    title="更新成功",
                    content=f"命令 \"{name}\" 已更新",
                    parent=self,
                    position=InfoBarPosition.TOP,
                )
        else:
            cmd = self._command_manager.add_command(name, command, pattern, description, delay)
            if cmd:
                InfoBar.success(
                    title="添加成功",
                    content=f"命令 \"{name}\" 已添加",
                    parent=self,
                    position=InfoBarPosition.TOP,
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
                duration=2000,
            )
        elif success:
            InfoBar.success(
                title="启动成功",
                content=f"{cmd_name} 已启动",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000,
            )
        else:
            InfoBar.error(
                title="启动失败",
                content=message,
                parent=self,
                position=InfoBarPosition.TOP,
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
                position=InfoBarPosition.TOP,
            )
            self._load_commands()

    def refresh(self):
        self._load_commands()
