import os
import json
import base64
import tempfile
from typing import List, Optional, Set, Dict, Any
from datetime import datetime
from .actions import Action, ActionType
from .action_group import (
    LocalActionGroupManager, GlobalActionGroupManager, ActionGroup,
    encode_image_to_base64
)


class Exporter:
    def __init__(self):
        self.script_name = "RPA_Script"
        self.author = ""
        self.description = ""
        self.include_window_setup = False
        self.target_window_title = ""
        self._local_group_manager: Optional[LocalActionGroupManager] = None
        self._global_group_manager = GlobalActionGroupManager.get_instance()
        self._used_groups: Set[str] = set()
        self._embedded_images: Dict[str, str] = {}
    
    def set_script_info(self, name: str = "", author: str = "", description: str = ""):
        self.script_name = name or "RPA_Script"
        self.author = author
        self.description = description
    
    def set_window_setup(self, include: bool, window_title: str = ""):
        self.include_window_setup = include
        self.target_window_title = window_title
    
    def set_local_group_manager(self, manager: LocalActionGroupManager):
        self._local_group_manager = manager
    
    def _collect_used_groups(self, actions: List[Action], action_groups: dict = None):
        if action_groups is None:
            action_groups = {}
        
        for action in actions:
            if action.action_type == ActionType.ACTION_GROUP_REF:
                group_name = action.params.get('group_name', '')
                if group_name and group_name not in action_groups:
                    group = None
                    if self._local_group_manager:
                        group = self._local_group_manager.get_group(group_name)
                    if not group:
                        group = self._global_group_manager.get_group(group_name)
                    
                    if group:
                        self._used_groups.add(group_name)
                        action_groups[group_name] = group.to_dict()
                        self._collect_used_groups(group.actions, action_groups)
        
        return action_groups
    
    def _collect_embedded_images(self, actions: List[Action]):
        for action in actions:
            if action.action_type in [ActionType.IMAGE_CLICK, ActionType.IMAGE_WAIT_CLICK, ActionType.IMAGE_CHECK]:
                image_path = action.params.get('image_path', '')
                if image_path and os.path.exists(image_path):
                    if image_path not in self._embedded_images:
                        base64_data = encode_image_to_base64(image_path)
                        if base64_data:
                            self._embedded_images[image_path] = base64_data
    
    def export_to_python(self, actions: List[Action], filepath: str) -> bool:
        try:
            self._used_groups.clear()
            self._embedded_images.clear()
            self._collect_used_groups(actions)
            self._collect_embedded_images(actions)
            
            code = self._generate_python_code(actions)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(code)
            
            return True
        except Exception as e:
            print(f"Export failed: {e}")
            return False
    
    def _generate_python_code(self, actions: List[Action]) -> str:
        lines = []
        
        lines.append("#!/usr/bin/env python3")
        lines.append("# -*- coding: utf-8 -*-")
        lines.append("")
        lines.append('"""')
        lines.append(f"RPA Script: {self.script_name}")
        if self.author:
            lines.append(f"Author: {self.author}")
        if self.description:
            lines.append(f"Description: {self.description}")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append('"""')
        lines.append("")
        lines.append("import pyautogui")
        lines.append("import time")
        lines.append("import os")
        lines.append("import base64")
        lines.append("import tempfile")
        lines.append("")
        
        if self._embedded_images:
            lines.append("# Embedded Images (Base64)")
            lines.append("EMBEDDED_IMAGES = {")
            for image_path, base64_data in self._embedded_images.items():
                image_name = os.path.basename(image_path)
                safe_name = image_name.replace('.', '_').replace(' ', '_').replace('-', '_')
                lines.append(f"    '{safe_name}': \"\"\"{base64_data}\"\"\",")
            lines.append("}")
            lines.append("")
            lines.append("_image_cache = {}")
            lines.append("")
            lines.append("def get_embedded_image(image_name):")
            lines.append('    """Get image path from embedded data."""')
            lines.append("    if image_name in _image_cache:")
            lines.append("        return _image_cache[image_name]")
            lines.append("    ")
            lines.append("    if image_name not in EMBEDDED_IMAGES:")
            lines.append("        return None")
            lines.append("    ")
            lines.append("    temp_dir = tempfile.gettempdir()")
            lines.append("    image_path = os.path.join(temp_dir, f'rpa_embedded_{image_name}.png')")
            lines.append("    ")
            lines.append("    if not os.path.exists(image_path):")
            lines.append("        image_data = base64.b64decode(EMBEDDED_IMAGES[image_name])")
            lines.append("        with open(image_path, 'wb') as f:")
            lines.append("            f.write(image_data)")
            lines.append("    ")
            lines.append("    _image_cache[image_name] = image_path")
            lines.append("    return image_path")
            lines.append("")
            lines.append("")
        
        if self._used_groups:
            lines.append("# Action Group Definitions")
            lines.append("ACTION_GROUPS = {}")
            lines.append("")
            lines.append("def register_action_group(name, actions):")
            lines.append('    """Register an action group."""')
            lines.append("    ACTION_GROUPS[name] = actions")
            lines.append("")
            lines.append("def execute_action_group(name):")
            lines.append('    """Execute an action group by name."""')
            lines.append("    if name not in ACTION_GROUPS:")
            lines.append('        raise ValueError(f"Action group not found: {name}")')
            lines.append("    for action in ACTION_GROUPS[name]:")
            lines.append("        action()")
            lines.append("")
            lines.append("")
        
        for group_name in sorted(self._used_groups):
            group = None
            if self._local_group_manager:
                group = self._local_group_manager.get_group(group_name)
            if not group:
                group = self._global_group_manager.get_group(group_name)
            
            if group:
                lines.append(f"def action_group_{self._sanitize_name(group_name)}():")
                lines.append(f'    """Execute action group: {group_name}"""')
                for group_action in group.actions:
                    if group_action.action_type == ActionType.ACTION_GROUP_REF:
                        ref_name = group_action.params.get('group_name', '')
                        lines.append(f"    execute_action_group('{ref_name}')")
                    else:
                        action_code = self._action_to_code(group_action)
                        for code_line in action_code.split('\n'):
                            lines.append(code_line)
                lines.append("")
                lines.append(f"register_action_group('{group_name}', [action_group_{self._sanitize_name(group_name)}])")
                lines.append("")
        
        lines.append("def main():")
        lines.append('    """Main function to execute the RPA script."""')
        lines.append("    ")
        lines.append("    # Safety settings")
        lines.append("    pyautogui.FAILSAFE = True")
        lines.append("    pyautogui.PAUSE = 0.1")
        lines.append("    ")
        
        has_relative_coords = any(
            action.action_type in [ActionType.MOUSE_CLICK_RELATIVE, ActionType.MOUSE_MOVE_RELATIVE]
            for action in actions
        )
        
        if self.include_window_setup and self.target_window_title:
            lines.append("    # Window setup")
            lines.append("    window_x, window_y = 0, 0")
            lines.append("    try:")
            lines.append("        import win32gui")
            lines.append("        import win32con")
            lines.append("        ")
            lines.append(f"        # Find and activate target window: {self.target_window_title}")
            lines.append(f'        hwnd = win32gui.FindWindow(None, "{self.target_window_title}")')
            lines.append("        if hwnd:")
            lines.append("            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)")
            lines.append("            win32gui.SetForegroundWindow(hwnd)")
            lines.append("            time.sleep(0.5)")
            lines.append("            rect = win32gui.GetWindowRect(hwnd)")
            lines.append("            window_x, window_y = rect[0], rect[1]")
            lines.append("    except ImportError:")
            lines.append("        print('win32gui not available, skipping window setup')")
            lines.append("    except Exception as e:")
            lines.append("        print(f'Window setup failed: {{e}}')")
            lines.append("    ")
        elif has_relative_coords:
            lines.append("    # Window coordinates (no target window specified)")
            lines.append("    window_x, window_y = 0, 0")
            lines.append("    ")
        
        lines.append("    # Execute actions")
        lines.append("    print('Starting RPA script execution...')")
        lines.append("    ")
        
        for i, action in enumerate(actions):
            if action.action_type == ActionType.ACTION_GROUP_REF:
                group_name = action.params.get('group_name', '')
                lines.append(f"    # Action {i + 1}: Execute action group: {group_name}")
                lines.append(f"    execute_action_group('{group_name}')")
            else:
                lines.append(f"    # Action {i + 1}: {action.description}")
                action_code = self._action_to_code(action)
                lines.append(action_code)
            lines.append("    ")
        
        lines.append("    print('RPA script execution completed.')")
        lines.append("")
        lines.append("")
        lines.append("if __name__ == '__main__':")
        lines.append("    try:")
        lines.append("        main()")
        lines.append("    except KeyboardInterrupt:")
        lines.append("        print('\\nScript interrupted by user.')")
        lines.append("    except Exception as e:")
        lines.append("        print(f'Script error: {{e}}')")
        lines.append("")
        
        return '\n'.join(lines)
    
    def _action_to_code(self, action: Action) -> str:
        indent = "    "
        code_lines = []
        
        if action.delay_before > 0:
            code_lines.append(f"time.sleep({action.delay_before})")
        
        if action.action_type == ActionType.MOUSE_CLICK:
            x, y = action.params.get('x', 0), action.params.get('y', 0)
            button = action.params.get('button', 'left')
            clicks = action.params.get('clicks', 1)
            code_lines.append(f"pyautogui.click(x={x}, y={y}, button='{button}', clicks={clicks})")
        
        elif action.action_type == ActionType.MOUSE_DOUBLE_CLICK:
            x, y = action.params.get('x', 0), action.params.get('y', 0)
            code_lines.append(f"pyautogui.doubleClick(x={x}, y={y})")
        
        elif action.action_type == ActionType.MOUSE_RIGHT_CLICK:
            x, y = action.params.get('x', 0), action.params.get('y', 0)
            code_lines.append(f"pyautogui.rightClick(x={x}, y={y})")
        
        elif action.action_type == ActionType.MOUSE_MOVE:
            x, y = action.params.get('x', 0), action.params.get('y', 0)
            duration = action.params.get('duration', 0.0)
            code_lines.append(f"pyautogui.moveTo(x={x}, y={y}, duration={duration})")
        
        elif action.action_type == ActionType.MOUSE_DRAG:
            start_x = action.params.get('start_x', 0)
            start_y = action.params.get('start_y', 0)
            end_x = action.params.get('end_x', 0)
            end_y = action.params.get('end_y', 0)
            duration = action.params.get('duration', 0.5)
            code_lines.append(f"pyautogui.moveTo({start_x}, {start_y})")
            code_lines.append(f"pyautogui.drag({end_x - start_x}, {end_y - start_y}, duration={duration})")
        
        elif action.action_type == ActionType.MOUSE_SCROLL:
            clicks = action.params.get('clicks', 0)
            x, y = action.params.get('x', 0), action.params.get('y', 0)
            code_lines.append(f"pyautogui.scroll({clicks}, x={x}, y={y})")
        
        elif action.action_type == ActionType.KEY_PRESS:
            key = action.params.get('key', '')
            code_lines.append(f"pyautogui.press('{key}')")
        
        elif action.action_type == ActionType.KEY_TYPE:
            text = action.params.get('text', '')
            interval = action.params.get('interval', 0.0)
            escaped_text = text.replace("'", "\\'")
            code_lines.append(f"pyautogui.typewrite('{escaped_text}', interval={interval})")
        
        elif action.action_type == ActionType.HOTKEY:
            keys = action.params.get('keys', [])
            keys_str = ', '.join([f"'{k}'" for k in keys])
            code_lines.append(f"pyautogui.hotkey({keys_str})")
        
        elif action.action_type == ActionType.WAIT:
            seconds = action.params.get('seconds', 1.0)
            code_lines.append(f"time.sleep({seconds})")
        
        elif action.action_type == ActionType.SCREENSHOT:
            filename = action.params.get('filename', 'screenshot.png')
            region = action.params.get('region')
            if region:
                code_lines.append(f"pyautogui.screenshot('{filename}', region={region})")
            else:
                code_lines.append(f"pyautogui.screenshot('{filename}')")
        
        elif action.action_type in [ActionType.MOUSE_MOVE_RELATIVE, ActionType.MOUSE_CLICK_RELATIVE]:
            x, y = action.params.get('x', 0), action.params.get('y', 0)
            if action.action_type == ActionType.MOUSE_MOVE_RELATIVE:
                duration = action.params.get('duration', 0.0)
                code_lines.append(f"pyautogui.moveTo(x=window_x + {x}, y=window_y + {y}, duration={duration})")
            else:
                code_lines.append(f"pyautogui.click(x=window_x + {x}, y=window_y + {y})")
        
        elif action.action_type == ActionType.IMAGE_CLICK:
            image_path = action.params.get('image_path', '')
            confidence = action.params.get('confidence', 0.9)
            
            if image_path in self._embedded_images:
                image_name = os.path.basename(image_path).replace('.', '_').replace(' ', '_').replace('-', '_')
                code_lines.append(f"image_path = get_embedded_image('{image_name}')")
                code_lines.append("if image_path:")
                code_lines.append(f"    location = pyautogui.locateOnScreen(image_path, confidence={confidence})")
                code_lines.append("    if location:")
                code_lines.append("        center = pyautogui.center(location)")
                code_lines.append("        pyautogui.click(center.x, center.y)")
            else:
                escaped_path = image_path.replace('\\', '\\\\')
                code_lines.append(f"location = pyautogui.locateOnScreen(r'{escaped_path}', confidence={confidence})")
                code_lines.append("if location:")
                code_lines.append("    center = pyautogui.center(location)")
                code_lines.append("    pyautogui.click(center.x, center.y)")
        
        elif action.action_type == ActionType.IMAGE_WAIT_CLICK:
            image_path = action.params.get('image_path', '')
            confidence = action.params.get('confidence', 0.9)
            timeout = action.params.get('timeout', 10)
            
            if image_path in self._embedded_images:
                image_name = os.path.basename(image_path).replace('.', '_').replace(' ', '_').replace('-', '_')
                code_lines.append(f"image_path = get_embedded_image('{image_name}')")
                code_lines.append("location = None")
                code_lines.append("if image_path:")
                code_lines.append(f"    start_time = time.time()")
                code_lines.append(f"    while location is None and (time.time() - start_time) < {timeout}:")
                code_lines.append("        time.sleep(0.5)")
                code_lines.append(f"        location = pyautogui.locateOnScreen(image_path, confidence={confidence})")
            else:
                escaped_path = image_path.replace('\\', '\\\\')
                code_lines.append(f"location = pyautogui.locateOnScreen(r'{escaped_path}', confidence={confidence})")
                code_lines.append(f"start_time = time.time()")
                code_lines.append(f"while location is None and (time.time() - start_time) < {timeout}:")
                code_lines.append("    time.sleep(0.5)")
                code_lines.append(f"    location = pyautogui.locateOnScreen(r'{escaped_path}', confidence={confidence})")
            
            code_lines.append("if location:")
            code_lines.append("    center = pyautogui.center(location)")
            code_lines.append("    pyautogui.click(center.x, center.y)")
        
        elif action.action_type == ActionType.IMAGE_CHECK:
            image_path = action.params.get('image_path', '')
            confidence = action.params.get('confidence', 0.9)
            marker = action.condition_marker
            var_name = marker[1:] if marker else 'image_found'
            
            if image_path in self._embedded_images:
                image_name = os.path.basename(image_path).replace('.', '_').replace(' ', '_').replace('-', '_')
                code_lines.append(f"image_path = get_embedded_image('{image_name}')")
                code_lines.append(f"{var_name} = False")
                code_lines.append("if image_path:")
                code_lines.append(f"    location = pyautogui.locateOnScreen(image_path, confidence={confidence})")
                code_lines.append(f"    {var_name} = location is not None")
            else:
                escaped_path = image_path.replace('\\', '\\\\')
                code_lines.append(f"location = pyautogui.locateOnScreen(r'{escaped_path}', confidence={confidence})")
                code_lines.append(f"{var_name} = location is not None")
        
        elif action.action_type == ActionType.ACTION_GROUP_REF:
            group_name = action.params.get('group_name', '')
            code_lines.append(f"# 执行动作组: {group_name}")
            code_lines.append(f"execute_action_group('{group_name}')")
        
        if action.delay_after > 0:
            code_lines.append(f"time.sleep({action.delay_after})")
        
        return '\n'.join([indent + line for line in code_lines])
    
    def _sanitize_name(self, name: str) -> str:
        return name.replace(' ', '_').replace('-', '_').replace('.', '_')
    
    def export_to_json(self, actions: List[Action], filepath: str) -> bool:
        try:
            self._used_groups.clear()
            self._embedded_images.clear()
            
            action_groups = self._collect_used_groups(actions)
            self._collect_embedded_images(actions)
            
            data = {
                'name': self.script_name,
                'author': self.author,
                'description': self.description,
                'created': datetime.now().isoformat(),
                'version': '2.0',
                'actions': [action.to_dict() for action in actions],
                'action_groups': action_groups,
                'embedded_images': {os.path.basename(k): v for k, v in self._embedded_images.items()}
            }
            
            if self._local_group_manager:
                local_groups = self._local_group_manager.to_dict()
                if local_groups:
                    data['local_action_groups'] = local_groups
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Export to JSON failed: {e}")
            return False
    
    @staticmethod
    def import_from_json(filepath: str, local_group_manager: LocalActionGroupManager = None) -> Optional[List[Action]]:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            embedded_images = data.get('embedded_images', {})
            temp_dir = os.path.join(os.path.dirname(filepath), '.images')
            
            image_path_map = {}
            for image_name, base64_data in embedded_images.items():
                image_data = base64.b64decode(base64_data)
                os.makedirs(temp_dir, exist_ok=True)
                image_path = os.path.join(temp_dir, image_name)
                with open(image_path, 'wb') as f:
                    f.write(image_data)
                image_path_map[image_name] = image_path
            
            if local_group_manager is not None:
                local_groups = data.get('local_action_groups', {}) or data.get('action_groups', {})
                local_group_manager.load_from_dict(local_groups)
            
            actions = []
            for action_data in data.get('actions', []):
                action = Action.from_dict(action_data)
                
                if action.action_type in [ActionType.IMAGE_CLICK, ActionType.IMAGE_WAIT_CLICK, ActionType.IMAGE_CHECK]:
                    original_path = action.params.get('image_path', '')
                    image_name = os.path.basename(original_path)
                    if image_name in image_path_map:
                        action.params['image_path'] = image_path_map[image_name]
                
                actions.append(action)
            
            return actions
        except Exception as e:
            print(f"Import from JSON failed: {e}")
            return None
    
    @staticmethod
    def get_pyinstaller_command(script_path: str, output_dir: str = None) -> str:
        cmd_parts = ["pyinstaller", "--onefile", "--windowed"]
        
        if output_dir:
            cmd_parts.extend(["--distpath", output_dir])
        
        script_name = os.path.splitext(os.path.basename(script_path))[0]
        cmd_parts.extend(["--name", script_name])
        
        cmd_parts.append(f'"{script_path}"')
        
        return " ".join(cmd_parts)
