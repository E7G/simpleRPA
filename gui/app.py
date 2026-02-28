import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt


def run_app():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    
    from gui.main_window import MainWindow
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())
