import os
import json
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QLabel, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from typing import Dict, Optional, List
from dataclasses import dataclass

from qfluentwidgets import (
    FluentIcon, PushButton, PrimaryPushButton, SpinBox, DoubleSpinBox,
    BodyLabel, StrongBodyLabel, ProgressBar, CardWidget, ElevatedCardWidget,
    CheckBox, SubtitleLabel, CaptionLabel, IconWidget, ScrollArea,
    TransparentToolButton, InfoBadge, TitleLabel, HeaderCardWidget,
    isDarkTheme, themeColor, SimpleCardWidget, InfoBar, InfoBarPosition,
    ComboBox, LineEdit, MessageBox
)

from core.actions import Action, ActionType
from core.player import Player, PlayerState
from core.exporter import Exporter
from core.command_manager import CommandManager
from utils.config import Config
from utils.window_utils import WindowUtils
from .widgets import WindowSelector


ACTION_ICONS = {
    ActionType.MOUSE_CLICK: FluentIcon.CARE_DOWN_SOLID,
    ActionType.MOUSE_DOUBLE_CLICK: FluentIcon.CARE_DOWN_SOLID,
    ActionType.MOUSE_RIGHT_CLICK: FluentIcon.CARE_DOWN_SOLID,
    ActionType.MOUSE_MOVE: FluentIcon.MOVE,
    ActionType.MOUSE_DRAG: FluentIcon.MOVE,
    ActionType.MOUSE_SCROLL: FluentIcon.SCROLL,
    ActionType.KEY_PRESS: FluentIcon.PENCIL_INK,
    ActionType.KEY_TYPE: FluentIcon.PENCIL_INK,
    ActionType.HOTKEY: FluentIcon.PENCIL_INK,
    ActionType.WAIT: FluentIcon.STOP_WATCH,
    ActionType.SCREENSHOT: FluentIcon.CAMERA,
    ActionType.MOUSE_MOVE_RELATIVE: FluentIcon.MOVE,
    ActionType.MOUSE_CLICK_RELATIVE: FluentIcon.CARE_DOWN_SOLID,
    ActionType.IMAGE_CLICK: FluentIcon.PHOTO,
    ActionType.IMAGE_WAIT_CLICK: FluentIcon.PHOTO,
    ActionType.IMAGE_CHECK: FluentIcon.PHOTO,
    ActionType.ACTION_GROUP_REF: FluentIcon.FOLDER,
}


@dataclass
class ScriptItem:
    id: str
    name: str
    path: str
    actions: List[Action] = None
    delay_before: float = 0.0
    repeat_count: int = 1
    enabled: bool = True
    
    def __post_init__(self):
        if self.actions is None:
            self.actions = []


class SubActionRow(QWidget):
    def __init__(self, action: Action, index: int, depth: int = 0, parent=None):
        super().__init__(parent)
        self._action = action
        self._index = index
        self._depth = depth
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(self._depth * 16 + 12, 4, 8, 4)
        layout.setSpacing(6)
        
        self._index_label = CaptionLabel(f"{self._index + 1}")
        self._index_label.setFixedWidth(16)
        self._index_label.setStyleSheet("color: #888;")
        layout.addWidget(self._index_label)
        
        icon = ACTION_ICONS.get(self._action.action_type, FluentIcon.PLAY)
        self._icon = IconWidget(icon, self)
        self._icon.setFixedSize(12, 12)
        layout.addWidget(self._icon)
        
        self._desc_label = CaptionLabel(self._action.description[:40])
        layout.addWidget(self._desc_label, 1)
        
        self.setFixedHeight(24)


