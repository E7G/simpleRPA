"""应用设置页 — 托盘、通知、调度等行为。"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import pyqtSignal

from qfluentwidgets import (
    FluentIcon, TitleLabel, BodyLabel, StrongBodyLabel,
    SwitchButton, ComboBox, HeaderCardWidget, PushButton,
    SpinBox, InfoBar, InfoBarPosition
)

from utils.config import Config
from core.scheduler import SchedulerService


class SettingsPage(QWidget):
    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = Config.get_instance()
        self._scheduler = SchedulerService.get_instance()
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        header = QHBoxLayout()
        header.addWidget(TitleLabel("设置"))
        header.addStretch()
        layout.addLayout(header)

        layout.addWidget(BodyLabel("托盘、通知与定时调度相关选项"))

        tray_card = HeaderCardWidget(self)
        tray_card.setTitle("系统托盘")
        tray_content = QWidget()
        tray_layout = QVBoxLayout(tray_content)
        tray_layout.setContentsMargins(20, 12, 20, 20)
        tray_layout.setSpacing(16)

        self._tray_enable = self._add_switch_row(
            tray_layout, "启用系统托盘", "在任务栏显示图标，支持最小化到托盘"
        )
        self._minimize_tray = self._add_switch_row(
            tray_layout, "最小化到托盘", "点击最小化时隐藏到托盘而非任务栏"
        )
        self._close_tray = self._add_switch_row(
            tray_layout, "关闭时最小化到托盘", "点击关闭按钮时隐藏到托盘，不退出程序"
        )
        self._start_minimized = self._add_switch_row(
            tray_layout, "启动时最小化到托盘", "应用启动后仅显示托盘图标"
        )

        tray_card.viewLayout.addWidget(tray_content)
        layout.addWidget(tray_card)

        notify_card = HeaderCardWidget(self)
        notify_card.setTitle("通知")
        notify_content = QWidget()
        notify_layout = QVBoxLayout(notify_content)
        notify_layout.setContentsMargins(20, 12, 20, 20)
        notify_layout.setSpacing(16)

        self._notify_enable = self._add_switch_row(
            notify_layout, "执行完成通知", "脚本执行结束或定时任务完成后弹出通知"
        )
        self._notify_sched = self._add_switch_row(
            notify_layout, "定时任务通知", "定时任务触发与执行结果通知"
        )

        notify_card.viewLayout.addWidget(notify_content)
        layout.addWidget(notify_card)

        sched_card = HeaderCardWidget(self)
        sched_card.setTitle("定时调度")
        sched_content = QWidget()
        sched_layout = QVBoxLayout(sched_content)
        sched_layout.setContentsMargins(20, 12, 20, 20)
        sched_layout.setSpacing(16)

        self._sched_auto = self._add_switch_row(
            sched_layout, "启动时自动运行调度器", "应用启动后在后台检查并执行到期任务"
        )

        interval_row = QHBoxLayout()
        interval_row.addWidget(StrongBodyLabel("检查间隔"))
        self._check_interval = SpinBox()
        self._check_interval.setRange(10, 300)
        self._check_interval.setSuffix(" 秒")
        self._check_interval.setFixedWidth(120)
        interval_row.addWidget(self._check_interval)
        interval_row.addStretch()
        sched_layout.addLayout(interval_row)

        theme_row = QHBoxLayout()
        theme_row.addWidget(StrongBodyLabel("界面主题"))
        self._theme_combo = ComboBox()
        self._theme_combo.addItems(["跟随系统", "浅色", "深色"])
        self._theme_combo.setFixedWidth(160)
        theme_row.addWidget(self._theme_combo)
        theme_row.addStretch()
        sched_layout.addLayout(theme_row)

        sched_card.viewLayout.addWidget(sched_content)
        layout.addWidget(sched_card)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = PushButton(FluentIcon.SAVE, "保存设置")
        save_btn.setFixedHeight(36)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        layout.addStretch()

    def _add_switch_row(self, layout, title: str, subtitle: str) -> SwitchButton:
        row = QHBoxLayout()
        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        text_col.addWidget(StrongBodyLabel(title))
        text_col.addWidget(BodyLabel(subtitle))
        row.addLayout(text_col, 1)
        sw = SwitchButton()
        row.addWidget(sw)
        layout.addLayout(row)
        return sw

    def _load_values(self):
        c = self._config
        self._tray_enable.setChecked(c.tray_enabled)
        self._minimize_tray.setChecked(c.minimize_to_tray)
        self._close_tray.setChecked(c.close_to_tray)
        self._start_minimized.setChecked(c.start_minimized)
        self._notify_enable.setChecked(c.notify_on_complete)
        self._notify_sched.setChecked(c.notify_on_schedule)
        self._sched_auto.setChecked(c.scheduler_auto_start)
        self._check_interval.setValue(c.scheduler_check_interval)

        theme_map = {'auto': 0, 'light': 1, 'dark': 2}
        self._theme_combo.setCurrentIndex(theme_map.get(c.theme, 0))

    def _save(self):
        c = self._config
        c.tray_enabled = self._tray_enable.isChecked()
        c.minimize_to_tray = self._minimize_tray.isChecked()
        c.close_to_tray = self._close_tray.isChecked()
        c.start_minimized = self._start_minimized.isChecked()
        c.notify_on_complete = self._notify_enable.isChecked()
        c.notify_on_schedule = self._notify_sched.isChecked()
        c.scheduler_auto_start = self._sched_auto.isChecked()
        c.scheduler_check_interval = self._check_interval.value()

        themes = ['auto', 'light', 'dark']
        c.theme = themes[self._theme_combo.currentIndex()]
        c.save()

        self._scheduler._check_interval = c.scheduler_check_interval
        if c.scheduler_auto_start and not self._scheduler.is_running:
            self._scheduler.start()

        self.settings_changed.emit()
        InfoBar.success(
            title="已保存",
            content="设置已生效",
            parent=self,
            position=InfoBarPosition.TOP,
        )

    def apply_theme(self):
        from qfluentwidgets import setTheme, Theme
        theme_map = {
            'auto': Theme.AUTO,
            'light': Theme.LIGHT,
            'dark': Theme.DARK,
        }
        setTheme(theme_map.get(self._config.theme, Theme.AUTO))
