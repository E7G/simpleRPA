import pyautogui
import time
import os
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Callable
import json


class ActionType(Enum):
    MOUSE_CLICK = "mouse_click"
    MOUSE_DOUBLE_CLICK = "mouse_double_click"
    MOUSE_RIGHT_CLICK = "mouse_right_click"
    MOUSE_MOVE = "mouse_move"
    MOUSE_DRAG = "mouse_drag"
    MOUSE_SCROLL = "mouse_scroll"
    KEY_PRESS = "key_press"
    KEY_TYPE = "key_type"
    HOTKEY = "hotkey"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    MOUSE_MOVE_RELATIVE = "mouse_move_relative"
    MOUSE_CLICK_RELATIVE = "mouse_click_relative"
    IMAGE_CLICK = "image_click"
    IMAGE_WAIT_CLICK = "image_wait_click"
    IMAGE_CHECK = "image_check"
    ACTION_GROUP_REF = "action_group_ref"


class VariableManager:
    _instance = None
    
    def __init__(self):
        self._variables: Dict[str, Any] = {}
    
    @classmethod
    def get_instance(cls) -> 'VariableManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def set(self, name: str, value: Any):
        self._variables[name] = value
    
    def get(self, name: str, default: Any = None) -> Any:
        return self._variables.get(name, default)
    
    def has(self, name: str) -> bool:
        return name in self._variables
    
    def clear(self):
        self._variables.clear()
    
    def get_all(self) -> Dict[str, Any]:
        return self._variables.copy()


