"""定时任务管理页。"""

import os
from datetime import datetime
from typing import Optional, List

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog,
    QDialog, QFormLayout, QButtonGroup, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer

from qfluentwidgets import (
    FluentIcon, TitleLabel, BodyLabel, StrongBodyLabel, CaptionLabel,
    PushButton, PrimaryPushButton, CardWidget, ScrollArea,
    TransparentToolButton, SwitchButton, ComboBox, LineEdit,
    SpinBox, TimeEdit, CheckBox, InfoBar, InfoBarPosition,
    MessageBox, HeaderCardWidget, IconWidget, ElevatedCardWidget,
    IndeterminateProgressRing
)

from core.scheduler import (
    SchedulerService, ScheduledTask, ScheduleType, WEEKDAY_LABELS
)
from utils.config import Config


class WeekdaySelector(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self._boxes: List[CheckBox] = []
        for i, label in enumerate(WEEKDAY_LABELS):
            cb = CheckBox(label)
            cb.setChecked(i < 5)
            self._boxes.append(cb)
            layout.addWidget(cb)
        layout.addStretch()

    def get_selected(self) -> List[int]:
        return [i for i, cb in enumerate(self._boxes) if cb.isChecked()]

    def set_selected(self, days: List[int]):
        for i, cb in enumerate(self._boxes):
            cb.setChecked(i in days)


class TaskEditDialog(QDialog):
    def __init__(self, task: Optional[ScheduledTask] = None, parent=None):
        super().__init__(parent)
        self._task = task
        self._result_task: Optional[ScheduledTask] = None
        self.setWindowTitle("编辑定时任务" if task else "新建定时任务")
        self.setMinimumWidth(480)
        self._setup_ui()
        if task:
            self._load_task(task)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(12)

        self._name_edit = LineEdit()
        self._name_edit.setPlaceholderText("任务名称")
        form.addRow("名称", self._name_edit)

        path_row = QHBoxLayout()
        self._path_edit = LineEdit()
        self._path_edit.setPlaceholderText("选择 .rpa.json 或 .scripts.json")
        path_row.addWidget(self._path_edit, 1)
        browse_btn = PushButton(FluentIcon.FOLDER, "浏览")
        browse_btn.clicked.connect(self._browse_script)
        path_row.addWidget(browse_btn)
        form.addRow("脚本", path_row)

        self._type_combo = ComboBox()
        self._type_combo.addItems(["每天", "每周", "单次", "间隔"])
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        form.addRow("调度类型", self._type_combo)

        self._time_edit = TimeEdit()
        form.addRow("执行时间", self._time_edit)

        self._weekday_widget = WeekdaySelector()
        form.addRow("星期", self._weekday_widget)

        self._interval_spin = SpinBox()
        self._interval_spin.setRange(1, 10080)
        self._interval_spin.setValue(60)
        self._interval_spin.setSuffix(" 分钟")
        form.addRow("间隔", self._interval_spin)

        self._speed_spin = SpinBox()
        self._speed_spin.setRange(1, 10)
        self._speed_spin.setValue(1)
        form.addRow("速度倍率", self._speed_spin)

        self._repeat_spin = SpinBox()
        self._repeat_spin.setRange(1, 999)
        self._repeat_spin.setValue(1)
        form.addRow("重复次数", self._repeat_spin)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = PushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        ok_btn = PrimaryPushButton("确定")
        ok_btn.clicked.connect(self._accept)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

        self._on_type_changed(0)

    def _on_type_changed(self, _index):
        idx = self._type_combo.currentIndex()
        is_weekly = idx == 1
        is_interval = idx == 3
        self._time_edit.setEnabled(not is_interval)
        self._weekday_widget.setEnabled(is_weekly)
        self._interval_spin.setEnabled(is_interval)

    def _browse_script(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择脚本",
            "",
            "RPA脚本 (*.rpa.json);;脚本列表 (*.scripts.json);;JSON (*.json);;所有文件 (*)"
        )
        if path:
            self._path_edit.setText(path)
            if not self._name_edit.text():
                self._name_edit.setText(os.path.splitext(os.path.basename(path))[0])

    def _load_task(self, task: ScheduledTask):
        self._name_edit.setText(task.name)
        self._path_edit.setText(task.script_path)
        type_map = {
            ScheduleType.DAILY.value: 0,
            ScheduleType.WEEKLY.value: 1,
            ScheduleType.ONCE.value: 2,
            ScheduleType.INTERVAL.value: 3,
        }
        self._type_combo.setCurrentIndex(type_map.get(task.schedule_type, 0))
        try:
            h, m = map(int, task.time_str.split(':'))
            self._time_edit.setTime(
                __import__('PyQt5.QtCore', fromlist=['QTime']).QTime(h, m)
            )
        except Exception:
            pass
        self._weekday_widget.set_selected(task.weekdays)
        self._interval_spin.setValue(task.interval_minutes)
        self._speed_spin.setValue(int(task.speed))
        self._repeat_spin.setValue(task.repeat_count)

    def _accept(self):
        name = self._name_edit.text().strip()
        path = self._path_edit.text().strip()
        if not name:
            MessageBox("提示", "请输入任务名称", self).exec()
            return
        if not path or not os.path.exists(path):
            MessageBox("提示", "请选择有效的脚本文件", self).exec()
            return

        types = [
            ScheduleType.DAILY.value,
            ScheduleType.WEEKLY.value,
            ScheduleType.ONCE.value,
            ScheduleType.INTERVAL.value,
        ]
        t = self._time_edit.time()
        time_str = f"{t.hour():02d}:{t.minute():02d}"

        if self._task:
            task = self._task
            task.name = name
            task.script_path = path
            task.schedule_type = types[self._type_combo.currentIndex()]
            task.time_str = time_str
            task.weekdays = self._weekday_widget.get_selected()
            task.interval_minutes = self._interval_spin.value()
            task.speed = float(self._speed_spin.value())
            task.repeat_count = self._repeat_spin.value()
        else:
            task = ScheduledTask(
                name=name,
                script_path=path,
                schedule_type=types[self._type_combo.currentIndex()],
                time_str=time_str,
                weekdays=self._weekday_widget.get_selected(),
                interval_minutes=self._interval_spin.value(),
                speed=float(self._speed_spin.value()),
                repeat_count=self._repeat_spin.value(),
            )

        self._result_task = task
        self.accept()

    def get_task(self) -> Optional[ScheduledTask]:
        return self._result_task


class ScheduleTaskCard(CardWidget):
    run_requested = pyqtSignal(str)
    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    toggle_requested = pyqtSignal(str, bool)

    def __init__(self, task: ScheduledTask, index: int, scheduler: SchedulerService, parent=None):
        super().__init__(parent)
        self._task = task
        self._index = index
        self._scheduler = scheduler
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 12, 14)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(12)

        idx_label = StrongBodyLabel(str(self._index + 1))
        idx_label.setFixedWidth(24)
        header.addWidget(idx_label)

        icon = IconWidget(FluentIcon.CALENDAR, self)
        icon.setFixedSize(20, 20)
        icon.setStyleSheet("color: #0078d4;")
        header.addWidget(icon)

        info_col = QVBoxLayout()
        info_col.setSpacing(4)
        self._name_label = StrongBodyLabel(self._task.name)
        info_col.addWidget(self._name_label)

        sub = CaptionLabel(
            f"{self._task.schedule_summary()}  •  {self._task.script_basename()}"
        )
        info_col.addWidget(sub)
        header.addLayout(info_col, 1)

        self._enable_sw = SwitchButton()
        self._enable_sw.setChecked(self._task.enabled)
        self._enable_sw.checkedChanged.connect(self._on_toggle)
        header.addWidget(self._enable_sw)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)

        for icon_def, tip, slot in [
            (FluentIcon.PLAY, "立即运行", lambda: self.run_requested.emit(self._task.id)),
            (FluentIcon.EDIT, "编辑", lambda: self.edit_requested.emit(self._task.id)),
            (FluentIcon.DELETE, "删除", lambda: self.delete_requested.emit(self._task.id)),
        ]:
            btn = TransparentToolButton(icon_def)
            btn.setFixedSize(28, 28)
            btn.setToolTip(tip)
            btn.clicked.connect(slot)
            btn_row.addWidget(btn)

        header.addLayout(btn_row)
        layout.addLayout(header)

        meta_row = QHBoxLayout()
        self._next_label = CaptionLabel("")
        self._last_label = CaptionLabel("")
        meta_row.addWidget(self._next_label)
        meta_row.addStretch()
        meta_row.addWidget(self._last_label)
        layout.addLayout(meta_row)

        self.refresh_meta()

    def _on_toggle(self, checked: bool):
        self._task.enabled = checked
        self.toggle_requested.emit(self._task.id, checked)
        self.refresh_meta()

    def refresh_meta(self):
        nxt = self._scheduler.get_next_run_hint(self._task)
        self._next_label.setText(f"下次: {nxt}")
        if self._task.last_run:
            lr = self._task.last_run[:16].replace('T', ' ')
            res = self._task.last_result or "—"
            self._last_label.setText(f"上次 {lr} ({res})")
        else:
            self._last_label.setText("尚未执行")

    def update_task(self, task: ScheduledTask, index: int):
        self._task = task
        self._index = index
        self._name_label.setText(task.name)
        self._enable_sw.setChecked(task.enabled)
        self.refresh_meta()


