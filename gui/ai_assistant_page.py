import os

from PyQt5.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap

from qfluentwidgets import (
    ScrollArea, TitleLabel, StrongBodyLabel, BodyLabel, CaptionLabel,
    TextEdit, LineEdit, PasswordLineEdit,
    PushButton, PrimaryPushButton, SwitchButton,
    ImageLabel, InfoBar, InfoBarPosition, IndeterminateProgressRing,
    FluentIcon as FIF,
    qconfig, toggleTheme, isDarkTheme,
)

from .widgets import WindowSelector


class AIToolBar(QWidget):
    """Toolbar copied from the official QFluentWidgets GalleryInterface pattern."""

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.titleLabel = TitleLabel("AI 视觉助手", self)
        self.subtitleLabel = CaptionLabel(
            "选择目标窗口，然后直接用自然语言描述任务。", self
        )

        self.vBoxLayout = QVBoxLayout(self)
        self.buttonLayout = QHBoxLayout()

        self.setFixedHeight(118)
        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.setContentsMargins(36, 22, 36, 12)
        self.vBoxLayout.addWidget(self.titleLabel)
        self.vBoxLayout.addSpacing(4)
        self.vBoxLayout.addWidget(self.subtitleLabel)
        self.vBoxLayout.addSpacing(4)
        self.vBoxLayout.addLayout(self.buttonLayout, 1)
        self.vBoxLayout.setAlignment(Qt.AlignTop)

        self.buttonLayout.setSpacing(4)
        self.buttonLayout.setContentsMargins(0, 0, 0, 0)
        self.buttonLayout.addStretch(1)
        self.buttonLayout.setAlignment(Qt.AlignVCenter | Qt.AlignRight)


class ExampleCard(QWidget):
    """Official GalleryInterface ExampleCard layout without the source footer."""

    def __init__(self, title, widget: QWidget, stretch=0, parent=None):
        super().__init__(parent=parent)

        self.widget = widget
        self.stretch = stretch

        self.titleLabel = StrongBodyLabel(title, self)
        self.card = QFrame(self)

        self.vBoxLayout = QVBoxLayout(self)
        self.cardLayout = QVBoxLayout(self.card)
        self.topLayout = QHBoxLayout()

        self.card.setObjectName("card")

        self.vBoxLayout.setSizeConstraint(QVBoxLayout.SetMinimumSize)
        self.cardLayout.setSizeConstraint(QVBoxLayout.SetMinimumSize)
        self.topLayout.setSizeConstraint(QHBoxLayout.SetMinimumSize)

        self.vBoxLayout.setSpacing(12)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.topLayout.setContentsMargins(18, 18, 18, 18)
        self.cardLayout.setContentsMargins(0, 0, 0, 0)

        self.vBoxLayout.addWidget(self.titleLabel, 0, Qt.AlignTop)
        self.vBoxLayout.addWidget(self.card, 0, Qt.AlignTop)
        self.vBoxLayout.setAlignment(Qt.AlignTop)

        self.cardLayout.setSpacing(0)
        self.cardLayout.setAlignment(Qt.AlignTop)
        self.cardLayout.addLayout(self.topLayout, 0)

        self.widget.setParent(self.card)
        self.topLayout.addWidget(self.widget)
        if self.stretch == 0:
            self.topLayout.addStretch(1)

        self.widget.show()


