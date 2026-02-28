import sys
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QFileDialog, QApplication, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from typing import List, Optional, Dict

from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, FluentIcon,
    PushButton, PrimaryPushButton, SpinBox, DoubleSpinBox,
    BodyLabel, StrongBodyLabel,
    ProgressBar, MessageBox,
    Pivot, CardWidget, ElevatedCardWidget,
    setTheme, Theme, setThemeColor, CheckBox
)

from core.actions import Action, ActionManager, ActionType
from core.player import Player, PlayerState
from core.exporter import Exporter
from core.action_group import LocalActionGroupManager
from utils.config import Config
from utils.window_utils import WindowUtils, WindowInfo

from .action_panel import ActionPanel
from .script_editor import ScriptEditor
from .property_panel import PropertyPanel
from .recorder_panel import RecorderPanel
from .widgets import WindowSelector


class MainWindow(FluentWindow):
    _update_progress_signal = pyqtSignal(float, int, int)
    _update_state_signal = pyqtSignal(object, str)
    _update_finished_signal = pyqtSignal(bool, str)
    _update_error_signal = pyqtSignal(str, str)
    _update_action_start_signal = pyqtSignal(object, int, str)
    
    def __init__(self):
        super().__init__()
        
        self._config = Config.get_instance()
        self._exporter = Exporter()
        self._window_utils = WindowUtils()
        
        self._tab_players: Dict[str, Player] = {}
        self._tab_files: Dict[str, Optional[str]] = {}
        self._tab_modified: Dict[str, bool] = {}
        
        self._setup_ui()
        self._setup_navigation()
        self._setup_connections()
        self._load_settings()
        
        self._mouse_pos_timer = QTimer(self)
        self._mouse_pos_timer.timeout.connect(self._update_mouse_position)
        self._mouse_pos_timer.start(100)
        
        self._update_progress_signal.connect(self._on_player_progress)
        self._update_state_signal.connect(self._on_player_state_changed)
        self._update_finished_signal.connect(self._on_player_finished)
        self._update_error_signal.connect(self._on_player_error_gui)
        self._update_action_start_signal.connect(self._on_player_action_start_gui)
    
    def _setup_ui(self):
        setTheme(Theme.AUTO)
        setThemeColor('#0078d4')
        
        font = QApplication.font()
        font.setPointSize(15)
        QApplication.setFont(font)
        
        self.setWindowTitle("SimpleRPA - RPA自动化工具")
        self.setMinimumSize(1280, 850)
        
        self.homeInterface = QWidget()
        self.homeInterface.setObjectName('homeInterface')
        self.addSubInterface(
            self.homeInterface, FluentIcon.HOME, '主页'
        )
        
        main_layout = QVBoxLayout(self.homeInterface)
        main_layout.setContentsMargins(24, 20, 24, 24)
        main_layout.setSpacing(16)
        
        control_card = ElevatedCardWidget(self.homeInterface)
        control_layout = QHBoxLayout(control_card)
        control_layout.setContentsMargins(20, 16, 20, 16)
        control_layout.setSpacing(24)
        
        window_group = QVBoxLayout()
        window_group.setSpacing(8)
        window_label = StrongBodyLabel("目标窗口")
        window_group.addWidget(window_label)
        
        self._window_selector = WindowSelector()
        self._window_selector.setMinimumWidth(220)
        self._window_selector.refresh_windows()
        window_group.addWidget(self._window_selector)
        control_layout.addLayout(window_group)
        
        speed_group = QVBoxLayout()
        speed_group.setSpacing(8)
        speed_label = StrongBodyLabel("执行速度")
        speed_group.addWidget(speed_label)
        
        self._speed_spin = DoubleSpinBox()
        self._speed_spin.setRange(0.1, 10.0)
        self._speed_spin.setSingleStep(0.1)
        self._speed_spin.setValue(self._config.default_speed)
        self._speed_spin.setSuffix(" 倍")
        self._speed_spin.setMinimumWidth(120)
        self._speed_spin.setMinimumHeight(32)
        speed_group.addWidget(self._speed_spin)
        control_layout.addLayout(speed_group)
        
        repeat_group = QVBoxLayout()
        repeat_group.setSpacing(8)
        repeat_label = StrongBodyLabel("重复次数")
        repeat_group.addWidget(repeat_label)
        
        self._repeat_spin = SpinBox()
        self._repeat_spin.setRange(1, 999)
        self._repeat_spin.setValue(self._config.default_repeat_count)
        self._repeat_spin.setMinimumWidth(120)
        self._repeat_spin.setMinimumHeight(32)
        repeat_group.addWidget(self._repeat_spin)
        
        self._infinite_cb = CheckBox("无限循环")
        self._infinite_cb.stateChanged.connect(self._on_infinite_changed)
        repeat_group.addWidget(self._infinite_cb)
        control_layout.addLayout(repeat_group)
        
        timeout_group = QVBoxLayout()
        timeout_group.setSpacing(8)
        timeout_label = StrongBodyLabel("超时设置")
        timeout_group.addWidget(timeout_label)
        
        self._timeout_spin = DoubleSpinBox()
        self._timeout_spin.setRange(0, 3600)
        self._timeout_spin.setValue(0)
        self._timeout_spin.setSuffix(" 秒")
        self._timeout_spin.setSpecialValueText("不限制")
        self._timeout_spin.setMinimumWidth(120)
        self._timeout_spin.setMinimumHeight(32)
        timeout_group.addWidget(self._timeout_spin)
        control_layout.addLayout(timeout_group)
        
        control_layout.addStretch()
        
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)
        
        run_pause_layout = QHBoxLayout()
        run_pause_layout.setSpacing(8)
        
        self._run_btn = PrimaryPushButton("运行")
        self._run_btn.setMinimumSize(100, 40)
        self._run_btn.clicked.connect(self._run_script)
        run_pause_layout.addWidget(self._run_btn)
        
        self._pause_btn = PushButton("暂停")
        self._pause_btn.setMinimumSize(100, 40)
        self._pause_btn.clicked.connect(self._pause_script)
        self._pause_btn.setEnabled(False)
        run_pause_layout.addWidget(self._pause_btn)
        
        btn_layout.addLayout(run_pause_layout)
        
        self._stop_btn = PushButton("停止")
        self._stop_btn.setMinimumSize(208, 40)
        self._stop_btn.clicked.connect(self._stop_script)
        self._stop_btn.setEnabled(False)
        btn_layout.addWidget(self._stop_btn)
        
        control_layout.addLayout(btn_layout)
        
        main_layout.addWidget(control_card)
        
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)
        
        left_card = CardWidget()
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(8, 8, 8, 8)
        
        self._pivot = Pivot()
        self._pivot.addItem(routeKey='actions', text='动作列表')
        self._pivot.addItem(routeKey='recorder', text='录制控制')
        left_layout.addWidget(self._pivot)
        
        self._action_panel = ActionPanel()
        self._recorder_panel = RecorderPanel()
        
        self._action_panel.hide()
        self._recorder_panel.hide()
        left_layout.addWidget(self._action_panel)
        left_layout.addWidget(self._recorder_panel)
        
        self._pivot.currentItemChanged.connect(self._on_pivot_changed)
        self._pivot.setCurrentItem('actions')
        
        content_layout.addWidget(left_card, 1)
        
        self._script_editor = ScriptEditor()
        content_layout.addWidget(self._script_editor, 2)
        
        self._property_panel = PropertyPanel()
        content_layout.addWidget(self._property_panel, 1)
        
        main_layout.addLayout(content_layout, 1)
        
        self._progress_bar = ProgressBar()
        self._progress_bar.setFixedHeight(4)
        self._progress_bar.setVisible(False)
        main_layout.addWidget(self._progress_bar)
        
        self._status_bar = QWidget()
        status_layout = QHBoxLayout(self._status_bar)
        status_layout.setContentsMargins(16, 8, 16, 8)
        
        self._status_label = BodyLabel("就绪")
        status_layout.addWidget(self._status_label)
        
        status_layout.addStretch()
        
        self._coord_label = BodyLabel("屏幕坐标: (0, 0)")
        status_layout.addWidget(self._coord_label)
        
        main_layout.addWidget(self._status_bar)
    
    def _setup_navigation(self):
        self.navigationInterface.addItem(
            routeKey='open',
            icon=FluentIcon.FOLDER,
            text='打开',
            onClick=self._open_script,
            position=NavigationItemPosition.BOTTOM
        )
        
        self.navigationInterface.addItem(
            routeKey='save',
            icon=FluentIcon.SAVE,
            text='保存',
            onClick=self._save_script,
            position=NavigationItemPosition.BOTTOM
        )
        
        self.navigationInterface.addItem(
            routeKey='export',
            icon=FluentIcon.SHARE,
            text='导出',
            onClick=self._export_python,
            position=NavigationItemPosition.BOTTOM
        )
    
    def _on_pivot_changed(self, key: str):
        self._action_panel.setVisible(key == 'actions')
        self._recorder_panel.setVisible(key == 'recorder')
    
    def _setup_connections(self):
        self._action_panel.action_added.connect(self._on_action_added)
        self._script_editor.action_selected.connect(self._on_action_selected)
        self._script_editor.actions_changed.connect(self._on_actions_changed)
        self._script_editor.execute_single.connect(self._on_execute_single)
        self._property_panel.action_updated.connect(self._on_action_updated)
        
        self._recorder_panel.action_recorded.connect(self._on_action_recorded)
        self._recorder_panel.recording_started.connect(self._on_recording_started)
        self._recorder_panel.recording_stopped.connect(self._on_recording_stopped)
        self._recorder_panel.actions_cleared.connect(self._on_actions_cleared)
        self._recorder_panel.last_action_removed.connect(self._on_last_action_removed)
        
        self._script_editor.tab_changed.connect(self._on_script_tab_changed)
        self._script_editor.tab_close_requested.connect(self._on_tab_close_requested)
        self._script_editor.set_modified_check_callback(self._is_tab_modified)
        
        self._window_selector.window_selected.connect(self._on_window_selected)
        
        self._create_player_for_tab(self._script_editor.get_current_route_key())
    
    def _on_window_selected(self, hwnd):
        offset = self._window_selector.get_window_offset()
        self._property_panel.set_window_offset(offset)
    
    def _create_player_for_tab(self, route_key: str):
        if not route_key:
            return
        
        if route_key not in self._tab_players:
            local_group_manager = self._script_editor.get_local_group_manager()
            player = Player(tab_key=route_key, local_group_manager=local_group_manager)
            player.add_callback('on_action_start', lambda a, i, rk=route_key: self._on_player_action_start_thread(a, i, rk))
            player.add_callback('on_action_end', self._on_player_action_end)
            player.add_callback('on_progress', lambda p, i, r, rk=route_key: self._on_player_progress_thread(p, i, r, rk))
            player.add_callback('on_state_changed', lambda s, rk=route_key: self._on_player_state_changed_thread(s, rk))
            player.add_callback('on_finished', lambda s, rk=route_key: self._on_player_finished_thread(s, rk))
            player.add_callback('on_error', lambda a, i, e, rk=route_key: self._on_player_error_thread(a, i, e, rk))
            self._tab_players[route_key] = player
        
        self._update_run_buttons_for_current_tab()
    
    def _get_current_player(self) -> Optional[Player]:
        route_key = self._script_editor.get_current_route_key()
        return self._tab_players.get(route_key)
    
    def _on_script_tab_changed(self, route_key: str):
        if route_key and route_key not in self._tab_players:
            self._create_player_for_tab(route_key)
        self._update_run_buttons_for_current_tab()
        self._update_window_title()
    
    def _on_tab_close_requested(self, route_key: str, tab_name: str):
        box = MessageBox('确认关闭', f'标签页 "{tab_name}" 有未保存的内容，确定要关闭吗?', self)
        box.yesButton.setText('确定')
        box.cancelButton.setText('取消')
        
        if box.exec():
            if route_key in self._tab_players:
                player = self._tab_players[route_key]
                player.stop_and_wait(timeout=1.0)
                del self._tab_players[route_key]
            
            if route_key in self._tab_files:
                del self._tab_files[route_key]
            if route_key in self._tab_modified:
                del self._tab_modified[route_key]
            
            index = self._find_tab_index_by_route_key(route_key)
            if index >= 0:
                self._script_editor._close_tab_by_route_key(route_key, index)
    
    def _find_tab_index_by_route_key(self, route_key: str) -> int:
        for i in range(self._script_editor._tab_bar.count()):
            item = self._script_editor._tab_bar.tabItem(i)
            if item and item.routeKey() == route_key:
                return i
        return -1
    
    def _update_run_buttons_for_current_tab(self):
        player = self._get_current_player()
        if player:
            state = player.state
            is_running = state in [PlayerState.PLAYING, PlayerState.PAUSED, PlayerState.STOPPED]
            self._run_btn.setEnabled(not is_running)
            self._pause_btn.setEnabled(state == PlayerState.PLAYING or state == PlayerState.PAUSED)
            self._stop_btn.setEnabled(is_running)
            
            if state == PlayerState.PAUSED:
                self._pause_btn.setText("继续")
            else:
                self._pause_btn.setText("暂停")
        else:
            self._run_btn.setEnabled(True)
            self._pause_btn.setEnabled(False)
            self._stop_btn.setEnabled(False)
            self._pause_btn.setText("暂停")
    
    def _load_settings(self):
        geometry = self._config.window_geometry
        self.setGeometry(
            geometry.get('x', 100),
            geometry.get('y', 100),
            geometry.get('width', 1280),
            geometry.get('height', 850)
        )
        
        if self._config.bound_window:
            self._window_selector.set_selected_window(
                self._config.bound_window.get('hwnd', 0),
                self._config.bound_window.get('title', '')
            )
        
        self._infinite_cb.setChecked(self._config.infinite_loop)
        self._timeout_spin.setValue(self._config.timeout_seconds)
        
        if self._config.open_tabs:
            self._restore_open_tabs()
    
    def _restore_open_tabs(self):
        for i, tab_data in enumerate(self._config.open_tabs):
            if i == 0:
                self._script_editor.set_current_tab_name(tab_data.get('name', '任务 1'))
                actions = [Action.from_dict(a) for a in tab_data.get('actions', [])]
                self._script_editor.set_actions(actions)
                local_groups = tab_data.get('local_action_groups', {})
                if local_groups:
                    local_mgr = self._script_editor.get_local_group_manager()
                    if local_mgr:
                        local_mgr.load_from_dict(local_groups)
            else:
                actions = [Action.from_dict(a) for a in tab_data.get('actions', [])]
                route_key = self._script_editor.add_new_tab(tab_data.get('name'), actions)
                local_groups = tab_data.get('local_action_groups', {})
                if local_groups:
                    tab_content = self._script_editor._tabs.get(route_key)
                    if tab_content and hasattr(tab_content, '_local_group_manager'):
                        tab_content._local_group_manager.load_from_dict(local_groups)
        
        self._script_editor.set_current_tab_index(self._config.current_tab_index)
        self._script_editor.refresh_groups()
        
        for saved_route_key, filepath in self._config.tab_files.items():
            if os.path.exists(filepath):
                tab_name = os.path.splitext(os.path.basename(filepath))[0]
                route_key = self._script_editor.get_route_key_by_tab_name(tab_name)
                if route_key:
                    self._tab_files[route_key] = filepath
    
    def _save_settings(self):
        geometry = self.geometry()
        self._config.set_window_geometry(
            geometry.x(), geometry.y(),
            geometry.width(), geometry.height()
        )
        
        hwnd = self._window_selector.get_selected_hwnd()
        if hwnd:
            self._config.bound_window = {
                'hwnd': hwnd,
                'title': self._window_selector.get_selected_title()
            }
        
        self._config.infinite_loop = self._infinite_cb.isChecked()
        self._config.timeout_seconds = self._timeout_spin.value()
        
        all_tabs = self._script_editor.get_all_tabs()
        all_local_groups = self._script_editor.get_all_local_groups()
        self._config.open_tabs = []
        for name, actions in all_tabs.items():
            tab_data = {
                'name': name,
                'actions': [a.to_dict() for a in actions]
            }
            if name in all_local_groups:
                tab_data['local_action_groups'] = all_local_groups[name]
            self._config.open_tabs.append(tab_data)
        self._config.current_tab_index = self._script_editor.get_current_tab_index()
        
        self._config.tab_files = {}
        for route_key, filepath in self._tab_files.items():
            if filepath and os.path.exists(filepath):
                self._config.tab_files[route_key] = filepath
        
        self._config.save()
    
    def closeEvent(self, event):
        has_unsaved = any(self._tab_modified.values())
        if has_unsaved:
            box = MessageBox('保存更改', '有未保存的脚本，是否保存?', self)
            box.yesButton.setText('保存')
            box.cancelButton.setText('不保存')
            
            if box.exec():
                if not self._save_script():
                    event.ignore()
                    return
        
        self._recorder_panel.stop_recording()
        for player in self._tab_players.values():
            player.stop_and_wait(timeout=1.0)
        self._save_settings()
        event.accept()
    
    def _update_mouse_position(self):
        try:
            import pyautogui
            x, y = pyautogui.position()
            
            window_offset = self._window_selector.get_window_offset()
            if window_offset:
                rel_x = x - window_offset[0]
                rel_y = y - window_offset[1]
                self._coord_label.setText(f"屏幕: ({x}, {y})  窗口: ({rel_x}, {rel_y})")
            else:
                self._coord_label.setText(f"屏幕坐标: ({x}, {y})")
        except Exception:
            pass
    
    def _get_current_tab_key(self) -> str:
        return self._script_editor.get_current_route_key()
    
    def _is_current_tab_modified(self) -> bool:
        tab_key = self._get_current_tab_key()
        return self._tab_modified.get(tab_key, False)
    
    def _is_tab_modified(self, route_key: str) -> bool:
        return self._tab_modified.get(route_key, False)
    
    def _set_current_tab_modified(self, modified: bool):
        tab_key = self._get_current_tab_key()
        self._tab_modified[tab_key] = modified
        self._update_window_title()
    
    def _get_current_tab_file(self) -> Optional[str]:
        tab_key = self._get_current_tab_key()
        return self._tab_files.get(tab_key)
    
    def _set_current_tab_file(self, filepath: Optional[str]):
        tab_key = self._get_current_tab_key()
        self._tab_files[tab_key] = filepath
        self._update_window_title()
    
    def _update_window_title(self):
        title = "SimpleRPA - RPA自动化工具"
        current_file = self._get_current_tab_file()
        if current_file:
            title = f"{os.path.basename(current_file)} - {title}"
        elif self._get_current_tab_key():
            title = f"{self._get_current_tab_key()} - {title}"
        if self._is_current_tab_modified():
            title = f"*{title}"
        self.setWindowTitle(title)
    
    def _new_script(self):
        self._script_editor.add_new_tab()
        self._property_panel.clear()
        route_key = self._script_editor.get_current_route_key()
        self._tab_files[route_key] = None
        self._tab_modified[route_key] = False
        self._create_player_for_tab(route_key)
        self._update_window_title()
        self._status_label.setText("新建任务")
    
    def _open_script(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "打开脚本", "",
            "RPA脚本 (*.rpa.json);;Python脚本 (*.py);;所有文件 (*)"
        )
        
        if filepath:
            self._load_script_file(filepath)
    
    def _load_script_file(self, filepath: str):
        if filepath.endswith('.json') or filepath.endswith('.rpa.json'):
            with open(filepath, 'r', encoding='utf-8') as f:
                import json
                data = json.load(f)
            
            actions_data = data.get('actions', [])
            local_groups_data = data.get('local_action_groups', {}) or data.get('action_groups', {})
            embedded_images = data.get('embedded_images', {})
            
            temp_dir = os.path.join(os.path.dirname(filepath), '.images')
            import base64
            image_path_map = {}
            for image_name, base64_data in embedded_images.items():
                image_data = base64.b64decode(base64_data)
                os.makedirs(temp_dir, exist_ok=True)
                image_path = os.path.join(temp_dir, image_name)
                with open(image_path, 'wb') as f:
                    f.write(image_data)
                image_path_map[image_name] = image_path
            
            from core.actions import Action, ActionType
            actions = []
            for action_data in actions_data:
                action = Action.from_dict(action_data)
                if action.action_type in [ActionType.IMAGE_CLICK, ActionType.IMAGE_WAIT_CLICK, ActionType.IMAGE_CHECK]:
                    original_path = action.params.get('image_path', '')
                    image_name = os.path.basename(original_path)
                    if image_name in image_path_map:
                        action.params['image_path'] = image_path_map[image_name]
                actions.append(action)
            
            if actions is not None:
                tab_name = os.path.splitext(os.path.basename(filepath))[0]
                current_actions = self._script_editor.get_actions()
                current_file = self._get_current_tab_file()
                
                if not current_actions and not current_file:
                    self._script_editor.set_actions(actions)
                    local_group_manager = self._script_editor.get_local_group_manager()
                    if local_group_manager:
                        local_group_manager.load_from_dict(local_groups_data)
                    current_index = 0
                    for i in range(100):
                        try:
                            if self._script_editor._tab_bar.tabText(i) == self._script_editor.get_current_tab_name():
                                current_index = i
                                break
                        except:
                            break
                    self._script_editor.set_tab_name(current_index, tab_name)
                else:
                    route_key = self._script_editor.add_new_tab(name=tab_name, actions=actions)
                    tab_content = self._script_editor._tabs.get(route_key)
                    if tab_content and hasattr(tab_content, '_local_group_manager'):
                        tab_content._local_group_manager.load_from_dict(local_groups_data)
                
                self._script_editor.refresh_groups()
                
                route_key = self._script_editor.get_current_route_key()
                self._tab_files[route_key] = filepath
                self._tab_modified[route_key] = False
                self._create_player_for_tab(route_key)
                self._update_window_title()
                self._config.add_recent_file(filepath)
                self._status_label.setText(f"已打开: {os.path.basename(filepath)}")
            else:
                MessageBox('错误', '无法加载脚本文件', self).exec()
        else:
            MessageBox('提示', '目前只支持打开JSON格式的脚本文件', self).exec()
    
    def _save_script(self) -> bool:
        current_file = self._get_current_tab_file()
        if current_file:
            return self._save_script_to_file(current_file)
        else:
            return self._save_script_as()
    
    def _save_script_as(self) -> bool:
        filepath, _ = QFileDialog.getSaveFileName(
            self, "保存脚本", "",
            "RPA脚本 (*.rpa.json);;所有文件 (*)"
        )
        
        if filepath:
            if not filepath.endswith('.json'):
                filepath += '.json'
            return self._save_script_to_file(filepath)
        return False
    
    def _save_script_to_file(self, filepath: str) -> bool:
        actions = self._script_editor.get_actions()
        
        self._exporter.set_script_info(
            name=os.path.splitext(os.path.basename(filepath))[0]
        )
        
        local_group_manager = self._script_editor.get_local_group_manager()
        self._exporter.set_local_group_manager(local_group_manager)
        
        if self._exporter.export_to_json(actions, filepath):
            tab_name = os.path.splitext(os.path.basename(filepath))[0]
            current_index = 0
            for i in range(100):
                try:
                    if self._script_editor._tab_bar.tabText(i) == self._script_editor.get_current_tab_name():
                        current_index = i
                        break
                except:
                    break
            self._script_editor.set_tab_name(current_index, tab_name)
            self._set_current_tab_file(filepath)
            self._set_current_tab_modified(False)
            self._config.add_recent_file(filepath)
            self._status_label.setText(f"已保存: {os.path.basename(filepath)}")
            return True
        else:
            MessageBox('错误', '保存失败', self).exec()
            return False
    
    def _export_python(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出Python脚本", "",
            "Python文件 (*.py);;所有文件 (*)"
        )
        
        if filepath:
            if not filepath.endswith('.py'):
                filepath += '.py'
            
            actions = self._script_editor.get_actions()
            
            window_title = ""
            if self._window_selector.get_selected_window():
                window_info = self._window_utils.get_window_by_hwnd(
                    self._window_selector.get_selected_window()
                )
                if window_info:
                    window_title = window_info.title
            
            self._exporter.set_window_setup(bool(window_title), window_title)
            
            if self._exporter.export_to_python(actions, filepath):
                self._status_label.setText(f"已导出: {os.path.basename(filepath)}")
                
                box = MessageBox('导出成功', f'脚本已导出到:\n{filepath}\n\n是否打开文件所在目录?', self)
                box.yesButton.setText('打开目录')
                box.cancelButton.setText('关闭')
                
                if box.exec():
                    os.startfile(os.path.dirname(filepath))
            else:
                MessageBox('错误', '导出失败', self).exec()
    
    def _run_script(self):
        player = self._get_current_player()
        if not player:
            return
        
        actions = self._script_editor.get_actions()
        if not actions:
            MessageBox('警告', '脚本为空，请先添加动作', self).exec()
            return
        
        player.set_actions(actions)
        player.set_speed(self._speed_spin.value())
        player.set_repeat_count(self._repeat_spin.value())
        player.set_infinite_loop(self._infinite_cb.isChecked())
        player.set_timeout(self._timeout_spin.value())
        
        window_offset = self._window_selector.get_window_offset()
        player.set_window_offset(window_offset)
        
        selected_hwnd = self._window_selector.get_selected_hwnd()
        if selected_hwnd:
            self._window_utils.activate_window(selected_hwnd)
        
        for action in actions:
            if action.action_type in [ActionType.MOUSE_CLICK_RELATIVE, ActionType.MOUSE_MOVE_RELATIVE]:
                action.use_relative_coords = True
        
        self._run_btn.setEnabled(False)
        self._pause_btn.setEnabled(True)
        self._stop_btn.setEnabled(True)
        
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(0)
        
        player.play()
        self._status_label.setText("正在执行...")
    
    def _on_infinite_changed(self, state):
        is_infinite = state == Qt.Checked
        self._repeat_spin.setEnabled(not is_infinite)
        if is_infinite:
            self._status_label.setText("无限循环模式")
    
    def _pause_script(self):
        player = self._get_current_player()
        if not player:
            return
        
        new_state = player.toggle_pause()
        if new_state == PlayerState.PAUSED:
            self._pause_btn.setText("继续")
            self._status_label.setText("已暂停")
        elif new_state == PlayerState.PLAYING:
            self._pause_btn.setText("暂停")
            self._status_label.setText("正在执行...")
    
    def _stop_script(self):
        player = self._get_current_player()
        if player:
            player.stop()
            self._status_label.setText("已停止")
    
    def _on_action_added(self, action: Action):
        self._script_editor.add_action(action)
        self._set_current_tab_modified(True)
    
    def _on_action_selected(self, action: Action):
        index = self._script_editor.get_selected_index()
        self._property_panel.set_action(action, index)
    
    def _on_actions_changed(self):
        self._set_current_tab_modified(True)
        self._property_panel.set_all_actions(self._script_editor.get_actions())
    
    def _on_action_updated(self, action: Action):
        index = self._script_editor.get_selected_index()
        if index >= 0:
            self._script_editor.update_action(index, action)
    
    def _on_action_recorded(self, action: Action):
        window_offset = self._window_selector.get_window_offset()
        if window_offset and action.action_type in [ActionType.MOUSE_CLICK, ActionType.MOUSE_MOVE]:
            x = action.params.get('x', 0)
            y = action.params.get('y', 0)
            rel_x = x - window_offset[0]
            rel_y = y - window_offset[1]
            
            if action.action_type == ActionType.MOUSE_CLICK:
                new_action = Action(
                    action_type=ActionType.MOUSE_CLICK_RELATIVE,
                    params={'x': rel_x, 'y': rel_y},
                    delay_before=action.delay_before,
                    use_relative_coords=True
                )
            else:
                new_action = Action(
                    action_type=ActionType.MOUSE_MOVE_RELATIVE,
                    params={'x': rel_x, 'y': rel_y, 'duration': action.params.get('duration', 0.0)},
                    delay_before=action.delay_before,
                    use_relative_coords=True
                )
            self._script_editor.add_action(new_action)
        else:
            self._script_editor.add_action(action)
        self._set_current_tab_modified(True)
    
    def _on_recording_started(self):
        self._status_label.setText("正在录制...")
    
    def _on_recording_stopped(self):
        self._status_label.setText("录制完成")
    
    def _on_actions_cleared(self):
        self._script_editor.clear_actions()
        self._property_panel.clear()
        self._set_current_tab_modified(False)
        self._status_label.setText("已清除录制")
    
    def _on_last_action_removed(self):
        actions = self._script_editor.get_actions()
        if actions:
            self._script_editor.remove_action(len(actions) - 1)
    
    def _on_execute_single(self, index: int):
        player = self._get_current_player()
        if not player:
            return
        
        if player.state != PlayerState.IDLE:
            self._status_label.setText("请先停止当前运行的脚本")
            return
        
        actions = self._script_editor.get_actions()
        if not actions or index < 0 or index >= len(actions):
            return
        
        window_offset = self._window_selector.get_window_offset()
        
        selected_hwnd = self._window_selector.get_selected_hwnd()
        if selected_hwnd:
            self._window_utils.activate_window(selected_hwnd)
        
        def execute():
            try:
                player.actions = actions
                player.set_window_offset(window_offset)
                player.speed = self._speed_spin.value()
                player.execute_single_action(index, window_offset)
            except Exception as e:
                print(f"[单步调试错误] {e}")
        
        import threading
        thread = threading.Thread(target=execute, daemon=True)
        thread.start()
        self._status_label.setText(f"调试执行: 第 {index + 1} 个动作")
    
    def _on_player_action_start_thread(self, action: Action, index: int, route_key: str):
        current_route_key = self._script_editor.get_current_route_key()
        if route_key == current_route_key:
            self._update_action_start_signal.emit(action, index, route_key)
    
    def _on_player_action_start_gui(self, action: Action, index: int, route_key: str):
        player = self._tab_players.get(route_key)
        if player:
            total_actions = len(player.actions)
            desc = action.description[:50] + "..." if len(action.description) > 50 else action.description
            self._status_label.setText(f"执行动作 {index + 1}/{total_actions}: {desc}")
        
        current_route_key = self._script_editor.get_current_route_key()
        if route_key == current_route_key:
            self._script_editor.set_action_running(index)
    
    def _on_player_action_start(self, action: Action, index: int):
        pass
    
    def _on_player_action_end(self, action: Action, index: int, success: bool):
        pass
    
    def _on_player_progress_thread(self, progress: float, action_index: int, repeat: int, route_key: str):
        self._update_progress_signal.emit(progress, action_index, repeat)
    
    def _on_player_state_changed_thread(self, state: PlayerState, route_key: str):
        self._update_state_signal.emit(state, route_key)
    
    def _on_player_finished_thread(self, success: bool, route_key: str):
        self._update_finished_signal.emit(success, route_key)
    
    def _on_player_error_thread(self, action: Action, index: int, error: str, route_key: str):
        self._update_error_signal.emit(error, route_key)
    
    def _on_player_progress(self, progress: float, action_index: int, repeat: int):
        player = self._get_current_player()
        if player:
            if player.infinite_loop:
                self._status_label.setText(f"正在执行... 第 {repeat} 轮")
            else:
                total = player.repeat_count
                self._status_label.setText(f"正在执行... 第 {repeat}/{total} 轮")
        
        if progress >= 0:
            self._progress_bar.setValue(int(progress))
    
    def _on_player_state_changed(self, state: PlayerState, route_key: str):
        current_route_key = self._script_editor.get_current_route_key()
        
        if route_key == current_route_key:
            if state == PlayerState.IDLE:
                self._run_btn.setEnabled(True)
                self._pause_btn.setEnabled(False)
                self._stop_btn.setEnabled(False)
                self._pause_btn.setText("暂停")
                self._script_editor.clear_all_running()
            elif state == PlayerState.PAUSED:
                self._pause_btn.setText("继续")
                self._status_label.setText("已暂停")
            elif state == PlayerState.PLAYING:
                self._pause_btn.setText("暂停")
            elif state == PlayerState.STOPPED:
                self._run_btn.setEnabled(False)
                self._pause_btn.setEnabled(False)
                self._stop_btn.setEnabled(False)
                self._script_editor.clear_all_running()
    
    def _on_player_finished(self, success: bool, route_key: str):
        current_route_key = self._script_editor.get_current_route_key()
        
        if route_key == current_route_key:
            self._progress_bar.setVisible(False)
            if success:
                self._status_label.setText("执行完成")
            else:
                self._status_label.setText("执行中断")
            
            self._run_btn.setEnabled(True)
            self._pause_btn.setEnabled(False)
            self._stop_btn.setEnabled(False)
            self._pause_btn.setText("暂停")
    
    def _on_player_error_gui(self, error: str, route_key: str):
        print(f"[执行错误] {error}")
        current_route_key = self._script_editor.get_current_route_key()
        if route_key == current_route_key:
            self._status_label.setText(f"执行错误: {error}")