class SchedulerPage(QWidget):
    tasks_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = Config.get_instance()
        self._scheduler = SchedulerService.get_instance()
        self._cards: List[ScheduleTaskCard] = []
        self._setup_ui()
        self._setup_scheduler_callbacks()
        self._load_tasks()

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_cards_meta)
        self._refresh_timer.start(30000)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        header = QHBoxLayout()
        header.addWidget(TitleLabel("定时任务"))
        header.addStretch()

        self._status_badge = CaptionLabel("")
        header.addWidget(self._status_badge)

        self._add_btn = PushButton(FluentIcon.ADD, "新建任务")
        self._add_btn.setFixedHeight(32)
        self._add_btn.clicked.connect(self._add_task)
        header.addWidget(self._add_btn)

        self._toggle_sched_btn = PushButton(FluentIcon.PLAY, "启动调度")
        self._toggle_sched_btn.setFixedHeight(32)
        self._toggle_sched_btn.clicked.connect(self._toggle_scheduler)
        header.addWidget(self._toggle_sched_btn)

        layout.addLayout(header)

        layout.addWidget(BodyLabel("按计划自动执行脚本，支持单脚本与执行面板列表"))

        status_card = ElevatedCardWidget(self)
        status_layout = QHBoxLayout(status_card)
        status_layout.setContentsMargins(20, 16, 20, 16)
        status_layout.setSpacing(16)

        self._running_ring = IndeterminateProgressRing(status_card)
        self._running_ring.setFixedSize(28, 28)
        self._running_ring.setVisible(False)
        status_layout.addWidget(self._running_ring)

        status_col = QVBoxLayout()
        self._status_title = StrongBodyLabel("调度器空闲")
        status_col.addWidget(self._status_title)
        self._status_detail = BodyLabel("添加任务后点击「启动调度」开始后台检查")
        status_col.addWidget(self._status_detail)
        status_layout.addLayout(status_col, 1)

        self._task_count_label = StrongBodyLabel("0 个任务")
        status_layout.addWidget(self._task_count_label)

        layout.addWidget(status_card)

        list_header = QHBoxLayout()
        list_header.addWidget(StrongBodyLabel("任务列表"))
        list_header.addStretch()
        layout.addLayout(list_header)

        self._scroll = ScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(
            "QScrollArea { border: 1px solid rgba(0,0,0,0.06); border-radius: 8px; background: transparent; }"
        )

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._container)
        self._list_layout.setAlignment(Qt.AlignTop)
        self._list_layout.setContentsMargins(8, 8, 8, 8)
        self._list_layout.setSpacing(8)
        self._list_layout.addStretch()

        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll, 1)

        self._empty_widget = QWidget()
        empty_layout = QVBoxLayout(self._empty_widget)
        empty_layout.setContentsMargins(40, 48, 40, 48)
        empty_icon = IconWidget(FluentIcon.CALENDAR)
        empty_icon.setFixedSize(48, 48)
        empty_layout.addWidget(empty_icon, 0, Qt.AlignCenter)
        empty_layout.addWidget(StrongBodyLabel("暂无定时任务"), 0, Qt.AlignCenter)
        empty_layout.addWidget(
            BodyLabel("点击「新建任务」添加脚本与执行计划"), 0, Qt.AlignCenter
        )
        layout.addWidget(self._empty_widget)

        self._update_scheduler_ui()

    def _setup_scheduler_callbacks(self):
        self._scheduler.add_callback('on_triggered', self._on_task_triggered)
        self._scheduler.add_callback('on_completed', self._on_task_completed)
        self._scheduler.add_callback('on_error', self._on_task_error)

    def _load_tasks(self):
        self._scheduler.load_tasks(self._config.scheduled_tasks)
        self._scheduler._check_interval = self._config.scheduler_check_interval
        if self._config.scheduler_auto_start:
            self._scheduler.start()
        self._refresh_list()

    def save_tasks(self):
        self._config.scheduled_tasks = self._scheduler.get_tasks_data()
        self._config.save()
        self.tasks_changed.emit()

    def _refresh_list(self):
        for card in self._cards:
            card.deleteLater()
        self._cards.clear()

        tasks = self._scheduler.tasks
        self._empty_widget.setVisible(len(tasks) == 0)
        self._scroll.setVisible(len(tasks) > 0)
        self._task_count_label.setText(f"{len(tasks)} 个任务")

        for i, task in enumerate(tasks):
            card = ScheduleTaskCard(task, i, self._scheduler, self)
            card.run_requested.connect(self._run_task)
            card.edit_requested.connect(self._edit_task)
            card.delete_requested.connect(self._delete_task)
            card.toggle_requested.connect(self._on_toggle_task)
            self._cards.append(card)
            self._list_layout.insertWidget(self._list_layout.count() - 1, card)

        self._update_scheduler_ui()

    def _refresh_cards_meta(self):
        for card in self._cards:
            task = self._scheduler.get_task(card._task.id)
            if task:
                card.update_task(task, card._index)

    def _update_scheduler_ui(self):
        running = self._scheduler.is_running
        self._toggle_sched_btn.setText("停止调度" if running else "启动调度")
        self._toggle_sched_btn.setIcon(FluentIcon.PAUSE if running else FluentIcon.PLAY)
        enabled_count = sum(1 for t in self._scheduler.tasks if t.enabled)
        if running:
            self._status_badge.setText(f"运行中 · {enabled_count} 个启用")
            self._status_title.setText("调度器运行中")
            self._status_detail.setText(
                f"每 {self._config.scheduler_check_interval} 秒检查到期任务"
            )
        else:
            self._status_badge.setText("已停止")
            self._status_title.setText("调度器已停止")
            self._status_detail.setText("点击「启动调度」在后台自动执行到期任务")

    def _toggle_scheduler(self):
        if self._scheduler.is_running:
            self._scheduler.stop()
            InfoBar.info("调度器", "已停止定时调度", self, InfoBarPosition.TOP)
        else:
            if not self._scheduler.tasks:
                InfoBar.warning("提示", "请先添加至少一个任务", self, InfoBarPosition.TOP)
                return
            self._scheduler.start()
            InfoBar.success("调度器", "已启动，将在后台检查任务", self, InfoBarPosition.TOP)
        self._update_scheduler_ui()

    def _add_task(self):
        dlg = TaskEditDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            task = dlg.get_task()
            if task:
                self._scheduler.add_task(task)
                self.save_tasks()
                self._refresh_list()
                InfoBar.success("已添加", f"任务「{task.name}」已创建", self, InfoBarPosition.TOP)

    def _edit_task(self, task_id: str):
        task = self._scheduler.get_task(task_id)
        if not task:
            return
        dlg = TaskEditDialog(task, self)
        if dlg.exec() == QDialog.Accepted:
            updated = dlg.get_task()
            if updated:
                self._scheduler.update_task(updated)
                self.save_tasks()
                self._refresh_list()

    def _delete_task(self, task_id: str):
        task = self._scheduler.get_task(task_id)
        if not task:
            return
        box = MessageBox("确认删除", f"确定删除任务「{task.name}」？", self)
        if box.exec():
            self._scheduler.remove_task(task_id)
            self.save_tasks()
            self._refresh_list()

    def _on_toggle_task(self, task_id: str, enabled: bool):
        self._scheduler.set_task_enabled(task_id, enabled)
        self.save_tasks()

    def _run_task(self, task_id: str):
        self._scheduler.run_now(task_id)
        InfoBar.info("执行中", "任务已在后台开始运行", self, InfoBarPosition.TOP)

    def _on_task_triggered(self, task: ScheduledTask):
        self._running_ring.setVisible(True)
        self._status_title.setText(f"正在执行: {task.name}")
        QTimer.singleShot(0, self._refresh_list)

    def _on_task_completed(self, task: ScheduledTask, result):
        self._running_ring.setVisible(False)
        self._status_title.setText("调度器运行中" if self._scheduler.is_running else "调度器已停止")
        self.save_tasks()
        self._refresh_list()
        if self._config.notify_on_schedule:
            from utils.notification import send_notification
            title = "定时任务完成" if result.success else "定时任务失败"
            send_notification(title, f"{task.name}: {result.message}")

    def _on_task_error(self, task: ScheduledTask, error: str):
        self._running_ring.setVisible(False)
        self.save_tasks()
        self._refresh_list()
        if self._config.notify_on_schedule:
            from utils.notification import send_notification
            send_notification("定时任务错误", f"{task.name}: {error}")
