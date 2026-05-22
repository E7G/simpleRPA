"""Power Automate 风格的 Fluent Design 主题与面板组件。"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QApplication, QLabel,
    QAbstractSpinBox, QGridLayout, QSizePolicy,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from qfluentwidgets import (
    setTheme, Theme, setThemeColor, isDarkTheme,
    StrongBodyLabel, BodyLabel, CaptionLabel, themeColor, SpinBox, DoubleSpinBox,
)

try:
    from qfluentwidgets import CompactSpinBox, CompactDoubleSpinBox
except ImportError:
    CompactSpinBox = SpinBox
    CompactDoubleSpinBox = DoubleSpinBox


ACCENT = "#0078D4"
PA_BRAND = "#742774"


def apply_app_theme():
    setTheme(Theme.AUTO)
    setThemeColor(ACCENT)
    font = QApplication.font()
    font.setFamily("Segoe UI")
    font.setPointSize(11)
    QApplication.setFont(font)


def text_primary() -> str:
    return "#FFFFFF" if isDarkTheme() else "#1A1A1A"


def text_secondary() -> str:
    return "rgba(255, 255, 255, 0.72)" if isDarkTheme() else "rgba(0, 0, 0, 0.62)"


def text_muted() -> str:
    return "rgba(255, 255, 255, 0.50)" if isDarkTheme() else "rgba(0, 0, 0, 0.45)"


def accent_color() -> str:
    return themeColor().name()


def success_color() -> str:
    return "#4ADE80" if isDarkTheme() else "#16A34A"


def muted_label_style(extra: str = "") -> str:
    return f"color: {text_secondary()}; {extra}".strip()


def muted_caption_style(extra: str = "") -> str:
    return f"color: {text_muted()}; {extra}".strip()


def _panel_border_color() -> str:
    if isDarkTheme():
        return "rgba(255, 255, 255, 0.10)"
    return "rgba(0, 0, 0, 0.10)"


def _panel_bg_color() -> str:
    if isDarkTheme():
        return "rgba(255, 255, 255, 0.05)"
    return "rgba(0, 0, 0, 0.03)"


def _canvas_bg_color() -> str:
    if isDarkTheme():
        return "rgba(255, 255, 255, 0.07)"
    return "#FAFAFA"


def step_badge_style(running: bool = False) -> str:
    c = themeColor()
    if running:
        return (
            f"background-color: {c.name()}; color: #FFFFFF; font-weight: bold;"
            f"border-radius: 14px; min-width: 28px; min-height: 28px; padding: 2px 8px;"
        )
    return (
        f"background-color: rgba({c.red()}, {c.green()}, {c.blue()}, 0.20);"
        f"color: {c.name()}; font-weight: bold; border-radius: 14px;"
        f"min-width: 28px; min-height: 28px; padding: 2px 8px;"
    )


def make_step_index_label(text: str, parent=None, running: bool = False) -> QLabel:
    """流程步骤序号，宽度随数字位数自适应。"""
    label = StrongBodyLabel(text, parent)
    label.setAlignment(Qt.AlignCenter)
    label.setMinimumHeight(28)
    label.setStyleSheet(step_badge_style(running))
    return label


def make_flow_index_label(text: str, parent=None) -> QLabel:
    """控制台/子步骤序号。"""
    label = StrongBodyLabel(text, parent)
    label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
    label.setMinimumWidth(22)
    label.setStyleSheet(
        f"color: {accent_color()}; font-weight: bold; padding: 0 4px;"
    )
    return label


def panel_title_style() -> str:
    """面板标题（无背景块，参考 Clash Verge 设置分组标题）。"""
    return (
        f"color: {text_secondary()}; font-size: 12px; font-weight: 600;"
        "background: transparent; border: none; padding: 0;"
    )


class AutomatePanel(QFrame):
    """带标题的分栏面板，Clash Verge 风格：透明标题栏 + 细边框容器。"""

    def __init__(self, title: str = "", parent=None, canvas: bool = False):
        super().__init__(parent)
        self.setObjectName("automatePanel")
        bg = _canvas_bg_color() if canvas else _panel_bg_color()
        border = _panel_border_color()
        self.setStyleSheet(f"""
            QFrame#automatePanel {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QFrame#automatePanel QWidget#automatePanelHeader {{
                background: transparent;
                border: none;
            }}
            QFrame#automatePanel QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._header = QWidget()
        self._header.setObjectName("automatePanelHeader")
        self._header.setFixedHeight(36 if title else 44)
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(12, 8, 12, 4)
        header_layout.setSpacing(8)

        self._title_label = None
        if title:
            self._title_label = CaptionLabel(title)
            self._title_label.setStyleSheet(panel_title_style())
            header_layout.addWidget(self._title_label)

        header_layout.addStretch()
        layout.addWidget(self._header)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background-color: {border}; border: none;")
        layout.addWidget(divider)

        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        self.content_layout.setSpacing(8)
        content = QWidget()
        content.setObjectName("automatePanelContent")
        content.setLayout(self.content_layout)
        content.setStyleSheet("background: transparent;")
        layout.addWidget(content, 1)

    def add_header_widget(self, widget: QWidget):
        header_layout = self._header.layout()
        header_layout.insertWidget(header_layout.count() - 1, widget)


