from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog,
    QAbstractItemView, QListWidgetItem, QInputDialog,
    QStackedWidget, QStackedLayout, QAction, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt5 import sip
from typing import List, Optional, Dict
from core.actions import Action as ScriptAction
from core.action_group import ActionGroup, LocalActionGroupManager, GlobalActionGroupManager
import copy

from qfluentwidgets import (
    StrongBodyLabel, BodyLabel, PushButton, PrimaryPushButton,
    ListWidget, CardWidget, MessageBox, LineEdit, SubtitleLabel,
    ScrollArea, TransparentToolButton, FluentIcon, Pivot,
    TabBar, TabCloseButtonDisplayMode, RoundMenu, Action,
    MessageBoxBase, InfoBar, InfoBarPosition
)


class ActionItemWidget(QWidget):
    action_changed = pyqtSignal()
    delete_requested = pyqtSignal()
    
    def __init__(self, action: ScriptAction, index: int, parent=None):
        super().__init__(parent)
        self._action = action
        self._index = index
        self._is_running = False
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        is_from_group = getattr(self._action, '_is_from_group', False)
        group_name = getattr(self._action, '_group_name', '')
        
        self._index_label = StrongBodyLabel(f"{self._index + 1}")
        self._index_label.setObjectName("indexLabel")
        self._index_label.setFixedWidth(30)
        self._index_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._index_label)
        
        if is_from_group:
            group_indicator = BodyLabel(f"📁 {group_name}")
            layout.addWidget(group_indicator)
        
        self._desc_label = BodyLabel(self._action.description)
        self._desc_label.setObjectName("descLabel")
        self._desc_label.setWordWrap(True)
        layout.addWidget(self._desc_label, 1)
        
        self._delete_btn = PushButton("删除")
        self._delete_btn.setFixedWidth(60)
        self._delete_btn.setMinimumHeight(36)
        self._delete_btn.clicked.connect(self.delete_requested.emit)
        layout.addWidget(self._delete_btn)
    
    def update_index(self, index: int):
        self._index = index
        self._index_label.setText(f"{self._index + 1}")
    
    def set_running(self, running: bool):
        self._is_running = running
        if running:
            from qfluentwidgets import themeColor
            color = themeColor()
            highlight_color = color.name()
            bg_color = f"rgba({color.red()}, {color.green()}, {color.blue()}, 0.2)"
            
            self.setStyleSheet(f"""
                ActionItemWidget {{
                    background-color: {bg_color};
                    border: 2px solid {highlight_color};
                    border-radius: 6px;
                }}
                #indexLabel, #descLabel {{
                    color: {highlight_color};
                    font-weight: bold;
                }}
            """)
        else:
            self.setStyleSheet("")


class ActionGroupItemWidget(CardWidget):
    insert_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    edit_requested = pyqtSignal(str)
    
    def __init__(self, group: ActionGroup, is_local: bool = False, parent=None):
        super().__init__(parent)
        self._group = group
        self._is_local = is_local
        self._expanded = False
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        header_layout = QHBoxLayout()
        
        self._expand_btn = TransparentToolButton(FluentIcon.CHEVRON_RIGHT_MED, self)
        self._expand_btn.setFixedSize(24, 24)
        self._expand_btn.clicked.connect(self._toggle_expand)
        header_layout.addWidget(self._expand_btn)
        
        name_label = StrongBodyLabel(self._group.name)
        header_layout.addWidget(name_label)
        
        if self._is_local:
            from qfluentwidgets import InfoBadge
            local_badge = InfoBadge.custom("局部", "#2d5a27", "#b8e6b0")
            header_layout.addWidget(local_badge)
        
        count_label = BodyLabel(f"{self._group.get_action_count()} 个动作")
        header_layout.addWidget(count_label)
        
        header_layout.addStretch()
        
        edit_btn = TransparentToolButton(FluentIcon.EDIT, self)
        edit_btn.setToolTip("编辑动作组")
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(self._group.name))
        header_layout.addWidget(edit_btn)
        
        insert_btn = TransparentToolButton(FluentIcon.ADD, self)
        insert_btn.setToolTip("插入到脚本")
        insert_btn.clicked.connect(lambda: self.insert_requested.emit(self._group.name))
        header_layout.addWidget(insert_btn)
        
        delete_btn = TransparentToolButton(FluentIcon.DELETE, self)
        delete_btn.setToolTip("删除")
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(self._group.name))
        header_layout.addWidget(delete_btn)
        
        layout.addLayout(header_layout)
        
        if self._group.description:
            desc_label = BodyLabel(self._group.description)
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)
        
        self._actions_container = QWidget()
        self._actions_layout = QVBoxLayout(self._actions_container)
        self._actions_layout.setContentsMargins(24, 8, 8, 8)
        self._actions_layout.setSpacing(4)
        self._actions_container.hide()
        layout.addWidget(self._actions_container)
        
        self._populate_actions()
    
    def _toggle_expand(self):
        self._expanded = not self._expanded
        self._actions_container.setVisible(self._expanded)
        
        if self._expanded:
            self._expand_btn.setIcon(FluentIcon.CHEVRON_DOWN_MED)
        else:
            self._expand_btn.setIcon(FluentIcon.CHEVRON_RIGHT_MED)
    
    def _populate_actions(self):
        while self._actions_layout.count():
            item = self._actions_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        for i, action in enumerate(self._group.actions):
            action_label = BodyLabel(f"{i + 1}. {action.description}")
            action_label.setWordWrap(True)
            self._actions_layout.addWidget(action_label)


