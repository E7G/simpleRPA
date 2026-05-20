import sys
import os
from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QFont, QColor


def get_icon_path():
    icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'icon.ico')
    if os.path.exists(icon_path):
        return icon_path
    png_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'icon.png')
    if os.path.exists(png_path):
        return png_path
    return None


def _create_splash():
    pixmap = QPixmap(480, 240)
    pixmap.fill(QColor(0, 120, 212))
    painter = QPainter(pixmap)
    painter.setPen(QColor(255, 255, 255))
    font = QFont("Microsoft YaHei", 24, QFont.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect().adjusted(0, -30, 0, 0), Qt.AlignCenter, "SimpleRPA")
    font2 = QFont("Microsoft YaHei", 11)
    painter.setFont(font2)
    painter.setPen(QColor(200, 230, 255))
    painter.drawText(pixmap.rect().adjusted(0, 30, 0, 0), Qt.AlignCenter, "RPA \u81ea\u52a8\u5316\u5de5\u5177")
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
    
    from gui.main_window import MainWindow
    
    window = MainWindow()
    window.show()
    splash.finish(window)
    
    sys.exit(app.exec_())