class ScriptCard(CardWidget):
    run_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    move_up_requested = pyqtSignal(str)
    move_down_requested = pyqtSignal(str)
    toggle_enabled = pyqtSignal(str, bool)
    
    def __init__(self, item: ScriptItem, index: int, parent=None):
        super().__init__(parent)
        self._item = item
        self._index = index
        self._expanded = False
        self._sub_widgets: List[QWidget] = []
        self._is_running = False
        self._is_completed = False
        self._setup_ui()
    
    def _setup_ui(self):
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(16, 12, 12, 12)
        self._main_layout.setSpacing(0)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        
        self._index_label = TitleLabel(str(self._index + 1))
        self._index_label.setFixedWidth(28)
        header_layout.addWidget(self._index_label)
        
        icon_widget = IconWidget(FluentIcon.DOCUMENT, self)
        icon_widget.setFixedSize(20, 20)
        icon_widget.setStyleSheet("color: #0078D4;")
        header_layout.addWidget(icon_widget)
        
        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)
        
        self._name_label = StrongBodyLabel(self._item.name)
        content_layout.addWidget(self._name_label)
        
        info_parts = []
        if self._item.delay_before > 0:
            info_parts.append(f"等待 {self._item.delay_before}s")
        if self._item.repeat_count > 1:
            info_parts.append(f"重复 {self._item.repeat_count} 次")
        action_count = len(self._item.actions) if self._item.actions else 0
        info_parts.append(f"{action_count} 个动作")
        
        self._info_label = CaptionLabel("  •  ".join(info_parts))
        content_layout.addWidget(self._info_label)
        
        header_layout.addLayout(content_layout, 1)
        
        self._status_label = QLabel()
        self._status_label.setFixedSize(20, 20)
        self._status_label.setVisible(False)
        header_layout.addWidget(self._status_label)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)
        
        self._expand_btn = TransparentToolButton(FluentIcon.CARE_RIGHT_SOLID)
        self._expand_btn.setFixedSize(28, 28)
        self._expand_btn.setToolTip("展开/折叠")
        self._expand_btn.clicked.connect(self._toggle_expand)
        btn_layout.addWidget(self._expand_btn)
        
        self._run_btn = TransparentToolButton(FluentIcon.PLAY)
        self._run_btn.setFixedSize(28, 28)
        self._run_btn.setToolTip("执行此脚本")
        self._run_btn.clicked.connect(lambda: self.run_requested.emit(self._item.id))
        btn_layout.addWidget(self._run_btn)
        
        self._toggle_btn = TransparentToolButton(FluentIcon.CHECKBOX)
        self._toggle_btn.setFixedSize(28, 28)
        self._toggle_btn.setToolTip("启用/禁用")
        self._toggle_btn.clicked.connect(self._on_toggle)
        btn_layout.addWidget(self._toggle_btn)
        
        self._up_btn = TransparentToolButton(FluentIcon.UP)
        self._up_btn.setFixedSize(28, 28)
        self._up_btn.setToolTip("上移")
        self._up_btn.clicked.connect(lambda: self.move_up_requested.emit(self._item.id))
        btn_layout.addWidget(self._up_btn)
        
        self._down_btn = TransparentToolButton(FluentIcon.DOWN)
        self._down_btn.setFixedSize(28, 28)
        self._down_btn.setToolTip("下移")
        self._down_btn.clicked.connect(lambda: self.move_down_requested.emit(self._item.id))
        btn_layout.addWidget(self._down_btn)
        
        self._delete_btn = TransparentToolButton(FluentIcon.DELETE)
        self._delete_btn.setFixedSize(28, 28)
        self._delete_btn.setToolTip("移除")
        self._delete_btn.clicked.connect(lambda: self.delete_requested.emit(self._item.id))
        btn_layout.addWidget(self._delete_btn)
        
        header_layout.addLayout(btn_layout)
        
        self._main_layout.addLayout(header_layout)
        
        self._sub_container = QWidget()
        self._sub_container.setVisible(False)
        self._sub_layout = QVBoxLayout(self._sub_container)
        self._sub_layout.setContentsMargins(0, 8, 0, 0)
        self._sub_layout.setSpacing(1)
        self._main_layout.addWidget(self._sub_container)
        
        self._update_style()
        self._update_toggle_icon()
    
    def _toggle_expand(self):
        self._expanded = not self._expanded
        if self._expanded:
            self._expand_btn.setIcon(FluentIcon.CARE_DOWN_SOLID)
            self._build_sub_widgets()
            self._sub_container.setVisible(True)
        else:
            self._expand_btn.setIcon(FluentIcon.CARE_RIGHT_SOLID)
            self._sub_container.setVisible(False)
    
    def _build_sub_widgets(self):
        for w in self._sub_widgets:
            w.deleteLater()
        self._sub_widgets.clear()
        
        if not self._item.actions:
            return
        
        for i, action in enumerate(self._item.actions[:50]):
            w = SubActionRow(action, i, depth=1)
            self._sub_widgets.append(w)
            self._sub_layout.addWidget(w)
        
        if len(self._item.actions) > 50:
            more_label = CaptionLabel(f"... 还有 {len(self._item.actions) - 50} 个动作")
            more_label.setStyleSheet("color: #888; padding-left: 28px;")
            self._sub_layout.addWidget(more_label)
    
    def _on_toggle(self):
        self._item.enabled = not self._item.enabled
        self._update_toggle_icon()
        self._update_style()
        self.toggle_enabled.emit(self._item.id, self._item.enabled)
    
    def _update_toggle_icon(self):
        if self._item.enabled:
            self._toggle_btn.setIcon(FluentIcon.CHECKBOX)
        else:
            self._toggle_btn.setIcon(FluentIcon.REMOVE)
    
    def _update_style(self):
        if self._is_running:
            self.setStyleSheet("CardWidget { background-color: rgba(0, 120, 212, 0.1); border: 1px solid rgba(0, 120, 212, 0.4); }")
        elif self._is_completed:
            self.setStyleSheet("CardWidget { background-color: rgba(22, 163, 74, 0.08); border: 1px solid rgba(22, 163, 74, 0.2); }")
        elif not self._item.enabled:
            self.setStyleSheet("CardWidget { background-color: rgba(128, 128, 128, 0.1); }")
        else:
            self.setStyleSheet("")
    
    def update_index(self, index: int):
        self._index = index
        self._index_label.setText(str(index + 1))
    
    def set_running(self, running: bool):
        self._is_running = running
        self._is_completed = False
        self._update_style()
        if running:
            self._status_label.setVisible(False)
    
    def set_completed(self, completed: bool):
        self._is_completed = completed
        self._is_running = False
        self._update_style()
        if completed:
            self._status_label.setText("✓")
            self._status_label.setStyleSheet("color: #16a34a; font-weight: bold; font-size: 14px;")
            self._status_label.setVisible(True)
    
    def reset(self):
        self._is_running = False
        self._is_completed = False
        self._status_label.setVisible(False)
        self._update_style()


class StatCard(CardWidget):
    def __init__(self, title: str, value: str, icon: FluentIcon, parent=None):
        super().__init__(parent)
        self._title = title
        self._value = value
        self._icon = icon
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)
        
        icon_widget = IconWidget(self._icon, self)
        icon_widget.setFixedSize(32, 32)
        icon_widget.setStyleSheet("color: #0078d4;")
        layout.addWidget(icon_widget)
        
        content = QVBoxLayout()
        content.setSpacing(4)
        
        self._value_label = TitleLabel(self._value)
        content.addWidget(self._value_label)
        
        title_label = BodyLabel(self._title)
        title_label.setStyleSheet("color: #666;")
        content.addWidget(title_label)
        
        layout.addLayout(content)
        layout.addStretch()
    
    def set_value(self, value: str):
        self._value_label.setText(value)


