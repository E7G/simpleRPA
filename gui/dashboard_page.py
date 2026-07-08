import os

import json

from PyQt5.QtWidgets import (

    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QLabel, QFrame,

    QApplication,

)

from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QTime

from PyQt5.QtGui import QColor

from typing import Dict, Optional, List

from dataclasses import dataclass



from qfluentwidgets import (

    FluentIcon, PushButton, PrimaryPushButton,

    BodyLabel, StrongBodyLabel, ProgressBar, CardWidget, ElevatedCardWidget,

    CheckBox, SubtitleLabel, CaptionLabel, IconWidget, ScrollArea,

    TransparentToolButton, InfoBadge, TitleLabel, HeaderCardWidget,

    isDarkTheme, themeColor, SimpleCardWidget, InfoBar, InfoBarPosition,

    ComboBox, LineEdit, MessageBox, SwitchButton, TimeEdit, SpinBox

)



from core.actions import Action, ActionType, can_actions_run_offscreen

from core.action_group import LocalActionGroupManager

from core.player import Player, PlayerState

from core.exporter import Exporter

from core.command_manager import CommandManager

from utils.config import Config

from utils.window_utils import WindowUtils

from .widgets import WindowSelector, WindowPreview

from .fluent_theme import (

    muted_label_style, muted_caption_style, accent_color, success_color,

    scroll_border_style,

    create_compact_int_spin, create_compact_float_spin, InlineNumericField,

)





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

    def __init__(self, action: Action, index: int, depth: int = 0, parent=None, local_group_manager=None):

        super().__init__(parent)

        self._action = action

        self._index = index

        self._depth = depth

        self._is_running = False

        self._is_completed = False

        self._expanded = False

        self._sub_widgets: List[QWidget] = []

        self._local_group_manager = local_group_manager

        self._repeat_count = action.repeat_count or 1

        self._current_repeat = 0

        self._sub_action_index = -1

        self._setup_ui()



    def _setup_ui(self):

        self._main_layout = QVBoxLayout(self)

        self._main_layout.setContentsMargins(0, 0, 0, 0)

        self._main_layout.setSpacing(0)



        header = QWidget()

        header_layout = QHBoxLayout(header)

        header_layout.setContentsMargins(self._depth * 16 + 12, 4, 8, 4)

        header_layout.setSpacing(6)



        self._index_label = CaptionLabel(f"{self._index + 1}")

        self._index_label.setFixedWidth(16)

        self._index_label.setStyleSheet("color: #888;")

        header_layout.addWidget(self._index_label)



        is_action_group = self._action.action_type == ActionType.ACTION_GROUP_REF



        if is_action_group:

            self._expand_btn = TransparentToolButton(FluentIcon.CARE_RIGHT_SOLID)

            self._expand_btn.setFixedSize(16, 16)

            self._expand_btn.clicked.connect(self._toggle_expand)

            header_layout.addWidget(self._expand_btn)

        else:

            icon = ACTION_ICONS.get(self._action.action_type, FluentIcon.PLAY)

            self._icon = IconWidget(icon, self)

            self._icon.setFixedSize(12, 12)

            header_layout.addWidget(self._icon)



        desc_text = self._action.description[:40]

        self._desc_label = CaptionLabel(desc_text)

        header_layout.addWidget(self._desc_label, 1)



        self._status_label = CaptionLabel("")

        self._status_label.setFixedWidth(40)

        header_layout.addWidget(self._status_label)



        self._main_layout.addWidget(header)



        self._sub_container = QWidget()

        self._sub_container.setVisible(False)

        self._sub_layout = QVBoxLayout(self._sub_container)

        self._sub_layout.setContentsMargins(0, 0, 0, 0)

        self._sub_layout.setSpacing(0)

        self._main_layout.addWidget(self._sub_container)



        header.setFixedHeight(24)



    def _toggle_expand(self):

        self._expanded = not self._expanded

        if self._expanded:

            self._expand_btn.setIcon(FluentIcon.CARE_DOWN_SOLID)

            self._build_sub_actions()

            self._sub_container.setVisible(True)

        else:

            self._expand_btn.setIcon(FluentIcon.CARE_RIGHT_SOLID)

            self._sub_container.setVisible(False)



    def _build_sub_actions(self):

        for w in self._sub_widgets:

            w.deleteLater()

        self._sub_widgets.clear()



        if self._action.action_type != ActionType.ACTION_GROUP_REF:

            return



        group_name = self._action.params.get('group_name', '')

        if not group_name:

            return



        from core.action_group import ensure_action_group_available

        group = ensure_action_group_available(group_name, self._local_group_manager)



        if not group:

            return



        for i, sub_action in enumerate(group.actions[:30]):

            w = SubActionRow(sub_action, i, depth=self._depth + 1, local_group_manager=self._local_group_manager)

            self._sub_widgets.append(w)

            self._sub_layout.addWidget(w)



        if len(group.actions) > 30:

            more_label = CaptionLabel(f"... 还有 {len(group.actions) - 30} 个动作")

            more_label.setStyleSheet("color: #888; padding-left: 28px;")

            self._sub_layout.addWidget(more_label)



    def expand_if_needed(self):

        if not self._expanded and self._action.action_type == ActionType.ACTION_GROUP_REF:

            self._toggle_expand()



    def set_local_group_manager(self, manager):

        self._local_group_manager = manager

        if self._expanded:

            self._build_sub_actions()

        for w in self._sub_widgets:

            if hasattr(w, 'set_local_group_manager'):

                w.set_local_group_manager(manager)



    def set_running(self, running: bool, repeat: int = 0, sub_index: int = -1):

        self._is_running = running

        self._is_completed = False

        self._current_repeat = repeat

        self._sub_action_index = sub_index



        if running:

            if self._action.action_type == ActionType.ACTION_GROUP_REF:

                if self._repeat_count > 1:

                    self._status_label.setText(f"▶R{repeat}/{self._repeat_count}")

                else:

                    self._status_label.setText("▶")

                self._status_label.setStyleSheet("color: #0078D4; font-weight: bold;")

                self.setStyleSheet("background-color: rgba(0, 120, 212, 0.1);")



                if sub_index >= 0:

                    self.expand_if_needed()

                    if len(self._sub_widgets) == 0:

                        self._build_sub_actions()



                    for i, w in enumerate(self._sub_widgets):

                        if hasattr(w, 'set_running'):

                            if i == sub_index:

                                w.set_running(True)

                            elif i < sub_index:

                                w.set_completed(True)

                            else:

                                w.reset()

            else:

                self._status_label.setText("▶")

                self._status_label.setStyleSheet("color: #0078D4; font-weight: bold;")

                self.setStyleSheet("background-color: rgba(0, 120, 212, 0.1);")

        else:

            self._status_label.setText("")

            self.setStyleSheet("")



    def set_completed(self, completed: bool):

        self._is_completed = completed

        self._is_running = False

        if completed:

            self._status_label.setText("✓")

            self._status_label.setStyleSheet("color: #16a34a; font-weight: bold;")

            self.setStyleSheet("background-color: rgba(22, 163, 74, 0.05);")

            for w in self._sub_widgets:

                if hasattr(w, 'set_completed'):

                    w.set_completed(True)

        else:

            self._status_label.setText("")

            self.setStyleSheet("")



    def reset(self):

        self._is_running = False

        self._is_completed = False

        self._current_repeat = 0

        self._sub_action_index = -1

        self._status_label.setText("")

        self.setStyleSheet("")

        for w in self._sub_widgets:

            if hasattr(w, 'reset'):

                w.reset()