def compact_spin_style() -> str:
    """紧凑数字框样式（Clash Verge 风格：小按钮 + 清晰数值）。"""
    fg = text_primary()
    accent = accent_color()
    if isDarkTheme():
        bg = "rgba(255, 255, 255, 0.08)"
    else:
        bg = "#FFFFFF"
    border = _panel_border_color()
    selectors = (
        "CompactSpinBox, CompactDoubleSpinBox, "
        "SpinBox, DoubleSpinBox"
    )
    line_selectors = (
        "CompactSpinBox QLineEdit, CompactDoubleSpinBox QLineEdit, "
        "SpinBox QLineEdit, DoubleSpinBox QLineEdit"
    )
    return f"""
        {selectors} {{
            color: {fg};
            background-color: {bg};
            border: 1px solid {border};
            border-radius: 6px;
            min-height: 28px;
            max-height: 28px;
            padding: 0 4px;
        }}
        {line_selectors} {{
            color: {fg};
            background-color: transparent;
            border: none;
            padding: 2px 4px;
            min-height: 22px;
            selection-background-color: {accent};
            selection-color: #FFFFFF;
        }}
    """


def toolbar_spin_style() -> str:
    return compact_spin_style()


def apply_compact_spin(spin: QWidget):
    """应用紧凑样式并保证数值区域可读。"""
    spin.setStyleSheet(compact_spin_style())
    spin.setFixedHeight(28)
    if type(spin).__name__.startswith("Compact") and hasattr(spin, "setButtonSymbols"):
        spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
    line = spin.lineEdit() if hasattr(spin, "lineEdit") else None
    if line:
        line.setAlignment(Qt.AlignCenter)
        line.setStyleSheet(
            f"color: {text_primary()}; background: transparent; border: none;"
        )


def create_compact_int_spin(
    minimum: int = 1,
    maximum: int = 999,
    value: int = 1,
    width: int = 72,
    parent=None,
) -> CompactSpinBox:
    spin = CompactSpinBox(parent)
    spin.setRange(minimum, maximum)
    spin.setValue(value)
    spin.setFixedWidth(width)
    apply_compact_spin(spin)
    return spin


def create_compact_float_spin(
    minimum: float = 0.1,
    maximum: float = 10.0,
    value: float = 1.0,
    step: float = 0.1,
    width: int = 76,
    suffix: str = "",
    parent=None,
) -> CompactDoubleSpinBox:
    spin = CompactDoubleSpinBox(parent)
    spin.setRange(minimum, maximum)
    spin.setSingleStep(step)
    spin.setValue(value)
    if suffix:
        spin.setSuffix(suffix)
    spin.setFixedWidth(width)
    apply_compact_spin(spin)
    return spin


