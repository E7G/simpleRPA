import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication
from qfluentwidgets import (
    Theme, setTheme, ScrollArea, HeaderCardWidget,
    GroupHeaderCardWidget, SettingCardGroup, TextEdit,
    PasswordLineEdit, OptionsSettingCard, SwitchSettingCard,
)

from gui.ai_assistant_page import AIAssistantPage


class AIAssistantLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _check_theme(self, theme):
        setTheme(theme)
        page = AIAssistantPage()
        page.resize(1180, 760)
        page.show()
        self.app.processEvents()

        self.assertIsInstance(page, ScrollArea)
        self.assertIsInstance(page.targetCard, HeaderCardWidget)
        self.assertIsInstance(page.taskCard, HeaderCardWidget)
        self.assertIsInstance(page.connectionCard, GroupHeaderCardWidget)
        self.assertIsInstance(page.behaviorGroup, SettingCardGroup)

        self.assertIsInstance(page.taskCard.historyEdit, TextEdit)
        self.assertIsInstance(page.taskCard.inputEdit, TextEdit)
        self.assertIsInstance(page.connectionCard.apiKeyEdit, PasswordLineEdit)
        self.assertIsInstance(page.themeCard, OptionsSettingCard)
        self.assertIsInstance(page.autoCleanupCard, SwitchSettingCard)
        self.assertIsInstance(page.returnHomeCard, SwitchSettingCard)
        self.assertIsInstance(page.backgroundCard, SwitchSettingCard)

        cards = [
            page.targetCard,
            page.taskCard,
            page.connectionCard,
            page.behaviorGroup,
        ]
        previous_bottom = -1
        for card in cards:
            rect = card.geometry()
            self.assertGreater(rect.width(), 700)
            self.assertGreater(rect.height(), 40)
            self.assertGreaterEqual(rect.x(), 20)
            self.assertGreater(rect.y(), previous_bottom)
            previous_bottom = rect.bottom()

        self.assertGreaterEqual(page.taskCard.historyEdit.height(), 250)
        self.assertGreaterEqual(page.taskCard.inputEdit.height(), 90)
        self.assertGreater(
            page.taskCard.inputEdit.geometry().top(),
            page.taskCard.historyEdit.geometry().bottom(),
        )

        self.assertTrue(page.autoCleanupCard.isChecked())
        self.assertTrue(page.returnHomeCard.isChecked())
        self.assertTrue(page.backgroundCard.isChecked())

        page.close()
        page.deleteLater()
        self.app.processEvents()

    def test_light_layout(self):
        self._check_theme(Theme.LIGHT)

    def test_dark_layout(self):
        self._check_theme(Theme.DARK)


if __name__ == "__main__":
    unittest.main()