class ScriptCard(CardWidget):

    run_requested = pyqtSignal(str)

    delete_requested = pyqtSignal(str)

    move_up_requested = pyqtSignal(str)

    move_down_requested = pyqtSignal(str)

    toggle_enabled = pyqtSignal(str, bool)

    

    def __init__(self, item: ScriptItem, index: int, parent=None, local_group_manager=None):

        super().__init__(parent)

        self._item = item

        self._index = index

        self._expanded = False

        self._sub_widgets: List[QWidget] = []

        self._is_running = False

        self._is_completed = False

        self._local_group_manager = local_group_manager

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



        local_mgr = self._local_group_manager or getattr(self._item, '_local_group_manager', None)



        for i, action in enumerate(self._item.actions[:50]):

            w = SubActionRow(action, i, depth=1, local_group_manager=local_mgr)

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

        for w in self._sub_widgets:

            if hasattr(w, 'reset'):

                w.reset()



    def set_sub_action_running(self, action_index: int, repeat: int = 0, sub_index: int = -1):

        if len(self._sub_widgets) == 0 and self._item.actions:

            self._build_sub_widgets()



        for i, w in enumerate(self._sub_widgets):

            if hasattr(w, 'set_running') and hasattr(w, 'set_completed'):

                if i == action_index:

                    w.set_running(True, repeat=repeat, sub_index=sub_index)

                elif i < action_index:

                    w.set_completed(True)

                else:

                    w.reset()



    def set_sub_action_completed(self, action_index: int):

        for i, w in enumerate(self._sub_widgets):

            if hasattr(w, 'set_completed'):

                if i <= action_index:

                    w.set_completed(True)

                else:

                    w.reset()



    def set_local_group_manager(self, manager):

        self._local_group_manager = manager

        if self._expanded:

            self._build_sub_widgets()

        for w in self._sub_widgets:

            if hasattr(w, 'set_local_group_manager'):

                w.set_local_group_manager(manager)



    def expand_if_needed(self):

        if not self._expanded:

            self._toggle_expand()

        elif len(self._sub_widgets) == 0 and self._item.actions:

            self._build_sub_widgets()





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

        icon_widget.setStyleSheet(f"color: {accent_color()};")

        layout.addWidget(icon_widget)

        

        content = QVBoxLayout()

        content.setSpacing(4)

        

        self._value_label = TitleLabel(self._value)

        content.addWidget(self._value_label)

        

        title_label = BodyLabel(self._title)

        title_label.setStyleSheet(muted_label_style())

        content.addWidget(title_label)

        

        layout.addLayout(content)

        layout.addStretch()

    

    def set_value(self, value: str):

        self._value_label.setText(value)





class _OverlayBase(QWidget):

    """半透明遮罩 + 居中卡片的窗口内覆盖层，替代会发白的 fluent 弹窗。"""



    def __init__(self, parent=None):

        super().__init__(parent)

        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setObjectName("overlayMask")

        self.setStyleSheet("#overlayMask { background-color: rgba(0, 0, 0, 0.45); }")

        self.hide()



        self._card = QFrame(self)

        self._card.setObjectName("overlayCard")

        card_bg = "#2b2b2b" if isDarkTheme() else "#ffffff"

        self._card.setStyleSheet(

            "#overlayCard { background-color: %s; border-radius: 10px;"

            " border: 1px solid rgba(128,128,128,0.28); }" % card_bg

        )

        self._card.setMaximumWidth(460)

        self.card_layout = QVBoxLayout(self._card)

        self.card_layout.setContentsMargins(24, 24, 24, 20)

        self.card_layout.setSpacing(14)



    def resizeEvent(self, event):

        if self.parentWidget():

            self.setGeometry(self.parentWidget().rect())

        self._center_card()

        super().resizeEvent(event)



    def _center_card(self):

        hint = self._card.sizeHint()

        w = min(max(hint.width(), 360), 460)

        self._card.resize(w, hint.height())

        x = (self.width() - self._card.width()) // 2

        y = (self.height() - self._card.height()) // 2

        self._card.move(max(0, x), max(0, y))



    def show_overlay(self):

        if self.parentWidget():

            self.setGeometry(self.parentWidget().rect())

        self.raise_()

        self.show()

        self._center_card()



    def hide_overlay(self):

        self.hide()



    def mousePressEvent(self, event):

        if not self._card.geometry().contains(event.pos()):

            self.hide_overlay()



# __OVERLAY_MORE__