class ScriptTabContent(QWidget):
    action_selected = pyqtSignal(object)
    actions_changed = pyqtSignal()
    execute_single = pyqtSignal(int)
    highlight_action = pyqtSignal(int)
    clear_highlight = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._actions: List[ScriptAction] = []
        self._selected_index: int = -1
        self._clipboard: List[ScriptAction] = []
        self._local_group_manager = LocalActionGroupManager()
        self._global_group_manager = GlobalActionGroupManager.get_instance()
        self._setup_ui()
    
    def _get_main_window(self):
        widget = self
        while widget.parent():
            widget = widget.parent()
            if hasattr(widget, 'window') and callable(widget.window):
                main_window = widget.window()
                if main_window and main_window != widget:
                    return main_window
        return QApplication.instance().activeWindow() if QApplication.instance() else None
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        self._pivot = Pivot()
        self._pivot.addItem(routeKey='actions', text='动作列表')
        self._pivot.addItem(routeKey='groups', text='动作组')
        self._pivot.currentItemChanged.connect(self._on_pivot_changed)
        layout.addWidget(self._pivot)
        
        self._action_list = ListWidget()
        self._action_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._action_list.setDragDropMode(QAbstractItemView.InternalMove)
        self._action_list.currentRowChanged.connect(self._on_selection_changed)
        self._action_list.model().rowsMoved.connect(self._on_rows_moved)
        self._action_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._action_list.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self._action_list)
        
        self._groups_scroll_area = ScrollArea()
        self._groups_scroll_area.setWidgetResizable(True)
        self._groups_scroll_area.setStyleSheet("QScrollArea{border: none; background: transparent;}")
        
        self._groups_content_widget = QWidget()
        self._groups_content_widget.setStyleSheet("background: transparent;")
        self._groups_content_layout = QVBoxLayout(self._groups_content_widget)
        self._groups_content_layout.setAlignment(Qt.AlignTop)
        self._groups_content_layout.setSpacing(12)
        self._groups_scroll_area.setWidget(self._groups_content_widget)
        layout.addWidget(self._groups_scroll_area)
        
        self._empty_groups_label = BodyLabel("暂无保存的动作组\n\n在脚本列表中右键选择动作，\n点击\"保存为动作组...\"即可创建")
        self._empty_groups_label.setAlignment(Qt.AlignCenter)
        self._empty_groups_label.setWordWrap(True)
        self._groups_content_layout.addWidget(self._empty_groups_label)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self._debug_btn = PushButton("预览全部")
        self._debug_btn.setMinimumWidth(80)
        self._debug_btn.setMinimumHeight(40)
        self._debug_btn.clicked.connect(self._preview_all)
        btn_layout.addWidget(self._debug_btn)
        
        self._clear_btn = PushButton("清空全部")
        self._clear_btn.setMinimumHeight(40)
        self._clear_btn.clicked.connect(self._clear_all)
        btn_layout.addWidget(self._clear_btn)
        
        btn_layout.addStretch()
        
        self._up_btn = PushButton("上一个")
        self._up_btn.setMinimumWidth(70)
        self._up_btn.setMinimumHeight(40)
        self._up_btn.clicked.connect(self._select_previous)
        btn_layout.addWidget(self._up_btn)
        
        self._down_btn = PushButton("下一个")
        self._down_btn.setMinimumWidth(70)
        self._down_btn.setMinimumHeight(40)
        self._down_btn.clicked.connect(self._select_next)
        btn_layout.addWidget(self._down_btn)
        
        layout.addLayout(btn_layout)
        
        self._pivot.setCurrentItem('actions')
        self._refresh_groups()
    
    def _on_pivot_changed(self, key: str):
        self._action_list.setVisible(key == 'actions')
        self._groups_scroll_area.setVisible(key == 'groups')
        self._debug_btn.setVisible(key == 'actions')
        self._clear_btn.setVisible(key == 'actions')
        self._up_btn.setVisible(key == 'actions')
        self._down_btn.setVisible(key == 'actions')
    
    def _refresh_groups(self):
        while self._groups_content_layout.count():
            item = self._groups_content_layout.takeAt(0)
            widget = item.widget()
            if widget and widget != self._empty_groups_label:
                widget.setParent(None)
                widget.deleteLater()
        
        local_groups = self._local_group_manager.get_all_groups()
        local_names = {g.name for g in local_groups}
        
        global_groups = self._global_group_manager.get_all_groups()
        global_groups = [g for g in global_groups if g.name not in local_names]
        
        all_groups_with_flag = [(g, True) for g in local_groups] + [(g, False) for g in global_groups]
        
        has_groups = len(all_groups_with_flag) > 0
        
        try:
            if self._empty_groups_label and not sip.isdeleted(self._empty_groups_label):
                self._empty_groups_label.setVisible(not has_groups)
        except RuntimeError:
            self._empty_groups_label = BodyLabel("暂无保存的动作组\n\n在脚本列表中右键选择动作，\n点击\"保存为动作组...\"即可创建")
            self._empty_groups_label.setAlignment(Qt.AlignCenter)
            self._empty_groups_label.setWordWrap(True)
            self._groups_content_layout.addWidget(self._empty_groups_label)
            self._empty_groups_label.setVisible(not has_groups)
        
        for group, is_local in all_groups_with_flag:
            item_widget = ActionGroupItemWidget(group, is_local=is_local)
            item_widget.insert_requested.connect(self._on_group_insert_requested)
            item_widget.delete_requested.connect(self._on_group_delete_requested)
            item_widget.edit_requested.connect(self._on_group_edit_requested)
            self._groups_content_layout.addWidget(item_widget)
    
    def _on_group_insert_requested(self, name: str):
        from core.actions import ActionType
        ref_action = ScriptAction(
            action_type=ActionType.ACTION_GROUP_REF,
            params={'group_name': name}
        )
        
        current_row = self._action_list.currentRow()
        insert_index = current_row + 1 if current_row >= 0 else len(self._actions)
        
        self._actions.insert(insert_index, ref_action)
        
        self._refresh_list()
        self.actions_changed.emit()
        
        main_window = self._get_main_window()
        InfoBar.success(
            title='插入成功',
            content=f'动作组引用 "{name}" 已插入到脚本',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=main_window if main_window else self
        )
    
    def _on_group_delete_requested(self, name: str):
        box = MessageBox('确认删除', f'确定要删除动作组 "{name}" 吗?', self)
        box.yesButton.setText('确定')
        box.cancelButton.setText('取消')
        
        if box.exec():
            if not self._local_group_manager.delete_group(name):
                self._global_group_manager.delete_group(name)
            self._refresh_groups()
    
    def _on_group_edit_requested(self, name: str):
        group = self._local_group_manager.get_group(name)
        is_local = True
        if not group:
            group = self._global_group_manager.get_group(name)
            is_local = False
        
        if group:
            main_window = self._get_main_window()
            window_offset = None
            if main_window and hasattr(main_window, '_window_selector'):
                window_offset = main_window._window_selector.get_window_offset()
            
            dialog = ActionGroupEditDialog(main_window if main_window else self, group, window_offset)
            if dialog.exec_():
                is_valid, error_msg = dialog.validate()
                if not is_valid:
                    MessageBox('验证失败', error_msg, main_window if main_window else self).exec()
                    return
                
                new_name = dialog.get_name()
                new_description = dialog.get_description()
                new_actions = dialog.get_actions()
                
                if not new_name:
                    return
                
                if new_name != group.name:
                    if is_local:
                        self._local_group_manager.delete_group(group.name)
                    else:
                        self._global_group_manager.delete_group(group.name)
                
                group.name = new_name
                group.description = new_description
                group.actions = new_actions
                if is_local:
                    self._local_group_manager.save_group(group)
                else:
                    self._global_group_manager.save_group(group)
                self._refresh_groups()
                
                InfoBar.success(
                    title='保存成功',
                    content=f'动作组 "{new_name}" 已更新',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=main_window if main_window else self
                )
    
    def add_action(self, action: ScriptAction):
        self._actions.append(action)
        self._refresh_list()
        self.actions_changed.emit()
    
    def insert_action(self, index: int, action: ScriptAction):
        if 0 <= index <= len(self._actions):
            self._actions.insert(index, action)
        else:
            self._actions.append(action)
        self._refresh_list()
        self.actions_changed.emit()
    
    def remove_action(self, index: int):
        if 0 <= index < len(self._actions):
            del self._actions[index]
            self._refresh_list()
            self.actions_changed.emit()
    
    def update_action(self, index: int, action: ScriptAction):
        if 0 <= index < len(self._actions):
            self._actions[index] = action
            
            item = self._action_list.item(index)
            if item:
                widget = ActionItemWidget(action, index)
                widget.delete_requested.connect(lambda checked=False, idx=index: self._on_delete_requested(idx))
                item.setSizeHint(widget.sizeHint())
                self._action_list.setItemWidget(item, widget)
            
            self.actions_changed.emit()
    
    def set_actions(self, actions: List[ScriptAction]):
        self._actions = actions.copy()
        self._refresh_list()
        self.actions_changed.emit()
    
    def get_actions(self) -> List[ScriptAction]:
        return self._actions.copy()
    
    def clear_actions(self):
        self._actions = []
        self._refresh_list()
        self.actions_changed.emit()
    
    def _refresh_list(self):
        self._action_list.clear()
        
        for i, action in enumerate(self._actions):
            item = QListWidgetItem(self._action_list)
            widget = ActionItemWidget(action, i)
            widget.delete_requested.connect(lambda checked=False, idx=i: self._on_delete_requested(idx))
            item.setSizeHint(widget.sizeHint())
            self._action_list.setItemWidget(item, widget)
    
    def _on_selection_changed(self, current_row: int):
        self._selected_index = current_row
        if 0 <= current_row < len(self._actions):
            self.action_selected.emit(self._actions[current_row])
    
    def _on_rows_moved(self):
        new_actions: List[ScriptAction] = []
        for i in range(self._action_list.count()):
            item = self._action_list.item(i)
            widget = self._action_list.itemWidget(item)
            if widget:
                original_index = int(widget._index)
                new_actions.append(self._actions[original_index])
        
        self._actions = new_actions
        self._refresh_list()
        self.actions_changed.emit()
    
    def _on_delete_requested(self, index: int):
        self.remove_action(index)
    
    def _select_previous(self):
        current_row = self._action_list.currentRow()
        if current_row > 0:
            self._action_list.setCurrentRow(current_row - 1)
    
    def _select_next(self):
        current_row = self._action_list.currentRow()
        if current_row < len(self._actions) - 1:
            self._action_list.setCurrentRow(current_row + 1)
    
    def _move_up(self):
        current_row = self._action_list.currentRow()
        if current_row > 0:
            self._actions[current_row], self._actions[current_row - 1] = \
                self._actions[current_row - 1], self._actions[current_row]
            self._refresh_list()
            self._action_list.setCurrentRow(current_row - 1)
            self.actions_changed.emit()
    
    def _move_down(self):
        current_row = self._action_list.currentRow()
        if current_row < len(self._actions) - 1:
            self._actions[current_row], self._actions[current_row + 1] = \
                self._actions[current_row + 1], self._actions[current_row]
            self._refresh_list()
            self._action_list.setCurrentRow(current_row + 1)
            self.actions_changed.emit()
    
    def _clear_all(self):
        if self._actions:
            box = MessageBox('确认清空', '确定要清空所有动作吗?', self)
            box.yesButton.setText('确定')
            box.cancelButton.setText('取消')
            
            if box.exec():
                self.clear_actions()
    
    def _show_context_menu(self, pos):
        item = self._action_list.itemAt(pos)
        
        menu = RoundMenu(parent=self)
        
        selected_rows = sorted([self._action_list.row(item) for item in self._action_list.selectedItems()])
        
        local_groups = self._local_group_manager.get_all_groups()
        local_names = {g.name for g in local_groups}
        global_groups = self._global_group_manager.get_all_groups()
        global_groups = [g for g in global_groups if g.name not in local_names]
        unique_groups = local_groups + global_groups
        
        if item:
            index = self._action_list.row(item)
            action = self._actions[index] if 0 <= index < len(self._actions) else None
            
            menu.addAction(Action(FluentIcon.DELETE, "删除选中", triggered=lambda: self._delete_selected()))
            menu.addSeparator()
            menu.addAction(Action(FluentIcon.COPY, "复制选中", triggered=lambda: self._copy_selected()))
            
            if self._clipboard:
                menu.addAction(Action(FluentIcon.PASTE, f"粘贴 ({len(self._clipboard)} 个)", triggered=lambda: self._paste_actions(index)))
            
            menu.addSeparator()
            
            if unique_groups:
                add_group_menu = RoundMenu("添加动作组", self)
                add_group_menu.setIcon(FluentIcon.FOLDER_ADD)
                for group in unique_groups:
                    add_group_menu.addAction(Action(FluentIcon.FOLDER, group.name, triggered=lambda checked=False, n=group.name: self._insert_group_at(n, index)))
                menu.addMenu(add_group_menu)
            
            from core.actions import ActionType
            if action and action.action_type == ActionType.ACTION_GROUP_REF:
                menu.addAction(Action(FluentIcon.FOLDER, "解压动作组引用", triggered=lambda: self._expand_action_group(index)))
            
            if selected_rows:
                menu.addAction(Action(FluentIcon.SAVE, "保存为动作组...", triggered=lambda: self._save_as_group(selected_rows)))
            
            menu.addSeparator()
            
            menu.addAction(Action(FluentIcon.PLAY, "调试此动作", triggered=lambda: self.execute_single.emit(index)))
        else:
            if self._clipboard:
                menu.addAction(Action(FluentIcon.PASTE, f"粘贴 ({len(self._clipboard)} 个)", triggered=lambda: self._paste_actions(len(self._actions))))
            
            if unique_groups:
                menu.addSeparator()
                add_group_menu = RoundMenu("添加动作组", self)
                add_group_menu.setIcon(FluentIcon.FOLDER_ADD)
                for group in unique_groups:
                    add_group_menu.addAction(Action(FluentIcon.FOLDER, group.name, triggered=lambda checked=False, n=group.name: self._insert_group_at(n, len(self._actions))))
                menu.addMenu(add_group_menu)
        
        if menu.actions():
            menu.exec_(self._action_list.mapToGlobal(pos))
    
    def _insert_group_at(self, name: str, index: int):
        from core.actions import ActionType
        ref_action = ScriptAction(
            action_type=ActionType.ACTION_GROUP_REF,
            params={'group_name': name}
        )
        
        self._actions.insert(index + 1, ref_action)
        
        self._refresh_list()
        self.actions_changed.emit()
    
    def _expand_action_group(self, index: int):
        from core.actions import ActionType
        
        if not (0 <= index < len(self._actions)):
            return
        
        action = self._actions[index]
        if action.action_type != ActionType.ACTION_GROUP_REF:
            return
        
        group_name = action.params.get('group_name', '')
        if not group_name:
            return
        
        group = self._local_group_manager.get_group(group_name)
        if not group:
            group = self._global_group_manager.get_group(group_name)
        if not group:
            main_window = self._get_main_window()
            MessageBox('错误', f'动作组 "{group_name}" 不存在', main_window if main_window else self).exec()
            return
        
        expanded_actions = [copy.deepcopy(a) for a in group.actions]
        
        del self._actions[index]
        
        for i, expanded_action in enumerate(expanded_actions):
            self._actions.insert(index + i, expanded_action)
        
        self._refresh_list()
        self.actions_changed.emit()
        
        main_window = self._get_main_window()
        InfoBar.success(
            title='解压成功',
            content=f'动作组 "{group_name}" 已解压为 {len(expanded_actions)} 个动作',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=main_window if main_window else self
        )
    
    def _delete_selected(self):
        selected_rows = sorted([self._action_list.row(item) for item in self._action_list.selectedItems()], reverse=True)
        for row in selected_rows:
            if 0 <= row < len(self._actions):
                del self._actions[row]
        self._refresh_list()
        self.actions_changed.emit()
    
    def _copy_selected(self):
        selected_rows = sorted([self._action_list.row(item) for item in self._action_list.selectedItems()])
        self._clipboard = [copy.deepcopy(self._actions[row]) for row in selected_rows if 0 <= row < len(self._actions)]
    
    def _paste_actions(self, index: int):
        for i, action in enumerate(self._clipboard):
            self._actions.insert(index + i + 1, copy.deepcopy(action))
        self._refresh_list()
        self.actions_changed.emit()
    
    def _duplicate_action(self, index: int):
        if 0 <= index < len(self._actions):
            new_action = copy.deepcopy(self._actions[index])
            self._actions.insert(index + 1, new_action)
            self._refresh_list()
            self.actions_changed.emit()
    
    def _preview_all(self):
        if not self._actions:
            return
        self._preview_index = 0
        self._preview_timer = QTimer(self)
        self._preview_timer.timeout.connect(self._preview_next_action)
        self._preview_timer.start(1500)
        self._highlight_action(0)
    
    def _preview_next_action(self):
        self._preview_index += 1
        if self._preview_index >= len(self._actions):
            self._preview_timer.stop()
            self._clear_all_highlights()
            return
        self._highlight_action(self._preview_index)
    
    def _highlight_action(self, index: int):
        for i in range(self._action_list.count()):
            item = self._action_list.item(i)
            widget = self._action_list.itemWidget(item)
            if widget and hasattr(widget, 'set_running'):
                widget.set_running(i == index)
        self._action_list.setCurrentRow(index)
    
    def _clear_all_highlights(self):
        for i in range(self._action_list.count()):
            item = self._action_list.item(i)
            widget = self._action_list.itemWidget(item)
            if widget and hasattr(widget, 'set_running'):
                widget.set_running(False)
    
    def set_action_running(self, index: int):
        self._highlight_action(index)
    
    def clear_all_running(self):
        self._clear_all_highlights()
    
    def _save_as_group(self, selected_rows: List[int]):
        if not selected_rows:
            return
        
        dialog = SaveGroupDialog(self)
        if dialog.exec_():
            name = dialog.get_name()
            description = dialog.get_description()
            
            if not name:
                return
            
            actions = [copy.deepcopy(self._actions[row]) for row in selected_rows if 0 <= row < len(self._actions)]
            
            group = self._local_group_manager.create_group_from_actions(name, description, actions)
            
            if self._local_group_manager.save_group(group):
                self._refresh_groups()
            else:
                MessageBox('保存失败', '无法保存动作组', self).exec()
    
    def get_selected_index(self) -> int:
        return self._selected_index
    
    def get_selected_action(self) -> Optional[ScriptAction]:
        if 0 <= self._selected_index < len(self._actions):
            return self._actions[self._selected_index]
        return None


