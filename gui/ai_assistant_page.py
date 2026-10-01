import os

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QSizePolicy
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap

from qfluentwidgets import (
    ScrollArea, ExpandLayout,
    HeaderCardWidget, GroupHeaderCardWidget,
    SettingCardGroup, SwitchSettingCard, OptionsSettingCard,
    TextEdit, LineEdit, PasswordLineEdit,
    PushButton, PrimaryPushButton,
    ImageLabel, TitleLabel, BodyLabel, CaptionLabel,
    InfoBar, InfoBarPosition, IndeterminateProgressRing,
    FluentIcon as FIF,
    ConfigItem, BoolValidator, qconfig, setTheme,
)

from .widgets import WindowSelector


AUTO_CLEANUP_ITEM = ConfigItem(
    "AI", "AutoCleanup", True, BoolValidator()
)
RETURN_HOME_ITEM = ConfigItem(
    "AI", "ReturnHome", True, BoolValidator()
)
BACKGROUND_MODE_ITEM = ConfigItem(
    "AI", "BackgroundMode", True, BoolValidator()
)


class TargetWindowCard(HeaderCardWidget):
    """Official HeaderCardWidget pattern, matching QFluentWidgets examples."""

    window_selected = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("目标窗口")
        self.setBorderRadius(8)

        self.windowSelector = WindowSelector(compact=True)
        self.windowSelector.refresh_windows()
        self.windowSelector.window_selected.connect(self._on_window_selected)

        self.refreshButton = PushButton(FIF.SYNC, "刷新预览", self)
        self.refreshButton.clicked.connect(self.refresh_preview)

        self.previewLabel = ImageLabel(self)
        self.previewLabel.setText("选择目标窗口后显示预览")
        self.previewLabel.setAlignment(Qt.AlignCenter)
        self.previewLabel.setMinimumHeight(260)
        self.previewLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.stateLabel = CaptionLabel("尚未选择窗口", self)
        self.stateLabel.setWordWrap(True)

        self.topLayout = QHBoxLayout()
        self.topLayout.setContentsMargins(0, 0, 0, 0)
        self.topLayout.setSpacing(10)
        self.topLayout.addWidget(self.windowSelector, 1)
        self.topLayout.addWidget(self.refreshButton, 0, Qt.AlignRight)

        self.contentLayout = QVBoxLayout()
        self.contentLayout.setContentsMargins(0, 0, 0, 0)
        self.contentLayout.setSpacing(10)
        self.contentLayout.addLayout(self.topLayout)
        self.contentLayout.addWidget(self.previewLabel)
        self.contentLayout.addWidget(self.stateLabel)

        # HeaderCardWidget.viewLayout is a QHBoxLayout in QFluentWidgets.
        # The official examples add one vertical layout into it.
        self.viewLayout.addLayout(self.contentLayout)

        self._last_preview = None

    def _on_window_selected(self, hwnd):
        title = self.windowSelector.get_selected_title()
        self.stateLabel.setText(f"已选择：{title or hwnd}")
        self.window_selected.emit(hwnd)
        self.refresh_preview()

    def get_selected_hwnd(self):
        return self.windowSelector.get_selected_hwnd()

    def get_selected_title(self):
        return self.windowSelector.get_selected_title()

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