class ScheduleCountdownWindow(QWidget):

    """执行前的倒计时提醒，独立顶层窗口。



    不依赖主窗口可见（空闲触发时主窗口通常已最小化到托盘），

    用不透明背景的普通 QWidget，避开 fluent 半透明遮罩弹窗发白的问题。

    """



    accepted = pyqtSignal()

    rejected = pyqtSignal()



    def __init__(self):

        super().__init__(None)

        self._remaining = 15

        self._total = 15



        self.setWindowTitle("SimpleRPA 定时执行")

        self.setWindowFlags(

            Qt.Window | Qt.WindowStaysOnTopHint | Qt.Tool

            | Qt.WindowCloseButtonHint

        )

        self.setFixedWidth(400)

        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setObjectName("countdownWindow")

        bg = "#2b2b2b" if isDarkTheme() else "#ffffff"

        border = "rgba(128,128,128,0.3)"

        self.setStyleSheet(

            "#countdownWindow { background-color: %s;"

            " border: 1px solid %s; }" % (bg, border)

        )



        from .app import get_icon_path

        icon_path = get_icon_path()

        if icon_path:

            from PyQt5.QtGui import QIcon

            self.setWindowIcon(QIcon(icon_path))



        layout = QVBoxLayout(self)

        layout.setContentsMargins(24, 24, 24, 20)

        layout.setSpacing(14)



        self._title = SubtitleLabel("即将自动运行全部脚本")

        layout.addWidget(self._title)



        self._desc = BodyLabel("")

        self._desc.setWordWrap(True)

        layout.addWidget(self._desc)



        self._bar = ProgressBar()

        self._bar.setFixedHeight(6)

        layout.addWidget(self._bar)



        btn_row = QHBoxLayout()

        btn_row.addStretch()

        self._cancel_btn = PushButton(FluentIcon.CANCEL, "取消本次")

        self._cancel_btn.clicked.connect(self._on_cancel)

        btn_row.addWidget(self._cancel_btn)

        self._run_now_btn = PrimaryPushButton(FluentIcon.PLAY, "立即运行")

        self._run_now_btn.clicked.connect(self._on_accept)

        btn_row.addWidget(self._run_now_btn)

        layout.addLayout(btn_row)



        self._timer = QTimer(self)

        self._timer.timeout.connect(self._tick)



    def start(self, seconds: int):

        self._remaining = max(1, seconds)

        self._total = self._remaining

        self._bar.setRange(0, self._total)

        self._update_text()

        self._show_centered()

        self._timer.start(1000)



    def _show_centered(self):

        self.adjustSize()

        screen = QApplication.primaryScreen()

        if screen:

            geo = screen.availableGeometry()

            x = geo.x() + (geo.width() - self.width()) // 2

            y = geo.y() + (geo.height() - self.height()) // 2

            self.move(max(geo.x(), x), max(geo.y(), y))

        self.show()

        self.raise_()



    def _update_text(self):

        self._desc.setText(

            f"将在 {self._remaining} 秒后开始执行。\n"

            f"如果你正在使用电脑，请点击「取消本次」。"

        )

        self._bar.setValue(self._remaining)



    def _tick(self):

        self._remaining -= 1

        if self._remaining <= 0:

            self._on_accept()

            return

        self._update_text()



    def _on_accept(self):

        self._timer.stop()

        self.hide()

        self.accepted.emit()



    def _on_cancel(self):

        self._timer.stop()

        self.hide()

        self.rejected.emit()



    def closeEvent(self, event):

        # 点窗口关闭按钮等同于取消本次

        if self._timer.isActive():

            self._timer.stop()

            self.rejected.emit()

        super().closeEvent(event)





