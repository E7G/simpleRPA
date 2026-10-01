import os
import threading
import time
from collections import deque

from PyQt5.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QSizePolicy
)
from PyQt5.QtCore import Qt, QSize, QTimer, pyqtSignal
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
from utils.secure_store import (
    load_saved_agnes_key,
    save_agnes_key,
    delete_saved_agnes_key,
)


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


class PreviewPane(QWidget):
    """Large preview viewport that keeps QFluentWidgets ImageLabel from resizing the page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._source = QImage()

        self.setMinimumSize(350, 600)
        self.setMaximumHeight(760)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(8, 8, 8, 8)
        self.vBoxLayout.setSpacing(0)

        self.placeholderLabel = CaptionLabel("选择目标窗口后显示大预览", self)
        self.placeholderLabel.setAlignment(Qt.AlignCenter)

        self.imageLabel = ImageLabel(self)
        self.imageLabel.setAlignment(Qt.AlignCenter)
        self.imageLabel.setBorderRadius(8, 8, 8, 8)
        self.imageLabel.hide()

        self.vBoxLayout.addWidget(self.placeholderLabel, 1, Qt.AlignCenter)
        self.vBoxLayout.addWidget(self.imageLabel, 0, Qt.AlignCenter)

    def clear_preview(self, text="选择目标窗口后显示大预览"):
        self._source = QImage()
        self.imageLabel.hide()
        self.placeholderLabel.setText(text)
        self.placeholderLabel.show()

    def set_image(self, image: QImage):
        self._source = image.copy()
        self.placeholderLabel.hide()
        self.imageLabel.show()
        self.imageLabel.setImage(self._source)
        self._fit_image()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_image()

    def _fit_image(self):
        if self._source.isNull() or not self.imageLabel.isVisible():
            return

        margins = self.vBoxLayout.contentsMargins()
        available_w = max(1, self.width() - margins.left() - margins.right())
        available_h = max(1, self.height() - margins.top() - margins.bottom())

        image_w = max(1, self._source.width())
        image_h = max(1, self._source.height())
        scale = min(available_w / image_w, available_h / image_h)

        fitted = QSize(
            max(1, int(image_w * scale)),
            max(1, int(image_h * scale)),
        )
        self.imageLabel.setScaledSize(fitted)


class TargetPanel(QWidget):
    window_selected = pyqtSignal(object)
    preview_result = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_preview = None
        self._preview_busy = False
        self._preview_failures = 0
        self._live_page_active = True
        self._frame_times = deque(maxlen=90)
        self._preview_clicker = None
        self._preview_clicker_hwnd = None

        self.preview_result.connect(self._on_preview_result)

        self.liveTimer = QTimer(self)
        self.liveTimer.setTimerType(Qt.PreciseTimer)
        # Poll faster than the capture backend so the next frame starts
        # immediately after the previous one finishes. Real PrintWindow preview
        # on Windows measures ~29 FPS without queueing frames or stealing focus.
        self.liveTimer.setInterval(16)
        self.liveTimer.timeout.connect(self._request_live_frame)

        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(10)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(8)

        self.windowSelector = WindowSelector(compact=True)
        self.windowSelector.refresh_windows()
        self.windowSelector.window_selected.connect(self._on_window_selected)

        self.refreshButton = PushButton(FIF.SYNC, "立即刷新", self)
        self.refreshButton.clicked.connect(self.refresh_preview)

        top.addWidget(self.windowSelector, 1)
        top.addWidget(self.refreshButton)

        self.previewPane = PreviewPane(self)
        # Backward-compatible alias for code/tests that still reference previewLabel.
        self.previewLabel = self.previewPane.imageLabel

        self.stateLabel = CaptionLabel("尚未选择窗口", self)
        self.stateLabel.setWordWrap(True)

        self.vBoxLayout.addLayout(top)
        self.vBoxLayout.addWidget(self.previewPane)
        self.vBoxLayout.addWidget(self.stateLabel)

    def get_selected_hwnd(self):
        return self.windowSelector.get_selected_hwnd()

    def get_selected_title(self):
        return self.windowSelector.get_selected_title()

    def _on_window_selected(self, hwnd):
        title = self.get_selected_title()
        self.stateLabel.setText(f"实时预览：{title or hwnd}")
        self.window_selected.emit(hwnd)
        self._preview_failures = 0
        self._preview_clicker = None
        self._preview_clicker_hwnd = None
        self._frame_times.clear()
        self._update_live_timer()
        self._request_live_frame(force=True)

    def set_live_page_active(self, active: bool):
        self._live_page_active = bool(active)
        self._update_live_timer()
        if active:
            self._request_live_frame(force=True)

    def _update_live_timer(self):
        # Live preview is a fixed behavior of the AI assistant, not a user option.
        should_run = bool(
            self._live_page_active
            and self.get_selected_hwnd()
        )
        if should_run:
            if not self.liveTimer.isActive():
                self.liveTimer.start()
        else:
            self.liveTimer.stop()

    def refresh_preview(self):
        self._request_live_frame(force=True)

    def _request_live_frame(self, force=False):
        hwnd = self.get_selected_hwnd()
        if not hwnd:
            self.liveTimer.stop()
            self._last_preview = None
            self.previewPane.clear_preview("请先选择目标窗口")
            return

        if self._preview_busy:
            return

        if not force and not self._live_page_active:
            return

        self._preview_busy = True
        thread = threading.Thread(
            target=self._capture_preview_worker,
            args=(hwnd,),
            daemon=True,
            name="simpleRPA-live-preview",
        )
        thread.start()

    def _capture_preview_worker(self, hwnd):
        result = {
            "hwnd": hwnd,
            "image": None,
            "width": 0,
            "height": 0,
            "error": None,
        }
        try:
            from utils.background_click import create_background_clicker

            if self._preview_clicker is None or self._preview_clicker_hwnd != hwnd:
                self._preview_clicker = create_background_clicker(hwnd=hwnd)
                self._preview_clicker_hwnd = hwnd

            clicker = self._preview_clicker
            if not clicker:
                raise RuntimeError("无法创建后台截图器")

            image = clicker.capture(background=True)
            if image is None:
                raise RuntimeError("后台窗口截图失败")

            rgb = image.convert("RGB")
            width, height = rgb.size
            data = rgb.tobytes("raw", "RGB")
            qimg = QImage(
                data, width, height, width * 3, QImage.Format_RGB888
            ).copy()

            result["image"] = qimg
            result["width"] = width
            result["height"] = height
        except Exception as exc:
            result["error"] = str(exc)

        self.preview_result.emit(result)

    def _on_preview_result(self, result):
        self._preview_busy = False

        hwnd = result.get("hwnd")
        if hwnd != self.get_selected_hwnd():
            return

        qimg = result.get("image")
        if qimg is not None and not qimg.isNull():
            self._preview_failures = 0
            self._last_preview = QPixmap.fromImage(qimg)
            self.previewPane.set_image(qimg)

            now = time.perf_counter()
            self._frame_times.append(now)
            actual_fps = 0.0
            if len(self._frame_times) >= 2:
                elapsed = self._frame_times[-1] - self._frame_times[0]
                if elapsed > 0:
                    actual_fps = (len(self._frame_times) - 1) / elapsed

            self.stateLabel.setText(
                f"后台实时预览 · {actual_fps:.1f} FPS · "
                f"{result.get('width')}×{result.get('height')} · "
                f"{self.get_selected_title()}"
            )
            return

        self._preview_failures += 1
        if self._preview_failures >= 3:
            self.stateLabel.setText(
                f"实时预览暂时无法抓帧：{result.get('error') or '后台截图失败'}"
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

        saved_key = None
        try:
            saved_key = load_saved_agnes_key()
        except Exception:
            saved_key = None

        if saved_key:
            os.environ["AGNES_API_KEY"] = saved_key
            self.apiKeyEdit.setText(saved_key)
        elif os.getenv("AGNES_API_KEY"):
            self.apiKeyEdit.setText(os.getenv("AGNES_API_KEY"))

        self.modelEdit = LineEdit(self)
        self.modelEdit.setText(os.getenv("AGNES_MODEL") or "agnes-3.0-flash")

        self.baseEdit = LineEdit(self)
        self.baseEdit.setText(
            os.getenv("AGNES_API_BASE") or "https://apihub.agnes-ai.com/v1"
        )

        self.applyButton = PrimaryPushButton(FIF.SETTING, "应用 Agnes 配置", self)
        self.applyButton.clicked.connect(self.apply_config)

        self.rememberKeySwitch = SwitchButton(self)
        self.rememberKeySwitch.setChecked(True)

        self.clearSavedKeyButton = PushButton(FIF.DELETE, "清除已保存 Key", self)
        self.clearSavedKeyButton.clicked.connect(self.clear_saved_key)

        self.keyStatusLabel = CaptionLabel(
            "已从 Windows 加密存储加载" if saved_key else "尚未保存到 Windows 加密存储",
            self,
        )
        self.keyStatusLabel.setWordWrap(True)

        self.themeButton = PushButton("切换浅色 / 深色", self)
        self.themeButton.clicked.connect(lambda: toggleTheme(True))

        self.vBoxLayout.addWidget(CaptionLabel("界面主题", self))
        self.vBoxLayout.addWidget(self.themeButton)
        self.vBoxLayout.addWidget(CaptionLabel("Agnes API Key", self))
        self.vBoxLayout.addWidget(self.apiKeyEdit)

        rememberRow = QWidget(self)
        rememberLayout = QHBoxLayout(rememberRow)
        rememberLayout.setContentsMargins(0, 4, 0, 4)
        rememberLayout.setSpacing(10)
        rememberText = QVBoxLayout()
        rememberText.setContentsMargins(0, 0, 0, 0)
        rememberText.setSpacing(1)
        rememberText.addWidget(BodyLabel("记住 API Key", rememberRow))
        rememberDesc = CaptionLabel(
            "使用 Windows DPAPI 按当前用户加密保存，下次启动自动加载",
            rememberRow,
        )
        rememberDesc.setWordWrap(True)
        rememberText.addWidget(rememberDesc)
        rememberLayout.addLayout(rememberText, 1)
        rememberLayout.addWidget(self.rememberKeySwitch, 0, Qt.AlignVCenter)
        self.vBoxLayout.addWidget(rememberRow)
        self.vBoxLayout.addWidget(self.keyStatusLabel)
        self.vBoxLayout.addWidget(self.clearSavedKeyButton)

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
            if self.rememberKeySwitch.isChecked():
                try:
                    save_agnes_key(key)
                    self.keyStatusLabel.setText("已使用 Windows DPAPI 加密保存")
                except Exception as exc:
                    self.keyStatusLabel.setText(f"加密保存失败：{exc}")
            else:
                try:
                    delete_saved_agnes_key()
                except Exception:
                    pass
                self.keyStatusLabel.setText("仅当前会话使用，不保存")
        else:
            os.environ.pop("AGNES_API_KEY", None)
            try:
                delete_saved_agnes_key()
            except Exception:
                pass
            self.keyStatusLabel.setText("未配置 API Key")

        if model:
            os.environ["AGNES_MODEL"] = model
        if base:
            os.environ["AGNES_API_BASE"] = base

        self.config_applied.emit()

    def clear_saved_key(self):
        try:
            delete_saved_agnes_key()
        finally:
            os.environ.pop("AGNES_API_KEY", None)
            os.environ.pop("AGNESAI_API_KEY", None)
            self.apiKeyEdit.clear()
            self.keyStatusLabel.setText("已清除 Windows 加密保存的 API Key")
            self.config_applied.emit()

    def get_options(self):
        return {
            "prepare_navigation": 1 if self.autoCleanupSwitch.isChecked() else 0,
            "return_home": 1 if self.returnHomeSwitch.isChecked() else 0,
            # AI Assistant is background-only. This is intentionally not a UI option.
            "background_mode": True,
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
        self.targetCard.setMinimumWidth(410)
        self.targetCard.setMaximumWidth(460)

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

        # Gallery-style page, but arranged as a workspace:
        # tall portrait preview on the left, task/settings stack on the right.
        self.bodyWidget = QWidget(self.view)
        self.bodyLayout = QHBoxLayout(self.bodyWidget)
        self.bodyLayout.setContentsMargins(0, 0, 0, 0)
        self.bodyLayout.setSpacing(20)
        self.bodyLayout.setAlignment(Qt.AlignTop)

        self.rightWidget = QWidget(self.bodyWidget)
        self.rightLayout = QVBoxLayout(self.rightWidget)
        self.rightLayout.setContentsMargins(0, 0, 0, 0)
        self.rightLayout.setSpacing(24)
        self.rightLayout.setAlignment(Qt.AlignTop)
        self.rightLayout.addWidget(self.taskCard, 0, Qt.AlignTop)
        self.rightLayout.addWidget(self.settingsCard, 0, Qt.AlignTop)
        self.rightLayout.addStretch(1)

        self.bodyLayout.addWidget(self.targetCard, 0, Qt.AlignTop)
        self.bodyLayout.addWidget(self.rightWidget, 1)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportMargins(0, self.toolBar.height(), 0, 0)
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setObjectName("aiInterface")

        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.setAlignment(Qt.AlignTop)
        self.vBoxLayout.setContentsMargins(36, 20, 36, 36)
        self.vBoxLayout.addWidget(self.bodyWidget, 0, Qt.AlignTop)

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

    def showEvent(self, event):
        super().showEvent(event)
        self.targetPanel.set_live_page_active(True)

    def hideEvent(self, event):
        self.targetPanel.set_live_page_active(False)
        super().hideEvent(event)

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
