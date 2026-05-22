from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTreeWidgetItem, QSizePolicy
from PyQt5.QtCore import Qt, pyqtSignal
from core.actions import Action, ActionType, ActionManager

from qfluentwidgets import (
    TreeWidget, BodyLabel, SearchLineEdit, CaptionLabel,
)

class ActionPanel(QWidget):
    action_added = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._load_actions()
    
    def _setup_ui(self):
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        self._search = SearchLineEdit()
        self._search.setPlaceholderText("搜索操作...")
        self._search.textChanged.connect(self._filter_actions)
        layout.addWidget(self._search)
        
        self._action_tree = TreeWidget()
        self._action_tree.setHeaderHidden(True)
        self._action_tree.setBorderVisible(True)
        self._action_tree.setBorderRadius(4)
        self._action_tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._action_tree, 1)
        
        tip = CaptionLabel("双击添加到流程")
        tip.setAlignment(Qt.AlignCenter)
        layout.addWidget(tip)
    
    def _load_actions(self):
        self._categories = ActionManager.get_all_categories()
        self._category_icons = {
            '鼠标操作': '🖱',
            '键盘操作': '⌨',
            '控制': '⚙',
            '其他': '📷',
            '窗口操作': '🪟',
            '图像识别': '🖼',
        }
        self._rebuild_tree()
    
    def _rebuild_tree(self, filter_text: str = ""):
        self._action_tree.clear()
        ft = filter_text.strip().lower()
        
        for category, action_types in self._categories.items():
            cat_label = f"{self._category_icons.get(category, '📁')} {category}"
            if ft and ft not in cat_label.lower():
                matched_types = []
                for action_type in action_types:
                    definition = ActionManager.get_action_definition(action_type)
                    name = definition.get('name', str(action_type))
                    if ft in name.lower() or ft in category.lower():
                        matched_types.append(action_type)
                if not matched_types:
                    continue
                action_types = matched_types
            
            category_item = QTreeWidgetItem(self._action_tree)
            category_item.setText(0, cat_label)
            category_item.setExpanded(True)
            
            for action_type in action_types:
                definition = ActionManager.get_action_definition(action_type)
                name = definition.get('name', str(action_type))
                if ft and ft not in name.lower() and ft not in category.lower():
                    continue
                action_item = QTreeWidgetItem(category_item)
                action_item.setText(0, f"  {name}")
                action_item.setData(0, Qt.UserRole, action_type)
    
    def _filter_actions(self, text: str):
        self._rebuild_tree(text)
    
    def _on_item_double_clicked(self, item, column):
        action_type = item.data(0, Qt.UserRole)
        if action_type and isinstance(action_type, ActionType):
            default_params = ActionManager.get_default_params(action_type)
            action = Action(action_type=action_type, params=default_params)
            self.action_added.emit(action)