class ScheduleSettingsOverlay(_OverlayBase):

    """定时设置面板，窗口内覆盖层。两种模式二选一：空闲时执行 / 定时执行。"""



    settings_changed = pyqtSignal()



    def __init__(self, config, parent=None):

        super().__init__(parent)

        self._config = config

        self._card.setMaximumWidth(440)



        header = QHBoxLayout()

        title = SubtitleLabel("定时设置")

        header.addWidget(title)

        header.addStretch()

        self._enable_switch = SwitchButton()

        self._enable_switch.setOnText("开")

        self._enable_switch.setOffText("关")

        header.addWidget(self._enable_switch)

        self.card_layout.addLayout(header)



        mode_row = QHBoxLayout()

        mode_row.setSpacing(10)

        mode_label = BodyLabel("模式")

        mode_label.setFixedWidth(56)

        mode_row.addWidget(mode_label)

        self._mode_combo = ComboBox()

        self._mode_combo.addItem("空闲时执行", userData="idle")

        self._mode_combo.addItem("定时执行", userData="time")

        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)

        mode_row.addWidget(self._mode_combo, 1)

        self.card_layout.addLayout(mode_row)



        self._time_row = QHBoxLayout()

        self._time_row.setSpacing(10)

        time_label = BodyLabel("时间")

        time_label.setFixedWidth(56)

        self._time_row.addWidget(time_label)

        self._time_edit = TimeEdit()

        self._time_edit.setDisplayFormat("HH:mm")

        self._time_row.addWidget(self._time_edit, 1)

        self.card_layout.addLayout(self._time_row)



        self._require_idle_cb = CheckBox("到点后还需系统空闲再执行")

        self.card_layout.addWidget(self._require_idle_cb)



        self._idle_row = QHBoxLayout()

        self._idle_row.setSpacing(10)

        idle_label = BodyLabel("空闲")

        idle_label.setFixedWidth(56)

        self._idle_row.addWidget(idle_label)

        self._idle_spin = SpinBox()

        self._idle_spin.setRange(10, 3600)

        self._idle_spin.setSuffix(" 秒无操作")

        self._idle_row.addWidget(self._idle_spin, 1)

        self.card_layout.addLayout(self._idle_row)



        countdown_row = QHBoxLayout()

        countdown_row.setSpacing(10)

        countdown_label = BodyLabel("提醒")

        countdown_label.setFixedWidth(56)

        countdown_row.addWidget(countdown_label)

        self._countdown_spin = SpinBox()

        self._countdown_spin.setRange(0, 120)

        self._countdown_spin.setSuffix(" 秒倒计时")

        countdown_row.addWidget(self._countdown_spin, 1)

        self.card_layout.addLayout(countdown_row)



        self._hint = CaptionLabel("")

        self._hint.setWordWrap(True)

        self._hint.setStyleSheet(muted_caption_style())

        self.card_layout.addWidget(self._hint)



        btn_row = QHBoxLayout()

        btn_row.addStretch()

        close_btn = PrimaryPushButton(FluentIcon.ACCEPT, "完成")

        close_btn.clicked.connect(self._on_done)

        btn_row.addWidget(close_btn)

        self.card_layout.addLayout(btn_row)



        self._require_idle_cb.stateChanged.connect(self._on_any_changed)

        self._enable_switch.checkedChanged.connect(self._on_any_changed)

        self._time_edit.timeChanged.connect(self._on_any_changed)

        self._idle_spin.valueChanged.connect(self._on_any_changed)

        self._countdown_spin.valueChanged.connect(self._on_any_changed)



        self._loading = False



    def load_from_config(self):

        cfg = self._config

        self._loading = True

        idx = self._mode_combo.findData(cfg.schedule_mode)

        self._mode_combo.setCurrentIndex(idx if idx >= 0 else 0)

        try:

            hh, mm = map(int, cfg.schedule_time.split(':'))

            self._time_edit.setTime(QTime(hh, mm))

        except (ValueError, AttributeError):

            self._time_edit.setTime(QTime(9, 0))

        self._require_idle_cb.setChecked(cfg.schedule_require_idle)

        self._idle_spin.setValue(max(10, cfg.schedule_idle_seconds))

        self._countdown_spin.setValue(max(0, cfg.schedule_prompt_countdown))

        self._enable_switch.setChecked(cfg.schedule_enabled)

        self._loading = False

        self._update_rows()

        self._update_hint()



    def _on_mode_changed(self, _i):

        self._update_rows()

        self._on_any_changed()



    def _update_rows(self):

        is_time = (self._mode_combo.currentData() == 'time')

        for i in range(self._time_row.count()):

            w = self._time_row.itemAt(i).widget()

            if w:

                w.setVisible(is_time)

        self._require_idle_cb.setVisible(is_time)

        # 空闲秒数：idle 模式始终需要；time 模式仅在勾选"还需空闲"时需要

        idle_needed = (not is_time) or self._require_idle_cb.isChecked()

        for i in range(self._idle_row.count()):

            w = self._idle_row.itemAt(i).widget()

            if w:

                w.setVisible(idle_needed)

        self._center_card()



    def _on_any_changed(self, *_):

        if self._loading:

            return

        self._update_rows()

        self._save()

        self._update_hint()



    def _save(self):

        cfg = self._config

        cfg.schedule_enabled = self._enable_switch.isChecked()

        cfg.schedule_mode = self._mode_combo.currentData() or 'idle'

        cfg.schedule_time = self._time_edit.time().toString("HH:mm")

        cfg.schedule_require_idle = self._require_idle_cb.isChecked()

        cfg.schedule_idle_seconds = self._idle_spin.value()

        cfg.schedule_prompt_countdown = self._countdown_spin.value()

        cfg.save()

        self.settings_changed.emit()



    def summary_text(self) -> str:

        cfg = self._config

        if not cfg.schedule_enabled:

            return "定时执行：未启用"

        if cfg.schedule_mode == 'time':

            base = f"每天 {cfg.schedule_time} 执行"

            if cfg.schedule_require_idle:

                base += f"（需空闲 {cfg.schedule_idle_seconds} 秒）"

        else:

            base = f"空闲 {cfg.schedule_idle_seconds} 秒后执行"

        base += "，每天一次"

        return base



    def _update_hint(self):

        self._hint.setText(self.summary_text())



    def _on_done(self):

        self.hide_overlay()

        self.settings_changed.emit()





