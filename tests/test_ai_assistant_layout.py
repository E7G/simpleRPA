import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication
from qfluentwidgets import Theme, setTheme

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

        widgets = [
            page._left_column,
            page._target_card,
            page._settings_card,
            page._chat_card,
            page._history,
            page._input,
            page._run_btn,
            page._preview,
        ]
        for widget in widgets:
            rect = widget.geometry()
            self.assertGreater(rect.width(), 20)
            self.assertGreater(rect.height(), 20)
            self.assertGreaterEqual(rect.x(), 0)
            self.assertGreaterEqual(rect.y(), 0)

        left = page._left_column.geometry()
        chat = page._chat_card.geometry()
        self.assertGreaterEqual(chat.x(), left.x() + left.width())
        self.assertGreaterEqual(chat.width(), 500)
        self.assertGreaterEqual(page._history.height(), 250)
        self.assertGreaterEqual(page._input.height(), 90)
        self.assertGreater(page._input.geometry().top(), page._history.geometry().bottom())

        self.assertEqual(page._history.__class__.__name__, "TextEdit")
        self.assertEqual(page._input.__class__.__name__, "TextEdit")
        self.assertEqual(page._api_key.__class__.__name__, "PasswordLineEdit")
        self.assertEqual(page._preview.__class__.__name__, "ImageLabel")
        self.assertEqual(page._theme.__class__.__name__, "ComboBox")

        page.close()
        page.deleteLater()
        self.app.processEvents()

    def test_light_layout(self):
        self._check_theme(Theme.LIGHT)

    def test_dark_layout(self):
        self._check_theme(Theme.DARK)


if __name__ == "__main__":
    unittest.main()