class TaskCard(HeaderCardWidget):
    """Task editor using the official HeaderCardWidget.viewLayout API."""

    submit_requested = pyqtSignal(str, bool)
    stop_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("对话任务")
        self.setBorderRadius(8)

        self.historyEdit = TextEdit(self)
        self.historyEdit.setReadOnly(True)
        self.historyEdit.setMinimumHeight(260)
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

        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setContentsMargins(0, 0, 0, 0)
        self.buttonLayout.setSpacing(8)
        self.buttonLayout.addWidget(self.addButton)
        self.buttonLayout.addWidget(self.runButton, 1)
        self.buttonLayout.addWidget(self.stopButton)

        self.progressRing = IndeterminateProgressRing(self)
        self.progressRing.setFixedSize(22, 22)
        self.progressRing.hide()

        self.statusLabel = BodyLabel("就绪", self)
        self.statusLayout = QHBoxLayout()
        self.statusLayout.setContentsMargins(0, 0, 0, 0)
        self.statusLayout.setSpacing(8)
        self.statusLayout.addWidget(self.progressRing)
        self.statusLayout.addWidget(self.statusLabel)
        self.statusLayout.addStretch(1)

        self.contentLayout = QVBoxLayout()
        self.contentLayout.setContentsMargins(0, 0, 0, 0)
        self.contentLayout.setSpacing(10)
        self.contentLayout.addWidget(self.historyEdit)
        self.contentLayout.addWidget(CaptionLabel("快捷任务", self))
        self.contentLayout.addLayout(self.quickLayout)
        self.contentLayout.addWidget(self.inputEdit)
        self.contentLayout.addLayout(self.buttonLayout)
        self.contentLayout.addLayout(self.statusLayout)

        # Same composition pattern as the official SystemRequirementCard demo:
        # one internal vertical layout is attached to HeaderCardWidget.viewLayout.
        self.viewLayout.addLayout(self.contentLayout)

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


class AgnesConnectionCard(GroupHeaderCardWidget):
    """Official GroupHeaderCardWidget.addGroup() pattern from the gallery demo."""

    config_applied = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Agnes 连接")
        self.setBorderRadius(8)

        self.apiKeyEdit = PasswordLineEdit(self)
        self.apiKeyEdit.setPlaceholderText("粘贴 API Key")
        self.apiKeyEdit.setFixedWidth(360)

        self.modelEdit = LineEdit(self)
        self.modelEdit.setText(os.getenv("AGNES_MODEL") or "agnes-3.0-flash")
        self.modelEdit.setFixedWidth(360)

        self.baseEdit = LineEdit(self)
        self.baseEdit.setText(
            os.getenv("AGNES_API_BASE") or "https://apihub.agnes-ai.com/v1"
        )
        self.baseEdit.setFixedWidth(360)

        self.applyButton = PrimaryPushButton("应用", self)
        self.applyButton.setFixedWidth(120)
        self.applyButton.clicked.connect(self.apply_config)

        self.addGroup(
            FIF.SETTING,
            "API Key",
            "仅保存到当前程序会话，不写入脚本或仓库",
            self.apiKeyEdit,
        )
        self.addGroup(
            FIF.APPLICATION,
            "模型",
            "Agnes 视觉模型名称",
            self.modelEdit,
        )
        self.addGroup(
            FIF.SYNC,
            "API Base",
            "OpenAI 兼容 API 地址",
            self.baseEdit,
        )
        self.addGroup(
            FIF.SETTING,
            "应用配置",
            "使上面的连接设置立即生效",
            self.applyButton,
        )

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


