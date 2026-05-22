"""系统托盘服务。"""

import os
from typing import Optional, Callable

from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QObject, pyqtSignal


class TrayService(QObject):
    show_window_requested = pyqtSignal()
    hide_window_requested = pyqtSignal()
    run_dashboard_requested = pyqtSignal()
    open_scheduler_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tray: Optional[QSystemTrayIcon] = None
        self._enabled = True

    @property
    def is_available(self) -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    @property
    def is_visible(self) -> bool:
        return self._tray is not None and self._tray.isVisible()

    def setup(self, window, icon_path: Optional[str] = None):
        if not self.is_available:
            return False

        app = QApplication.instance()
        icon = QIcon()
        if icon_path and os.path.exists(icon_path):
            icon = QIcon(icon_path)
        elif app and not app.windowIcon().isNull():
            icon = app.windowIcon()
        else:
            style = QApplication.style()
            if style:
                icon = style.standardIcon(style.SP_ComputerIcon)

        self._tray = QSystemTrayIcon(icon, window)
        self._tray.setToolTip("SimpleRPA")
        self._build_menu()
        self._tray.activated.connect(self._on_activated)
        self._tray.show()
        return True

    def _build_menu(self):
        menu = QMenu()

        show_action = QAction("显示主窗口", menu)
        show_action.triggered.connect(self.show_window_requested.emit)
        menu.addAction(show_action)

        run_action = QAction("运行执行面板", menu)
        run_action.triggered.connect(self.run_dashboard_requested.emit)
        menu.addAction(run_action)

        sched_action = QAction("定时任务", menu)
        sched_action.triggered.connect(self.open_scheduler_requested.emit)
        menu.addAction(sched_action)

        menu.addSeparator()

        quit_action = QAction("退出", menu)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_window_requested.emit()

    def show_message(self, title: str, message: str, icon=QSystemTrayIcon.Information, duration=4000):
        if self._tray and self._tray.isVisible():
            self._tray.showMessage(title, message, icon, duration)

    def set_tooltip(self, text: str):
        if self._tray:
            self._tray.setToolTip(text)

    def hide(self):
        if self._tray:
            self._tray.hide()

    def show(self):
        if self._tray:
            self._tray.show()
