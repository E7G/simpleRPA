import sys
import os
from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QFont, QColor, QLinearGradient


def get_icon_path():
    icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'icon.ico')
    if os.path.exists(icon_path):
        return icon_path
    png_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'icon.png')
    if os.path.exists(png_path):
        return png_path
    return None


def _create_splash():
    w, h = 480, 200
    pixmap = QPixmap(w, h)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, w, h)
    grad.setColorAt(0, QColor(0, 120, 212))
    grad.setColorAt(1, QColor(116, 39, 116))
    painter.fillRect(0, 0, w, h, grad)
    painter.setPen(QColor(255, 255, 255))
    font = QFont("Segoe UI", 26, QFont.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect().adjusted(0, -24, 0, 0), Qt.AlignCenter, "SimpleRPA")
    font2 = QFont("Segoe UI", 10)
    painter.setFont(font2)
    painter.setPen(QColor(230, 230, 255))
    painter.drawText(pixmap.rect().adjusted(0, 28, 0, 0), Qt.AlignCenter, "桌面流程自动化")
    painter.end()
    return pixmap


def run_app():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    
    icon_path = get_icon_path()
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))
    
    splash = QSplashScreen(_create_splash())
    splash.show()
    splash.showMessage("\u6b63\u5728\u52a0\u8f7d...", Qt.AlignBottom | Qt.AlignHCenter, Qt.white)
    app.processEvents()
    
    from gui.fluent_theme import apply_app_theme
    from gui.main_window import MainWindow
    
    apply_app_theme()
    window = MainWindow()
    window.show()
    splash.finish(window)
    
    sys.exit(app.exec_())
