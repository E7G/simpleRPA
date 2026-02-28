import os
import json
import copy
import base64
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from .actions import Action


@dataclass
class ActionGroup:
    name: str
    description: str = ""
    actions: List[Action] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'actions': [action.to_dict() for action in self.actions]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionGroup':
        return cls(
            name=data.get('name', '未命名'),
            description=data.get('description', ''),
            actions=[Action.from_dict(a) for a in data.get('actions', [])]
        )
    
    def get_action_count(self) -> int:
        return len(self.actions)
    
    def validate(self) -> Tuple[bool, str]:
        if not self.name or not self.name.strip():
            return False, "动作组名称不能为空"
        
        if len(self.actions) == 0:
            return False, "动作组必须包含至少一个动作"
        
        for i, action in enumerate(self.actions):
            is_valid, error_msg = action.validate()
            if not is_valid:
                return False, f"动作 {i + 1} 验证失败: {error_msg}"
        
        return True, ""
    
    def validate_dependencies(self) -> Tuple[bool, List[str]]:
        missing_deps = []
        for action in self.actions:
            from .actions import ActionType
            if action.action_type == ActionType.ACTION_GROUP_REF:
                group_name = action.params.get('group_name', '')
                if group_name:
                    missing_deps.append(group_name)
        return len(missing_deps) == 0, missing_deps


class LocalActionGroupManager:
    def __init__(self):
        self._groups: Dict[str, ActionGroup] = {}
    
    def get_all_groups(self) -> List[ActionGroup]:
        seen_names = set()
        unique_groups = []
        for group in self._groups.values():
            if group.name not in seen_names:
                seen_names.add(group.name)
                unique_groups.append(group)
        return unique_groups
    
    def get_group(self, name: str) -> Optional[ActionGroup]:
        return self._groups.get(name)
    
    def has_group(self, name: str) -> bool:
        return name in self._groups
    
    def save_group(self, group: ActionGroup) -> bool:
        is_valid, error_msg = group.validate()
        if not is_valid:
            print(f"动作组验证失败: {error_msg}")
            return False
        self._groups[group.name] = group
        return True
    
    def delete_group(self, name: str) -> bool:
        if name not in self._groups:
            return False
        del self._groups[name]
        return True
    
    def create_group_from_actions(self, name: str, description: str, actions: List[Action]) -> ActionGroup:
        group = ActionGroup(
            name=name,
            description=description,
            actions=[copy.deepcopy(a) for a in actions]
        )
        return group
    
    def get_actions_copy(self, name: str) -> List[Action]:
        group = self.get_group(name)
        if group:
            return [copy.deepcopy(a) for a in group.actions]
        return []
    
    def to_dict(self) -> Dict[str, Any]:
        return {name: group.to_dict() for name, group in self._groups.items()}
    
    def load_from_dict(self, data: Dict[str, Any]) -> Tuple[int, int]:
        self._groups.clear()
        success_count = 0
        fail_count = 0
        for name, group_data in data.items():
            try:
                group = ActionGroup.from_dict(group_data)
                is_valid, error_msg = group.validate()
                if is_valid:
                    self._groups[name] = group
                    success_count += 1
                else:
                    print(f"动作组 '{name}' 验证失败: {error_msg}")
                    fail_count += 1
            except Exception as e:
                print(f"加载动作组 '{name}' 失败: {e}")
                fail_count += 1
        return success_count, fail_count
    
    def clear(self):
        self._groups.clear()
    
    def ensure_group_available(self, name: str, global_manager: 'GlobalActionGroupManager' = None) -> Optional[ActionGroup]:
        group = self.get_group(name)
        if group:
            return group
        
        if global_manager:
            global_group = global_manager.get_group(name)
            if global_group:
                self._groups[name] = copy.deepcopy(global_group)
                return self._groups[name]
        
        return None