@dataclass
class Action:
    action_type: ActionType
    params: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    delay_before: float = 0.0
    delay_after: float = 0.0
    window_title: Optional[str] = None
    use_relative_coords: bool = False
    background_mode: bool = False
    name: str = ""
    condition: str = ""
    repeat_count: int = 1
    
    def __post_init__(self):
        if not self.description:
            self.description = self._generate_description()
    
    @property
    def condition_marker(self) -> str:
        if self.action_type == ActionType.IMAGE_CHECK:
            image_name = os.path.basename(self.params.get('image_path', ''))
            if image_name:
                name_without_ext = os.path.splitext(image_name)[0]
                safe_name = name_without_ext.replace(' ', '_').replace('-', '_')
                return f"${safe_name}"
        return ""
    
    def _generate_description(self) -> str:
        name_prefix = f"[{self.name}] " if self.name else ""
        delay_prefix = f"[等待{self.delay_before:.2f}秒] " if self.delay_before > 0.05 else ""
        repeat_suffix = f" (x{self.repeat_count})" if self.repeat_count > 1 else ""
        bg_suffix = " [后台]" if self.background_mode else ""
        desc_map = {
            ActionType.MOUSE_CLICK: f"鼠标单击 ({self.params.get('x', 0)}, {self.params.get('y', 0)})",
            ActionType.MOUSE_DOUBLE_CLICK: f"鼠标双击 ({self.params.get('x', 0)}, {self.params.get('y', 0)})",
            ActionType.MOUSE_RIGHT_CLICK: f"鼠标右键 ({self.params.get('x', 0)}, {self.params.get('y', 0)})",
            ActionType.MOUSE_MOVE: f"鼠标移动至 ({self.params.get('x', 0)}, {self.params.get('y', 0)})",
            ActionType.MOUSE_DRAG: f"鼠标拖拽 ({self.params.get('start_x', 0)}, {self.params.get('start_y', 0)}) → ({self.params.get('end_x', 0)}, {self.params.get('end_y', 0)})",
            ActionType.MOUSE_SCROLL: f"鼠标滚轮 {self.params.get('clicks', 0)} 格",
            ActionType.KEY_PRESS: f"按键: {self.params.get('key', '')}",
            ActionType.KEY_TYPE: f"输入文本: {self.params.get('text', '')}",
            ActionType.HOTKEY: f"快捷键: {'+'.join(self.params.get('keys', []))}",
            ActionType.WAIT: f"等待 {self.params.get('seconds', 0)} 秒",
            ActionType.SCREENSHOT: f"截图: {self.params.get('filename', 'screenshot.png')}",
            ActionType.MOUSE_MOVE_RELATIVE: f"窗口内移动至 ({self.params.get('x', 0)}, {self.params.get('y', 0)})",
            ActionType.MOUSE_CLICK_RELATIVE: f"窗口内点击 ({self.params.get('x', 0)}, {self.params.get('y', 0)})",
            ActionType.IMAGE_CLICK: f"图片点击: {os.path.basename(self.params.get('image_path', ''))}",
            ActionType.IMAGE_WAIT_CLICK: f"等待图片点击: {os.path.basename(self.params.get('image_path', ''))}",
            ActionType.IMAGE_CHECK: f"检查图片: {os.path.basename(self.params.get('image_path', ''))}",
            ActionType.ACTION_GROUP_REF: f"📁 动作组引用: {self.params.get('group_name', '未知')}",
        }
        return name_prefix + delay_prefix + desc_map.get(self.action_type, "未知动作") + bg_suffix + repeat_suffix
    
    def execute(self, window_offset: Optional[Tuple[int, int]] = None, should_stop: Optional[Callable[[], bool]] = None, local_group_manager=None) -> bool:
        repeat = max(1, self.repeat_count)
        for i in range(repeat):
            if should_stop and should_stop():
                return False
            if i > 0:
                time.sleep(0.1)
            result = self._execute_once(window_offset, should_stop, local_group_manager)
            if not result:
                return False
        return True
    
    def _activate_window_for_image(self):
        if not self.window_title:
            return
        try:
            import win32gui
            import win32con
            
            def enum_callback(hwnd, result):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if self.window_title.lower() in title.lower():
                        result.append(hwnd)
                return True
            
            windows = []
            win32gui.EnumWindows(enum_callback, windows)
            
            if windows:
                hwnd = windows[0]
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.1)
        except Exception as e:
            print(f"[激活窗口失败] {e}")
    
    def _execute_once(self, window_offset: Optional[Tuple[int, int]] = None, should_stop: Optional[Callable[[], bool]] = None, local_group_manager=None) -> bool:
        if self.delay_before > 0:
            end_time = time.time() + self.delay_before
            while time.time() < end_time:
                if should_stop and should_stop():
                    return False
                sleep_time = min(0.05, end_time - time.time())
                if sleep_time > 0:
                    time.sleep(sleep_time)
        
        if should_stop and should_stop():
            return False
        
        if window_offset and self.use_relative_coords:
            x = self.params.get('x', 0) + window_offset[0]
            y = self.params.get('y', 0) + window_offset[1]
        else:
            x = self.params.get('x')
            y = self.params.get('y')
        
        try:
            if self.action_type == ActionType.MOUSE_CLICK:
                button = self.params.get('button', 'left')
                clicks = self.params.get('clicks', 1)
                if x is not None and y is not None:
                    pyautogui.click(x=x, y=y, button=button, clicks=clicks)
                else:
                    pyautogui.click(button=button, clicks=clicks)
            
            elif self.action_type == ActionType.MOUSE_DOUBLE_CLICK:
                if x is not None and y is not None:
                    pyautogui.doubleClick(x=x, y=y)
                else:
                    pyautogui.doubleClick()
            
            elif self.action_type == ActionType.MOUSE_RIGHT_CLICK:
                if x is not None and y is not None:
                    pyautogui.rightClick(x=x, y=y)
                else:
                    pyautogui.rightClick()
            
            elif self.action_type == ActionType.MOUSE_MOVE:
                pyautogui.moveTo(x=x, y=y, duration=self.params.get('duration', 0.0))
            
            elif self.action_type == ActionType.MOUSE_DRAG:
                start_x = self.params.get('start_x', 0)
                start_y = self.params.get('start_y', 0)
                end_x = self.params.get('end_x', 0)
                end_y = self.params.get('end_y', 0)
                if window_offset:
                    start_x += window_offset[0]
                    start_y += window_offset[1]
                    end_x += window_offset[0]
                    end_y += window_offset[1]
                pyautogui.moveTo(start_x, start_y)
                pyautogui.drag(end_x - start_x, end_y - start_y, duration=self.params.get('duration', 0.5))
            
            elif self.action_type == ActionType.MOUSE_SCROLL:
                pyautogui.scroll(self.params.get('clicks', 0), x=x, y=y)
            
            elif self.action_type == ActionType.KEY_PRESS:
                pyautogui.press(self.params.get('key', ''))
            
            elif self.action_type == ActionType.KEY_TYPE:
                pyautogui.typewrite(self.params.get('text', ''), interval=self.params.get('interval', 0.0))
            
            elif self.action_type == ActionType.HOTKEY:
                keys = self.params.get('keys', [])
                if keys:
                    pyautogui.hotkey(*keys)
            
            elif self.action_type == ActionType.WAIT:
                time.sleep(self.params.get('seconds', 1.0))
            
            elif self.action_type == ActionType.SCREENSHOT:
                filename = self.params.get('filename', 'screenshot.png')
                region = self.params.get('region')
                pyautogui.screenshot(filename, region=region)
            
            elif self.action_type == ActionType.MOUSE_MOVE_RELATIVE:
                if window_offset:
                    x = self.params.get('x', 0) + window_offset[0]
                    y = self.params.get('y', 0) + window_offset[1]
                else:
                    x, y = self.params.get('x', 0), self.params.get('y', 0)
                
                if self.background_mode and self.window_title:
                    from utils.background_click import create_background_clicker
                    clicker = create_background_clicker(window_title=self.window_title)
                    if clicker:
                        result = clicker.move(self.params.get('x', 0), self.params.get('y', 0), background=True)
                        if not result.success:
                            pyautogui.moveTo(x=x, y=y, duration=self.params.get('duration', 0.0))
                    else:
                        pyautogui.moveTo(x=x, y=y, duration=self.params.get('duration', 0.0))
                else:
                    pyautogui.moveTo(x=x, y=y, duration=self.params.get('duration', 0.0))
            
            elif self.action_type == ActionType.MOUSE_CLICK_RELATIVE:
                if window_offset:
                    x = self.params.get('x', 0) + window_offset[0]
                    y = self.params.get('y', 0) + window_offset[1]
                else:
                    x, y = self.params.get('x', 0), self.params.get('y', 0)
                
                if self.background_mode and self.window_title:
                    from utils.background_click import create_background_clicker
                    clicker = create_background_clicker(window_title=self.window_title)
                    if clicker:
                        button = self.params.get('button', 'left')
                        result = clicker.click(self.params.get('x', 0), self.params.get('y', 0), button=button, background=True)
                        if not result.success:
                            pyautogui.click(x=x, y=y)
                    else:
                        pyautogui.click(x=x, y=y)
                else:
                    pyautogui.click(x=x, y=y)
            
            elif self.action_type == ActionType.IMAGE_CLICK:
                image_path = self.params.get('image_path', '')
                confidence = self.params.get('confidence', 0.9)
                if not image_path:
                    raise Exception("未设置图片路径，请先选择或截取图片")
                if not os.path.exists(image_path):
                    raise Exception(f"图片文件不存在: {image_path}")
                
                if not self.background_mode:
                    self._activate_window_for_image()
                
                location = None
                for attempt in range(3):
                    try:
                        location = pyautogui.locateOnScreen(image_path, confidence=confidence)
                        if location:
                            break
                    except pyautogui.ImageNotFoundException:
                        pass
                    time.sleep(0.2)
                
                if location:
                    center = pyautogui.center(location)
                    if self.background_mode and self.window_title:
                        from utils.background_click import create_background_clicker
                        clicker = create_background_clicker(window_title=self.window_title)
                        if clicker:
                            rect = clicker.rect
                            rel_x = center.x - rect[0]
                            rel_y = center.y - rect[1]
                            result = clicker.click(rel_x, rel_y, background=True)
                            if not result.success:
                                pyautogui.click(center.x, center.y)
                        else:
                            pyautogui.click(center.x, center.y)
                    else:
                        pyautogui.click(center.x, center.y)
                else:
                    raise Exception(f"屏幕上未找到匹配图片 (置信度: {confidence})")
            
            elif self.action_type == ActionType.IMAGE_WAIT_CLICK:
                image_path = self.params.get('image_path', '')
                confidence = self.params.get('confidence', 0.9)
                timeout = self.params.get('timeout', 10)
                if not image_path:
                    raise Exception("未设置图片路径，请先选择或截取图片")
                if not os.path.exists(image_path):
                    raise Exception(f"图片文件不存在: {image_path}")
                
                if not self.background_mode:
                    self._activate_window_for_image()
                
                location = None
                start_time = time.time()
                while (time.time() - start_time) < timeout:
                    if should_stop and should_stop():
                        return False
                    try:
                        location = pyautogui.locateOnScreen(image_path, confidence=confidence)
                        if location:
                            break
                    except pyautogui.ImageNotFoundException:
                        pass
                    except Exception:
                        pass
                    time.sleep(0.5)
                
                if location:
                    center = pyautogui.center(location)
                    if self.background_mode and self.window_title:
                        from utils.background_click import create_background_clicker
                        clicker = create_background_clicker(window_title=self.window_title)
                        if clicker:
                            rect = clicker.rect
                            rel_x = center.x - rect[0]
                            rel_y = center.y - rect[1]
                            result = clicker.click(rel_x, rel_y, background=True)
                            if not result.success:
                                pyautogui.click(center.x, center.y)
                        else:
                            pyautogui.click(center.x, center.y)
                    else:
                        pyautogui.click(center.x, center.y)
                else:
                    raise Exception(f"等待超时，屏幕上未找到匹配图片 (置信度: {confidence}, 超时: {timeout}秒)")
            
            elif self.action_type == ActionType.IMAGE_CHECK:
                image_path = self.params.get('image_path', '')
                confidence = self.params.get('confidence', 0.9)
                
                if not image_path:
                    raise Exception("未设置图片路径")
                if not os.path.exists(image_path):
                    raise Exception(f"图片文件不存在: {image_path}")
                
                if not self.background_mode:
                    self._activate_window_for_image()
                
                marker = self.condition_marker
                if not marker:
                    raise Exception("无法生成条件标记")
                
                var_name = marker[1:]
                var_manager = VariableManager.get_instance()
                
                location = None
                for attempt in range(3):
                    try:
                        location = pyautogui.locateOnScreen(image_path, confidence=confidence)
                        if location:
                            break
                    except pyautogui.ImageNotFoundException:
                        pass
                    time.sleep(0.1)
                
                if location:
                    var_manager.set(var_name, True)
                    var_manager.set(f"{var_name}_x", location.left)
                    var_manager.set(f"{var_name}_y", location.top)
                    var_manager.set(f"{var_name}_width", location.width)
                    var_manager.set(f"{var_name}_height", location.height)
                else:
                    var_manager.set(var_name, False)
            
            elif self.action_type == ActionType.ACTION_GROUP_REF:
                from .action_group import ensure_action_group_available, GlobalActionGroupManager
                group_name = self.params.get('group_name', '')
                if not group_name:
                    raise Exception("未指定动作组名称")
                
                group = ensure_action_group_available(group_name, local_group_manager)
                if not group:
                    global_manager = GlobalActionGroupManager.get_instance()
                    group = global_manager.ensure_group_loaded(group_name)
                    if not group:
                        raise Exception(f"动作组不存在: {group_name}")
                
                self._sub_actions = []
                for sub_index, group_action in enumerate(group.actions):
                    if should_stop and should_stop():
                        return False
                    if not group_action.check_condition():
                        print(f"[条件跳过] {group_action.description} - 条件不满足: {group_action.condition}")
                        continue
                    
                    if group_action.action_type in [ActionType.MOUSE_CLICK_RELATIVE, ActionType.MOUSE_MOVE_RELATIVE]:
                        group_action.use_relative_coords = True
                        if group_action.background_mode and not group_action.window_title:
                            group_action.window_title = self.window_title
                    
                    if group_action.action_type in [ActionType.ACTION_GROUP_REF, ActionType.IMAGE_CLICK, ActionType.IMAGE_WAIT_CLICK, ActionType.IMAGE_CHECK]:
                        if not group_action.window_title:
                            group_action.window_title = self.window_title
                    
                    group_action._is_from_group = True
                    group_action._group_name = group_name
                    group_action._sub_index = sub_index
                    self._sub_actions.append(group_action)
                    
                    if hasattr(self, '_on_sub_action_start') and self._on_sub_action_start:
                        self._on_sub_action_start(group_action, sub_index)
                    
                    def on_nested_sub_start(nested_action, nested_index):
                        if hasattr(self, '_on_nested_sub_action_start') and self._on_nested_sub_action_start:
                            self._on_nested_sub_action_start(sub_index, nested_action, nested_index)
                    
                    def on_nested_sub_end(nested_action, nested_index, success):
                        if hasattr(self, '_on_nested_sub_action_end') and self._on_nested_sub_action_end:
                            self._on_nested_sub_action_end(sub_index, nested_action, nested_index, success)
                    
                    group_action._on_sub_action_start = on_nested_sub_start
                    group_action._on_sub_action_end = on_nested_sub_end
                    
                    group_action.execute(window_offset=window_offset, should_stop=should_stop, local_group_manager=local_group_manager)
                    
                    if hasattr(self, '_on_sub_action_end') and self._on_sub_action_end:
                        self._on_sub_action_end(group_action, sub_index, True)
            
            time.sleep(self.delay_after)
            return True
            
        except Exception as e:
            error_msg = f"[{self.description}] 执行失败: {str(e)}"
            print(f"[动作错误] {error_msg}")
            raise Exception(error_msg)
    
    def validate(self) -> Tuple[bool, str]:
        if self.action_type in [ActionType.IMAGE_CLICK, ActionType.IMAGE_WAIT_CLICK, ActionType.IMAGE_CHECK]:
            image_path = self.params.get('image_path', '')
            if not image_path:
                return False, "未设置图片路径"
            if not os.path.exists(image_path):
                return False, f"图片文件不存在: {image_path}"
        
        if self.action_type == ActionType.WAIT:
            seconds = self.params.get('seconds', 0)
            if seconds < 0:
                return False, "等待时间不能为负数"
        
        if self.action_type in [ActionType.MOUSE_CLICK, ActionType.MOUSE_DOUBLE_CLICK, 
                                ActionType.MOUSE_RIGHT_CLICK, ActionType.MOUSE_MOVE]:
            x = self.params.get('x')
            y = self.params.get('y')
            if x is not None and (x < 0 or x > 10000):
                return False, f"X 坐标值异常: {x}"
            if y is not None and (y < 0 or y > 10000):
                return False, f"Y 坐标值异常: {y}"
        
        if self.action_type == ActionType.ACTION_GROUP_REF:
            group_name = self.params.get('group_name', '')
            if not group_name:
                return False, "未指定动作组名称"
        
        return True, ""
    
    def check_condition(self) -> bool:
        if not self.condition:
            return True
        
        var_manager = VariableManager.get_instance()
        
        try:
            condition = self.condition.strip()
            
            if '==' in condition:
                parts = condition.split('==')
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip()
                    
                    if left.startswith('$'):
                        left_val = var_manager.get(left[1:], '')
                    else:
                        left_val = left
                    
                    if right.startswith('$'):
                        right_val = var_manager.get(right[1:], '')
                    else:
                        right_val = right
                    
                    return str(left_val) == str(right_val)
            
            if '!=' in condition:
                parts = condition.split('!=')
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip()
                    
                    if left.startswith('$'):
                        left_val = var_manager.get(left[1:], '')
                    else:
                        left_val = left
                    
                    if right.startswith('$'):
                        right_val = var_manager.get(right[1:], '')
                    else:
                        right_val = right
                    
                    return str(left_val) != str(right_val)
            
            if condition.startswith('$'):
                var_name = condition[1:]
                return bool(var_manager.get(var_name, False))
            
            return True
        except Exception:
            return True
    
    def to_dict(self) -> Dict[str, Any]:
        data = {
            'action_type': self.action_type.value,
            'params': self.params,
            'description': self.description,
            'delay_before': self.delay_before,
            'delay_after': self.delay_after,
            'window_title': self.window_title,
            'use_relative_coords': self.use_relative_coords,
            'background_mode': self.background_mode,
            'name': self.name,
            'condition': self.condition,
            'repeat_count': self.repeat_count
        }
        
        if hasattr(self, '_is_from_group') and self._is_from_group:
            data['_is_from_group'] = True
            data['_group_name'] = getattr(self, '_group_name', '')
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Action':
        action = cls(
            action_type=ActionType(data['action_type']),
            params=data.get('params', {}),
            description=data.get('description', ''),
            delay_before=data.get('delay_before', 0.0),
            delay_after=data.get('delay_after', 0.0),
            window_title=data.get('window_title'),
            use_relative_coords=data.get('use_relative_coords', False),
            background_mode=data.get('background_mode', False),
            name=data.get('name', ''),
            condition=data.get('condition', ''),
            repeat_count=data.get('repeat_count', 1)
        )
        
        if data.get('_is_from_group'):
            action._is_from_group = True
            action._group_name = data.get('_group_name', '')
        
        return action
    
    def to_code(self) -> str:
        indent = "    "
        code_lines = []
        
        if self.delay_before > 0:
            code_lines.append(f"time.sleep({self.delay_before})")
        
        if self.action_type == ActionType.MOUSE_CLICK:
            x, y = self.params.get('x', 0), self.params.get('y', 0)
            button = self.params.get('button', 'left')
            clicks = self.params.get('clicks', 1)
            code_lines.append(f"pyautogui.click(x={x}, y={y}, button='{button}', clicks={clicks})")
        
        elif self.action_type == ActionType.MOUSE_DOUBLE_CLICK:
            x, y = self.params.get('x', 0), self.params.get('y', 0)
            code_lines.append(f"pyautogui.doubleClick(x={x}, y={y})")
        
        elif self.action_type == ActionType.MOUSE_RIGHT_CLICK:
            x, y = self.params.get('x', 0), self.params.get('y', 0)
            code_lines.append(f"pyautogui.rightClick(x={x}, y={y})")
        
        elif self.action_type == ActionType.MOUSE_MOVE:
            x, y = self.params.get('x', 0), self.params.get('y', 0)
            duration = self.params.get('duration', 0.0)
            code_lines.append(f"pyautogui.moveTo(x={x}, y={y}, duration={duration})")
        
        elif self.action_type == ActionType.MOUSE_DRAG:
            start_x = self.params.get('start_x', 0)
            start_y = self.params.get('start_y', 0)
            end_x = self.params.get('end_x', 0)
            end_y = self.params.get('end_y', 0)
            duration = self.params.get('duration', 0.5)
            code_lines.append(f"pyautogui.moveTo({start_x}, {start_y})")
            code_lines.append(f"pyautogui.drag({end_x - start_x}, {end_y - start_y}, duration={duration})")
        
        elif self.action_type == ActionType.MOUSE_SCROLL:
            clicks = self.params.get('clicks', 0)
            x, y = self.params.get('x', 0), self.params.get('y', 0)
            code_lines.append(f"pyautogui.scroll({clicks}, x={x}, y={y})")
        
        elif self.action_type == ActionType.KEY_PRESS:
            key = self.params.get('key', '')
            code_lines.append(f"pyautogui.press('{key}')")
        
        elif self.action_type == ActionType.KEY_TYPE:
            text = self.params.get('text', '')
            interval = self.params.get('interval', 0.0)
            escaped_text = text.replace("'", "\\'")
            code_lines.append(f"pyautogui.typewrite('{escaped_text}', interval={interval})")
        
        elif self.action_type == ActionType.HOTKEY:
            keys = self.params.get('keys', [])
            keys_str = ', '.join([f"'{k}'" for k in keys])
            code_lines.append(f"pyautogui.hotkey({keys_str})")
        
        elif self.action_type == ActionType.WAIT:
            seconds = self.params.get('seconds', 1.0)
            code_lines.append(f"time.sleep({seconds})")
        
        elif self.action_type == ActionType.SCREENSHOT:
            filename = self.params.get('filename', 'screenshot.png')
            region = self.params.get('region')
            if region:
                code_lines.append(f"pyautogui.screenshot('{filename}', region={region})")
            else:
                code_lines.append(f"pyautogui.screenshot('{filename}')")
        
        elif self.action_type in [ActionType.MOUSE_MOVE_RELATIVE, ActionType.MOUSE_CLICK_RELATIVE]:
            x, y = self.params.get('x', 0), self.params.get('y', 0)
            
            if self.background_mode and self.window_title:
                escaped_title = self.window_title.replace("'", "\\'")
                if self.action_type == ActionType.MOUSE_MOVE_RELATIVE:
                    code_lines.append(f"from utils.background_click import create_background_clicker")
                    code_lines.append(f"clicker = create_background_clicker(window_title='{escaped_title}')")
                    code_lines.append(f"if clicker:")
                    code_lines.append(f"    clicker.move({x}, {y}, background=True)")
                    code_lines.append(f"else:")
                    code_lines.append(f"    pyautogui.moveTo(x=window_x + {x}, y=window_y + {y})")
                else:
                    button = self.params.get('button', 'left')
                    code_lines.append(f"from utils.background_click import create_background_clicker")
                    code_lines.append(f"clicker = create_background_clicker(window_title='{escaped_title}')")
                    code_lines.append(f"if clicker:")
                    code_lines.append(f"    clicker.click({x}, {y}, button='{button}', background=True)")
                    code_lines.append(f"else:")
                    code_lines.append(f"    pyautogui.click(x=window_x + {x}, y=window_y + {y})")
            else:
                if self.action_type == ActionType.MOUSE_MOVE_RELATIVE:
                    duration = self.params.get('duration', 0.0)
                    code_lines.append(f"pyautogui.moveTo(x=window_x + {x}, y=window_y + {y}, duration={duration})")
                else:
                    code_lines.append(f"pyautogui.click(x=window_x + {x}, y=window_y + {y})")
        
        elif self.action_type == ActionType.IMAGE_CLICK:
            image_path = self.params.get('image_path', '')
            confidence = self.params.get('confidence', 0.9)
            escaped_path = image_path.replace('\\', '\\\\')
            code_lines.append(f"location = pyautogui.locateOnScreen(r'{escaped_path}', confidence={confidence})")
            code_lines.append("if location:")
            code_lines.append("    center = pyautogui.center(location)")
            code_lines.append("    pyautogui.click(center.x, center.y)")
        
        elif self.action_type == ActionType.IMAGE_WAIT_CLICK:
            image_path = self.params.get('image_path', '')
            confidence = self.params.get('confidence', 0.9)
            timeout = self.params.get('timeout', 10)
            escaped_path = image_path.replace('\\', '\\\\')
            code_lines.append(f"location = pyautogui.locateOnScreen(r'{escaped_path}', confidence={confidence})")
            code_lines.append(f"start_time = time.time()")
            code_lines.append(f"while location is None and (time.time() - start_time) < {timeout}:")
            code_lines.append("    time.sleep(0.5)")
            code_lines.append(f"    location = pyautogui.locateOnScreen(r'{escaped_path}', confidence={confidence})")
            code_lines.append("if location:")
            code_lines.append("    center = pyautogui.center(location)")
            code_lines.append("    pyautogui.click(center.x, center.y)")
        
        elif self.action_type == ActionType.IMAGE_CHECK:
            image_path = self.params.get('image_path', '')
            confidence = self.params.get('confidence', 0.9)
            marker = self.condition_marker
            var_name = marker[1:] if marker else 'image_found'
            escaped_path = image_path.replace('\\', '\\\\')
            code_lines.append(f"location = pyautogui.locateOnScreen(r'{escaped_path}', confidence={confidence})")
            code_lines.append(f"{var_name} = location is not None")
        
        elif self.action_type == ActionType.ACTION_GROUP_REF:
            group_name = self.params.get('group_name', '')
            code_lines.append(f"# 执行动作组: {group_name}")
            code_lines.append(f"execute_action_group('{group_name}')")
        
        if self.delay_after > 0:
            code_lines.append(f"time.sleep({self.delay_after})")
        
        return '\n'.join([indent + line for line in code_lines])