class InlineNumericField(QWidget):
    """标签 + 紧凑数字框，单行排列（参考 Clash Verge 设置项）。"""

    def __init__(self, label: str, spin: QWidget, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        lbl = BodyLabel(label)
        lbl.setStyleSheet(muted_label_style())
        layout.addWidget(lbl)
        layout.addWidget(spin)


def list_item_card_style() -> str:
    """列表项卡片（Clash Verge 风格圆角与悬停）。"""
    border = _panel_border_color()
    if isDarkTheme():
        bg = "rgba(255, 255, 255, 0.04)"
        hover = "rgba(255, 255, 255, 0.08)"
    else:
        bg = "#FFFFFF"
        hover = "#F5F7FA"
    accent = accent_color()
    return f"""
        CardWidget {{
            background-color: {bg};
            border: 1px solid {border};
            border-radius: 8px;
        }}
        CardWidget:hover {{
            border-color: {accent};
            background-color: {hover};
        }}
    """


def setting_form_style() -> str:
    border = _panel_border_color()
    if isDarkTheme():
        bg = "rgba(255, 255, 255, 0.05)"
    else:
        bg = "#FFFFFF"
    return f"""
        CardWidget#settingFormCard {{
            background-color: {bg};
            border: 1px solid {border};
            border-radius: 10px;
        }}
    """


class AutomateToolbar(QFrame):
    """流程设计器顶部工具栏。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("automateToolbar")
        border = _panel_border_color()
        bg = _panel_bg_color()
        self.setStyleSheet(f"""
            QFrame#automateToolbar {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 4px;
            }}
            QFrame#automateToolbar > QLabel,
            QFrame#automateToolbar BodyLabel {{
                color: {text_secondary()};
            }}
        """)
        self.setFixedHeight(48)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 6, 12, 6)
        self._layout.setSpacing(10)


def flow_list_style() -> str:
    """流程动作列表容器（项样式由 ActionItemWidget 自身绘制）。"""
    fg = text_primary()
    c = themeColor()
    if isDarkTheme():
        item_sel = f"rgba({c.red()}, {c.green()}, {c.blue()}, 0.22)"
    else:
        item_sel = f"rgba({c.red()}, {c.green()}, {c.blue()}, 0.12)"
    return f"""
        QListWidget {{
            border: none;
            background: transparent;
            outline: none;
            color: {fg};
        }}
        QListWidget::item {{
            background: transparent;
            border: none;
            margin: 3px 0;
            padding: 0;
        }}
        QListWidget::item:selected {{
            background: transparent;
            border: none;
        }}
    """


def flow_action_item_style(running: bool = False, selected: bool = False) -> str:
    """流程设计器动作行外框（Clash Verge 列表项）。"""
    border = _panel_border_color()
    if isDarkTheme():
        bg = "rgba(255, 255, 255, 0.04)"
    else:
        bg = "#FFFFFF"
    accent = accent_color()
    if running:
        c = themeColor()
        return (
            f"ActionItemWidget {{ background-color: rgba({c.red()}, {c.green()}, {c.blue()}, 0.12);"
            f" border: 1px solid {accent}; border-radius: 8px; }}"
        )
    if selected:
        c = themeColor()
        return (
            f"ActionItemWidget {{ background-color: rgba({c.red()}, {c.green()}, {c.blue()}, 0.08);"
            f" border: 1px solid {accent}; border-radius: 8px; }}"
        )
    return (
        f"ActionItemWidget {{ background-color: {bg}; border: 1px solid {border};"
        f" border-radius: 8px; }}"
    )


def flow_sub_action_row_style(running: bool = False, completed: bool = False) -> str:
    border = _panel_border_color()
    if running:
        c = themeColor()
        return (
            f"background-color: rgba({c.red()}, {c.green()}, {c.blue()}, 0.10);"
            f"border-left: 2px solid {c.name()}; border-radius: 4px;"
        )
    if completed:
        return (
            f"background-color: rgba(22, 163, 74, 0.06);"
            f"border-left: 2px solid {success_color()}; border-radius: 4px;"
        )
    return f"background: transparent; border-left: 2px solid {border}; border-radius: 4px;"


FORM_LABEL_WIDTH = 76


class SettingFormGrid(QWidget):
    """启动命令等表单的标签列对齐网格。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(12)
        self._grid.setVerticalSpacing(10)
        self._grid.setColumnMinimumWidth(0, FORM_LABEL_WIDTH)
        self._grid.setColumnStretch(1, 1)
        self._row = 0

    def add_row(self, label: str, field: QWidget):
        lbl = BodyLabel(label)
        lbl.setFixedWidth(FORM_LABEL_WIDTH)
        lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        lbl.setStyleSheet(muted_label_style())
        self._grid.addWidget(lbl, self._row, 0, Qt.AlignLeft | Qt.AlignVCenter)
        self._grid.addWidget(field, self._row, 1)
        self._row += 1


def flow_step_running_style() -> str:
    return flow_action_item_style(running=True)


def flow_step_idle_style() -> str:
    return flow_action_item_style()


def status_bar_style() -> str:
    border = _panel_border_color()
    bg = _panel_bg_color()
    return f"""
        QWidget#statusBar {{
            background-color: {bg};
            border-top: 1px solid {border};
        }}
        QWidget#statusBar QLabel {{
            color: {text_secondary()};
        }}
    """


def scroll_border_style() -> str:
    border = _panel_border_color()
    return f"QScrollArea {{ border: 1px solid {border}; border-radius: 8px; background: transparent; }}"
