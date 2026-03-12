import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QApplication,
    QFrame, QLabel, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QPixmap, QFont
from typing import List, Optional, Dict, Any, Set, Tuple
from core.actions import Action, ActionType, ActionManager, VariableManager

from qfluentwidgets import (
    StrongBodyLabel, BodyLabel, PushButton,
    SpinBox, DoubleSpinBox, LineEdit, ComboBox,
    ScrollArea, MessageBox, CardWidget, CheckBox
)

from .widgets import CoordinateWidget, KeySequenceDialog, CaptureWidget, DragCoordinateWidget
from .preview_overlay import PreviewOverlay


class PropertyPanel(CardWidget):
    action_updated = pyqtSignal(object)
    variables_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_action: Optional[Action] = None
        self._current_index: int = -1
        self._param_widgets: Dict[str, QWidget] = {}
        self._image_path_edit = None
        self._image_preview_label = None
        self._all_actions: List[Action] = []
        self._preview_overlay: Optional[PreviewOverlay] = None
        self._window_offset: Optional[Tuple[int, int]] = None
        self._preview_queue: List[Action] = []
        self._preview_timer = QTimer(self)
        self._preview_timer.timeout.connect(self._preview_next_in_queue)
        self._var_values: List[str] = []
        self._setup_ui()
    
    def set_window_offset(self, offset: Optional[Tuple[int, int]]):
        self._window_offset = offset
    
    def set_all_actions(self, actions: List[Action]):
        self._all_actions = actions
    
    def _collect_script_variables(self) -> Set[str]:
        variables = set()
        for action in self._all_actions:
            if action.action_type == ActionType.IMAGE_CHECK:
                marker = action.condition_marker
                if marker:
                    variables.add(marker[1:])
        var_manager = VariableManager.get_instance()
        for var_name in var_manager.get_all().keys():
            variables.add(var_name)
        return variables
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        header = StrongBodyLabel("属性面板")
        layout.addWidget(header)
        
        self._scroll_area = ScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setStyleSheet("QScrollArea{border: none; background: transparent;}")
        
        self._content_widget = QWidget()
        self._content_widget.setStyleSheet("background: transparent;")
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setAlignment(Qt.AlignTop)
        self._content_layout.setSpacing(8)
        self._scroll_area.setWidget(self._content_widget)
        
        layout.addWidget(self._scroll_area)
        
        self._placeholder = BodyLabel("选择一个动作以编辑其属性")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._content_layout.addWidget(self._placeholder)
    
    def set_action(self, action: Action, index: int = -1):
        self._current_action = action
        self._current_index = index
        self._refresh_ui()
    
    def clear(self):
        self._current_action = None
        self._current_index = -1
        self._refresh_ui()
    
    def _clear_content(self):
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
        
        self._param_widgets = {}
        self._image_path_edit = None
        self._image_preview_label = None
    
    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
    
    def _refresh_ui(self):
        self._clear_content()
        
        if not self._current_action:
            self._placeholder = BodyLabel("选择一个动作以编辑其属性")
            self._placeholder.setAlignment(Qt.AlignCenter)
            self._content_layout.addWidget(self._placeholder)
            return
        
        definition = ActionManager.get_action_definition(self._current_action.action_type)
        
        type_label_title = BodyLabel("动作类型")
        self._content_layout.addWidget(type_label_title)
        
        type_label = StrongBodyLabel(definition.get('name', str(self._current_action.action_type)))
        self._content_layout.addWidget(type_label)
        
        self._content_layout.addSpacing(4)
        
        name_label = BodyLabel("动作名称")
        self._content_layout.addWidget(name_label)
        
        self._name_edit = LineEdit()
        self._name_edit.setPlaceholderText("可选，用于备注动作用途")
        self._name_edit.setText(self._current_action.name)
        self._name_edit.setMinimumHeight(36)
        self._name_edit.textChanged.connect(self._on_name_changed)
        self._content_layout.addWidget(self._name_edit)
        
        self._content_layout.addSpacing(4)
        
        self._add_condition_editor()
        
        self._content_layout.addSpacing(8)
        
        params_label = StrongBodyLabel("参数设置")
        self._content_layout.addWidget(params_label)
        
        if self._current_action.action_type in [ActionType.MOUSE_CLICK_RELATIVE, ActionType.MOUSE_MOVE_RELATIVE, ActionType.IMAGE_CLICK, ActionType.IMAGE_WAIT_CLICK]:
            self._add_window_mode_section()
        
        processed_params = set()
        
        if self._current_action.action_type == ActionType.MOUSE_CLICK_RELATIVE:
            processed_params.add('button')
        
        for param_def in definition.get('params', []):
            param_name = param_def['name']
            
            if param_name in processed_params:
                continue
            
            param_type = param_def['type']
            param_desc = param_def['description']
            param_default = param_def['default']
            
            current_value = self._current_action.params.get(param_name, param_default)
            
            use_relative = self._current_action.use_relative_coords or \
                           self._current_action.action_type in [ActionType.MOUSE_CLICK_RELATIVE, ActionType.MOUSE_MOVE_RELATIVE]
            window_offset_for_pick = self._window_offset if use_relative else None
            
            if param_name in ['x', 'y']:
                coord_widget = CoordinateWidget(title="坐标", window_offset=window_offset_for_pick)
                y_value = self._current_action.params.get('y', 0)
                coord_widget.set_coordinates(current_value, y_value)
                coord_widget.coordinates_changed.connect(self._on_coord_changed)
                self._param_widgets['x'] = coord_widget
                self._param_widgets['y'] = coord_widget
                self._content_layout.addWidget(coord_widget)
                processed_params.add('x')
                processed_params.add('y')
                continue
            
            if param_name in ['start_x', 'start_y', 'end_x', 'end_y']:
                if param_name == 'start_x':
                    start_coord = CoordinateWidget(title="起始坐标", window_offset=window_offset_for_pick)
                    start_y = self._current_action.params.get('start_y', 0)
                    start_coord.set_coordinates(current_value, start_y)
                    start_coord.coordinates_changed.connect(self._on_start_coord_changed)
                    self._param_widgets['start_x'] = start_coord
                    self._param_widgets['start_y'] = start_coord
                    self._content_layout.addWidget(start_coord)
                    processed_params.add('start_x')
                    processed_params.add('start_y')
                elif param_name == 'end_x':
                    end_coord = CoordinateWidget(title="结束坐标", window_offset=window_offset_for_pick)
                    end_y = self._current_action.params.get('end_y', 0)
                    end_coord.set_coordinates(current_value, end_y)
                    end_coord.coordinates_changed.connect(self._on_end_coord_changed)
                    self._param_widgets['end_x'] = end_coord
                    self._param_widgets['end_y'] = end_coord
                    self._content_layout.addWidget(end_coord)
                    processed_params.add('end_x')
                    processed_params.add('end_y')
                continue
            
            if param_name == 'image_path':
                self._add_image_picker(param_name, current_value)
                processed_params.add('image_path')
                continue
            
            if param_name == 'region':
                self._add_region_picker(param_name, current_value)
                processed_params.add('region')
                continue
            
            self._add_param_widget(param_name, param_type, param_desc, current_value)
            processed_params.add(param_name)
        
        self._content_layout.addSpacing(8)
        
        delay_label = StrongBodyLabel("延迟设置")
        self._content_layout.addWidget(delay_label)
        
        before_label = BodyLabel("动作前延迟")
        self._content_layout.addWidget(before_label)
        
        before_spin = DoubleSpinBox()
        before_spin.setRange(0, 60)
        before_spin.setDecimals(2)
        before_spin.setValue(self._current_action.delay_before)
        before_spin.setSuffix(" 秒")
        before_spin.setMinimumHeight(36)
        before_spin.valueChanged.connect(self._on_delay_before_changed)
        self._param_widgets['_delay_before'] = before_spin
        self._content_layout.addWidget(before_spin)
        
        after_label = BodyLabel("动作后延迟")
        self._content_layout.addWidget(after_label)
        
        after_spin = DoubleSpinBox()
        after_spin.setRange(0, 60)
        after_spin.setDecimals(2)
        after_spin.setValue(self._current_action.delay_after)
        after_spin.setSuffix(" 秒")
        after_spin.setMinimumHeight(36)
        after_spin.valueChanged.connect(self._on_delay_after_changed)
        self._param_widgets['_delay_after'] = after_spin
        self._content_layout.addWidget(after_spin)
        
        self._content_layout.addSpacing(8)
        
        repeat_label = StrongBodyLabel("重复设置")
        self._content_layout.addWidget(repeat_label)
        
        repeat_count_label = BodyLabel("重复次数")
        self._content_layout.addWidget(repeat_count_label)
        
        repeat_spin = SpinBox()
        repeat_spin.setRange(1, 9999)
        repeat_spin.setValue(getattr(self._current_action, 'repeat_count', 1))
        repeat_spin.setMinimumHeight(36)
        repeat_spin.valueChanged.connect(self._on_repeat_count_changed)
        self._param_widgets['_repeat_count'] = repeat_spin
        self._content_layout.addWidget(repeat_spin)
        
        self._content_layout.addSpacing(8)
        
        self._add_preview_section()
        
        self._content_layout.addStretch()
    
    def _add_condition_editor(self):
        all_vars = self._collect_script_variables()
        
        condition_label = BodyLabel("执行条件")
        self._content_layout.addWidget(condition_label)
        
        self._var_combo = ComboBox()
        self._var_combo.addItem("(无)")
        self._var_combo.setMinimumHeight(40)
        
        self._var_values = [""]  # 存储对应的值
        
        for var_name in sorted(all_vars):
            self._var_combo.addItem(f"${var_name}")
            self._var_values.append(f"${var_name}")
        
        self._var_combo.currentIndexChanged.connect(self._on_var_selected)
        
        self._content_layout.addWidget(self._var_combo)
        
        target_condition = self._current_action.condition if self._current_action.condition else ""
        
        if target_condition:
            idx = -1
            for i, val in enumerate(self._var_values):
                if val == target_condition:
                    idx = i
                    break
            if idx < 0:
                self._var_combo.addItem(target_condition)
                self._var_values.append(target_condition)
                idx = len(self._var_values) - 1
            
            if idx >= 0:
                self._var_combo.blockSignals(True)
                self._var_combo.setCurrentIndex(idx)
                self._var_combo.blockSignals(False)
        
        if self._current_action and self._current_action.action_type == ActionType.IMAGE_CHECK:
            current_marker = self._current_action.condition_marker
            if current_marker:
                info_label = BodyLabel(f"💡 此动作将生成条件标记: {current_marker}")
                info_label.setStyleSheet("color: #666; font-size: 11px;")
                self._content_layout.addWidget(info_label)
    
    def _on_var_selected(self, index):
        if 0 <= index < len(self._var_values):
            data = self._var_values[index]
        else:
            data = ""
        if self._current_action:
            self._current_action.condition = data if data else ""
    
    def _add_window_mode_section(self):
        mode_label = StrongBodyLabel("窗口模式")
        self._content_layout.addWidget(mode_label)
        
        bg_checkbox = CheckBox("后台模式")
        bg_checkbox.setChecked(getattr(self._current_action, 'background_mode', False))
        bg_checkbox.setMinimumHeight(36)
        bg_checkbox.stateChanged.connect(self._on_background_mode_changed)
        self._param_widgets['_background_mode'] = bg_checkbox
        self._content_layout.addWidget(bg_checkbox)
        
        info_label = BodyLabel("💡 后台模式: 不激活窗口即可操作")
        info_label.setStyleSheet("color: #666; font-size: 11px;")
        self._content_layout.addWidget(info_label)
        
        if self._current_action.action_type == ActionType.MOUSE_CLICK_RELATIVE:
            button_label = BodyLabel("鼠标按钮")
            self._content_layout.addWidget(button_label)
            
            button_combo = ComboBox()
            button_combo.addItem("左键", "left")
            button_combo.addItem("右键", "right")
            button_combo.addItem("中键", "middle")
            button_combo.setMinimumHeight(36)
            
            current_button = self._current_action.params.get('button', 'left')
            if current_button == 'right':
                button_combo.setCurrentIndex(1)
            elif current_button == 'middle':
                button_combo.setCurrentIndex(2)
            else:
                button_combo.setCurrentIndex(0)
            
            button_combo.currentIndexChanged.connect(self._on_button_changed)
            self._param_widgets['_button'] = button_combo
            self._content_layout.addWidget(button_combo)
        
        self._content_layout.addSpacing(8)
    
    def _on_background_mode_changed(self, state):
        if self._current_action:
            self._current_action.background_mode = (state == Qt.Checked)
            self._current_action.description = self._current_action._generate_description()
            self.action_updated.emit(self._current_action)
    
    def _on_button_changed(self, index):
        if self._current_action:
            buttons = ['left', 'right', 'middle']
            if 0 <= index < len(buttons):
                self._current_action.params['button'] = buttons[index]
                self._current_action.description = self._current_action._generate_description()
                self.action_updated.emit(self._current_action)
    
    def _add_param_widget(self, param_name: str, param_type: str, param_desc: str, current_value: Any):
        param_label = BodyLabel(f"{param_desc}")
        self._content_layout.addWidget(param_label)
        
        if param_type == 'int':
            widget = SpinBox()
            widget.setRange(-9999, 9999)
            widget.setValue(current_value)
            widget.setMinimumHeight(36)
            widget.valueChanged.connect(lambda v, n=param_name: self._on_param_changed(n, v))
        
        elif param_type == 'float':
            widget = DoubleSpinBox()
            widget.setRange(0, 999)
            widget.setDecimals(2)
            widget.setValue(current_value)
            widget.setMinimumHeight(36)
            widget.valueChanged.connect(lambda v, n=param_name: self._on_param_changed(n, v))
        
        elif param_type == 'str':
            widget = LineEdit()
            widget.setText(str(current_value))
            widget.setMinimumHeight(36)
            widget.textChanged.connect(lambda v, n=param_name: self._on_param_changed(n, v))
        
        elif param_type == 'list':
            widget = PushButton("设置快捷键")
            widget.setMinimumHeight(36)
            widget.clicked.connect(lambda checked=False, n=param_name: self._on_hotkey_button_clicked(n))
        
        else:
            widget = LineEdit()
            widget.setText(str(current_value))
            widget.setMinimumHeight(36)
            widget.textChanged.connect(lambda v, n=param_name: self._on_param_changed(n, v))
        
        self._param_widgets[param_name] = widget
        self._content_layout.addWidget(widget)
    
    def _add_image_picker(self, param_name: str, current_value: str):
        path_label = BodyLabel("图片路径")
        self._content_layout.addWidget(path_label)
        
        self._image_path_edit = LineEdit()
        self._image_path_edit.textChanged.connect(lambda v, n=param_name: self._on_param_changed(n, v))
        self._image_path_edit.setPlaceholderText("选择图片文件...")
        self._image_path_edit.setMinimumHeight(36)
        self._content_layout.addWidget(self._image_path_edit)
        
        browse_btn = PushButton("浏览文件")
        browse_btn.setMinimumHeight(36)
        browse_btn.clicked.connect(lambda: self._browse_image(param_name))
        self._content_layout.addWidget(browse_btn)
        
        capture_btn = PushButton("截取屏幕区域")
        capture_btn.setMinimumHeight(36)
        capture_btn.clicked.connect(lambda: self._capture_region(param_name))
        self._content_layout.addWidget(capture_btn)
        
        self._image_preview_label = QLabel()
        self._image_preview_label.setAlignment(Qt.AlignCenter)
        self._image_preview_label.setMaximumHeight(150)
        self._image_preview_label.hide()
        self._content_layout.addWidget(self._image_preview_label)
        
        self._param_widgets[param_name] = self._image_path_edit
        
        if current_value:
            self._image_path_edit.blockSignals(True)
            self._image_path_edit.setText(current_value)
            self._image_path_edit.blockSignals(False)
            self._show_image_preview(current_value)
    
    def _add_region_picker(self, param_name: str, current_value):
        region_widget = DragCoordinateWidget(title="截图区域")
        
        if current_value and isinstance(current_value, (list, tuple)) and len(current_value) == 4:
            region_widget.set_region(current_value[0], current_value[1], current_value[2], current_value[3])
        
        region_widget.coordinates_changed.connect(self._on_region_changed)
        self._param_widgets[param_name] = region_widget
        self._content_layout.addWidget(region_widget)
    
    def _on_region_changed(self, x: int, y: int, width: int, height: int):
        if self._current_action:
            self._current_action.params['region'] = (x, y, width, height)
            self._current_action.description = self._current_action._generate_description()
            self.action_updated.emit(self._current_action)
    
    def _browse_image(self, param_name: str):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif);;所有文件 (*)"
        )
        if filepath:
            self._image_path_edit.setText(filepath)
            self._show_image_preview(filepath)
    
    def _capture_region(self, param_name: str):
        self._capture_widget = CaptureWidget(self)
        self._capture_widget.captured.connect(lambda rect: self._on_captured(rect, param_name))
        self._capture_widget.show()
    
    def _on_captured(self, rect, param_name: str):
        if rect and rect.width() > 10 and rect.height() > 10:
            import pyautogui
            import os
            import time
            
            images_dir = os.path.join(os.path.expanduser('~'), '.simpleRPA', 'images')
            os.makedirs(images_dir, exist_ok=True)
            
            filename = f"capture_{int(time.time())}.png"
            filepath = os.path.join(images_dir, filename)
            
            screenshot = pyautogui.screenshot(region=(
                rect.x(),
                rect.y(),
                rect.width(),
                rect.height()
            ))
            screenshot.save(filepath)
            
            self._image_path_edit.setText(filepath)
            self._show_image_preview(filepath)
    
    def _show_image_preview(self, filepath: str):
        if not self._image_preview_label:
            return
        
        try:
            pixmap = QPixmap(filepath)
            if not pixmap.isNull():
                scaled = pixmap.scaled(200, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self._image_preview_label.setPixmap(scaled)
                self._image_preview_label.show()
            else:
                self._image_preview_label.hide()
        except Exception:
            self._image_preview_label.hide()
    
    def _on_param_changed(self, param_name: str, value: Any):
        if self._current_action:
            self._current_action.params[param_name] = value
            self._current_action.description = self._current_action._generate_description()
            self.action_updated.emit(self._current_action)
    
    def _on_name_changed(self, value: str):
        if self._current_action:
            self._current_action.name = value
            self._current_action.description = self._current_action._generate_description()
            self.action_updated.emit(self._current_action)
    
    def _on_condition_changed(self, value: str):
        if self._current_action:
            self._current_action.condition = value
    
    def _on_coord_changed(self, x: int, y: int):
        if self._current_action:
            self._current_action.params['x'] = x
            self._current_action.params['y'] = y
            self._current_action.description = self._current_action._generate_description()
            self.action_updated.emit(self._current_action)
    
    def _on_start_coord_changed(self, x: int, y: int):
        if self._current_action:
            self._current_action.params['start_x'] = x
            self._current_action.params['start_y'] = y
            self._current_action.description = self._current_action._generate_description()
            self.action_updated.emit(self._current_action)
    
    def _on_end_coord_changed(self, x: int, y: int):
        if self._current_action:
            self._current_action.params['end_x'] = x
            self._current_action.params['end_y'] = y
            self._current_action.description = self._current_action._generate_description()
            self.action_updated.emit(self._current_action)
    
    def _on_delay_before_changed(self, value: float):
        if self._current_action:
            self._current_action.delay_before = value
            self._current_action.description = self._current_action._generate_description()
            self.action_updated.emit(self._current_action)
    
    def _on_delay_after_changed(self, value: float):
        if self._current_action:
            self._current_action.delay_after = value
    
    def _on_repeat_count_changed(self, value: int):
        if self._current_action:
            self._current_action.repeat_count = value
            self._current_action.description = self._current_action._generate_description()
            self.action_updated.emit(self._current_action)
    
    def _on_hotkey_button_clicked(self, param_name: str):
        current_keys = self._current_action.params.get(param_name, [])
        dialog = KeySequenceDialog(self, current_keys)
        if dialog.exec_():
            keys = dialog.get_keys()
            self._current_action.params[param_name] = keys
            self._current_action.description = self._current_action._generate_description()
            
            if param_name in self._param_widgets:
                self._param_widgets[param_name].setText('+'.join(keys) if keys else "设置快捷键")
            
            self.action_updated.emit(self._current_action)
    
    def _add_preview_section(self):
        preview_label = StrongBodyLabel("效果预览")
        self._content_layout.addWidget(preview_label)
        
        preview_btn = PushButton("预览效果")
        preview_btn.setMinimumHeight(40)
        preview_btn.clicked.connect(self._preview_action)
        self._content_layout.addWidget(preview_btn)
    
    def _preview_action(self):
        if not self._current_action:
            return
        
        self._preview_queue = []
        self._preview_timer.stop()
        
        self._queue_action_preview(self._current_action)
        
        if self._preview_queue:
            self._preview_next_in_queue()
    
    def _queue_action_preview(self, action: Action):
        if action.action_type == ActionType.ACTION_GROUP_REF:
            from core.action_group import ActionGroupManager
            group_name = action.params.get('group_name', '')
            if group_name:
                group_manager = ActionGroupManager.get_instance()
                group = group_manager.get_group(group_name)
                if group:
                    for group_action in group.actions:
                        self._queue_action_preview(group_action)
        else:
            self._preview_queue.append(action)
    
    def _preview_next_in_queue(self):
        if not self._preview_queue:
            self._preview_timer.stop()
            return
        
        action = self._preview_queue.pop(0)
        self._show_single_preview(action)
        
        if self._preview_queue:
            self._preview_timer.start(500)
    
    def _show_single_preview(self, action: Action):
        if self._preview_overlay is None:
            self._preview_overlay = PreviewOverlay()
        
        action_type = action.action_type
        params = action.params
        
        offset_x, offset_y = self._window_offset if self._window_offset else (0, 0)
        
        if action_type in [ActionType.MOUSE_CLICK, ActionType.MOUSE_DOUBLE_CLICK, 
                          ActionType.MOUSE_RIGHT_CLICK]:
            x = params.get('x', 0)
            y = params.get('y', 0)
            label = f"({x}, {y})"
            self._preview_overlay.show_click_position(x, y, label)
        
        elif action_type == ActionType.MOUSE_CLICK_RELATIVE:
            x = params.get('x', 0) + offset_x
            y = params.get('y', 0) + offset_y
            label = f"窗口内 ({params.get('x', 0)}, {params.get('y', 0)})"
            self._preview_overlay.show_click_position(x, y, label)
        
        elif action_type == ActionType.MOUSE_MOVE:
            x = params.get('x', 0)
            y = params.get('y', 0)
            label = f"移动至 ({x}, {y})"
            self._preview_overlay.show_click_position(x, y, label)
        
        elif action_type == ActionType.MOUSE_MOVE_RELATIVE:
            x = params.get('x', 0) + offset_x
            y = params.get('y', 0) + offset_y
            label = f"窗口内移动至 ({params.get('x', 0)}, {params.get('y', 0)})"
            self._preview_overlay.show_click_position(x, y, label)
        
        elif action_type == ActionType.MOUSE_DRAG:
            start_x = params.get('start_x', 0)
            start_y = params.get('start_y', 0)
            end_x = params.get('end_x', 0)
            end_y = params.get('end_y', 0)
            self._preview_overlay.show_drag_line(start_x, start_y, end_x, end_y)
        
        elif action_type == ActionType.MOUSE_SCROLL:
            x = params.get('x', 0)
            y = params.get('y', 0)
            clicks = params.get('clicks', 0)
            self._preview_overlay.show_scroll_position(x, y, clicks)
        
        elif action_type == ActionType.KEY_PRESS:
            key = params.get('key', '')
            self._preview_overlay.show_text_preview(f"按下按键: {key}", "按键预览")
        
        elif action_type == ActionType.KEY_TYPE:
            text = params.get('text', '')
            self._preview_overlay.show_text_preview(text, "输入文本预览")
        
        elif action_type == ActionType.HOTKEY:
            keys = params.get('keys', [])
            self._preview_overlay.show_hotkey_preview(keys)
        
        elif action_type == ActionType.WAIT:
            seconds = params.get('seconds', 1.0)
            self._preview_overlay.show_text_preview(f"等待 {seconds} 秒", "等待预览")
        
        elif action_type == ActionType.SCREENSHOT:
            region = params.get('region')
            filename = params.get('filename', 'screenshot.png')
            if region and len(region) == 4:
                self._preview_overlay.show_region(region[0], region[1], region[2], region[3], f"截图: {filename}")
            else:
                self._preview_overlay.show_text_preview(f"全屏截图: {filename}", "截图预览")
        
        elif action_type in [ActionType.IMAGE_CLICK, ActionType.IMAGE_WAIT_CLICK, ActionType.IMAGE_CHECK]:
            image_path = params.get('image_path', '')
            confidence = params.get('confidence', 0.9)
            if image_path and os.path.exists(image_path):
                self._preview_overlay.show_image_match(image_path, confidence)
            else:
                self._preview_overlay.show_text_preview("请先选择图片文件", "图片识别预览")