class AIAssistantPage(ScrollArea):
    """AI page following QFluentWidgets official ScrollArea examples."""

    task_requested = pyqtSignal(str, bool)
    stop_requested = pyqtSignal()
    window_selected = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)

        self.titleLabel = TitleLabel("AI 视觉助手", self)
        self.subtitleLabel = CaptionLabel(
            "选择目标窗口，然后直接描述任务。", self
        )

        self.targetCard = TargetWindowCard(self.view)
        self.taskCard = TaskCard(self.view)
        self.connectionCard = AgnesConnectionCard(self.view)

        self.behaviorGroup = SettingCardGroup("界面与执行", self.view)
        self.themeCard = OptionsSettingCard(
            qconfig.themeMode,
            FIF.BRUSH,
            "应用主题",
            "切换浅色、深色或跟随系统",
            texts=["浅色", "深色", "跟随系统"],
            parent=self.behaviorGroup,
        )
        self.autoCleanupCard = SwitchSettingCard(
            FIF.APPLICATION,
            "自动清理页面",
            "任务开始前关闭公告、活动说明和普通提示",
            configItem=AUTO_CLEANUP_ITEM,
            parent=self.behaviorGroup,
        )
        self.returnHomeCard = SwitchSettingCard(
            FIF.HOME,
            "完成后返回首页",
            "任务完成后由视觉导航逐级返回首页或大厅",
            configItem=RETURN_HOME_ITEM,
            parent=self.behaviorGroup,
        )
        self.backgroundCard = SwitchSettingCard(
            FIF.SETTING,
            "后台视觉操作",
            "优先使用后台截图和后台点击，不抢占鼠标",
            configItem=BACKGROUND_MODE_ITEM,
            parent=self.behaviorGroup,
        )

        self._init_widget()
        self._init_layout()
        self._connect_signals()

    def _init_widget(self):
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 86, 0, 20)
        self.setObjectName("aiInterface")
        self.view.setObjectName("aiScrollWidget")

        # This is the same approach used by the official AppInterface demo.
        self.enableTransparentBackground()

        self.titleLabel.move(36, 24)
        self.subtitleLabel.move(36, 56)

    def _init_layout(self):
        self.behaviorGroup.addSettingCard(self.themeCard)
        self.behaviorGroup.addSettingCard(self.autoCleanupCard)
        self.behaviorGroup.addSettingCard(self.returnHomeCard)
        self.behaviorGroup.addSettingCard(self.backgroundCard)

        self.vBoxLayout.setSpacing(18)
        self.vBoxLayout.setContentsMargins(36, 8, 36, 36)
        self.vBoxLayout.addWidget(self.targetCard, 0, Qt.AlignTop)
        self.vBoxLayout.addWidget(self.taskCard, 0, Qt.AlignTop)
        self.vBoxLayout.addWidget(self.connectionCard, 0, Qt.AlignTop)
        self.vBoxLayout.addWidget(self.behaviorGroup, 0, Qt.AlignTop)
        self.vBoxLayout.addStretch(1)

    def _connect_signals(self):
        self.targetCard.window_selected.connect(self.window_selected.emit)
        self.taskCard.submit_requested.connect(self._on_submit)
        self.taskCard.stop_requested.connect(self.stop_requested.emit)
        self.connectionCard.config_applied.connect(self._on_config_applied)

        # OptionsSettingCard updates qconfig.themeMode itself. Because this page
        # uses the global qconfig item directly, refresh the Fluent stylesheet after
        # the option changes (the official demo does this via its own cfg.themeChanged).
        self.themeCard.optionChanged.connect(
            lambda _: setTheme(qconfig.get(qconfig.themeMode))
        )

    def _on_submit(self, text, run_now):
        if not self.get_selected_hwnd():
            self.set_status("请先选择要操作的窗口", error=True)
            return

        self.task_requested.emit(text, run_now)

    def _on_config_applied(self):
        if os.getenv("AGNES_API_KEY") or os.getenv("AGNESAI_API_KEY"):
            self.taskCard.append_assistant("Agnes 配置已应用到当前程序会话。")
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
        return self.targetCard.get_selected_hwnd()

    def get_selected_title(self):
        return self.targetCard.get_selected_title()

    def get_task_options(self):
        return {
            "prepare_navigation": 1 if qconfig.get(AUTO_CLEANUP_ITEM) else 0,
            "return_home": 1 if qconfig.get(RETURN_HOME_ITEM) else 0,
            "background_mode": bool(qconfig.get(BACKGROUND_MODE_ITEM)),
        }

    def refresh_preview(self):
        self.targetCard.refresh_preview()

    def append_user(self, text):
        self.taskCard.append_user(text)

    def append_assistant(self, text):
        self.taskCard.append_assistant(text)

    def set_status(self, text, running=False, error=False):
        self.taskCard.set_status(text, running=running)

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
