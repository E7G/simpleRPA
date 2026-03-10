import json
import os
import subprocess
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


@dataclass
class LaunchCommand:
    id: str
    name: str
    command: str
    window_title_pattern: str = ""
    description: str = ""
    created_at: str = ""
    last_used: str = ""
    use_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LaunchCommand':
        return cls(**data)


class CommandManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._commands: Dict[str, LaunchCommand] = {}
        self._config_path = self._get_config_path()
        self.load()
    
    def _get_config_path(self) -> str:
        config_dir = os.path.join(os.path.expanduser('~'), '.simpleRPA')
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, 'launch_commands.json')
    
    def load(self) -> bool:
        try:
            if not os.path.exists(self._config_path):
                return False
            
            with open(self._config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._commands = {
                cmd_id: LaunchCommand.from_dict(cmd_data)
                for cmd_id, cmd_data in data.get('commands', {}).items()
            }
            return True
        except Exception as e:
            print(f"[CommandManager] 加载命令失败: {e}")
            return False
    
    def save(self) -> bool:
        try:
            data = {
                'commands': {
                    cmd_id: cmd.to_dict()
                    for cmd_id, cmd in self._commands.items()
                }
            }
            
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"[CommandManager] 保存命令失败: {e}")
            return False
    
    def add_command(self, name: str, command: str, window_title_pattern: str = "", 
                    description: str = "") -> Optional[LaunchCommand]:
        import uuid
        from datetime import datetime
        
        cmd_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        
        launch_cmd = LaunchCommand(
            id=cmd_id,
            name=name,
            command=command,
            window_title_pattern=window_title_pattern,
            description=description,
            created_at=now,
            last_used=now,
            use_count=0
        )
        
        self._commands[cmd_id] = launch_cmd
        self.save()
        return launch_cmd
    
    def update_command(self, cmd_id: str, **kwargs) -> bool:
        if cmd_id not in self._commands:
            return False
        
        cmd = self._commands[cmd_id]
        for key, value in kwargs.items():
            if hasattr(cmd, key):
                setattr(cmd, key, value)
        
        self.save()
        return True
    
    def delete_command(self, cmd_id: str) -> bool:
        if cmd_id not in self._commands:
            return False
        
        del self._commands[cmd_id]
        self.save()
        return True
    
    def get_command(self, cmd_id: str) -> Optional[LaunchCommand]:
        return self._commands.get(cmd_id)
    
    def get_all_commands(self) -> List[LaunchCommand]:
        return list(self._commands.values())
    
    def execute_command(self, cmd_id: str) -> tuple:
        cmd = self.get_command(cmd_id)
        if not cmd:
            return False, "命令不存在"
        
        try:
            if os.name == 'nt':
                subprocess.Popen(cmd.command, shell=True)
            else:
                subprocess.Popen(cmd.command, shell=True, start_new_session=True)
            
            from datetime import datetime
            cmd.last_used = datetime.now().isoformat()
            cmd.use_count += 1
            self.save()
            
            return True, "命令执行成功"
        except Exception as e:
            return False, f"执行失败: {str(e)}"
    
    def is_window_running(self, window_title_pattern: str) -> bool:
        if not window_title_pattern:
            return False
        
        if PSUTIL_AVAILABLE:
            try:
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        cmdline = proc.info.get('cmdline', [])
                        if cmdline:
                            cmd_str = ' '.join(cmdline).lower()
                            if window_title_pattern.lower() in cmd_str:
                                return True
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                return False
            except Exception:
                return False
        else:
            try:
                if os.name == 'nt':
                    import win32gui
                    import win32process
                    import ctypes
                    
                    def enum_windows_callback(hwnd, results):
                        if win32gui.IsWindowVisible(hwnd):
                            title = win32gui.GetWindowText(hwnd)
                            if window_title_pattern.lower() in title.lower():
                                results.append(hwnd)
                        return True
                    
                    results = []
                    win32gui.EnumWindows(enum_windows_callback, results)
                    return len(results) > 0
                return False
            except Exception:
                return False
    
    def check_and_launch(self, cmd_id: str) -> tuple:
        cmd = self.get_command(cmd_id)
        if not cmd:
            return False, "命令不存在", False
        
        if cmd.window_title_pattern and self.is_window_running(cmd.window_title_pattern):
            return True, "窗口已在运行", True
        
        success, message = self.execute_command(cmd_id)
        return success, message, False
    
    @classmethod
    def get_instance(cls) -> 'CommandManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
