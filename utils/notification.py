import sys
import threading


def send_notification(title: str, message: str, app_name: str = "SimpleRPA"):
    if sys.platform != 'win32':
        return False

    try:
        from PyQt5.QtWidgets import QApplication, QSystemTrayIcon

        app = QApplication.instance()
        if app is not None:
            for widget in app.topLevelWidgets():
                tray_service = getattr(widget, '_tray_service', None)
                if tray_service and getattr(tray_service, 'is_visible', False):
                    tray_service.show_message(
                        title, message, QSystemTrayIcon.Information, 5000
                    )
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
