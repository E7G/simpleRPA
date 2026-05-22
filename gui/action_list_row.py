"""Clash Verge 风格动作列表行（流程设计器 / 控制台脚本列表共用）。"""
from typing import List, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QSizePolicy,
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize

from qfluentwidgets import (
    BodyLabel, CaptionLabel, IconWidget, FluentIcon, TransparentToolButton,
)

from core.actions import Action, ActionType
from .fluent_theme import (
    accent_color, muted_caption_style, text_primary, text_muted,
    isDarkTheme, themeColor,
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


def notify_layout_changed(widget: QWidget):
    w = widget
    while w:
        w.adjustSize()
        w.updateGeometry()
        lay = w.layout()
        if lay:
            lay.invalidate()
            lay.activate()
        w = w.parentWidget()


def _nested_list_style() -> str:
    if isDarkTheme():
        bg = "rgba(255, 255, 255, 0.04)"
    else:
        bg = "rgba(0, 0, 0, 0.03)"
    return f"""
        QFrame#nestedActionList {{
            background-color: {bg};
            border: none;
            border-radius: 6px;
        }}
    """


def _row_idle_style() -> str:
    return "ActionListRow { background: transparent; border: none; }"


def _row_running_style() -> str:
    c = themeColor()
    return (
        f"ActionListRow {{ background-color: rgba({c.red()}, {c.green()}, {c.blue()}, 0.12);"
        f" border: none; border-radius: 4px; }}"
    )


def _row_completed_style() -> str:
    return "ActionListRow { background-color: rgba(22, 163, 74, 0.08); border: none; border-radius: 4px; }"


class NestedActionList(QFrame):
    """展开后的嵌套动作列表容器。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("nestedActionList")
        self.setStyleSheet(_nested_list_style())
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 6)
        self._layout.setSpacing(0)

    def clear_rows(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

    def add_row(self, row: QWidget):
        self._layout.addWidget(row)


class ActionListRow(QWidget):
    """单行动作；动作组可展开子动作。"""

    delete_requested = pyqtSignal()

    ROW_HEIGHT = 34

    def __init__(
        self,
        action: Action,
        index: int,
        depth: int = 0,
        parent=None,
        local_group_manager=None,
        show_delete: bool = False,
        allow_group_expand: bool = True,
    ):
        super().__init__(parent)
        self.setObjectName("ActionListRow")
        self._action = action
        self._index = index
        self._depth = depth
        self._local_group_manager = local_group_manager
        self._show_delete = show_delete
        self._allow_group_expand = allow_group_expand
        self._expanded = False
        self._child_rows: List[ActionListRow] = []
        self._is_running = False
        self._is_completed = False
        self._repeat_count = action.repeat_count or 1
        self._setup_ui()

    def _is_group(self) -> bool:
        return self._action.action_type == ActionType.ACTION_GROUP_REF

    def _setup_ui(self):
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(self.ROW_HEIGHT)
        self.setStyleSheet(_row_idle_style())

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._header = QWidget()
        hl = QHBoxLayout(self._header)
        hl.setContentsMargins(8 + self._depth * 14, 0, 6, 0)
        hl.setSpacing(6)

        self._index_label = CaptionLabel(f"{self._index + 1}")
        self._index_label.setFixedWidth(18)
        self._index_label.setAlignment(Qt.AlignCenter)
        self._index_label.setStyleSheet(
            f"color: {text_muted()}; font-size: 11px; background: transparent;"
        )
        hl.addWidget(self._index_label)

        if self._is_group() and self._allow_group_expand:
            self._expand_btn = TransparentToolButton(FluentIcon.CHEVRON_RIGHT_MED)
            self._expand_btn.setFixedSize(20, 20)
            self._expand_btn.clicked.connect(self._toggle_expand)
            hl.addWidget(self._expand_btn)
            iw = IconWidget(FluentIcon.FOLDER)
            iw.setFixedSize(16, 16)
            hl.addWidget(iw)
        else:
            ph = QWidget()
            ph.setFixedSize(20, 20)
            hl.addWidget(ph)
            icon = ACTION_ICONS.get(self._action.action_type, FluentIcon.PLAY)
            iw = IconWidget(icon)
            iw.setFixedSize(16, 16)
            hl.addWidget(iw)

        desc = self._action.description or "未命名动作"
        if len(desc) > 52:
            desc = desc[:49] + "..."
        self._desc_label = BodyLabel(desc)
        self._desc_label.setStyleSheet(
            f"color: {text_primary()}; font-size: 13px; background: transparent;"
        )
        hl.addWidget(self._desc_label, 1)

        self._status_label = CaptionLabel("")
        self._status_label.setFixedWidth(44)
        self._status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        hl.addWidget(self._status_label)

        if self._show_delete:
            del_btn = TransparentToolButton(FluentIcon.DELETE)
            del_btn.setFixedSize(22, 22)
            del_btn.setToolTip("删除")
            del_btn.clicked.connect(self.delete_requested.emit)
            hl.addWidget(del_btn)

        root.addWidget(self._header)

        self._nested = NestedActionList()
        self._nested.setVisible(False)
        root.addWidget(self._nested)

    def _toggle_expand(self):
        if not self._is_group() or not self._allow_group_expand:
            return
        self._expanded = not self._expanded
        if self._expanded:
            self._expand_btn.setIcon(FluentIcon.CHEVRON_DOWN_MED)
            self._build_children()
            self._nested.setVisible(True)
            self.setFixedHeight(self.ROW_HEIGHT + self._nested.sizeHint().height())
        else:
            self._expand_btn.setIcon(FluentIcon.CHEVRON_RIGHT_MED)
            self._nested.setVisible(False)
            self._nested.clear_rows()
            self._child_rows.clear()
            self.setFixedHeight(self.ROW_HEIGHT)
        notify_layout_changed(self)

    def _build_children(self):
        self._nested.clear_rows()
        self._child_rows.clear()

        group_name = self._action.params.get("group_name", "")
        if not group_name:
            hint = CaptionLabel("未指定动作组名称")
            hint.setStyleSheet(muted_caption_style("padding: 6px 8px;"))
            self._nested._layout.addWidget(hint)
            return

        from core.action_group import ensure_action_group_available
        group = ensure_action_group_available(group_name, self._local_group_manager)
        if not group:
            hint = CaptionLabel(f"无法加载: {group_name}")
            hint.setStyleSheet(muted_caption_style("padding: 6px 8px;"))
            self._nested._layout.addWidget(hint)
            return

        for i, sub in enumerate(group.actions[:40]):
            row = ActionListRow(
                sub, i, depth=self._depth + 1,
                local_group_manager=self._local_group_manager,
                show_delete=False,
                allow_group_expand=True,
            )
            self._child_rows.append(row)
            self._nested.add_row(row)

        if len(group.actions) > 40:
            more = CaptionLabel(f"… 还有 {len(group.actions) - 40} 项")
            more.setStyleSheet(muted_caption_style("padding: 4px 8px;"))
            self._nested._layout.addWidget(more)

        h = self._nested.sizeHint().height()
        self.setFixedHeight(self.ROW_HEIGHT + h)

    def expand_if_needed(self):
        if self._is_group() and self._allow_group_expand and not self._expanded:
            self._toggle_expand()

    def set_local_group_manager(self, manager):
        self._local_group_manager = manager
        if self._expanded:
            self._build_children()
        for c in self._child_rows:
            c.set_local_group_manager(manager)

    def set_running(self, running: bool, repeat: int = 0, sub_index: int = -1):
        self._is_running = running
        self._is_completed = False
        if running:
            self.setStyleSheet(_row_running_style())
            if self._is_group() and self._repeat_count > 1:
                self._status_label.setText(f"R{repeat}/{self._repeat_count}")
            else:
                self._status_label.setText("▶")
            self._status_label.setStyleSheet(f"color: {accent_color()}; font-weight: 600;")
            if sub_index >= 0:
                self.expand_if_needed()
                for i, c in enumerate(self._child_rows):
                    if i == sub_index:
                        c.set_running(True)
                    elif i < sub_index:
                        c.set_completed(True)
                    else:
                        c.reset()
        else:
            self._status_label.setText("")
            self.setStyleSheet(_row_idle_style())

    def set_completed(self, completed: bool):
        self._is_completed = completed
        self._is_running = False
        if completed:
            self.setStyleSheet(_row_completed_style())
            self._status_label.setText("✓")
            self._status_label.setStyleSheet(f"color: #16A34A; font-weight: 600;")
            for c in self._child_rows:
                c.set_completed(True)
        else:
            self._status_label.setText("")
            self.setStyleSheet(_row_idle_style())

    def reset(self):
        self._is_running = False
        self._is_completed = False
        self._status_label.setText("")
        self.setStyleSheet(_row_idle_style())
        for c in self._child_rows:
            c.reset()

    def sizeHint(self) -> QSize:
        h = self.ROW_HEIGHT
        if self._expanded and self._nested.isVisible():
            h += self._nested.sizeHint().height()
        return QSize(-1, h)
