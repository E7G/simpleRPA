import sys
import threading


def send_notification(title: str, message: str, app_name: str = "SimpleRPA"):
    if sys.platform != 'win32':
        return False

    try:
        from PyQt5.QtWidgets import QSystemTrayIcon, QApplication
        from PyQt5.QtCore import QTimer

        app = QApplication.instance()
        if app is not None:
            tray = QSystemTrayIcon(app)
            icon = app.windowIcon()
            if icon.isNull():
                style = QApplication.style()
                if style:
                    icon = style.standardIcon(style.SP_ComputerIcon)
            tray.setIcon(icon)
            tray.show()
            tray.showMessage(title, message, QSystemTrayIcon.Information, 5000)
            QTimer.singleShot(6000, tray.deleteLater)
            return True
    except Exception:
        pass

    try:
        import ctypes

        def _show_msgbox():
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)

        threading.Thread(target=_show_msgbox, daemon=True).start()
        return True
    except Exception:
        return False
