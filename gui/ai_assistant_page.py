import os

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPlainTextEdit, QSizePolicy, QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap

from qfluentwidgets import (
    StrongBodyLabel, BodyLabel, CaptionLabel, LineEdit,
    PushButton, PrimaryPushButton, CheckBox, CardWidget,
)

from .widgets import WindowSelector
from .fluent_theme import muted_caption_style, text_secondary


class AIAssistantPage(QWidget):
    """Conversation-first UI for Agnes visual automation."""

    task_requested = pyqtSignal(str, bool)  # instruction, run_now
    stop_requested = pyqtSignal()
    window_selected = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_preview = None
        self._setup_ui()
        self.refresh_api_status()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 22)
        root.setSpacing(16)

        title_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = StrongBodyLabel("AI 视觉助手")
        title.setStyleSheet("font-size: 24px; font-weight: 700;")
        subtitle = BodyLabel("一句话告诉它要做什么，坐标、识别、弹窗处理和返回路径交给视觉模型。")
        subtitle.setStyleSheet(muted_caption_style("font-size: 12px;"))
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        title_row.addLayout(title_box)
        title_row.addStretch()

        self._api_badge = CaptionLabel("Agnes：未配置")
        self._api_badge.setStyleSheet(
            "padding: 6px 10px; border-radius: 10px; background: rgba(128,128,128,0.12);"
        )
        title_row.addWidget(self._api_badge)
        root.addLayout(title_row)

        body = QHBoxLayout()
        body.setSpacing(14)

        # Left: target and live preview
        left = CardWidget()
        left.setMinimumWidth(340)
        left.setMaximumWidth(440)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(10)

        left_title = StrongBodyLabel("1. 选择目标窗口")
        left_layout.addWidget(left_title)

        self._window_selector = WindowSelector(compact=False)
        self._window_selector.refresh_windows()
        self._window_selector.window_selected.connect(self._on_window_selected)
        left_layout.addWidget(self._window_selector)

        preview_head = QHBoxLayout()
        preview_head.addWidget(BodyLabel("窗口预览"))
        preview_head.addStretch()
        self._preview_btn = PushButton("刷新预览")
        self._preview_btn.clicked.connect(self.refresh_preview)
        preview_head.addWidget(self._preview_btn)
        left_layout.addLayout(preview_head)

        self._preview = QLabel("选择窗口后点击“刷新预览”")
        self._preview.setAlignment(Qt.AlignCenter)
        self._preview.setMinimumHeight(260)
        self._preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._preview.setStyleSheet(
            "QLabel { border: 1px dashed rgba(128,128,128,0.45); "
            "border-radius: 10px; background: rgba(128,128,128,0.05); padding: 8px; }"
        )
        left_layout.addWidget(self._preview, 1)

        self._window_state = CaptionLabel("尚未选择窗口")
        self._window_state.setWordWrap(True)
        self._window_state.setStyleSheet(muted_caption_style())
        left_layout.addWidget(self._window_state)

        body.addWidget(left, 0)

        # Center: chat authoring
        center = CardWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(18, 16, 18, 16)
        center_layout.setSpacing(10)

        center_title = StrongBodyLabel("2. 直接描述任务")
        center_layout.addWidget(center_title)

        self._history = QPlainTextEdit()
        self._history.setReadOnly(True)
        self._history.setMinimumHeight(330)
        self._history.setPlaceholderText("任务与执行状态会显示在这里")
        center_layout.addWidget(self._history, 1)
        self.append_assistant(
            "可以直接说：\n"
            "• 关闭所有公告并返回首页\n"
            "• 进入签到页面，把免费的奖励领完\n"
            "• 进入战令，领取所有可领取的免费奖励，完成后回首页"
        )

        quick_label = CaptionLabel("快捷任务")
        quick_label.setStyleSheet(muted_caption_style())
        center_layout.addWidget(quick_label)

        quick = QGridLayout()
        quick.setHorizontalSpacing(8)
        quick.setVerticalSpacing(8)
        presets = [
            ("清理公告", "关闭当前所有公告、活动说明和普通提示，让页面恢复可操作状态"),
            ("返回首页", "识别当前页面并逐级返回首页或大厅"),
            ("签到奖励", "进入签到页面，把所有免费的可领取奖励领完"),
            ("免费奖励", "在当前页面领取所有明确免费的可领取奖励，不进行购买或消耗"),
        ]
        for i, (label, prompt) in enumerate(presets):
            btn = PushButton(label)
            btn.clicked.connect(lambda checked=False, p=prompt: self._set_prompt(p))
            quick.addWidget(btn, i // 2, i % 2)
        center_layout.addLayout(quick)

        self._input = QPlainTextEdit()
        self._input.setPlaceholderText("输入你要完成的任务……")
        self._input.setFixedHeight(96)
        center_layout.addWidget(self._input)

        actions = QHBoxLayout()
        self._add_btn = PushButton("生成到流程")
        self._add_btn.clicked.connect(lambda: self._submit(False))
        actions.addWidget(self._add_btn)

        self._run_btn = PrimaryPushButton("立即执行")
        self._run_btn.clicked.connect(lambda: self._submit(True))
        actions.addWidget(self._run_btn, 1)

        self._stop_btn = PushButton("停止")
        self._stop_btn.clicked.connect(self.stop_requested.emit)
        self._stop_btn.setEnabled(False)
        actions.addWidget(self._stop_btn)
        center_layout.addLayout(actions)

        self._status = BodyLabel("就绪")
        self._status.setStyleSheet(f"color: {text_secondary()};")
        center_layout.addWidget(self._status)

        body.addWidget(center, 1)

        # Right: session config and behavior
        right = CardWidget()
        right.setMinimumWidth(300)
        right.setMaximumWidth(360)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(10)

        right_layout.addWidget(StrongBodyLabel("3. AI 与执行设置"))

        right_layout.addWidget(CaptionLabel("Agnes API Key（仅当前会话）"))
        self._api_key = LineEdit()
        self._api_key.setEchoMode(LineEdit.Password)
        self._api_key.setPlaceholderText("粘贴 API Key")
        right_layout.addWidget(self._api_key)

        right_layout.addWidget(CaptionLabel("模型"))
        self._model = LineEdit()
        self._model.setText(os.getenv("AGNES_MODEL") or "agnes-3.0-flash")
        right_layout.addWidget(self._model)

        right_layout.addWidget(CaptionLabel("API Base"))
        self._base = LineEdit()
        self._base.setText(os.getenv("AGNES_API_BASE") or "https://apihub.agnes-ai.com/v1")
        right_layout.addWidget(self._base)

        self._apply_api_btn = PrimaryPushButton("应用 Agnes 配置")
        self._apply_api_btn.clicked.connect(self.apply_api_config)
        right_layout.addWidget(self._apply_api_btn)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("color: rgba(128,128,128,0.25);")
        right_layout.addWidget(separator)

        self._auto_cleanup = CheckBox("任务前自动关闭公告/弹窗")
        self._auto_cleanup.setChecked(True)
        right_layout.addWidget(self._auto_cleanup)

        self._return_home = CheckBox("任务完成后自动返回首页")
        self._return_home.setChecked(True)
        right_layout.addWidget(self._return_home)

        self._background = CheckBox("优先后台截图和点击")
        self._background.setChecked(True)
        right_layout.addWidget(self._background)

        hint = CaptionLabel(
            "视觉 Agent 有最大步骤数限制，并禁止自动购买、支付、充值、删除数据等高风险操作。"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(muted_caption_style())
        right_layout.addWidget(hint)
        right_layout.addStretch()

        body.addWidget(right, 0)
        root.addLayout(body, 1)

    def get_selected_hwnd(self):
        return self._window_selector.get_selected_hwnd()

    def get_selected_title(self):
        return self._window_selector.get_selected_title()

    def get_task_options(self):
        return {
            "prepare_navigation": 1 if self._auto_cleanup.isChecked() else 0,
            "return_home": 1 if self._return_home.isChecked() else 0,
            "background_mode": self._background.isChecked(),
        }

    def _on_window_selected(self, hwnd):
        title = self._window_selector.get_selected_title()
        self._window_state.setText(f"已选择：{title or hwnd}")
        self.window_selected.emit(hwnd)
        self.refresh_preview()

    def _set_prompt(self, prompt):
        self._input.setPlainText(prompt)
        self._input.setFocus()

    def _submit(self, run_now):
        text = self._input.toPlainText().strip()
        if not text:
            self.set_status("请先输入任务描述", error=True)
            return
        if not self.get_selected_hwnd():
            self.set_status("请先选择要操作的窗口", error=True)
            return
        self.append_user(text)
        self._input.clear()
        self.task_requested.emit(text, run_now)

    def apply_api_config(self):
        key = self._api_key.text().strip()
        model = self._model.text().strip()
        base = self._base.text().strip()

        if key:
            os.environ["AGNES_API_KEY"] = key
        if model:
            os.environ["AGNES_MODEL"] = model
        if base:
            os.environ["AGNES_API_BASE"] = base

        self.refresh_api_status()
        if os.getenv("AGNES_API_KEY") or os.getenv("AGNESAI_API_KEY"):
            self.append_assistant("Agnes 配置已应用到当前程序会话。")
        else:
            self.set_status("尚未填写 Agnes API Key", error=True)

    def refresh_api_status(self):
        configured = bool(os.getenv("AGNES_API_KEY") or os.getenv("AGNESAI_API_KEY"))
        if configured:
            self._api_badge.setText("Agnes：已配置")
            self._api_badge.setStyleSheet(
                "padding: 6px 10px; border-radius: 10px; "
                "background: rgba(22,163,74,0.16); color: #16A34A;"
            )
        else:
            self._api_badge.setText("Agnes：未配置")
            self._api_badge.setStyleSheet(
                "padding: 6px 10px; border-radius: 10px; "
                "background: rgba(245,158,11,0.16); color: #D97706;"
            )

    def refresh_preview(self):
        hwnd = self.get_selected_hwnd()
        if not hwnd:
            self._preview.setText("请先选择目标窗口")
            return
        try:
            from utils.background_click import create_background_clicker
            clicker = create_background_clicker(hwnd=hwnd)
            if not clicker:
                raise RuntimeError("无法创建后台截图器")
            image = clicker.capture(background=True)
            if image is None:
                image = clicker.capture(background=False)
            if image is None:
                raise RuntimeError("窗口截图失败")

            rgb = image.convert("RGB")
            width, height = rgb.size
            data = rgb.tobytes("raw", "RGB")
            qimg = QImage(data, width, height, width * 3, QImage.Format_RGB888).copy()
            pixmap = QPixmap.fromImage(qimg)
            self._last_preview = pixmap
            self._update_preview_pixmap()
            self._window_state.setText(
                f"已捕获：{self.get_selected_title()} · {width}×{height}"
            )
        except Exception as exc:
            self._preview.setText(f"预览失败\n{exc}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._last_preview is not None:
            self._update_preview_pixmap()

    def _update_preview_pixmap(self):
        if self._last_preview is None:
            return
        target = self._preview.size()
        if target.width() <= 10 or target.height() <= 10:
            return
        self._preview.setPixmap(
            self._last_preview.scaled(
                target.width() - 16,
                target.height() - 16,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

    def append_user(self, text):
        self._history.appendPlainText(f"你：{text}\n")

    def append_assistant(self, text):
        self._history.appendPlainText(f"simpleRPA：{text}\n")

    def set_status(self, text, running=False, error=False):
        self._status.setText(text)
        self._run_btn.setEnabled(not running)
        self._add_btn.setEnabled(not running)
        self._stop_btn.setEnabled(running)
        if error:
            self._status.setStyleSheet("color: #D13438;")
        elif running:
            self._status.setStyleSheet("color: #0078D4; font-weight: 600;")
        else:
            self._status.setStyleSheet(f"color: {text_secondary()};")