class ScriptEditor(CardWidget):
    action_selected = pyqtSignal(object)
    actions_changed = pyqtSignal()
    execute_single = pyqtSignal(int)
    tab_changed = pyqtSignal(str)
    tab_close_requested = pyqtSignal(str, str)
    highlight_action = pyqtSignal(int)
    clear_highlight = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tabs: Dict[str, ScriptTabContent] = {}
        self._tab_counter: int = 0
        self._external_modified_check = None
        self._setup_ui()
        self.add_new_tab()
    
    def set_modified_check_callback(self, callback):
        self._external_modified_check = callback
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        header_layout = QHBoxLayout()
        header = StrongBodyLabel("脚本编辑器")
        header_layout.addWidget(header)
        header_layout.addStretch()
        
        self._action_count_label = BodyLabel("共 0 个动作")
        header_layout.addWidget(self._action_count_label)
        layout.addLayout(header_layout)
        
        self._tab_bar = TabBar()
        self._tab_bar.setTabsClosable(True)
        self._tab_bar.setCloseButtonDisplayMode(TabCloseButtonDisplayMode.ON_HOVER)
        self._tab_bar.setMovable(True)
        self._tab_bar.setAddButtonVisible(True)
        self._tab_bar.setTabShadowEnabled(False)
        self._tab_bar.setFixedHeight(48)
        
        self._tab_bar.tabAddRequested.connect(self._on_tab_add_requested)
        self._tab_bar.tabCloseRequested.connect(self._on_tab_close_requested)
        self._tab_bar.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self._tab_bar)
        
        self._stacked_widget = QStackedWidget()
        layout.addWidget(self._stacked_widget)
    
    def add_new_tab(self, name: str = None, actions: List[ScriptAction] = None) -> str:
        self._tab_counter += 1
        if name is None:
            name = f"任务 {self._tab_counter}"
        
        route_key = f"tab_{self._tab_counter}"
        
        self.setUpdatesEnabled(False)
        
        try:
            tab_content = ScriptTabContent(self)
            if actions:
                tab_content.set_actions(actions)
            
            tab_content.action_selected.connect(self._on_action_selected)
            tab_content.actions_changed.connect(self._on_actions_changed)
            tab_content.execute_single.connect(self.execute_single.emit)
            tab_content.highlight_action.connect(self.highlight_action.emit)
            tab_content.clear_highlight.connect(self.clear_highlight.emit)
            
            self._tabs[route_key] = tab_content
            self._stacked_widget.addWidget(tab_content)
            self._tab_bar.addTab(route_key, name)
            self._tab_bar.setCurrentTab(route_key)
            self._stacked_widget.setCurrentWidget(tab_content)
            
            self._update_action_count()
        finally:
            self.setUpdatesEnabled(True)
        
        return route_key
    
    def _on_tab_add_requested(self):
        self.add_new_tab()
    
    def _on_tab_close_requested(self, index: int):
        if self._tab_bar.count() <= 1:
            return
        
        route_key = self._get_route_key_by_index(index)
        if route_key and route_key in self._tabs:
            tab_content = self._tabs[route_key]
            has_content = bool(tab_content.get_actions())
            
            is_modified = False
            if self._external_modified_check:
                is_modified = self._external_modified_check(route_key)
            
            if has_content and is_modified:
                self.tab_close_requested.emit(route_key, self._tab_bar.tabText(index))
            else:
                self._close_tab_by_route_key(route_key, index)
    
    def _close_tab_by_route_key(self, route_key: str, index: int):
        if route_key in self._tabs:
            tab_content = self._tabs[route_key]
            del self._tabs[route_key]
            self._stacked_widget.removeWidget(tab_content)
            tab_content.deleteLater()
            self._tab_bar.removeTab(index)
            self._update_action_count()
    
    def _on_tab_changed(self, index: int):
        route_key = self._get_route_key_by_index(index)
        if route_key and route_key in self._tabs:
            self._stacked_widget.setCurrentWidget(self._tabs[route_key])
            self._update_action_count()
            self.tab_changed.emit(route_key)
    
    def _get_route_key_by_index(self, index: int) -> Optional[str]:
        tab_item = self._tab_bar.tabItem(index)
        if tab_item:
            return tab_item.routeKey()
        return None
    
    def _get_current_tab(self) -> Optional[ScriptTabContent]:
        route_key = self._get_route_key_by_index(self._tab_bar.currentIndex())
        if route_key and route_key in self._tabs:
            return self._tabs[route_key]
        return None
    
    def _on_action_selected(self, action: Action):
        self.action_selected.emit(action)
    
    def _on_actions_changed(self):
        self.actions_changed.emit()
        self._update_action_count()
    
    def _update_action_count(self):
        current_tab = self._get_current_tab()
        if current_tab:
            count = len(current_tab.get_actions())
            self._action_count_label.setText(f"共 {count} 个动作")
        else:
            self._action_count_label.setText("共 0 个动作")
    
    def add_action(self, action: ScriptAction):
        current_tab = self._get_current_tab()
        if current_tab:
            current_tab.add_action(action)
    
    def insert_action(self, index: int, action: ScriptAction):
        current_tab = self._get_current_tab()
        if current_tab:
            current_tab.insert_action(index, action)
    
    def remove_action(self, index: int):
        current_tab = self._get_current_tab()
        if current_tab:
            current_tab.remove_action(index)
    
    def update_action(self, index: int, action: ScriptAction):
        current_tab = self._get_current_tab()
        if current_tab:
            current_tab.update_action(index, action)
    
    def set_actions(self, actions: List[ScriptAction]):
        current_tab = self._get_current_tab()
        if current_tab:
            current_tab.set_actions(actions)
    
    def get_actions(self) -> List[ScriptAction]:
        current_tab = self._get_current_tab()
        if current_tab:
            return current_tab.get_actions()
        return []
    
    def clear_actions(self):
        current_tab = self._get_current_tab()
        if current_tab:
            current_tab.clear_actions()
    
    def get_selected_index(self) -> int:
        current_tab = self._get_current_tab()
        if current_tab:
            return current_tab.get_selected_index()
        return -1
    
    def set_action_running(self, index: int):
        current_tab = self._get_current_tab()
        if current_tab:
            current_tab.set_action_running(index)
    
    def clear_all_running(self):
        current_tab = self._get_current_tab()
        if current_tab:
            current_tab.clear_all_running()
    
    def get_selected_action(self) -> Optional[ScriptAction]:
        current_tab = self._get_current_tab()
        if current_tab:
            return current_tab.get_selected_action()
        return None
    
    def get_all_tabs(self) -> Dict[str, List[ScriptAction]]:
        result = {}
        for i in range(self._tab_bar.count()):
            route_key = self._get_route_key_by_index(i)
            if route_key and route_key in self._tabs:
                tab_text = self._tab_bar.tabText(i)
                result[tab_text] = self._tabs[route_key].get_actions()
        return result
    
    def set_tab_name(self, index: int, name: str):
        if 0 <= index < self._tab_bar.count():
            route_key = self._get_route_key_by_index(index)
            if route_key:
                self._tab_bar.setTabText(index, name)
    
    def get_current_tab_name(self) -> str:
        index = self._tab_bar.currentIndex()
        if 0 <= index < self._tab_bar.count():
            return self._tab_bar.tabText(index)
        return ""
    
    def set_current_tab_name(self, name: str):
        index = self._tab_bar.currentIndex()
        if 0 <= index < self._tab_bar.count():
            self._tab_bar.setTabText(index, name)
    
    def get_current_tab_index(self) -> int:
        return self._tab_bar.currentIndex()
    
    def set_current_tab_index(self, index: int):
        if 0 <= index < self._tab_bar.count():
            self._tab_bar.setCurrentIndex(index)
    
    def get_current_route_key(self) -> str:
        index = self._tab_bar.currentIndex()
        if 0 <= index < self._tab_bar.count():
            return self._get_route_key_by_index(index) or ""
        return ""
    
    def get_route_key_by_tab_name(self, tab_name: str) -> Optional[str]:
        for i in range(self._tab_bar.count()):
            if self._tab_bar.tabText(i) == tab_name:
                return self._get_route_key_by_index(i)
        return None
    
    def close_all_tabs(self):
        keys_to_remove = list(self._tabs.keys())
        for route_key in keys_to_remove:
            tab_content = self._tabs[route_key]
            self._stacked_widget.removeWidget(tab_content)
            tab_content.deleteLater()
        self._tabs.clear()
        self._tab_bar.clear()
        self._tab_counter = 0
        self.add_new_tab()
    
    def get_local_group_manager(self):
        current_tab = self._get_current_tab()
        if current_tab:
            return current_tab._local_group_manager
        return None
    
    def get_all_local_groups(self):
        result = {}
        for route_key, tab_content in self._tabs.items():
            tab_name = self._tab_bar.tabText(list(self._tabs.keys()).index(route_key)) if route_key in self._tabs else ""
            if hasattr(tab_content, '_local_group_manager'):
                groups_dict = tab_content._local_group_manager.to_dict()
                if groups_dict:
                    result[tab_name] = groups_dict
        return result
    
    def refresh_groups(self):
        current_tab = self._get_current_tab()
        if current_tab and hasattr(current_tab, '_refresh_groups'):
            current_tab._refresh_groups()