class GlobalActionGroupManager:
    _instance = None
    
    def __init__(self):
        self._groups: Dict[str, ActionGroup] = {}
        self._groups_dir = os.path.join(os.path.expanduser('~'), '.simpleRPA', 'groups')
        os.makedirs(self._groups_dir, exist_ok=True)
        self._load_all_groups()
    
    @classmethod
    def get_instance(cls) -> 'GlobalActionGroupManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        cls._instance = None
    
    def _load_all_groups(self) -> Tuple[int, int]:
        if not os.path.exists(self._groups_dir):
            return 0, 0
        
        success_count = 0
        fail_count = 0
        
        for filename in os.listdir(self._groups_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self._groups_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    group = ActionGroup.from_dict(data)
                    is_valid, error_msg = group.validate()
                    if is_valid:
                        self._groups[group.name] = group
                        success_count += 1
                    else:
                        print(f"全局动作组 '{group.name}' 验证失败: {error_msg}")
                        fail_count += 1
                except Exception as e:
                    print(f"加载全局动作组失败 {filename}: {e}")
                    fail_count += 1
        
        return success_count, fail_count
    
    def reload_groups(self) -> Tuple[int, int]:
        self._groups.clear()
        return self._load_all_groups()
    
    def get_all_groups(self) -> List[ActionGroup]:
        seen_names = set()
        unique_groups = []
        for group in self._groups.values():
            if group.name not in seen_names:
                seen_names.add(group.name)
                unique_groups.append(group)
        return unique_groups
    
    def get_group(self, name: str) -> Optional[ActionGroup]:
        return self._groups.get(name)
    
    def has_group(self, name: str) -> bool:
        return name in self._groups
    
    def save_group(self, group: ActionGroup) -> bool:
        is_valid, error_msg = group.validate()
        if not is_valid:
            print(f"动作组验证失败: {error_msg}")
            return False
        
        try:
            self._groups[group.name] = group
            
            filepath = os.path.join(self._groups_dir, f"{group.name}.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(group.to_dict(), f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"保存全局动作组失败: {e}")
            return False
    
    def delete_group(self, name: str) -> bool:
        if name not in self._groups:
            return False
        
        try:
            del self._groups[name]
            
            filepath = os.path.join(self._groups_dir, f"{name}.json")
            if os.path.exists(filepath):
                os.remove(filepath)
            
            return True
        except Exception as e:
            print(f"删除全局动作组失败: {e}")
            return False
    
    def create_group_from_actions(self, name: str, description: str, actions: List[Action]) -> ActionGroup:
        group = ActionGroup(
            name=name,
            description=description,
            actions=[copy.deepcopy(a) for a in actions]
        )
        return group
    
    def get_actions_copy(self, name: str) -> List[Action]:
        group = self.get_group(name)
        if group:
            return [copy.deepcopy(a) for a in group.actions]
        return []
    
    def ensure_group_loaded(self, name: str) -> Optional[ActionGroup]:
        group = self.get_group(name)
        if group:
            return group
        
        filepath = os.path.join(self._groups_dir, f"{name}.json")
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                group = ActionGroup.from_dict(data)
                is_valid, error_msg = group.validate()
                if is_valid:
                    self._groups[group.name] = group
                    return group
                else:
                    print(f"动作组 '{name}' 验证失败: {error_msg}")
            except Exception as e:
                print(f"加载动作组 '{name}' 失败: {e}")
        
        return None
    
    def import_group_from_dict(self, data: Dict[str, Any], overwrite: bool = False) -> Tuple[bool, str]:
        try:
            group = ActionGroup.from_dict(data)
            is_valid, error_msg = group.validate()
            if not is_valid:
                return False, f"验证失败: {error_msg}"
            
            if not overwrite and self.has_group(group.name):
                return False, f"动作组 '{group.name}' 已存在"
            
            if self.save_group(group):
                return True, f"动作组 '{group.name}' 导入成功"
            else:
                return False, "保存失败"
        except Exception as e:
            return False, f"导入失败: {e}"


def encode_image_to_base64(image_path: str) -> Optional[str]:
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
        return base64.b64encode(image_data).decode('utf-8')
    except Exception as e:
        print(f"编码图片失败: {e}")
        return None


def decode_base64_to_image(base64_data: str, output_path: str) -> bool:
    try:
        image_data = base64.b64decode(base64_data)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(image_data)
        return True
    except Exception as e:
        print(f"解码图片失败: {e}")
        return False


def ensure_action_group_available(group_name: str, local_manager: LocalActionGroupManager = None) -> Optional[ActionGroup]:
    global_manager = GlobalActionGroupManager.get_instance()
    
    if local_manager:
        group = local_manager.get_group(group_name)
        if group:
            return group
    
    group = global_manager.get_group(group_name)
    if group:
        if local_manager:
            local_manager._groups[group_name] = copy.deepcopy(group)
        return group
    
    group = global_manager.ensure_group_loaded(group_name)
    if group and local_manager:
        local_manager._groups[group_name] = copy.deepcopy(group)
    
    return group