class TargetPanel(QWidget):
    window_selected = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_preview = None

        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(10)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(8)

        self.windowSelector = WindowSelector(compact=True)
        self.windowSelector.refresh_windows()
        self.windowSelector.window_selected.connect(self._on_window_selected)

        self.refreshButton = PushButton(FIF.SYNC, "刷新预览", self)
        self.refreshButton.clicked.connect(self.refresh_preview)

        top.addWidget(self.windowSelector, 1)
        top.addWidget(self.refreshButton)

        self.previewLabel = ImageLabel(self)
        self.previewLabel.setText("选择目标窗口后显示预览")
        self.previewLabel.setAlignment(Qt.AlignCenter)
        self.previewLabel.setMinimumHeight(220)
        self.previewLabel.setMaximumHeight(300)
        self.previewLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.stateLabel = CaptionLabel("尚未选择窗口", self)
        self.stateLabel.setWordWrap(True)

        self.vBoxLayout.addLayout(top)
        self.vBoxLayout.addWidget(self.previewLabel)
        self.vBoxLayout.addWidget(self.stateLabel)

    def get_selected_hwnd(self):
        return self.windowSelector.get_selected_hwnd()

    def get_selected_title(self):
        return self.windowSelector.get_selected_title()

    def _on_window_selected(self, hwnd):
        title = self.get_selected_title()
        self.stateLabel.setText(f"已选择：{title or hwnd}")
        self.window_selected.emit(hwnd)
        self.refresh_preview()

    def refresh_preview(self):
        hwnd = self.get_selected_hwnd()
        if not hwnd:
            self._last_preview = None
            self.previewLabel.clear()
            self.previewLabel.setText("请先选择目标窗口")
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
            self.stateLabel.setText(
                f"已捕获：{self.get_selected_title()} · {width}×{height}"
            )
        except Exception as exc:
            self._last_preview = None
            self.previewLabel.clear()
            self.previewLabel.setText("窗口预览失败")
            InfoBar.error(
                title="预览失败",
                content=str(exc),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3500,
                parent=self.window(),
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._last_preview is not None:
            self._update_preview_pixmap()

    def _update_preview_pixmap(self):
        if self._last_preview is None:
            return

        target = self.previewLabel.size()
        if target.width() <= 20 or target.height() <= 20:
            return

        self.previewLabel.setPixmap(
            self._last_preview.scaled(
                max(1, target.width() - 12),
                max(1, target.height() - 12),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )


class TaskPanel(QWidget):
    submit_requested = pyqtSignal(str, bool)
    stop_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(10)

        self.historyEdit = TextEdit(self)
        self.historyEdit.setReadOnly(True)
        self.historyEdit.setMinimumHeight(240)
        self.historyEdit.setPlaceholderText("任务、识别状态和执行结果会显示在这里")

        self.quickLayout = QGridLayout()
        self.quickLayout.setContentsMargins(0, 0, 0, 0)
        self.quickLayout.setHorizontalSpacing(8)
        self.quickLayout.setVerticalSpacing(8)

        presets = [
            ("清理公告", "关闭当前所有公告、活动说明和普通提示，让页面恢复可操作状态"),
            ("返回首页", "识别当前页面并逐级返回首页或大厅"),
            ("签到奖励", "进入签到页面，把所有免费的可领取奖励领完"),
            ("免费奖励", "在当前页面领取所有明确免费的可领取奖励，不进行购买或消耗"),
        ]
        for i, (label, prompt) in enumerate(presets):
            button = PushButton(label, self)
            button.clicked.connect(
                lambda checked=False, p=prompt: self.set_prompt(p)
            )
            self.quickLayout.addWidget(button, i // 2, i % 2)

        self.inputEdit = TextEdit(self)
        self.inputEdit.setPlaceholderText(
            "输入任务，例如：把今天能免费领取的奖励都领了……"
        )
        self.inputEdit.setFixedHeight(100)

        self.addButton = PushButton(FIF.ADD, "生成到流程", self)
        self.addButton.clicked.connect(lambda: self._submit(False))

        self.runButton = PrimaryPushButton(FIF.PLAY, "立即执行", self)
        self.runButton.clicked.connect(lambda: self._submit(True))

        self.stopButton = PushButton(FIF.CANCEL, "停止", self)
        self.stopButton.setEnabled(False)
        self.stopButton.clicked.connect(self.stop_requested.emit)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(8)
        buttons.addWidget(self.addButton)
        buttons.addWidget(self.runButton, 1)
        buttons.addWidget(self.stopButton)

        self.progressRing = IndeterminateProgressRing(self)
        self.progressRing.setFixedSize(22, 22)
        self.progressRing.hide()

        self.statusLabel = BodyLabel("就绪", self)
        status = QHBoxLayout()
        status.setContentsMargins(0, 0, 0, 0)
        status.setSpacing(8)
        status.addWidget(self.progressRing)
        status.addWidget(self.statusLabel)
        status.addStretch(1)

        self.vBoxLayout.addWidget(self.historyEdit)
        self.vBoxLayout.addWidget(CaptionLabel("快捷任务", self))
        self.vBoxLayout.addLayout(self.quickLayout)
        self.vBoxLayout.addWidget(self.inputEdit)
        self.vBoxLayout.addLayout(buttons)
        self.vBoxLayout.addLayout(status)

        self.append_assistant(
            "可以直接说：\n"
            "• 关闭所有公告并返回首页\n"
            "• 进入签到页面，把免费的奖励领完\n"
            "• 进入战令，领取所有可领取的免费奖励"
        )

    def set_prompt(self, prompt):
        self.inputEdit.setPlainText(prompt)
        self.inputEdit.setFocus()

    def _submit(self, run_now):
        text = self.inputEdit.toPlainText().strip()
        if not text:
            return

        self.append_user(text)
        self.inputEdit.clear()
        self.submit_requested.emit(text, run_now)

    def append_user(self, text):
        self.historyEdit.append(f"你：{text}\n")

    def append_assistant(self, text):
        self.historyEdit.append(f"simpleRPA：{text}\n")

    def set_status(self, text, running=False):
        self.statusLabel.setText(text)
        self.addButton.setEnabled(not running)
        self.runButton.setEnabled(not running)
        self.stopButton.setEnabled(running)

        if running:
            self.progressRing.show()
            self.progressRing.start()
        else:
            self.progressRing.stop()
            self.progressRing.hide()


class SettingsPanel(QWidget):
    config_applied = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.autoCleanup = True
        self.returnHome = True
        self.backgroundMode = True

        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(12)

        self.apiKeyEdit = PasswordLineEdit(self)
        self.apiKeyEdit.setPlaceholderText("Agnes API Key")

        self.modelEdit = LineEdit(self)
        self.modelEdit.setText(os.getenv("AGNES_MODEL") or "agnes-3.0-flash")

        self.baseEdit = LineEdit(self)
        self.baseEdit.setText(
            os.getenv("AGNES_API_BASE") or "https://apihub.agnes-ai.com/v1"
        )

        self.applyButton = PrimaryPushButton(FIF.SETTING, "应用 Agnes 配置", self)
        self.applyButton.clicked.connect(self.apply_config)

        self.themeButton = PushButton("切换浅色 / 深色", self)
        self.themeButton.clicked.connect(lambda: toggleTheme(True))

        self.vBoxLayout.addWidget(CaptionLabel("界面主题", self))
        self.vBoxLayout.addWidget(self.themeButton)
        self.vBoxLayout.addWidget(CaptionLabel("Agnes API Key（仅当前会话）", self))
        self.vBoxLayout.addWidget(self.apiKeyEdit)
        self.vBoxLayout.addWidget(CaptionLabel("模型", self))
        self.vBoxLayout.addWidget(self.modelEdit)
        self.vBoxLayout.addWidget(CaptionLabel("API Base", self))
        self.vBoxLayout.addWidget(self.baseEdit)
        self.vBoxLayout.addWidget(self.applyButton)

        self.vBoxLayout.addSpacing(6)
        self.vBoxLayout.addWidget(StrongBodyLabel("执行选项", self))

        self.autoCleanupSwitch = self._add_switch(
            "自动清理页面",
            "任务开始前关闭公告、活动说明和普通提示",
            True,
        )
        self.returnHomeSwitch = self._add_switch(
            "完成后返回首页",
            "任务完成后由视觉导航逐级返回首页或大厅",
            True,
        )
        self.backgroundSwitch = self._add_switch(
            "后台视觉操作",
            "优先使用后台截图和后台点击，不抢占鼠标",
            True,
        )

    def _add_switch(self, title, description, checked):
        rowWidget = QWidget(self)
        row = QHBoxLayout(rowWidget)
        row.setContentsMargins(0, 6, 0, 6)
        row.setSpacing(12)

        labels = QVBoxLayout()
        labels.setContentsMargins(0, 0, 0, 0)
        labels.setSpacing(1)
        labels.addWidget(BodyLabel(title, rowWidget))

        desc = CaptionLabel(description, rowWidget)
        desc.setWordWrap(True)
        labels.addWidget(desc)

        switch = SwitchButton(rowWidget)
        switch.setChecked(checked)

        row.addLayout(labels, 1)
        row.addWidget(switch, 0, Qt.AlignVCenter)
        self.vBoxLayout.addWidget(rowWidget)

        return switch

    def apply_config(self):
        key = self.apiKeyEdit.text().strip()
        model = self.modelEdit.text().strip()
        base = self.baseEdit.text().strip()

        if key:
            os.environ["AGNES_API_KEY"] = key
        if model:
            os.environ["AGNES_MODEL"] = model
        if base:
            os.environ["AGNES_API_BASE"] = base

        self.config_applied.emit()

    def get_options(self):
        return {
            "prepare_navigation": 1 if self.autoCleanupSwitch.isChecked() else 0,
            "return_home": 1 if self.returnHomeSwitch.isChecked() else 0,
            "background_mode": self.backgroundSwitch.isChecked(),
        }


class AIAssistantPage(ScrollArea):
    """AI page based on the official QFluentWidgets GalleryInterface example."""

    task_requested = pyqtSignal(str, bool)
    stop_requested = pyqtSignal()
    window_selected = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.view = QWidget(self)
        self.toolBar = AIToolBar(self)
        self.vBoxLayout = QVBoxLayout(self.view)

        self.targetPanel = TargetPanel(self.view)
        self.taskPanel = TaskPanel(self.view)
        self.settingsPanel = SettingsPanel(self.view)

        self.targetCard = ExampleCard(
            "目标窗口",
            self.targetPanel,
            stretch=1,
            parent=self.view,
        )
        self.taskCard = ExampleCard(
            "对话任务",
            self.taskPanel,
            stretch=1,
            parent=self.view,
        )
        self.settingsCard = ExampleCard(
            "AI 与执行设置",
            self.settingsPanel,
            stretch=1,
            parent=self.view,
        )

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportMargins(0, self.toolBar.height(), 0, 0)
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setObjectName("aiInterface")

        self.vBoxLayout.setSpacing(30)
        self.vBoxLayout.setAlignment(Qt.AlignTop)
        self.vBoxLayout.setContentsMargins(36, 20, 36, 36)
        self.vBoxLayout.addWidget(self.targetCard, 0, Qt.AlignTop)
        self.vBoxLayout.addWidget(self.taskCard, 0, Qt.AlignTop)
        self.vBoxLayout.addWidget(self.settingsCard, 0, Qt.AlignTop)

        self.view.setObjectName("view")

        self.targetPanel.window_selected.connect(self.window_selected.emit)
        self.taskPanel.submit_requested.connect(self._on_submit)
        self.taskPanel.stop_requested.connect(self.stop_requested.emit)
        self.settingsPanel.config_applied.connect(self._on_config_applied)

        qconfig.themeChangedFinished.connect(self._apply_qss)
        self._apply_qss()

    def _qss_path(self):
        theme = "dark" if isDarkTheme() else "light"
        return os.path.join(
            os.path.dirname(__file__),
            "resources",
            "qss",
            theme,
            "ai_assistant_page.qss",
        )

    def _apply_qss(self):
        try:
            with open(self._qss_path(), "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except Exception as exc:
            print(f"[AI助手样式加载失败] {exc}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.toolBar.resize(self.width(), self.toolBar.height())

    def _on_submit(self, text, run_now):
        if not self.get_selected_hwnd():
            self.set_status("请先选择要操作的窗口", error=True)
            return

        self.task_requested.emit(text, run_now)

    def _on_config_applied(self):
        if os.getenv("AGNES_API_KEY") or os.getenv("AGNESAI_API_KEY"):
            self.taskPanel.append_assistant("Agnes 配置已应用到当前程序会话。")
            InfoBar.success(
                title="Agnes 已配置",
                content="连接设置已生效。",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2500,
                parent=self.window(),
            )
        else:
            self.set_status("尚未填写 Agnes API Key", error=True)

    def get_selected_hwnd(self):
        return self.targetPanel.get_selected_hwnd()

    def get_selected_title(self):
        return self.targetPanel.get_selected_title()

    def get_task_options(self):
        return self.settingsPanel.get_options()

    def refresh_preview(self):
        self.targetPanel.refresh_preview()

    def append_user(self, text):
        self.taskPanel.append_user(text)

    def append_assistant(self, text):
        self.taskPanel.append_assistant(text)

    def set_status(self, text, running=False, error=False):
        self.taskPanel.set_status(text, running=running)

        if error:
            InfoBar.warning(
                title="需要处理",
                content=text,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self.window(),
            )