class SaveGroupDialog(MessageBoxBase):
    def __init__(self, parent=None, name: str = "", description: str = ""):
        super().__init__(parent)
        
        title_label = SubtitleLabel("动作组信息")
        self.viewLayout.addWidget(title_label)
        
        self.name_label = BodyLabel("名称")
        self.viewLayout.addWidget(self.name_label)
        
        self._name_edit = LineEdit()
        self._name_edit.setPlaceholderText("输入动作组名称")
        self._name_edit.setMinimumHeight(36)
        self.viewLayout.addWidget(self._name_edit)
        
        self.desc_label = BodyLabel("描述")
        self.viewLayout.addWidget(self.desc_label)
        
        self._desc_edit = LineEdit()
        self._desc_edit.setPlaceholderText("可选，描述动作组用途")
        self._desc_edit.setMinimumHeight(36)
        self.viewLayout.addWidget(self._desc_edit)
        
        self.yesButton.setText("保存")
        self.cancelButton.setText("取消")
        
        self.widget.setMinimumWidth(400)
        
        if name:
            self._name_edit.setText(name)
        if description:
            self._desc_edit.setText(description)
    
    def get_name(self) -> str:
        return self._name_edit.text().strip()
    
    def get_description(self) -> str:
        return self._desc_edit.text().strip()


class ActionGroupEditDialog(MessageBoxBase):
    action_selected = pyqtSignal(object)
    
    def __init__(self, parent=None, group: ActionGroup = None, window_offset=None):
        super().__init__(parent)
        self._group = group
        self._edited_actions: List[ScriptAction] = []
        self._selected_index: int = -1
        self._clipboard: List[ScriptAction] = []
        self._window_offset = window_offset
        
        self.widget.setMinimumWidth(800)
        self.widget.setMinimumHeight(600)
        
        title_label = SubtitleLabel(f"编辑动作组: {group.name if group else '新动作组'}")
        self.viewLayout.addWidget(title_label)
        
        info_layout = QHBoxLayout()
        name_label = BodyLabel("名称:")
        self._name_edit = LineEdit()
        self._name_edit.setText(group.name if group else "")
        self._name_edit.setMinimumHeight(36)
        info_layout.addWidget(name_label)
        info_layout.addWidget(self._name_edit)
        self.viewLayout.addLayout(info_layout)
        
        desc_layout = QHBoxLayout()
        desc_label = BodyLabel("描述:")
        self._desc_edit = LineEdit()
        self._desc_edit.setText(group.description if group else "")
        self._desc_edit.setMinimumHeight(36)
        desc_layout.addWidget(desc_label)
        desc_layout.addWidget(self._desc_edit)
        self.viewLayout.addLayout(desc_layout)
        
        self.viewLayout.addWidget(BodyLabel("动作列表:"))
        
        self._action_list = ListWidget()
        self._action_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._action_list.setDragDropMode(QAbstractItemView.InternalMove)
        self._action_list.setMinimumHeight(300)
        self._action_list.currentRowChanged.connect(self._on_selection_changed)
        self._action_list.model().rowsMoved.connect(self._on_rows_moved)
        self._action_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._action_list.customContextMenuRequested.connect(self._show_context_menu)
        self._action_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.viewLayout.addWidget(self._action_list)
        
        btn_layout = QHBoxLayout()
        
        self._add_btn = PushButton("添加动作")
        self._add_btn.setMinimumHeight(36)
        self._add_btn.clicked.connect(self._add_action)
        btn_layout.addWidget(self._add_btn)
        
        btn_layout.addStretch()
        
        self._up_btn = TransparentToolButton(FluentIcon.UP, self)
        self._up_btn.setToolTip("上移 (Ctrl+Up)")
        self._up_btn.clicked.connect(self._move_up)
        btn_layout.addWidget(self._up_btn)
        
        self._down_btn = TransparentToolButton(FluentIcon.DOWN, self)
        self._down_btn.setToolTip("下移 (Ctrl+Down)")
        self._down_btn.clicked.connect(self._move_down)
        btn_layout.addWidget(self._down_btn)
        
        btn_layout.addStretch()
        
        self._copy_btn = TransparentToolButton(FluentIcon.COPY, self)
        self._copy_btn.setToolTip("复制 (Ctrl+C)")
        self._copy_btn.clicked.connect(self._copy_selected)
        btn_layout.addWidget(self._copy_btn)
        
        self._paste_btn = TransparentToolButton(FluentIcon.PASTE, self)
        self._paste_btn.setToolTip("粘贴 (Ctrl+V)")
        self._paste_btn.clicked.connect(self._paste_actions)
        btn_layout.addWidget(self._paste_btn)
        
        self._delete_btn = TransparentToolButton(FluentIcon.DELETE, self)
        self._delete_btn.setToolTip("删除 (Delete)")
        self._delete_btn.clicked.connect(self._delete_selected)
        btn_layout.addWidget(self._delete_btn)
        
        self.viewLayout.addLayout(btn_layout)
        
        self.yesButton.setText("保存")
        self.cancelButton.setText("取消")
        
        if group:
            self._edited_actions = [copy.deepcopy(a) for a in group.actions]
            self._refresh_list()
    
    def _on_selection_changed(self, row: int):
        self._selected_index = row
        if 0 <= row < len(self._edited_actions):
            self.action_selected.emit(self._edited_actions[row])
    
    def _on_rows_moved(self):
        new_actions = []
        for i in range(self._action_list.count()):
            item = self._action_list.item(i)
            old_index = item.data(Qt.UserRole)
            if old_index is not None and 0 <= old_index < len(self._edited_actions):
                new_actions.append(self._edited_actions[old_index])
        self._edited_actions = new_actions
        self._refresh_list()
    
    def _on_item_double_clicked(self, item):
        row = self._action_list.row(item)
        if 0 <= row < len(self._edited_actions):
            self._edit_action(row)
    
    def _refresh_list(self):
        self._action_list.clear()
        for i, action in enumerate(self._edited_actions):
            item = QListWidgetItem(self._action_list)
            widget = ActionItemWidget(action, i)
            widget.delete_requested.connect(lambda checked=False, idx=i: self._delete_action_at(idx))
            item.setSizeHint(widget.sizeHint())
            self._action_list.setItemWidget(item, widget)
            item.setData(Qt.UserRole, i)
    
    def _add_action(self):
        from core.actions import ActionType
        
        action_types = [
            (ActionType.MOUSE_CLICK, "鼠标单击"),
            (ActionType.MOUSE_DOUBLE_CLICK, "鼠标双击"),
            (ActionType.MOUSE_RIGHT_CLICK, "鼠标右键"),
            (ActionType.MOUSE_MOVE, "鼠标移动"),
            (ActionType.MOUSE_DRAG, "鼠标拖拽"),
            (ActionType.MOUSE_SCROLL, "鼠标滚轮"),
            (ActionType.KEY_PRESS, "按键"),
            (ActionType.KEY_TYPE, "输入文本"),
            (ActionType.HOTKEY, "快捷键"),
            (ActionType.WAIT, "等待"),
            (ActionType.SCREENSHOT, "截图"),
            (ActionType.IMAGE_CLICK, "图片点击"),
            (ActionType.IMAGE_WAIT_CLICK, "等待图片点击"),
            (ActionType.IMAGE_CHECK, "图片检查"),
        ]
        
        menu = RoundMenu("选择动作类型", self)
        menu.setIcon(FluentIcon.ADD)
        
        for action_type, display_name in action_types:
            act = Action(FluentIcon.PLAY, display_name)
            act.triggered.connect(lambda checked=False, at=action_type: self._create_action(at))
            menu.addAction(act)
        
        menu.exec_(self._add_btn.mapToGlobal(self._add_btn.rect().bottomLeft()))
    
    def _create_action(self, action_type):
        from core.actions import ActionType
        
        default_params = {}
        if action_type == ActionType.MOUSE_CLICK:
            default_params = {'x': 0, 'y': 0}
        elif action_type == ActionType.WAIT:
            default_params = {'seconds': 1.0}
        elif action_type == ActionType.KEY_TYPE:
            default_params = {'text': ''}
        elif action_type == ActionType.HOTKEY:
            default_params = {'keys': []}
        
        action = ScriptAction(action_type, default_params)
        self._edited_actions.append(action)
        self._refresh_list()
        self._action_list.setCurrentRow(len(self._edited_actions) - 1)
    
    def _edit_action(self, index: int):
        if not (0 <= index < len(self._edited_actions)):
            return
        
        action = self._edited_actions[index]
        
        from .property_panel import PropertyPanel
        from qfluentwidgets import MessageBoxBase, SubtitleLabel
        
        class QuickEditDialog(MessageBoxBase):
            def __init__(self, parent, action, window_offset=None):
                super().__init__(parent)
                self._action = action
                
                self.widget.setMinimumWidth(500)
                self.widget.setMinimumHeight(400)
                
                title = SubtitleLabel(f"编辑动作: {action.description[:30]}...")
                self.viewLayout.addWidget(title)
                
                self._panel = PropertyPanel(self)
                self._panel.set_window_offset(window_offset)
                self._panel.set_action(action)
                self.viewLayout.addWidget(self._panel)
                
                self.yesButton.setText("确定")
                self.cancelButton.setText("取消")
            
            def get_action(self):
                return self._action
        
        dialog = QuickEditDialog(self, action, self._window_offset)
        if dialog.exec_():
            self._refresh_list()
            self._action_list.setCurrentRow(index)
    
    def _delete_action_at(self, index: int):
        if 0 <= index < len(self._edited_actions):
            del self._edited_actions[index]
            self._refresh_list()
    
    def _move_up(self):
        selected_rows = sorted([self._action_list.row(item) for item in self._action_list.selectedItems()])
        if not selected_rows or selected_rows[0] == 0:
            return
        
        for row in selected_rows:
            if row > 0:
                self._edited_actions[row], self._edited_actions[row - 1] = \
                    self._edited_actions[row - 1], self._edited_actions[row]
        
        self._refresh_list()
        for row in selected_rows:
            self._action_list.setCurrentRow(row - 1)
    
    def _move_down(self):
        selected_rows = sorted([self._action_list.row(item) for item in self._action_list.selectedItems()], reverse=True)
        if not selected_rows or selected_rows[0] == len(self._edited_actions) - 1:
            return
        
        for row in selected_rows:
            if row < len(self._edited_actions) - 1:
                self._edited_actions[row], self._edited_actions[row + 1] = \
                    self._edited_actions[row + 1], self._edited_actions[row]
        
        self._refresh_list()
        for row in selected_rows:
            self._action_list.setCurrentRow(row + 1)
    
    def _delete_selected(self):
        selected_rows = sorted([self._action_list.row(item) for item in self._action_list.selectedItems()], reverse=True)
        for row in selected_rows:
            if 0 <= row < len(self._edited_actions):
                del self._edited_actions[row]
        self._refresh_list()
    
    def _copy_selected(self):
        selected_rows = sorted([self._action_list.row(item) for item in self._action_list.selectedItems()])
        self._clipboard = [copy.deepcopy(self._edited_actions[row]) for row in selected_rows if 0 <= row < len(self._edited_actions)]
    
    def _paste_actions(self):
        if not self._clipboard:
            return
        
        current_row = self._action_list.currentRow()
        insert_index = current_row + 1 if current_row >= 0 else len(self._edited_actions)
        
        for i, action in enumerate(self._clipboard):
            self._edited_actions.insert(insert_index + i, copy.deepcopy(action))
        
        self._refresh_list()
    
    def _duplicate_selected(self):
        selected_rows = sorted([self._action_list.row(item) for item in self._action_list.selectedItems()], reverse=True)
        for row in selected_rows:
            if 0 <= row < len(self._edited_actions):
                new_action = copy.deepcopy(self._edited_actions[row])
                self._edited_actions.insert(row + 1, new_action)
        self._refresh_list()
    
    def _show_context_menu(self, pos):
        item = self._action_list.itemAt(pos)
        
        menu = RoundMenu(parent=self)
        
        selected_rows = sorted([self._action_list.row(item) for item in self._action_list.selectedItems()])
        
        if item:
            index = self._action_list.row(item)
            
            menu.addAction(Action(FluentIcon.EDIT, "编辑", triggered=lambda: self._edit_action(index)))
            menu.addSeparator()
            menu.addAction(Action(FluentIcon.DELETE, "删除选中", triggered=lambda: self._delete_selected()))
            menu.addAction(Action(FluentIcon.COPY, "复制选中", triggered=lambda: self._copy_selected()))
            menu.addAction(Action(FluentIcon.COPY, "复制并粘贴", triggered=lambda: self._duplicate_selected()))
            
            if self._clipboard:
                menu.addAction(Action(FluentIcon.PASTE, f"粘贴 ({len(self._clipboard)} 个)", triggered=lambda: self._paste_actions()))
            
            menu.addSeparator()
            menu.addAction(Action(FluentIcon.UP, "上移", triggered=lambda: self._move_up()))
            menu.addAction(Action(FluentIcon.DOWN, "下移", triggered=lambda: self._move_down()))
        else:
            menu.addAction(Action(FluentIcon.ADD, "添加动作", triggered=lambda: self._add_action()))
            
            if self._clipboard:
                menu.addAction(Action(FluentIcon.PASTE, f"粘贴 ({len(self._clipboard)} 个)", triggered=lambda: self._paste_actions()))
        
        if menu.actions():
            menu.exec_(self._action_list.mapToGlobal(pos))
    
    def get_name(self) -> str:
        return self._name_edit.text().strip()
    
    def get_description(self) -> str:
        return self._desc_edit.text().strip()
    
    def get_actions(self) -> List[ScriptAction]:
        return self._edited_actions
    
    def validate(self) -> tuple:
        name = self.get_name()
        if not name:
            return False, "动作组名称不能为空"
        if len(self._edited_actions) == 0:
            return False, "动作组必须包含至少一个动作"
        
        for i, action in enumerate(self._edited_actions):
            is_valid, error_msg = action.validate()
            if not is_valid:
                return False, f"动作 {i + 1} 验证失败: {error_msg}"
        
        return True, ""
    
    def keyPressEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_C:
                self._copy_selected()
            elif event.key() == Qt.Key_V:
                self._paste_actions()
            elif event.key() == Qt.Key_Up:
                self._move_up()
            elif event.key() == Qt.Key_Down:
                self._move_down()
        elif event.key() == Qt.Key_Delete:
            self._delete_selected()
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if self._selected_index >= 0:
                self._edit_action(self._selected_index)
        else:
            super().keyPressEvent(event)


class CollapsedActionGroupWidget(CardWidget):
    expand_requested = pyqtSignal()
    edit_actions_requested = pyqtSignal()
    delete_requested = pyqtSignal()
    
    def __init__(self, group_name: str, action_count: int, actions: List[ScriptAction] = None, parent=None):
        super().__init__(parent)
        self._group_name = group_name
        self._action_count = action_count
        self._actions = actions or []
        self._is_expanded = False
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        
        header_layout = QHBoxLayout()
        
        self._icon_label = BodyLabel("📁")
        self._icon_label.setFixedWidth(20)
        header_layout.addWidget(self._icon_label)
        
        self._name_label = StrongBodyLabel(self._group_name)
        header_layout.addWidget(self._name_label)
        
        self._count_label = BodyLabel(f"({self._action_count} 个动作)")
        self._count_label.setStyleSheet("color: #888;")
        header_layout.addWidget(self._count_label)
        
        header_layout.addStretch()
        
        self._expand_btn = TransparentToolButton(FluentIcon.CHEVRON_RIGHT_MED, self)
        self._expand_btn.setFixedSize(24, 24)
        self._expand_btn.setToolTip("展开/折叠")
        self._expand_btn.clicked.connect(self._toggle_expand)
        header_layout.addWidget(self._expand_btn)
        
        self._edit_btn = TransparentToolButton(FluentIcon.EDIT, self)
        self._edit_btn.setToolTip("编辑动作组内容")
        self._edit_btn.clicked.connect(self.edit_actions_requested.emit)
        header_layout.addWidget(self._edit_btn)
        
        self._delete_btn = TransparentToolButton(FluentIcon.DELETE, self)
        self._delete_btn.setToolTip("删除动作组")
        self._delete_btn.clicked.connect(self.delete_requested.emit)
        header_layout.addWidget(self._delete_btn)
        
        layout.addLayout(header_layout)
        
        self._actions_container = QWidget()
        self._actions_layout = QVBoxLayout(self._actions_container)
        self._actions_layout.setContentsMargins(24, 4, 4, 4)
        self._actions_layout.setSpacing(2)
        self._actions_container.hide()
        layout.addWidget(self._actions_container)
        
        self._populate_actions()
        
        self.setStyleSheet("""
            CollapsedActionGroupWidget {
                background-color: rgba(76, 175, 80, 0.1);
                border: 1px solid rgba(76, 175, 80, 0.3);
                border-radius: 6px;
            }
            CollapsedActionGroupWidget:hover {
                background-color: rgba(76, 175, 80, 0.15);
                border: 1px solid rgba(76, 175, 80, 0.5);
            }
        """)
    
    def _toggle_expand(self):
        self._is_expanded = not self._is_expanded
        self._actions_container.setVisible(self._is_expanded)
        
        if self._is_expanded:
            self._expand_btn.setIcon(FluentIcon.CHEVRON_DOWN_MED)
        else:
            self._expand_btn.setIcon(FluentIcon.CHEVRON_RIGHT_MED)
    
    def _populate_actions(self):
        while self._actions_layout.count():
            item = self._actions_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        for i, action in enumerate(self._actions):
            action_label = BodyLabel(f"  {i + 1}. {action.description}")
            action_label.setWordWrap(True)
            self._actions_layout.addWidget(action_label)
    
    def get_group_name(self) -> str:
        return self._group_name
    
    def update_actions(self, actions: List[ScriptAction]):
        self._actions = actions
        self._action_count = len(actions)
        self._count_label.setText(f"({self._action_count} 个动作)")
        self._populate_actions()
