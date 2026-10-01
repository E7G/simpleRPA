from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit
from PyQt5.QtCore import pyqtSignal

from qfluentwidgets import LineEdit, PushButton, PrimaryPushButton, CaptionLabel


class AIChatPanel(QWidget):
    """Minimal chat-style authoring surface for natural-language visual tasks."""

    task_submitted = pyqtSignal(str, bool)  # instruction, run_now

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.append_assistant(
            "直接告诉我想完成什么，例如：\n"
            "“领取签到奖励”\n"
            "“进入战令，把免费的可领取奖励领完”\n\n"
            "系统会自动处理普通公告/弹窗，任务完成后默认返回首页。"
        )

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._history = QPlainTextEdit()
        self._history.setReadOnly(True)
        self._history.setPlaceholderText("在这里用对话生成 AI 视觉任务")
        layout.addWidget(self._history, 1)

        tip = CaptionLabel("输入“撤销上一条”可删除刚加入的任务")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        self._input = LineEdit()
        self._input.setPlaceholderText("例如：领取签到奖励")
        self._input.setMinimumHeight(36)
        self._input.returnPressed.connect(self._submit_add)
        layout.addWidget(self._input)

        buttons = QHBoxLayout()
        buttons.setSpacing(6)

        self._add_btn = PrimaryPushButton("加入流程")
        self._add_btn.clicked.connect(self._submit_add)
        buttons.addWidget(self._add_btn)

        self._run_btn = PushButton("加入并运行")
        self._run_btn.clicked.connect(self._submit_run)
        buttons.addWidget(self._run_btn)

        layout.addLayout(buttons)

    def _take_text(self):
        text = self._input.text().strip()
        if not text:
            return ""
        self._input.clear()
        return text

    def _submit_add(self):
        text = self._take_text()
        if not text:
            return
        self.append_user(text)
        self.task_submitted.emit(text, False)

    def _submit_run(self):
        text = self._take_text()
        if not text:
            return
        self.append_user(text)
        self.task_submitted.emit(text, True)

    def append_user(self, text: str):
        self._history.appendPlainText(f"你：{text}\n")

    def append_assistant(self, text: str):
        self._history.appendPlainText(f"simpleRPA：{text}\n")
