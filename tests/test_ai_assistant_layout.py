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

        # Workspace layout: tall portrait preview rail on the left,
        # task/settings stacked on the right.
        target_rect = page.targetCard.geometry()
        right_rect = page.rightWidget.geometry()
        task_rect = page.taskCard.geometry()
        settings_rect = page.settingsCard.geometry()

        self.assertGreaterEqual(target_rect.width(), 390)
        self.assertGreaterEqual(page.targetPanel.previewPane.width(), 340)
        self.assertGreaterEqual(page.targetPanel.previewPane.height(), 560)
        self.assertGreaterEqual(right_rect.x(), target_rect.right())
        self.assertGreaterEqual(right_rect.width(), 500)
        self.assertGreater(settings_rect.y(), task_rect.bottom())

        self.assertGreaterEqual(page.taskPanel.historyEdit.height(), 200)
        self.assertGreaterEqual(page.taskPanel.inputEdit.height(), 90)
        self.assertGreater(
            page.taskPanel.inputEdit.geometry().top(),
            page.taskPanel.historyEdit.geometry().bottom(),
        )

        # Portrait game screenshots should fill most of the left rail while
        # preserving their native aspect ratio.
        portrait = QImage(720, 1280, QImage.Format_RGB32)
        portrait.fill(0xFF404040)
        page.targetPanel.previewPane.set_image(portrait)
        self.app.processEvents()
        portrait_size = page.targetPanel.previewPane.imageLabel.size()
        self.assertGreaterEqual(portrait_size.width(), 300)
        self.assertGreaterEqual(portrait_size.height(), 530)
        self.assertAlmostEqual(
            portrait_size.width() / portrait_size.height(),
            720 / 1280,
            delta=0.03,
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
