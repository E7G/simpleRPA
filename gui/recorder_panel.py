from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from core.recorder import Recorder, RecordConfig, RecordState

from qfluentwidgets import (
    StrongBodyLabel, BodyLabel, PushButton, PrimaryPushButton,
    CheckBox, SpinBox, DoubleSpinBox, ScrollArea, CardWidget
)


class RecorderPanel(CardWidget):
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    action_recorded = pyqtSignal(object)
    actions_cleared = pyqtSignal()
    last_action_removed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._recorder = Recorder()
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        scroll_area = ScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea{border: none; background: transparent;}")
        
        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        header_layout = QHBoxLayout()
        header = StrongBodyLabel("录制控制")
        header_layout.addWidget(header)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        self._status_label = StrongBodyLabel("就绪")
        self._status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._status_label)
        
        self._action_count_label = BodyLabel("已录制: 0 个动作")
        self._action_count_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._action_count_label)
        
        layout.addSpacing(8)
        
        self._start_btn = PrimaryPushButton("开始录制")
        self._start_btn.setMinimumHeight(40)
        self._start_btn.clicked.connect(self._toggle_recording)
        layout.addWidget(self._start_btn)
        
        layout.addSpacing(8)
        
        self._clear_btn = PushButton("清除录制")
        self._clear_btn.setMinimumHeight(36)
        self._clear_btn.clicked.connect(self._clear_recorded)
        layout.addWidget(self._clear_btn)
        
        options_label = StrongBodyLabel("录制选项")
        layout.addWidget(options_label)
        
        self._record_click_cb = CheckBox("录制鼠标点击")
        self._record_click_cb.setChecked(True)
        layout.addWidget(self._record_click_cb)
        
        self._record_scroll_cb = CheckBox("录制滚轮")
        self._record_scroll_cb.setChecked(True)
        layout.addWidget(self._record_scroll_cb)
        
        self._record_keyboard_cb = CheckBox("录制键盘")
        self._record_keyboard_cb.setChecked(True)
        layout.addWidget(self._record_keyboard_cb)
        
        self._record_move_cb = CheckBox("录制鼠标移动")
        self._record_move_cb.setChecked(False)
        layout.addWidget(self._record_move_cb)
        
        move_label = BodyLabel("最小移动距离")
        layout.addWidget(move_label)
        
        self._min_distance_spin = SpinBox()
        self._min_distance_spin.setRange(1, 100)
        self._min_distance_spin.setValue(10)
        self._min_distance_spin.setMinimumHeight(36)
        layout.addWidget(self._min_distance_spin)
        
        interval_label = BodyLabel("采样间隔(秒)")
        layout.addWidget(interval_label)
        
        self._interval_spin = DoubleSpinBox()
        self._interval_spin.setRange(0.01, 1.0)
        self._interval_spin.setDecimals(2)
        self._interval_spin.setValue(0.1)
        self._interval_spin.setMinimumHeight(36)
        layout.addWidget(self._interval_spin)
        
        layout.addSpacing(8)
        
        image_options_label = StrongBodyLabel("图像点击录制")
        layout.addWidget(image_options_label)
        
        self._record_image_click_cb = CheckBox("录制为图像点击")
        self._record_image_click_cb.setChecked(False)
        layout.addWidget(self._record_image_click_cb)
        
        size_label = BodyLabel("截图区域大小")
        layout.addWidget(size_label)
        
        self._image_size_spin = SpinBox()
        self._image_size_spin.setRange(10, 100)
        self._image_size_spin.setValue(30)
        self._image_size_spin.setMinimumHeight(36)
        layout.addWidget(self._image_size_spin)
        
        layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        self._update_config()
        
        for cb in [self._record_click_cb, self._record_scroll_cb, 
                   self._record_keyboard_cb, self._record_move_cb,
                   self._record_image_click_cb]:
            cb.stateChanged.connect(self._update_config)
        
        self._min_distance_spin.valueChanged.connect(self._update_config)
        self._interval_spin.valueChanged.connect(self._update_config)
        self._image_size_spin.valueChanged.connect(self._update_config)
    
    def _connect_signals(self):
        self._recorder.add_callback('on_action_recorded', self._on_action_recorded)
        self._recorder.add_callback('on_state_changed', self._on_state_changed)
        self._recorder.add_callback('on_last_action_removed', self._on_last_action_removed)
    
    def _update_config(self):
        config = RecordConfig(
            record_mouse_click=self._record_click_cb.isChecked(),
            record_mouse_scroll=self._record_scroll_cb.isChecked(),
            record_keyboard=self._record_keyboard_cb.isChecked(),
            record_mouse_move=self._record_move_cb.isChecked(),
            min_move_distance=self._min_distance_spin.value(),
            move_sample_interval=self._interval_spin.value(),
            ignore_last_click=True,
            record_as_image_click=self._record_image_click_cb.isChecked(),
            image_capture_size=self._image_size_spin.value()
        )
        self._recorder.config = config
    
    def _toggle_recording(self):
        if self._recorder.is_recording():
            self._recorder.stop()
            self._start_btn.setText("开始录制")
        else:
            self._update_config()
            self._recorder.start()
            self._start_btn.setText("停止录制")
    
    def _on_action_recorded(self, action):
        count = len(self._recorder.get_actions())
        self._action_count_label.setText(f"已录制: {count} 个动作")
        self.action_recorded.emit(action)
    
    def _on_state_changed(self, state: RecordState):
        if state == RecordState.RECORDING:
            self._status_label.setText("录制中...")
            self.recording_started.emit()
        elif state == RecordState.PAUSED:
            self._status_label.setText("已暂停")
        else:
            self._status_label.setText("就绪")
            self.recording_stopped.emit()
    
    def _on_last_action_removed(self):
        count = len(self._recorder.get_actions())
        self._action_count_label.setText(f"已录制: {count} 个动作")
        self.last_action_removed.emit()
    
    def _clear_recorded(self):
        self._recorder.clear_actions()
        self._action_count_label.setText("已录制: 0 个动作")
        self.actions_cleared.emit()
    
    def get_recorded_actions(self):
        return self._recorder.get_actions()
    
    def stop_recording(self):
        if self._recorder.is_recording():
            self._recorder.stop()
            self._start_btn.setText("开始录制")
    
    def is_recording(self) -> bool:
        return self._recorder.is_recording()