class ActionManager:
    ACTION_DEFINITIONS = {
        ActionType.MOUSE_CLICK: {
            'name': '鼠标单击',
            'category': '鼠标操作',
            'params': [
                {'name': 'x', 'type': 'int', 'default': 0, 'description': 'X坐标'},
                {'name': 'y', 'type': 'int', 'default': 0, 'description': 'Y坐标'},
                {'name': 'button', 'type': 'str', 'default': 'left', 'description': '鼠标按钮'},
                {'name': 'clicks', 'type': 'int', 'default': 1, 'description': '点击次数'},
            ]
        },
        ActionType.MOUSE_DOUBLE_CLICK: {
            'name': '鼠标双击',
            'category': '鼠标操作',
            'params': [
                {'name': 'x', 'type': 'int', 'default': 0, 'description': 'X坐标'},
                {'name': 'y', 'type': 'int', 'default': 0, 'description': 'Y坐标'},
            ]
        },
        ActionType.MOUSE_RIGHT_CLICK: {
            'name': '鼠标右键',
            'category': '鼠标操作',
            'params': [
                {'name': 'x', 'type': 'int', 'default': 0, 'description': 'X坐标'},
                {'name': 'y', 'type': 'int', 'default': 0, 'description': 'Y坐标'},
            ]
        },
        ActionType.MOUSE_MOVE: {
            'name': '鼠标移动',
            'category': '鼠标操作',
            'params': [
                {'name': 'x', 'type': 'int', 'default': 0, 'description': 'X坐标'},
                {'name': 'y', 'type': 'int', 'default': 0, 'description': 'Y坐标'},
                {'name': 'duration', 'type': 'float', 'default': 0.0, 'description': '移动时间(秒)'},
            ]
        },
        ActionType.MOUSE_DRAG: {
            'name': '鼠标拖拽',
            'category': '鼠标操作',
            'params': [
                {'name': 'start_x', 'type': 'int', 'default': 0, 'description': '起始X坐标'},
                {'name': 'start_y', 'type': 'int', 'default': 0, 'description': '起始Y坐标'},
                {'name': 'end_x', 'type': 'int', 'default': 0, 'description': '结束X坐标'},
                {'name': 'end_y', 'type': 'int', 'default': 0, 'description': '结束Y坐标'},
                {'name': 'duration', 'type': 'float', 'default': 0.5, 'description': '拖拽时间(秒)'},
            ]
        },
        ActionType.MOUSE_SCROLL: {
            'name': '鼠标滚轮',
            'category': '鼠标操作',
            'params': [
                {'name': 'clicks', 'type': 'int', 'default': 0, 'description': '滚动量(正数向上,负数向下)'},
                {'name': 'x', 'type': 'int', 'default': 0, 'description': 'X坐标'},
                {'name': 'y', 'type': 'int', 'default': 0, 'description': 'Y坐标'},
            ]
        },
        ActionType.KEY_PRESS: {
            'name': '按键',
            'category': '键盘操作',
            'params': [
                {'name': 'key', 'type': 'str', 'default': '', 'description': '按键名称'},
            ]
        },
        ActionType.KEY_TYPE: {
            'name': '输入文本',
            'category': '键盘操作',
            'params': [
                {'name': 'text', 'type': 'str', 'default': '', 'description': '要输入的文本'},
                {'name': 'interval', 'type': 'float', 'default': 0.0, 'description': '按键间隔(秒)'},
            ]
        },
        ActionType.HOTKEY: {
            'name': '快捷键',
            'category': '键盘操作',
            'params': [
                {'name': 'keys', 'type': 'list', 'default': [], 'description': '按键列表'},
            ]
        },
        ActionType.WAIT: {
            'name': '等待',
            'category': '控制',
            'params': [
                {'name': 'seconds', 'type': 'float', 'default': 1.0, 'description': '等待时间(秒)'},
            ]
        },
        ActionType.SCREENSHOT: {
            'name': '截图',
            'category': '其他',
            'params': [
                {'name': 'filename', 'type': 'str', 'default': 'screenshot.png', 'description': '文件名'},
                {'name': 'region', 'type': 'tuple', 'default': None, 'description': '截图区域(x,y,width,height)'},
            ]
        },
        ActionType.MOUSE_CLICK_RELATIVE: {
            'name': '窗口内点击',
            'category': '窗口操作',
            'params': [
                {'name': 'x', 'type': 'int', 'default': 0, 'description': '相对X坐标'},
                {'name': 'y', 'type': 'int', 'default': 0, 'description': '相对Y坐标'},
                {'name': 'button', 'type': 'str', 'default': 'left', 'description': '鼠标按钮(left/right/middle)'},
            ]
        },
        ActionType.MOUSE_MOVE_RELATIVE: {
            'name': '窗口内移动',
            'category': '窗口操作',
            'params': [
                {'name': 'x', 'type': 'int', 'default': 0, 'description': '相对X坐标'},
                {'name': 'y', 'type': 'int', 'default': 0, 'description': '相对Y坐标'},
                {'name': 'duration', 'type': 'float', 'default': 0.0, 'description': '移动时间(秒)'},
            ]
        },
        ActionType.IMAGE_CLICK: {
            'name': '图片点击',
            'category': '图像识别',
            'params': [
                {'name': 'image_path', 'type': 'str', 'default': '', 'description': '图片路径'},
                {'name': 'confidence', 'type': 'float', 'default': 0.9, 'description': '匹配精度(0-1)'},
            ]
        },
        ActionType.IMAGE_WAIT_CLICK: {
            'name': '等待图片点击',
            'category': '图像识别',
            'params': [
                {'name': 'image_path', 'type': 'str', 'default': '', 'description': '图片路径'},
                {'name': 'confidence', 'type': 'float', 'default': 0.9, 'description': '匹配精度(0-1)'},
                {'name': 'timeout', 'type': 'float', 'default': 10.0, 'description': '超时时间(秒)'},
            ]
        },
        ActionType.IMAGE_CHECK: {
            'name': '检查图片',
            'category': '图像识别',
            'params': [
                {'name': 'image_path', 'type': 'str', 'default': '', 'description': '图片路径'},
                {'name': 'confidence', 'type': 'float', 'default': 0.9, 'description': '匹配精度(0-1)'},
            ]
        },
        ActionType.ACTION_GROUP_REF: {
            'name': '动作组引用',
            'category': '流程控制',
            'params': [
                {'name': 'group_name', 'type': 'str', 'default': '', 'description': '动作组名称'},
            ]
        },
    }
    
    @classmethod
    def get_action_definition(cls, action_type: ActionType) -> Dict[str, Any]:
        return cls.ACTION_DEFINITIONS.get(action_type, {})
    
    @classmethod
    def get_all_categories(cls) -> Dict[str, List[ActionType]]:
        categories = {}
        for action_type, definition in cls.ACTION_DEFINITIONS.items():
            category = definition['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(action_type)
        return categories
    
    @classmethod
    def create_action(cls, action_type: ActionType, params: Dict[str, Any] = None, **kwargs) -> Action:
        if params is None:
            params = {}
        return Action(action_type=action_type, params=params, **kwargs)
    
    @classmethod
    def get_default_params(cls, action_type: ActionType) -> Dict[str, Any]:
        definition = cls.get_action_definition(action_type)
        defaults = {}
        for param in definition.get('params', []):
            defaults[param['name']] = param['default']
        return defaults
