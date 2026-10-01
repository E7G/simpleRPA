import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QImage
from qfluentwidgets import (
    Theme, setTheme, ScrollArea, TextEdit,
    PasswordLineEdit, SwitchButton, PushButton,
)

from gui.ai_assistant_page import AIAssistantPage, ExampleCard, AIToolBar, PreviewPane


class AIAssistantLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _check_theme(self, theme):
        setTheme(theme)
        page = AIAssistantPage()
        page.resize(1180, 760)
        page.show()
        page._apply_qss()
        self.app.processEvents()

        self.assertIsInstance(page, ScrollArea)
        self.assertIsInstance(page.toolBar, AIToolBar)
        self.assertIsInstance(page.targetCard, ExampleCard)
        self.assertIsInstance(page.taskCard, ExampleCard)
        self.assertIsInstance(page.settingsCard, ExampleCard)

        self.assertIsInstance(page.taskPanel.historyEdit, TextEdit)
        self.assertIsInstance(page.taskPanel.inputEdit, TextEdit)
        self.assertIsInstance(page.settingsPanel.apiKeyEdit, PasswordLineEdit)
        self.assertIsInstance(page.settingsPanel.autoCleanupSwitch, SwitchButton)
        self.assertIsInstance(page.settingsPanel.returnHomeSwitch, SwitchButton)
        self.assertIsInstance(page.settingsPanel.backgroundSwitch, SwitchButton)
        self.assertIsInstance(page.settingsPanel.themeButton, PushButton)
        self.assertIsInstance(page.targetPanel.previewPane, PreviewPane)

        # A normal 16:9 screenshot must be rendered as a genuinely large preview,
        # not at the source/native ImageLabel size or as a tiny fixed widget.
        image = QImage(1920, 1080, QImage.Format_RGB32)
        image.fill(0xFF404040)
        page.targetPanel.previewPane.set_image(image)
        self.app.processEvents()
        preview_size = page.targetPanel.previewPane.imageLabel.size()
        self.assertGreaterEqual(preview_size.width(), 600)
        self.assertGreaterEqual(preview_size.height(), 300)

        cards = [page.targetCard, page.taskCard, page.settingsCard]
        previous_bottom = -1
        for card in cards:
            rect = card.geometry()
            self.assertGreater(rect.width(), 700)
            self.assertGreater(rect.height(), 40)
            self.assertGreaterEqual(rect.x(), 20)
            self.assertGreater(rect.y(), previous_bottom)
            previous_bottom = rect.bottom()

        self.assertGreaterEqual(page.taskPanel.historyEdit.height(), 200)
        self.assertGreaterEqual(page.taskPanel.inputEdit.height(), 90)
        self.assertGreater(
            page.taskPanel.inputEdit.geometry().top(),
            page.taskPanel.historyEdit.geometry().bottom(),
        )

        self.assertTrue(page.settingsPanel.autoCleanupSwitch.isChecked())
        self.assertTrue(page.settingsPanel.returnHomeSwitch.isChecked())
        self.assertTrue(page.settingsPanel.backgroundSwitch.isChecked())

        qss = page.styleSheet()
        if theme == Theme.DARK:
            self.assertIn("rgba(0, 0, 0, 0.1795)", qss)
        else:
            self.assertIn("rgba(0, 0, 0, 0.024)", qss)

        page.close()
        page.deleteLater()
        self.app.processEvents()

    def test_light_layout(self):
        self._check_theme(Theme.LIGHT)

    def test_dark_layout(self):
        self._check_theme(Theme.DARK)


if __name__ == "__main__":
    unittest.main()