class DashboardPage(QWidget):

    _update_progress_signal = pyqtSignal(float, int, int)

    _update_state_signal = pyqtSignal(object, str)

    _update_finished_signal = pyqtSignal(bool, str)

    _show_info_signal = pyqtSignal(str)

    _show_error_signal = pyqtSignal(str)

    _show_warning_signal = pyqtSignal(str)

    _sub_action_start_signal = pyqtSignal(object, int, object, int, list)

    _sub_action_end_signal = pyqtSignal(object, int, object, int, list, bool)

    _action_start_signal = pyqtSignal(object, int)

    _action_end_signal = pyqtSignal(object, int, bool)

    _set_local_group_manager_signal = pyqtSignal(object)

    _reset_all_cards_signal = pyqtSignal()

    _set_card_running_signal = pyqtSignal(int)

    _stop_signal = pyqtSignal()

    

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

        if hasattr(self, '_offscreen_cb'):

            self._offscreen_cb.setChecked(self._config.run_window_offscreen)





        self._schedule_overlay = ScheduleSettingsOverlay(self._config, self)

        self._schedule_overlay.settings_changed.connect(self._on_schedule_settings_changed)

        self._schedule_overlay.load_from_config()



        self._countdown_window = ScheduleCountdownWindow()

        self._countdown_window.accepted.connect(self._on_countdown_accepted)

        self._countdown_window.rejected.connect(self._on_countdown_rejected)



        self._schedule_timer = QTimer(self)

        self._schedule_timer.timeout.connect(self._check_schedule)

        self._schedule_prompt_active = False

        self._update_schedule_summary()

        if self._config.schedule_enabled:

            self._schedule_timer.start(20000)



        from PyQt5.QtCore import QTimer as _QTimer

        _QTimer.singleShot(100, self._load_last_list)

    

    def _setup_ui(self):

        layout = QVBoxLayout(self)

        layout.setContentsMargins(12, 12, 12, 12)

        layout.setSpacing(16)

        

        header_layout = QHBoxLayout()

        

        title = TitleLabel("控制台")

        header_layout.addWidget(title)

        

        subtitle = CaptionLabel("管理并运行桌面自动化流程")

        subtitle.setStyleSheet(muted_label_style("margin-left: 8px;"))

        header_layout.addWidget(subtitle, 0, Qt.AlignBottom)

        

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

        

        main_layout = QHBoxLayout()

        main_layout.setSpacing(20)
        

        left_panel = QWidget()

        left_layout = QVBoxLayout(left_panel)

        left_layout.setContentsMargins(0, 0, 0, 0)

        left_layout.setSpacing(12)

        

        main_card = HeaderCardWidget(self)

        main_card.setTitle("控制台")

        main_content = QWidget()

        main_layout_inner = QVBoxLayout(main_content)

        main_layout_inner.setContentsMargins(16, 10, 16, 12)

        main_layout_inner.setSpacing(10)

        

        preview_row = QHBoxLayout()

        preview_row.setSpacing(12)

        

        self._window_preview = WindowPreview(main_content)

        preview_row.addWidget(self._window_preview, 1)

        

        right_side = QVBoxLayout()

        right_side.setSpacing(8)

        right_side.setContentsMargins(0, 0, 0, 0)

        

        window_header = QHBoxLayout()

        window_header.setSpacing(6)

        window_label = StrongBodyLabel("目标窗口")

        window_header.addWidget(window_label)

        window_header.addStretch()

        self._refresh_btn = TransparentToolButton(FluentIcon.SYNC)

        self._refresh_btn.setFixedSize(22, 22)

        self._refresh_btn.clicked.connect(self._refresh_windows)

        window_header.addWidget(self._refresh_btn)

        self._close_window_btn = TransparentToolButton(FluentIcon.CLOSE)

        self._close_window_btn.setFixedSize(22, 22)

        self._close_window_btn.setToolTip("关闭目标窗口")

        self._close_window_btn.clicked.connect(self._close_target_window)

        window_header.addWidget(self._close_window_btn)

        right_side.addLayout(window_header)

        

        self._window_selector = WindowSelector()

        self._window_selector.refresh_windows()

        right_side.addWidget(self._window_selector)

        self._window_selector.window_selected.connect(self._on_window_selected_for_preview)

        

        launch_label = BodyLabel("启动命令")

        right_side.addWidget(launch_label)

        self._launch_combo = ComboBox()

        self._launch_combo.setMinimumHeight(32)

        self._launch_combo.addItem("无")

        self._refresh_launch_commands()

        right_side.addWidget(self._launch_combo)

        

        self._test_launch_btn = PushButton(FluentIcon.PLAY, "测试启动")

        self._test_launch_btn.setFixedHeight(28)

        self._test_launch_btn.clicked.connect(self._test_launch_command)

        right_side.addWidget(self._test_launch_btn)

        

        speed_row = QVBoxLayout()

        speed_row.setSpacing(6)

        self._speed_spin = create_compact_float_spin(

            0.1, 10.0, self._config.default_speed, suffix="x", width=68,

        )

        speed_row.addWidget(InlineNumericField("速度", self._speed_spin))

        self._repeat_spin = create_compact_int_spin(

            1, 999, self._config.default_repeat_count, width=60,

        )

        speed_row.addWidget(InlineNumericField("重复", self._repeat_spin))

        right_side.addLayout(speed_row)

        

        self._offscreen_cb = CheckBox("离屏后台")

        self._offscreen_cb.setToolTip("把目标窗口移到屏幕外并隐藏任务栏图标，结束后自动恢复")

        right_side.addWidget(self._offscreen_cb)

        

        self._schedule_btn = PushButton(FluentIcon.DATE_TIME, "定时设置")

        self._schedule_btn.setFixedHeight(30)

        self._schedule_btn.clicked.connect(self._open_schedule_settings)

        right_side.addWidget(self._schedule_btn)

        

        self._schedule_summary_label = CaptionLabel("未启用")

        self._schedule_summary_label.setStyleSheet(muted_caption_style())

        right_side.addWidget(self._schedule_summary_label)

        

        preview_row.addLayout(right_side)

        main_layout_inner.addLayout(preview_row)

        

        btn_row = QHBoxLayout()

        btn_row.setSpacing(10)

        

        self._run_btn = PrimaryPushButton(FluentIcon.PLAY, "运行全部")

        self._run_btn.setFixedHeight(34)

        self._run_btn.clicked.connect(self._on_run_btn_clicked)

        btn_row.addWidget(self._run_btn, 1)

        

        self._stop_btn = PushButton(FluentIcon.CANCEL, "停止")

        self._stop_btn.setFixedHeight(34)

        self._stop_btn.clicked.connect(self._stop)

        self._stop_btn.setEnabled(False)

        btn_row.addWidget(self._stop_btn, 1)

        

        main_layout_inner.addLayout(btn_row)

        

        main_card.viewLayout.addWidget(main_content)

        left_layout.addWidget(main_card, 1)

        

        status_card = CardWidget(self)

        status_layout = QVBoxLayout(status_card)

        status_layout.setContentsMargins(16, 10, 16, 10)

        status_layout.setSpacing(6)

        

        status_row = QHBoxLayout()

        self._status_icon = IconWidget(FluentIcon.INFO, self)

        self._status_icon.setFixedSize(14, 14)

        status_row.addWidget(self._status_icon)

        self._status_label = CaptionLabel("就绪 - 请添加脚本文件")

        status_row.addWidget(self._status_label, 1)

        status_layout.addLayout(status_row)

        

        self._progress_bar = ProgressBar()

        self._progress_bar.setFixedHeight(4)

        self._progress_bar.setVisible(False)

        status_layout.addWidget(self._progress_bar)

        

        left_layout.addWidget(status_card, 0)
        

        main_layout.addWidget(left_panel, 3)

        

        right_panel = QWidget()

        right_panel.setMinimumWidth(360)

        right_layout = QVBoxLayout(right_panel)

        right_layout.setContentsMargins(0, 0, 0, 0)

        right_layout.setSpacing(8)

        

        stats_layout = QHBoxLayout()

        stats_layout.setSpacing(12)

        

        self._total_card = StatCard("脚本数量", "0", FluentIcon.DOCUMENT)

        stats_layout.addWidget(self._total_card, 1)

        

        self._progress_card = StatCard("执行进度", "0%", FluentIcon.SPEED_HIGH)

        stats_layout.addWidget(self._progress_card, 1)

        

        self._repeat_card = StatCard("当前轮次", "1", FluentIcon.SYNC)

        stats_layout.addWidget(self._repeat_card, 1)

        

        right_layout.addLayout(stats_layout)

        

        task_header = QHBoxLayout()
        task_title = StrongBodyLabel("脚本列表")

        task_header.addWidget(task_title)

        self._script_count_label = CaptionLabel("0 项")

        self._script_count_label.setStyleSheet(muted_caption_style("margin-left: 6px;"))

        task_header.addWidget(self._script_count_label, 0, Qt.AlignVCenter)

        task_header.addStretch()

        

        clear_btn = TransparentToolButton(FluentIcon.DELETE)

        clear_btn.setFixedSize(24, 24)

        clear_btn.setToolTip("清空列表")

        clear_btn.clicked.connect(self._clear_list)

        task_header.addWidget(clear_btn)

        

        right_layout.addLayout(task_header)

        

        self._scroll_area = ScrollArea()

        self._scroll_area.setWidgetResizable(True)

        self._scroll_area.setStyleSheet(scroll_border_style())

        

        self._task_container = QWidget()

        self._task_container.setStyleSheet("background: transparent;")

        self._task_layout = QVBoxLayout(self._task_container)

        self._task_layout.setAlignment(Qt.AlignTop)

        self._task_layout.setContentsMargins(8, 8, 8, 8)

        self._task_layout.setSpacing(6)

        self._task_layout.addStretch()

        

        self._scroll_area.setWidget(self._task_container)

        right_layout.addWidget(self._scroll_area)

        

        self._empty_label = QWidget()

        empty_layout = QVBoxLayout(self._empty_label)

        empty_layout.setContentsMargins(32, 48, 32, 48)

        empty_layout.setSpacing(10)

        

        empty_icon = IconWidget(FluentIcon.DOCUMENT)

        empty_icon.setFixedSize(40, 40)

        empty_layout.addWidget(empty_icon, 0, Qt.AlignCenter)

        

        empty_text = SubtitleLabel("暂无脚本")

        empty_text.setAlignment(Qt.AlignCenter)

        empty_layout.addWidget(empty_text)

        

        empty_hint = CaptionLabel("点击「添加脚本」将 .rpa.json 加入列表")

        empty_hint.setAlignment(Qt.AlignCenter)

        empty_hint.setStyleSheet(muted_caption_style())

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

        self._sub_action_start_signal.connect(self._on_sub_action_start)

        self._sub_action_end_signal.connect(self._on_sub_action_end)

        self._action_start_signal.connect(self._on_action_start)

        self._action_end_signal.connect(self._on_action_end)

        self._set_local_group_manager_signal.connect(self._on_set_local_group_manager)

        self._reset_all_cards_signal.connect(self._on_reset_all_cards)

        self._set_card_running_signal.connect(self._on_set_card_running)

        self._stop_signal.connect(self._on_stop_gui)



    def _open_schedule_settings(self):

        self._schedule_overlay.load_from_config()

        self._schedule_overlay.show_overlay()



    def _on_schedule_settings_changed(self):

        self._config.run_window_offscreen = self._offscreen_cb.isChecked()



        self._config.save()

        if self._config.schedule_enabled:

            if not self._schedule_timer.isActive():

                self._schedule_timer.start(20000)

        else:

            self._schedule_timer.stop()

        self._update_schedule_summary()



    def _update_schedule_summary(self):

        self._schedule_summary_label.setText(self._schedule_overlay.summary_text())



    def _refresh_windows(self):

        self._window_selector.refresh_windows()

    

    def _on_window_selected_for_preview(self, hwnd):

        self._window_preview.set_hwnd(hwnd)

    

    def _refresh_window_preview(self):

        self._window_preview.update_preview()

    

    def _close_target_window(self):

        hwnd = self._window_selector.get_selected_hwnd()

        if not hwnd:

            self._show_warning("请先选择目标窗口")

            return

        try:

            import win32gui

            win32gui.PostMessage(hwnd, 0x0010, 0, 0)

            self._show_info("已发送关闭消息")

        except Exception as e:

            self._show_error(f"关闭窗口失败: {e}")

    

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

    

    def _test_launch_command(self):

        cmd_id = self._get_selected_launch_command_id()

        if not cmd_id:

            self._show_warning("请先选择一个启动命令")

            return

        

        try:

            cmd_manager = CommandManager.get_instance()

            cmd = cmd_manager.get_command(cmd_id)

            if not cmd:

                self._show_error("启动命令不存在")

                return

            

            self._show_info(f"正在测试启动: {cmd.name}")

            success, message = cmd_manager.execute_command(cmd_id)

            

            if success:

                self._show_info(f"启动命令执行成功: {cmd.name}")

            else:

                self._show_error(f"启动命令执行失败: {message}")

        except Exception as e:

            self._show_error(f"测试启动失败: {e}")

    

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

                    local_group_manager = LocalActionGroupManager()

                    result = Exporter.import_from_json(filepath, local_group_manager)

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

                    item._local_group_manager = local_group_manager

                    print(f"[DEBUG] 加载脚本: {name}, local_group_manager={local_group_manager}, groups={list(local_group_manager._groups.keys()) if hasattr(local_group_manager, '_groups') else 'N/A'}")

                    self._scripts.append(item)

                except Exception as e:

                    print(f"加载脚本失败: {filepath}, {e}")

            

            self._refresh_list()

    

    def _refresh_list(self):

        for card in self._script_cards:

            card.deleteLater()

        self._script_cards.clear()

        

        count = len(self._scripts)

        self._empty_label.setVisible(count == 0)

        self._scroll_area.setVisible(count > 0)

        self._total_card.set_value(str(count))

        if hasattr(self, '_script_count_label'):

            self._script_count_label.setText(f"{count} 项")

        

        for i, item in enumerate(self._scripts):

            local_mgr = getattr(item, '_local_group_manager', None)

            card = ScriptCard(item, i, local_group_manager=local_mgr)

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

                script_path = s.get('path', '')

                if not script_path or not os.path.exists(script_path):

                    continue

                local_group_manager = LocalActionGroupManager()

                result = Exporter.import_from_json(script_path, local_group_manager)

                if result is None:

                    continue

                actions = result if isinstance(result, list) else result.get('actions', [])

                if not actions:

                    continue

                item = ScriptItem(

                    id=s['id'],

                    name=s['name'],

                    path=script_path,

                    actions=actions,

                    delay_before=s.get('delay_before', 0),

                    repeat_count=s.get('repeat_count', 1),

                    enabled=s.get('enabled', True)

                )

                item._local_group_manager = local_group_manager

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

            if 'offscreen' in data:
                self._offscreen_cb.setChecked(data['offscreen'])



            

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

                        'description': cmd.description,

                        'delay_after_launch': cmd.delay_after_launch

                    }

            

            data = {

                'scripts': scripts_data,

                'window': window_info,

                'speed': self._speed_spin.value(),

                'repeat': self._repeat_spin.value(),

                'offscreen': self._offscreen_cb.isChecked(),


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

        

        self._stop_btn.setEnabled(True)

        self._run_btn.setText("暂停")

        



        

        self._reset_all_cards_signal.emit()

        self._set_card_running_signal.emit(self._current_script_index)

        

        import threading

        thread = threading.Thread(target=self._execute_script_with_finish, args=(item,), daemon=True)

        thread.start()

    

    def _execute_script_with_finish(self, item: ScriptItem):

        self._execute_script(item)

        self._update_finished_signal.emit(self._is_running, "")



    def _check_schedule(self):

        from datetime import datetime

        cfg = self._config

        if not cfg.schedule_enabled:

            return

        if self._is_running or self._schedule_prompt_active:

            return



        now = datetime.now()

        today_key = now.strftime("%Y-%m-%d")

        # 每天只执行一次

        if cfg.schedule_last_run_date == today_key:

            return



        from utils.idle_monitor import get_idle_seconds



        if cfg.schedule_mode == 'time':

            # 定时执行：到点后触发（可选附加空闲条件）

            target = cfg.schedule_time

            if now.strftime("%H:%M") < target:

                return

            if cfg.schedule_require_idle:

                if get_idle_seconds() < cfg.schedule_idle_seconds:

                    return

        else:

            # 空闲执行：检测到足够空闲即触发，不限时间

            if get_idle_seconds() < cfg.schedule_idle_seconds:

                return



        # 先占位标记今天已运行，避免倒计时期间或运行中重复触发

        cfg.schedule_last_run_date = today_key

        cfg.save()

        self._trigger_scheduled_run()



    def _trigger_scheduled_run(self):

        enabled_scripts = [s for s in self._scripts if s.enabled]

        if not enabled_scripts:

            self._show_warning("定时触发：没有可运行的脚本")

            return



        countdown = self._config.schedule_prompt_countdown

        if countdown > 0:

            self._schedule_prompt_active = True

            self._countdown_window.start(countdown)

            return



        self._show_info("定时触发：开始运行全部脚本")

        self._run_all()



    def _on_countdown_accepted(self):

        self._schedule_prompt_active = False

        self._show_info("定时触发：开始运行全部脚本")

        self._run_all()



    def _on_countdown_rejected(self):

        self._schedule_prompt_active = False

        self._show_info("定时执行已取消本次")


    def _on_run_btn_clicked(self):
        if self._is_running and self._player:
            self._player.toggle_pause()
            is_paused = self._player.state == PlayerState.PAUSED
            self._run_btn.setText("继续" if is_paused else "暂停")
        else:
            self._run_all()


    def _run_all(self):

        enabled_scripts = [s for s in self._scripts if s.enabled]

        if not enabled_scripts:

            self._show_warning("请添加并启用至少一个脚本")

            return

        self._is_running = True

        self._stop_btn.setEnabled(True)
        self._run_btn.setText("暂停")
        self._reset_all_cards_signal.emit()

        

        import threading

        thread = threading.Thread(target=self._execute_all, daemon=True)

        thread.start()

    

    def _execute_script(self, item: ScriptItem):

        import time

        

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

                        launch_delay = cmd.delay_after_launch

                        if launch_delay > 0:

                            self._show_info_signal.emit(f"等待 {launch_delay} 秒后开始执行...")

                            waited = 0

                            while waited < launch_delay:

                                if not self._is_running:

                                    return

                                time.sleep(0.1)

                                waited += 0.1

                        

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

        

        local_group_manager = getattr(item, '_local_group_manager', None) or LocalActionGroupManager()

        result = Exporter.import_from_json(item.path, local_group_manager)

        if not result:

            return

        

        actions = result if isinstance(result, list) else result.get('actions', [])

        if not actions:

            return

        

        self._player = Player(tab_key="dashboard", local_group_manager=local_group_manager)

        self._player.set_actions(actions)

        self._player.set_speed(self._speed_spin.value())

        self._player.set_repeat_count(item.repeat_count)

        

        self._player.add_callback('on_action_start', lambda a, i: self._action_start_signal.emit(a, i))

        self._player.add_callback('on_action_end', lambda a, i, s: self._action_end_signal.emit(a, i, s))

        self._player.add_callback('on_sub_action_start', lambda pa, pi, sa, si, idx: self._sub_action_start_signal.emit(pa, pi, sa, si, idx))

        self._player.add_callback('on_sub_action_end', lambda pa, pi, sa, si, idx, s: self._sub_action_end_signal.emit(pa, pi, sa, si, idx, s))

        

        if self._current_script_index >= 0 and self._current_script_index < len(self._script_cards):

            self._script_cards[self._current_script_index]._local_group_manager = local_group_manager

        

        if selected_hwnd:

            self._player.set_window_hwnd(selected_hwnd, self._window_utils)

            window_offset = self._window_selector.get_window_offset()

            self._player.set_window_offset(window_offset)

        

        if window_title:

            self._player.set_window_title(window_title)



        offscreen_requested = bool(selected_hwnd and self._offscreen_cb.isChecked())

        offscreen_supported = can_actions_run_offscreen(actions, local_group_manager=local_group_manager) if offscreen_requested else False

        offscreen_enabled = offscreen_requested

        if offscreen_enabled:

            run_mode = "offscreen_hidden_taskbar"

        else:

            run_mode = "normal"

        self._player.set_window_run_mode(run_mode)

        if offscreen_requested and not offscreen_supported:

            self._show_warning_signal.emit("已强制启用离屏后台；当前脚本含可能依赖前台的动作，若失败请把相关动作改成后台模式。")

        

        total_actions = len(actions)

        self._status_label.setText(f"开始执行 {total_actions} 个动作，共 {item.repeat_count} 轮...")

        

        if selected_hwnd and not offscreen_enabled:

            self._window_utils.set_window_topmost(selected_hwnd)

            # 强制激活并触发重绘，避免目标窗口首帧空白（白屏）。

            self._window_utils.force_foreground_window(selected_hwnd)

            time.sleep(0.3)



        self._player.play()

        

        topmost_check_counter = 0

        while self._player.state not in [PlayerState.IDLE]:

            if not self._is_running:

                self._player.stop_and_wait(timeout=2.0)

                break

            time.sleep(0.1)

            

            if selected_hwnd and not offscreen_enabled:

                topmost_check_counter += 1

                if topmost_check_counter >= 10:

                    self._window_utils.set_window_topmost(selected_hwnd)

                    topmost_check_counter = 0

        

        if selected_hwnd and not offscreen_enabled:

            self._window_utils.remove_window_topmost(selected_hwnd)

    

    def _execute_all(self):

        import time

        

        enabled_scripts = [s for s in self._scripts if s.enabled]

        total = len(enabled_scripts)

        

        for i, item in enumerate(enabled_scripts):

            if not self._is_running:

                break

            

            idx = self._scripts.index(item)

            self._current_script_index = idx

            

            self._reset_all_cards_signal.emit()

            self._set_card_running_signal.emit(idx)

            

            progress = (i + 1) / total

            self._update_progress_signal.emit(progress, i + 1, 1)

            

            self._execute_script(item)

        

        self._update_finished_signal.emit(self._is_running, "")

    

    def _stop(self):

        self._is_running = False

        self._stop_signal.emit()

    def _pause(self):

        pass

    def _on_progress(self, progress, index, repeat):

        if progress >= 0:

            self._progress_bar.setValue(int(progress * 100))

            self._progress_card.set_value(f"{int(progress * 100)}%")

        self._repeat_card.set_value(str(repeat))

        

        if self._player:

            total_actions = len(self._player.actions)

            total = self._player.repeat_count

            self._status_label.setText(f"执行中: 第 {repeat}/{total} 轮 | 动作 {index + 1}/{total_actions}")

    

    def _on_action_start(self, action, index):

        if self._current_script_index >= 0 and self._current_script_index < len(self._script_cards):

            card = self._script_cards[self._current_script_index]

            card.expand_if_needed()

            

            repeat = 0

            sub_index = -1

            if action.action_type == ActionType.ACTION_GROUP_REF:

                repeat = getattr(action, '_current_repeat', 1) or 1

            

            card.set_sub_action_running(index, repeat=repeat, sub_index=sub_index)

            

            action_desc = action.description[:30]

            total_actions = len(self._player.actions) if self._player else 0

            if self._player:

                total = self._player.repeat_count

                repeat = self._player.current_repeat

                self._status_label.setText(f"第 {repeat}/{total} 轮 | {action_desc} | 动作 {index + 1}/{total_actions}")

    

    def _on_action_end(self, action, index, success):
        if self._current_script_index >= 0 and self._current_script_index < len(self._script_cards):

            card = self._script_cards[self._current_script_index]

            card.set_sub_action_completed(index)

    

    def _on_sub_action_start(self, parent_action, parent_index, sub_action, sub_index, indices):

        if self._current_script_index >= 0 and self._current_script_index < len(self._script_cards):

            card = self._script_cards[self._current_script_index]

            card.expand_if_needed()

            

            current_repeat = getattr(parent_action, '_current_repeat', 1) or 1

            

            if len(indices) == 1:

                card.set_sub_action_running(parent_index, repeat=current_repeat, sub_index=sub_index)

            elif len(indices) > 1:

                pass

            

            sub_desc = sub_action.description[:25]

            group_name = parent_action.params.get('group_name', '') if parent_action.action_type == ActionType.ACTION_GROUP_REF else ''

            total_actions = len(self._player.actions) if self._player else 0

            

            if group_name:

                repeat_count = parent_action.repeat_count or 1

                if self._player:

                    total = self._player.repeat_count

                    repeat = self._player.current_repeat

                    self._status_label.setText(f"第 {repeat}/{total} 轮 | [{group_name}] R{current_repeat}/{repeat_count} | {sub_desc}")

    

    def _on_sub_action_end(self, parent_action, parent_index, sub_action, sub_index, indices, success):

        pass

    

    def _on_set_local_group_manager(self, manager):

        if self._current_script_index >= 0 and self._current_script_index < len(self._script_cards):

            self._script_cards[self._current_script_index].set_local_group_manager(manager)

    

    def _on_reset_all_cards(self):

        for card in self._script_cards:

            card.reset()

    

    def _on_set_card_running(self, index: int):

        if 0 <= index < len(self._script_cards):

            self._script_cards[index].set_running(True)

    

    def _on_stop_gui(self):

        self._run_btn.setEnabled(True)

        self._stop_btn.setEnabled(False)
        self._run_btn.setText("运行全部")

        self._show_info("已停止")

    

    def _on_state_changed(self, state, message):

        if state == PlayerState.IDLE:

            self._run_btn.setEnabled(True)

            self._stop_btn.setEnabled(False)
            self._run_btn.setText("运行全部")

        

    def _on_finished(self, success, message):

        self._is_running = False

        self._run_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._run_btn.setText("运行全部")

        self._progress_bar.setVisible(False)

        if self._player and hasattr(self._player, '_restore_window_after_run'):

            self._player._restore_window_after_run()

        

        if success:

            if self._player:

                total_actions = len(self._player.actions)

                total_repeats = self._player.current_repeat

                self._status_label.setText(f"执行完成 | 共 {total_actions} 个动作，{total_repeats} 轮")

                from utils.notification import send_notification

                send_notification("SimpleRPA 执行完成", f"已完成 {total_actions} 个动作，共 {total_repeats} 轮")

            else:

                self._status_label.setText("执行完成")

            self._status_icon.setIcon(FluentIcon.COMPLETED)

            for card in self._script_cards:

                card.reset()

        else:

            if self._player:

                self._status_label.setText(f"已停止 | 已完成 {self._player.current_index} 个动作")

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

