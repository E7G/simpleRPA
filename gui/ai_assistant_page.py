import os

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QSizePolicy,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap

from qfluentwidgets import (
    TitleLabel, BodyLabel, CaptionLabel, TextEdit,
    LineEdit, PasswordLineEdit, PushButton, PrimaryPushButton,
    HeaderCardWidget, ImageLabel, InfoBadge, InfoBar, InfoBarPosition,
    SwitchSettingCard, IndeterminateProgressRing, FluentIcon,
    ComboBox, setTheme, Theme,
)

from .widgets import WindowSelector


class AIAssistantPage(QWidget):
    """Conversation-first UI built only from QFluentWidgets controls."""

    task_requested = pyqtSignal(str, bool)  # instruction, run_now
    stop_requested = pyqtSignal()
    window_selected = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_preview = None
        self._api_badge = None
        self._setup_ui()
        self.refresh_api_status()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # Header
        header = QHBoxLayout()
        header.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.addWidget(TitleLabel("AI 视觉助手"))
        title_box.addWidget(
            CaptionLabel("选择目标窗口，然后直接用自然语言描述任务。")
        )
        header.addLayout(title_box)
        header.addStretch()

        self._badge_host = QWidget(self)
        self._badge_layout = QHBoxLayout(self._badge_host)
        self._badge_layout.setContentsMargins(0, 0, 0, 0)
        self._badge_layout.setSpacing(0)
        header.addWidget(self._badge_host, 0, Qt.AlignTop)
        root.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(12)

        self._build_target_card()
        self._build_chat_card()
        self._build_settings_card()

        body.addWidget(self._target_card, 0)
        body.addWidget(self._chat_card, 1)
        body.addWidget(self._settings_card, 0)
        root.addLayout(body, 1)

    def _build_target_card(self):
        self._target_card = HeaderCardWidget(self)
        self._target_card.setTitle("1 · 目标窗口")
        self._target_card.setMinimumWidth(320)
        self._target_card.setMaximumWidth(430)

        layout = QVBoxLayout(self._target_card.view)
        layout.setContentsMargins(16, 10, 16, 16)
        layout.setSpacing(10)

        self._window_selector = WindowSelector(compact=False)
        self._window_selector.refresh_windows()
        self._window_selector.window_selected.connect(self._on_window_selected)
        layout.addWidget(self._window_selector)

        preview_row = QHBoxLayout()
        preview_row.addWidget(BodyLabel("窗口预览"))
        preview_row.addStretch()
        self._preview_btn = PushButton("刷新预览")
        self._preview_btn.clicked.connect(self.refresh_preview)
        preview_row.addWidget(self._preview_btn)
        layout.addLayout(preview_row)

        self._preview = ImageLabel(self)
        self._preview.setText("选择窗口后显示预览")
        self._preview.setAlignment(Qt.AlignCenter)
        self._preview.setMinimumHeight(280)
        self._preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self._preview, 1)

        self._window_state = CaptionLabel("尚未选择窗口")
        self._window_state.setWordWrap(True)
        layout.addWidget(self._window_state)

    def _build_chat_card(self):
        self._chat_card = HeaderCardWidget(self)
        self._chat_card.setTitle("2 · 对话任务")

        layout = QVBoxLayout(self._chat_card.view)
        layout.setContentsMargins(16, 10, 16, 16)
        layout.setSpacing(10)

        self._history = TextEdit(self)
        self._history.setReadOnly(True)
        self._history.setMinimumHeight(330)
        self._history.setPlaceholderText("任务、识别状态和执行结果会显示在这里")
        layout.addWidget(self._history, 1)

        self.append_assistant(
            "你可以直接说：\n"
            "• 关闭所有公告并返回首页\n"
            "• 进入签到页面，把免费的奖励领完\n"
            "• 进入战令，领取所有可领取的免费奖励，完成后回首页"
        )

        layout.addWidget(CaptionLabel("快捷任务"))

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
            button = PushButton(label)
            button.clicked.connect(lambda checked=False, p=prompt: self._set_prompt(p))
            quick.addWidget(button, i // 2, i % 2)
        layout.addLayout(quick)

        self._input = TextEdit(self)
        self._input.setPlaceholderText("输入任务，例如：把今天能免费领取的奖励都领了……")
        self._input.setFixedHeight(105)
        layout.addWidget(self._input)

        actions = QHBoxLayout()
        actions.setSpacing(8)

        self._add_btn = PushButton(FluentIcon.ADD, "生成到流程")
        self._add_btn.clicked.connect(lambda: self._submit(False))
        actions.addWidget(self._add_btn)

        self._run_btn = PrimaryPushButton(FluentIcon.PLAY, "立即执行")
        self._run_btn.clicked.connect(lambda: self._submit(True))
        actions.addWidget(self._run_btn, 1)

        self._stop_btn = PushButton(FluentIcon.CANCEL, "停止")
        self._stop_btn.clicked.connect(self.stop_requested.emit)
        self._stop_btn.setEnabled(False)
        actions.addWidget(self._stop_btn)
        layout.addLayout(actions)

        status_row = QHBoxLayout()
        self._progress = IndeterminateProgressRing(self)
        self._progress.setFixedSize(22, 22)
        self._progress.hide()
        status_row.addWidget(self._progress)
        self._status = BodyLabel("就绪")
        status_row.addWidget(self._status)
        status_row.addStretch()
        layout.addLayout(status_row)

    def _build_settings_card(self):
        self._settings_card = HeaderCardWidget(self)
        self._settings_card.setTitle("3 · AI 与执行设置")
        self._settings_card.setMinimumWidth(310)
        self._settings_card.setMaximumWidth(390)

        layout = QVBoxLayout(self._settings_card.view)
        layout.setContentsMargins(12, 10, 12, 16)
        layout.setSpacing(10)

        layout.addWidget(CaptionLabel("界面主题"))
        self._theme = ComboBox(self)
        self._theme.addItems(["跟随系统", "浅色", "深色"])
        self._theme.setCurrentIndex(0)
        self._theme.currentTextChanged.connect(self._on_theme_changed)
        layout.addWidget(self._theme)

        layout.addWidget(CaptionLabel("Agnes API Key（仅当前会话）"))
        self._api_key = PasswordLineEdit(self)
        self._api_key.setPlaceholderText("粘贴 API Key")
        layout.addWidget(self._api_key)

        layout.addWidget(CaptionLabel("模型"))
        self._model = LineEdit(self)
        self._model.setText(os.getenv("AGNES_MODEL") or "agnes-3.0-flash")
        layout.addWidget(self._model)

        layout.addWidget(CaptionLabel("API Base"))
        self._base = LineEdit(self)
        self._base.setText(
            os.getenv("AGNES_API_BASE") or "https://apihub.agnes-ai.com/v1"
        )
        layout.addWidget(self._base)

        self._apply_api_btn = PrimaryPushButton(FluentIcon.SETTING, "应用 Agnes 配置")
        self._apply_api_btn.clicked.connect(self.apply_api_config)
        layout.addWidget(self._apply_api_btn)

        self._auto_cleanup = SwitchSettingCard(
            FluentIcon.APPLICATION,
            "自动清理页面",
            "任务前关闭公告、活动说明和普通提示",
            parent=self,
        )
        self._auto_cleanup.setChecked(True)
        layout.addWidget(self._auto_cleanup)

        self._return_home = SwitchSettingCard(
            FluentIcon.HOME,
            "完成后返回首页",
            "任务完成后由视觉导航逐级返回首页或大厅",
            parent=self,
        )
        self._return_home.setChecked(True)
        layout.addWidget(self._return_home)

        self._background = SwitchSettingCard(
            FluentIcon.SETTING,
            "后台视觉操作",
            "优先使用后台截图和后台点击，不抢占鼠标",
            parent=self,
        )
        self._background.setChecked(True)
        layout.addWidget(self._background)

        hint = CaptionLabel(
            "视觉 Agent 有最大步骤数限制；购买、支付、充值、删除数据等高风险操作不会自动执行。"
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch()

    def _on_theme_changed(self, text):
        mapping = {
            "跟随系统": Theme.AUTO,
            "浅色": Theme.LIGHT,
            "深色": Theme.DARK,
        }
        setTheme(mapping.get(text, Theme.AUTO))

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
            InfoBar.success(
                title="Agnes 已配置",
                content="API 配置仅在当前程序会话中生效。",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2500,
                parent=self,
            )
        else:
            self.set_status("尚未填写 Agnes API Key", error=True)

    def _replace_api_badge(self, configured):
        if self._api_badge is not None:
            self._badge_layout.removeWidget(self._api_badge)
            self._api_badge.deleteLater()

        if configured:
            self._api_badge = InfoBadge.success("Agnes 已配置", parent=self)
        else:
            self._api_badge = InfoBadge.warning("Agnes 未配置", parent=self)

        self._badge_layout.addWidget(self._api_badge)

    def refresh_api_status(self):
        configured = bool(os.getenv("AGNES_API_KEY") or os.getenv("AGNESAI_API_KEY"))
        self._replace_api_badge(configured)

    def refresh_preview(self):
        hwnd = self.get_selected_hwnd()
        if not hwnd:
            self._preview.clear()
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
            qimg = QImage(
                data, width, height, width * 3, QImage.Format_RGB888
            ).copy()

            self._last_preview = QPixmap.fromImage(qimg)
            self._update_preview_pixmap()
            self._window_state.setText(
                f"已捕获：{self.get_selected_title()} · {width}×{height}"
            )
        except Exception as exc:
            self._last_preview = None
            self._preview.clear()
            self._preview.setText("窗口预览失败")
            InfoBar.error(
                title="预览失败",
                content=str(exc),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3500,
                parent=self,
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._last_preview is not None:
            self._update_preview_pixmap()

    def _update_preview_pixmap(self):
        if self._last_preview is None:
            return

        target = self._preview.size()
        if target.width() <= 20 or target.height() <= 20:
            return

        self._preview.setPixmap(
            self._last_preview.scaled(
                max(1, target.width() - 12),
                max(1, target.height() - 12),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

    def append_user(self, text):
        self._history.append(f"你：{text}\n")

    def append_assistant(self, text):
        self._history.append(f"simpleRPA：{text}\n")

    def set_status(self, text, running=False, error=False):
        self._status.setText(text)
        self._run_btn.setEnabled(not running)
        self._add_btn.setEnabled(not running)
        self._stop_btn.setEnabled(running)

        if running:
            self._progress.show()
            self._progress.start()
        else:
            self._progress.stop()
            self._progress.hide()

        if error:
            InfoBar.warning(
                title="需要处理",
                content=text,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )
