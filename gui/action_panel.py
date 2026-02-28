from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTreeWidgetItem
from PyQt5.QtCore import Qt, pyqtSignal
from core.actions import Action, ActionType, ActionManager

from qfluentwidgets import (
    TreeWidget, StrongBodyLabel, BodyLabel,
    PushButton, CardWidget
)


class ActionPanel(CardWidget):
    action_added = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._load_actions()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        header_layout = QHBoxLayout()
        header = StrongBodyLabel("动作列表")
        header_layout.addWidget(header)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        self._action_tree = TreeWidget()
        self._action_tree.setHeaderHidden(True)
        self._action_tree.setBorderVisible(True)
        self._action_tree.setBorderRadius(8)
        self._action_tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._action_tree)
        
        tip_label = BodyLabel("双击动作添加到脚本")
        tip_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(tip_label)
    
    def _load_actions(self):
        categories = ActionManager.get_all_categories()
        
        category_icons = {
            '鼠标操作': '🖱',
            '键盘操作': '⌨',
            '控制': '⚙',
            '其他': '📷',
            '窗口操作': '🪟',
            '图像识别': '🖼',
        }
        
        for category, action_types in categories.items():
            category_item = QTreeWidgetItem(self._action_tree)
            category_item.setText(0, f"{category_icons.get(category, '📁')} {category}")
            category_item.setExpanded(True)
            
            for action_type in action_types:
                definition = ActionManager.get_action_definition(action_type)
                action_item = QTreeWidgetItem(category_item)
                action_item.setText(0, f"    {definition.get('name', str(action_type))}")
                action_item.setData(0, Qt.UserRole, action_type)
    
    def _on_item_double_clicked(self, item, column):
        action_type = item.data(0, Qt.UserRole)
        if action_type and isinstance(action_type, ActionType):
            default_params = ActionManager.get_default_params(action_type)
            action = Action(action_type=action_type, params=default_params)
            self.action_added.emit(action)