class DashboardPage(QWidget):
    _update_progress_signal = pyqtSignal(float, int, int)
    _update_state_signal = pyqtSignal(object, str)
    _update_finished_signal = pyqtSignal(bool, str)
    _show_info_signal = pyqtSignal(str)
    _show_error_signal = pyqtSignal(str)
    _show_warning_signal = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._config = Config.get_instance()
        self._window_utils = WindowUtils()
        
        self._player: Optional[Player] = None
        self._scripts: List[ScriptItem] = []
        self._script_cards: List[ScriptCard] = []
        self._current_file: Optional[str] = None
        self._is_running = False
        self._current_script_index = -1
        
        self._setup_ui()
        self._setup_connections()
        
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self._load_last_list)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)
        
        header_layout = QHBoxLayout()
        
        title = TitleLabel("执行面板")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self._add_btn = PushButton(FluentIcon.ADD, "添加脚本")
        self._add_btn.setFixedHeight(32)
        self._add_btn.clicked.connect(self._add_scripts)
        header_layout.addWidget(self._add_btn)
        
        self._open_btn = PushButton(FluentIcon.FOLDER, "打开列表")
        self._open_btn.setFixedHeight(32)
        self._open_btn.clicked.connect(self._open_list)
        header_layout.addWidget(self._open_btn)
        
        self._save_btn = PushButton(FluentIcon.SAVE, "保存列表")
        self._save_btn.setFixedHeight(32)
        self._save_btn.clicked.connect(self._save_list)
        header_layout.addWidget(self._save_btn)
        
        layout.addLayout(header_layout)
        
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)
        
        self._total_card = StatCard("脚本数量", "0", FluentIcon.DOCUMENT)
        stats_layout.addWidget(self._total_card)
        
        self._progress_card = StatCard("执行进度", "0%", FluentIcon.SPEED_HIGH)
        stats_layout.addWidget(self._progress_card)
        
        self._repeat_card = StatCard("当前轮次", "1", FluentIcon.SYNC)
        stats_layout.addWidget(self._repeat_card)
        
        layout.addLayout(stats_layout)
        
        main_layout = QHBoxLayout()
        main_layout.setSpacing(20)
        
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)
        
        control_card = HeaderCardWidget(self)
        control_card.setTitle("控制面板")
        
        control_content = QWidget()
        control_layout = QVBoxLayout(control_content)
        control_layout.setContentsMargins(20, 12, 20, 20)
        control_layout.setSpacing(16)
        
        window_row = QHBoxLayout()
        window_label = StrongBodyLabel("目标窗口")
        window_row.addWidget(window_label)
        window_row.addStretch()
        
        self._refresh_btn = TransparentToolButton(FluentIcon.SYNC)
        self._refresh_btn.setFixedSize(28, 28)
        self._refresh_btn.clicked.connect(self._refresh_windows)
        window_row.addWidget(self._refresh_btn)
        
        control_layout.addLayout(window_row)
        
        self._window_selector = WindowSelector()
        self._window_selector.refresh_windows()
        control_layout.addWidget(self._window_selector)
        
        launch_row = QHBoxLayout()
        launch_label = StrongBodyLabel("启动命令")
        launch_row.addWidget(launch_label)
        launch_row.addStretch()
        
        self._launch_combo = ComboBox()
        self._launch_combo.setMinimumWidth(200)
        self._launch_combo.addItem("无")
        self._refresh_launch_commands()
        launch_row.addWidget(self._launch_combo)
        
        control_layout.addLayout(launch_row)
        
        settings_row = QHBoxLayout()
        settings_row.setSpacing(24)
        
        speed_group = QVBoxLayout()
        speed_group.setSpacing(6)
        speed_label = BodyLabel("执行速度")
        speed_group.addWidget(speed_label)
        self._speed_spin = DoubleSpinBox()
        self._speed_spin.setRange(0.1, 10.0)
        self._speed_spin.setSingleStep(0.1)
        self._speed_spin.setValue(self._config.default_speed)
        self._speed_spin.setSuffix(" 倍")
        self._speed_spin.setFixedWidth(100)
        speed_group.addWidget(self._speed_spin)
        settings_row.addLayout(speed_group)
        
        repeat_group = QVBoxLayout()
        repeat_group.setSpacing(6)
        repeat_label = BodyLabel("重复次数")
        repeat_group.addWidget(repeat_label)
        self._repeat_spin = SpinBox()
        self._repeat_spin.setRange(1, 999)
        self._repeat_spin.setValue(self._config.default_repeat_count)
        self._repeat_spin.setFixedWidth(100)
        repeat_group.addWidget(self._repeat_spin)
        settings_row.addLayout(repeat_group)
        
        settings_row.addStretch()
        
        self._infinite_cb = CheckBox("无限循环")
        settings_row.addWidget(self._infinite_cb)
        
        control_layout.addLayout(settings_row)
        
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        
        self._run_btn = PrimaryPushButton(FluentIcon.PLAY, "运行全部")
        self._run_btn.setFixedHeight(40)
        self._run_btn.clicked.connect(self._run_all)
        btn_row.addWidget(self._run_btn, 1)
        
        self._stop_btn = PushButton(FluentIcon.CANCEL, "停止")
        self._stop_btn.setFixedHeight(40)
        self._stop_btn.clicked.connect(self._stop)
        self._stop_btn.setEnabled(False)
        btn_row.addWidget(self._stop_btn, 1)
        
        control_layout.addLayout(btn_row)
        
        control_card.viewLayout.addWidget(control_content)
        left_layout.addWidget(control_card)
        
        status_card = CardWidget(self)
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(20, 16, 20, 16)
        status_layout.setSpacing(8)
        
        status_header = QHBoxLayout()
        self._status_icon = IconWidget(FluentIcon.INFO, self)
        self._status_icon.setFixedSize(16, 16)
        status_header.addWidget(self._status_icon)
        
        self._status_label = BodyLabel("就绪 - 请添加脚本文件")
        status_header.addWidget(self._status_label)
        status_header.addStretch()
        
        status_layout.addLayout(status_header)
        
        self._progress_bar = ProgressBar()
        self._progress_bar.setFixedHeight(6)
        self._progress_bar.setVisible(False)
        status_layout.addWidget(self._progress_bar)
        
        left_layout.addWidget(status_card)
        
        main_layout.addWidget(left_panel, 2)
        
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        
        task_header = QHBoxLayout()
        task_title = StrongBodyLabel("脚本列表")
        task_header.addWidget(task_title)
        task_header.addStretch()
        
        clear_btn = TransparentToolButton(FluentIcon.DELETE)
        clear_btn.setFixedSize(28, 28)
        clear_btn.setToolTip("清空列表")
        clear_btn.clicked.connect(self._clear_list)
        task_header.addWidget(clear_btn)
        
        right_layout.addLayout(task_header)
        
        self._scroll_area = ScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setStyleSheet("QScrollArea { border: 1px solid rgba(0, 0, 0, 0.06); border-radius: 8px; background: transparent; }")
        
        self._task_container = QWidget()
        self._task_container.setStyleSheet("background: transparent;")
        self._task_layout = QVBoxLayout(self._task_container)
        self._task_layout.setAlignment(Qt.AlignTop)
        self._task_layout.setContentsMargins(8, 8, 8, 8)
        self._task_layout.setSpacing(8)
        self._task_layout.addStretch()
        
        self._scroll_area.setWidget(self._task_container)
        right_layout.addWidget(self._scroll_area)
        
        self._empty_label = QWidget()
        empty_layout = QVBoxLayout(self._empty_label)
        empty_layout.setContentsMargins(40, 60, 40, 60)
        empty_layout.setSpacing(16)
        
        empty_icon = IconWidget(FluentIcon.DOCUMENT)
        empty_icon.setFixedSize(48, 48)
        empty_layout.addWidget(empty_icon, 0, Qt.AlignCenter)
        
        empty_text = StrongBodyLabel("暂无脚本")
        empty_text.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(empty_text)
        
        empty_hint = BodyLabel("点击\"添加脚本\"将脚本加入列表")
        empty_hint.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(empty_hint)
        
        right_layout.addWidget(self._empty_label)
        
        main_layout.addWidget(right_panel, 3)
        
        layout.addLayout(main_layout)
    
    def _setup_connections(self):
        self._update_progress_signal.connect(self._on_progress)
        self._update_state_signal.connect(self._on_state_changed)
        self._update_finished_signal.connect(self._on_finished)
        self._show_info_signal.connect(self._show_info)
        self._show_error_signal.connect(self._show_error)
        self._show_warning_signal.connect(self._show_warning)
    
    def _refresh_windows(self):
        self._window_selector.refresh_windows()
    
    def _refresh_launch_commands(self):
        self._launch_combo.blockSignals(True)
        self._launch_combo.clear()
        self._launch_combo.addItem("无", userData=None)
        
        try:
            cmd_manager = CommandManager.get_instance()
            commands = cmd_manager.get_all_commands()
            
            for cmd in commands:
                self._launch_combo.addItem(cmd.name, userData=cmd.id)
        except Exception as e:
            print(f"刷新启动命令失败: {e}")
        
        self._launch_combo.blockSignals(False)
    
    def _get_selected_launch_command_id(self) -> str:
        index = self._launch_combo.currentIndex()
        if index > 0:
            data = self._launch_combo.itemData(index)
            return str(data) if data else ""
        return ""
    
    def _set_selected_launch_command(self, cmd_id: str):
        if not cmd_id:
            self._launch_combo.setCurrentIndex(0)
            return
        
        for i in range(self._launch_combo.count()):
            if self._launch_combo.itemData(i) == cmd_id:
                self._launch_combo.setCurrentIndex(i)
                break
    
    def _add_scripts(self):
        filepaths, _ = QFileDialog.getOpenFileNames(
            self, "选择脚本文件", "", "JSON 脚本 (*.json)"
        )
        if filepaths:
            import uuid
            for filepath in filepaths:
                try:
                    result = Exporter.import_from_json(filepath)
                    if result is None:
                        continue
                    
                    actions = result if isinstance(result, list) else result.get('actions', [])
                    if not actions:
                        continue
                    
                    name = os.path.splitext(os.path.basename(filepath))[0]
                    
                    item = ScriptItem(
                        id=str(uuid.uuid4()),
                        name=name,
                        path=filepath,
                        actions=actions
                    )
                    self._scripts.append(item)
                except Exception as e:
                    print(f"加载脚本失败: {filepath}, {e}")
            
            self._refresh_list()
    
    def _refresh_list(self):
        for card in self._script_cards:
            card.deleteLater()
        self._script_cards.clear()
        
        self._empty_label.setVisible(len(self._scripts) == 0)
        self._total_card.set_value(str(len(self._scripts)))
        
        for i, item in enumerate(self._scripts):
            card = ScriptCard(item, i)
            card.run_requested.connect(self._run_single)
            card.delete_requested.connect(self._remove_script)
            card.move_up_requested.connect(self._move_up)
            card.move_down_requested.connect(self._move_down)
            card.toggle_enabled.connect(self._toggle_enabled)
            self._script_cards.append(card)
            self._task_layout.insertWidget(self._task_layout.count() - 1, card)
    
    def _remove_script(self, script_id: str):
        self._scripts = [s for s in self._scripts if s.id != script_id]
        self._refresh_list()
    
    def _move_up(self, script_id: str):
        idx = next((i for i, s in enumerate(self._scripts) if s.id == script_id), -1)
        if idx > 0:
            self._scripts[idx], self._scripts[idx-1] = self._scripts[idx-1], self._scripts[idx]
            self._refresh_list()
    
    def _move_down(self, script_id: str):
        idx = next((i for i, s in enumerate(self._scripts) if s.id == script_id), -1)
        if idx < len(self._scripts) - 1:
            self._scripts[idx], self._scripts[idx+1] = self._scripts[idx+1], self._scripts[idx]
            self._refresh_list()
    
    def _toggle_enabled(self, script_id: str, enabled: bool):
        item = next((s for s in self._scripts if s.id == script_id), None)
        if item:
            item.enabled = enabled
    
    def _clear_list(self):
        if not self._scripts:
            return
        box = MessageBox("确认清空", "确定要清空脚本列表吗？", self)
        if box.exec():
            self._scripts.clear()
            self._refresh_list()
    
    def _open_list(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "打开脚本列表", "", "脚本列表 (*.scripts.json)"
        )
        if filepath:
            self._load_list_from_file(filepath)
    
    def _load_list_from_file(self, filepath: str):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._scripts.clear()
            for s in data.get('scripts', []):
                result = Exporter.import_from_json(s['path'])
                if result:
                    actions = result if isinstance(result, list) else result.get('actions', [])
                    
                    item = ScriptItem(
                        id=s['id'],
                        name=s['name'],
                        path=s['path'],
                        actions=actions,
                        delay_before=s.get('delay_before', 0),
                        repeat_count=s.get('repeat_count', 1),
                        enabled=s.get('enabled', True)
                    )
                    self._scripts.append(item)
            
            window_info = data.get('window', {})
            if window_info:
                saved_hwnd = window_info.get('hwnd', 0)
                saved_title = window_info.get('title', '')
                if saved_hwnd:
                    self._window_selector.set_selected_window(saved_hwnd, saved_title)
            
            if 'speed' in data:
                self._speed_spin.setValue(data['speed'])
            if 'repeat' in data:
                self._repeat_spin.setValue(data['repeat'])
            if 'infinite' in data:
                self._infinite_cb.setChecked(data['infinite'])
            
            if 'launch_command_id' in data:
                self._set_selected_launch_command(data['launch_command_id'])
            
            self._current_file = filepath
            self._refresh_list()
            self._save_last_list(filepath)
            self._show_info("已加载脚本列表")
        except Exception as e:
            self._show_error(f"打开失败: {e}")
    
    def _save_list(self):
        if not self._current_file:
            self._current_file, _ = QFileDialog.getSaveFileName(
                self, "保存脚本列表", "", "脚本列表 (*.scripts.json)"
            )
        if self._current_file:
            self._save_list_to_file(self._current_file)
    
    def _save_list_to_file(self, filepath: str):
        try:
            scripts_data = []
            for s in self._scripts:
                script_info = {
                    'id': s.id,
                    'name': s.name,
                    'path': s.path,
                    'delay_before': s.delay_before,
                    'repeat_count': s.repeat_count,
                    'enabled': s.enabled
                }
                scripts_data.append(script_info)
            
            window_info = {}
            selected_hwnd = self._window_selector.get_selected_hwnd()
            if selected_hwnd:
                window_info['hwnd'] = selected_hwnd
                window_info_obj = self._window_utils.get_window_by_hwnd(selected_hwnd)
                if window_info_obj:
                    window_info['title'] = window_info_obj.title
            
            launch_cmd_id = self._get_selected_launch_command_id()
            launch_command = None
            if launch_cmd_id:
                cmd_manager = CommandManager.get_instance()
                cmd = cmd_manager.get_command(launch_cmd_id)
                if cmd:
                    launch_command = {
                        'id': cmd.id,
                        'name': cmd.name,
                        'command': cmd.command,
                        'window_title_pattern': cmd.window_title_pattern,
                        'description': cmd.description
                    }
            
            data = {
                'scripts': scripts_data,
                'window': window_info,
                'speed': self._speed_spin.value(),
                'repeat': self._repeat_spin.value(),
                'infinite': self._infinite_cb.isChecked(),
                'launch_command_id': launch_cmd_id,
                'launch_command': launch_command
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._save_last_list(filepath)
            self._show_info("脚本列表已保存")
        except Exception as e:
            self._show_error(f"保存失败: {e}")
    
    def _save_last_list(self, filepath: str):
        config = Config.get_instance()
        config.last_dashboard_list = filepath
        config.save()
    
    def _load_last_list(self):
        config = Config.get_instance()
        last_list = config.last_dashboard_list
        if last_list and os.path.exists(last_list):
            self._load_list_from_file(last_list)
    
    def open_list_dialog(self):
        self._open_list()
    
    def save_list_dialog(self):
        self._save_list()
    
    def export_python(self):
        if not self._scripts:
            self._show_warning("请先添加脚本")
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出Python脚本", "", "Python文件 (*.py)"
        )
        if filepath:
            try:
                if not filepath.endswith('.py'):
                    filepath += '.py'
                
                code = self._generate_batch_python_code()
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(code)
                
                self._show_info(f"已导出到 {os.path.basename(filepath)}")
                
                from qfluentwidgets import MessageBox
                box = MessageBox('导出成功', f'脚本已导出到:\n{filepath}\n\n是否打开文件所在目录?', self)
                box.yesButton.setText('打开目录')
                box.cancelButton.setText('关闭')
                
                if box.exec():
                    os.startfile(os.path.dirname(filepath))
            except Exception as e:
                self._show_error(f"导出失败: {e}")
    
    def _generate_batch_python_code(self) -> str:
        from datetime import datetime
        
        lines = []
        lines.append("#!/usr/bin/env python3")
        lines.append("# -*- coding: utf-8 -*-")
        lines.append("")
        lines.append('"""')
        lines.append("RPA Batch Script")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Total Scripts: {len(self._scripts)}")
        lines.append('"""')
        lines.append("")
        lines.append("import pyautogui")
        lines.append("import time")
        lines.append("import os")
        lines.append("import sys")
        lines.append("import json")
        lines.append("")
        lines.append("pyautogui.FAILSAFE = True")
        lines.append("pyautogui.PAUSE = 0.1")
        lines.append("")
        lines.append("")
        
        lines.append("def launch_application(command):")
        lines.append('    """启动应用程序"""')
        lines.append("    import subprocess")
        lines.append("    try:")
        lines.append("        if os.name == 'nt':")
        lines.append("            subprocess.Popen(command, shell=True)")
        lines.append("        else:")
        lines.append("            subprocess.Popen(command, shell=True, start_new_session=True)")
        lines.append("        print(f'已执行启动命令: {command}')")
        lines.append("        return True")
        lines.append("    except Exception as e:")
        lines.append("        print(f'启动命令执行失败: {e}')")
        lines.append("        return False")
        lines.append("")
        lines.append("")
        
        for i, item in enumerate(self._scripts):
            if not item.enabled:
                continue
            
            func_name = f"script_{i + 1}_{self._sanitize_name(item.name)}"
            lines.append(f"def {func_name}():")
            lines.append(f'    """执行脚本: {item.name}"""')
            
            if item.delay_before > 0:
                lines.append(f"    time.sleep({item.delay_before})")
                lines.append("")
            
            if item.actions:
                for j, action in enumerate(item.actions):
                    action_code = self._action_to_python_code(action, j + 1)
                    for line in action_code.split('\n'):
                        lines.append(f"    {line}")
                    lines.append("")
            
            if item.repeat_count > 1:
                lines.append(f"    # 此脚本将重复执行 {item.repeat_count} 次")
                lines.append("")
            
            lines.append(f"    print('脚本 [{item.name}] 执行完成')")
            lines.append("")
            lines.append("")
        
        lines.append("def main():")
        lines.append('    """主函数：按顺序执行所有脚本"""')
        lines.append("    print('开始执行批量脚本...')")
        lines.append("    print(f'共 {len([s for s in scripts if s.enabled])} 个脚本')")
        lines.append("    print()")
        lines.append("    ")
        
        script_index = 0
        for i, item in enumerate(self._scripts):
            if not item.enabled:
                continue
            
            script_index += 1
            func_name = f"script_{i + 1}_{self._sanitize_name(item.name)}"
            
            lines.append(f"    print('=== 脚本 {script_index}: {item.name} ===')")
            
            if item.repeat_count > 1:
                lines.append(f"    for repeat in range({item.repeat_count}):")
                lines.append(f"        print(f'  第 {{repeat + 1}}/{{item.repeat_count}} 次')")
                lines.append(f"        {func_name}()")
            else:
                lines.append(f"    {func_name}()")
            
            lines.append("    print()")
        
        lines.append("    print('所有脚本执行完成!')")
        lines.append("")
        lines.append("")
        lines.append("scripts = [")
        for item in self._scripts:
            lines.append(f"    dict(name='{item.name}', enabled={item.enabled}),")
        lines.append("]")
        lines.append("")
        lines.append("")
        lines.append("if __name__ == '__main__':")
        lines.append("    try:")
        lines.append("        main()")
        lines.append("    except KeyboardInterrupt:")
        lines.append("        print('\\n脚本被用户中断')")
        lines.append("    except Exception as e:")
        lines.append("        print(f'执行错误: {e}')")
        lines.append("")
        
        return '\n'.join(lines)
    
    def _sanitize_name(self, name: str) -> str:
        safe = ""
        for c in name:
            if c.isalnum() or c == '_':
                safe += c
            else:
                safe += '_'
        return safe
    
    def _action_to_python_code(self, action, index: int) -> str:
        from core.actions import ActionType
        
        lines = []
        lines.append(f"# 动作 {index}: {action.description}")
        
        if action.delay_before > 0:
            lines.append(f"time.sleep({action.delay_before})")
        
        if action.action_type == ActionType.MOUSE_CLICK:
            x, y = action.params.get('x', 0), action.params.get('y', 0)
            button = action.params.get('button', 'left')
            clicks = action.params.get('clicks', 1)
            lines.append(f"pyautogui.click(x={x}, y={y}, button='{button}', clicks={clicks})")
        
        elif action.action_type == ActionType.MOUSE_DOUBLE_CLICK:
            x, y = action.params.get('x', 0), action.params.get('y', 0)
            lines.append(f"pyautogui.doubleClick(x={x}, y={y})")
        
        elif action.action_type == ActionType.MOUSE_RIGHT_CLICK:
            x, y = action.params.get('x', 0), action.params.get('y', 0)
            lines.append(f"pyautogui.rightClick(x={x}, y={y})")
        
        elif action.action_type == ActionType.MOUSE_MOVE:
            x, y = action.params.get('x', 0), action.params.get('y', 0)
            duration = action.params.get('duration', 0.0)
            lines.append(f"pyautogui.moveTo(x={x}, y={y}, duration={duration})")
        
        elif action.action_type == ActionType.MOUSE_DRAG:
            start_x = action.params.get('start_x', 0)
            start_y = action.params.get('start_y', 0)
            end_x = action.params.get('end_x', 0)
            end_y = action.params.get('end_y', 0)
            duration = action.params.get('duration', 0.5)
            lines.append(f"pyautogui.moveTo({start_x}, {start_y})")
            lines.append(f"pyautogui.drag({end_x - start_x}, {end_y - start_y}, duration={duration})")
        
        elif action.action_type == ActionType.MOUSE_SCROLL:
            clicks = action.params.get('clicks', 0)
            x, y = action.params.get('x', 0), action.params.get('y', 0)
            lines.append(f"pyautogui.scroll({clicks}, x={x}, y={y})")
        
        elif action.action_type == ActionType.KEY_PRESS:
            key = action.params.get('key', '')
            lines.append(f"pyautogui.press('{key}')")
        
        elif action.action_type == ActionType.KEY_TYPE:
            text = action.params.get('text', '')
            interval = action.params.get('interval', 0.0)
            escaped_text = text.replace("'", "\\'")
            lines.append(f"pyautogui.typewrite('{escaped_text}', interval={interval})")
        
        elif action.action_type == ActionType.HOTKEY:
            keys = action.params.get('keys', [])
            keys_str = ', '.join([f"'{k}'" for k in keys])
            lines.append(f"pyautogui.hotkey({keys_str})")
        
        elif action.action_type == ActionType.WAIT:
            seconds = action.params.get('seconds', 1.0)
            lines.append(f"time.sleep({seconds})")
        
        elif action.action_type == ActionType.SCREENSHOT:
            filename = action.params.get('filename', 'screenshot.png')
            lines.append(f"pyautogui.screenshot('{filename}')")
        
        elif action.action_type in [ActionType.MOUSE_MOVE_RELATIVE, ActionType.MOUSE_CLICK_RELATIVE]:
            x, y = action.params.get('x', 0), action.params.get('y', 0)
            lines.append("try:")
            lines.append("    wx, wy = window_x, window_y")
            if action.action_type == ActionType.MOUSE_MOVE_RELATIVE:
                duration = action.params.get('duration', 0.0)
                lines.append(f"    pyautogui.moveTo(x=wx + {x}, y=wy + {y}, duration={duration})")
            else:
                lines.append(f"    pyautogui.click(x=wx + {x}, y=wy + {y})")
            lines.append("except:")
            lines.append(f"    pyautogui.click(x={x}, y={y})")
        
        elif action.action_type == ActionType.IMAGE_CLICK:
            image_path = action.params.get('image_path', '')
            confidence = action.params.get('confidence', 0.9)
            lines.append(f"try:")
            lines.append(f"    location = pyautogui.locateOnScreen('{image_path}', confidence={confidence})")
            lines.append("    if location:")
            lines.append("        center = pyautogui.center(location)")
            lines.append("        pyautogui.click(center)")
            lines.append("    else:")
            lines.append(f"        print('未找到图片: {os.path.basename(image_path)}')")
            lines.append("except Exception as e:")
            lines.append("    print(f'图片点击失败: {e}')")
        
        elif action.action_type == ActionType.IMAGE_WAIT_CLICK:
            image_path = action.params.get('image_path', '')
            confidence = action.params.get('confidence', 0.9)
            timeout = action.params.get('timeout', 30)
            lines.append(f"location = None")
            lines.append(f"for _ in range({int(timeout * 2)}):")
            lines.append(f"    try:")
            lines.append(f"        location = pyautogui.locateOnScreen('{image_path}', confidence={confidence})")
            lines.append("        if location:")
            lines.append("            break")
            lines.append("    except:")
            lines.append("        pass")
            lines.append("    time.sleep(0.5)")
            lines.append("if location:")
            lines.append("    center = pyautogui.center(location)")
            lines.append("    pyautogui.click(center)")
            lines.append("else:")
            lines.append(f"    print('等待图片超时: {os.path.basename(image_path)}')")
        
        elif action.action_type == ActionType.IMAGE_CHECK:
            image_path = action.params.get('image_path', '')
            confidence = action.params.get('confidence', 0.9)
            lines.append(f"try:")
            lines.append(f"    location = pyautogui.locateOnScreen('{image_path}', confidence={confidence})")
            lines.append("    if location:")
            lines.append("        print('图片检查: 找到')")
            lines.append("    else:")
            lines.append("        print('图片检查: 未找到')")
            lines.append("except Exception as e:")
            lines.append("    print(f'图片检查失败: {e}')")
        
        if action.delay_after > 0:
            lines.append(f"time.sleep({action.delay_after})")
        
        return '\n'.join(lines)
    
    def _run_single(self, script_id: str):
        item = next((s for s in self._scripts if s.id == script_id), None)
        if not item:
            return
        
        self._is_running = True
        self._current_script_index = self._scripts.index(item)
        
        self._run_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        
        for card in self._script_cards:
            card.reset()
        
        self._script_cards[self._current_script_index].set_running(True)
        
        import threading
        thread = threading.Thread(target=self._execute_script_with_finish, args=(item,), daemon=True)
        thread.start()
    
    def _execute_script_with_finish(self, item: ScriptItem):
        self._execute_script(item)
        self._update_finished_signal.emit(True, "")
    
    def _run_all(self):
        enabled_scripts = [s for s in self._scripts if s.enabled]
        if not enabled_scripts:
            self._show_warning("请添加并启用至少一个脚本")
            return
        
        self._is_running = True
        self._run_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        
        for card in self._script_cards:
            card.reset()
        
        import threading
        thread = threading.Thread(target=self._execute_all, daemon=True)
        thread.start()
    
    def _execute_script(self, item: ScriptItem):
        import time
        from core.action_group import LocalActionGroupManager
        
        if item.delay_before > 0:
            time.sleep(item.delay_before)
        
        if not self._is_running:
            return
        
        selected_hwnd = self._window_selector.get_selected_hwnd()
        window_title = ""
        
        if selected_hwnd:
            window_info = self._window_utils.get_window_by_hwnd(selected_hwnd)
            if window_info:
                window_title = window_info.title
        else:
            launch_cmd_id = self._get_selected_launch_command_id()
            if launch_cmd_id:
                cmd_manager = CommandManager.get_instance()
                cmd = cmd_manager.get_command(launch_cmd_id)
                if cmd:
                    self._show_info_signal.emit(f"正在启动: {cmd.name}")
                    success, message, already_running = cmd_manager.check_and_launch(launch_cmd_id)
                    
                    if success:
                        target_pattern = cmd.window_title_pattern or cmd.name
                        
                        waited = 0
                        max_wait = 30
                        while waited < max_wait:
                            if not self._is_running:
                                return
                            
                            self._window_selector.refresh_windows()
                            
                            combo = self._window_selector._window_combo
                            for i in range(combo.count()):
                                hwnd = combo.itemData(i)
                                title = combo.itemText(i)
                                if hwnd and target_pattern.lower() in title.lower():
                                    self._window_selector.set_selected_window(hwnd, title)
                                    selected_hwnd = hwnd
                                    window_title = title
                                    break
                            
                            if selected_hwnd:
                                break
                            
                            time.sleep(0.5)
                            waited += 0.5
                        
                        if not selected_hwnd:
                            self._show_error_signal.emit(f"窗口启动超时: {target_pattern}")
                            return
                    elif not success:
                        self._show_error_signal.emit(f"启动命令执行失败: {message}")
                        return
        
        local_group_manager = LocalActionGroupManager()
        result = Exporter.import_from_json(item.path, local_group_manager)
        if not result:
            return
        
        actions = result if isinstance(result, list) else result.get('actions', [])
        if not actions:
            return
        
        player = Player(tab_key="dashboard")
        player.set_actions(actions)
        player.set_speed(self._speed_spin.value())
        player.set_repeat_count(item.repeat_count)
        
        if selected_hwnd:
            player.set_window_hwnd(selected_hwnd, self._window_utils)
            window_offset = self._window_selector.get_window_offset()
            player.set_window_offset(window_offset)
        
        if window_title:
            player.set_window_title(window_title)
        
        player.play()
        
        while player.state not in [PlayerState.IDLE]:
            if not self._is_running:
                player.stop()
                break
            time.sleep(0.1)
    
    def _execute_all(self):
        import time
        
        enabled_scripts = [s for s in self._scripts if s.enabled]
        total = len(enabled_scripts)
        
        for i, item in enumerate(enabled_scripts):
            if not self._is_running:
                break
            
            idx = self._scripts.index(item)
            self._current_script_index = idx
            
            from PyQt5.QtCore import QMetaObject, Qt
            
            for card in self._script_cards:
                card.reset()
            self._script_cards[idx].set_running(True)
            
            progress = (i + 1) / total
            self._update_progress_signal.emit(progress, i + 1, 1)
            
            self._execute_script(item)
        
        self._update_finished_signal.emit(True, "")
    
    def _stop(self):
        self._is_running = False
        if self._player:
            self._player.stop()
        self._run_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._show_info("已停止")
    
    def _on_progress(self, progress, index, repeat):
        if progress >= 0:
            self._progress_bar.setValue(int(progress * 100))
            self._progress_card.set_value(f"{int(progress * 100)}%")
        self._repeat_card.set_value(str(repeat))
    
    def _on_state_changed(self, state, message):
        if state == PlayerState.IDLE:
            self._run_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
    
    def _on_finished(self, success, message):
        self._is_running = False
        self._run_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._progress_bar.setVisible(False)
        
        if success:
            self._status_label.setText("执行完成")
            self._status_icon.setIcon(FluentIcon.COMPLETED)
            for card in self._script_cards:
                card.reset()
        else:
            self._status_label.setText("已停止")
            self._status_icon.setIcon(FluentIcon.STOP_WATCH)
    
    def _show_info(self, message: str):
        InfoBar.info(title="提示", content=message, parent=self, position=InfoBarPosition.TOP)
    
    def _show_error(self, message: str):
        InfoBar.error(title="错误", content=message, parent=self, position=InfoBarPosition.TOP)
    
    def _show_warning(self, message: str):
        InfoBar.warning(title="警告", content=message, parent=self, position=InfoBarPosition.TOP)
    
    def refresh_windows(self):
        self._window_selector.refresh_windows()
