import json
import os
from typing import Any, Dict
from dataclasses import dataclass, field


@dataclass
class Config:
    default_speed: float = 1.0
    default_repeat_count: int = 1
    record_mouse_move: bool = False
    record_mouse_click: bool = True
    record_mouse_scroll: bool = True
    record_keyboard: bool = True
    min_move_distance: int = 10
    move_sample_interval: float = 0.1
    action_delay: float = 0.1
    auto_save: bool = True
    recent_files: list = field(default_factory=list)
    window_geometry: Dict[str, int] = field(default_factory=lambda: {'x': 100, 'y': 100, 'width': 1200, 'height': 800})
    theme: str = 'light'
    language: str = 'zh_CN'
    
    bound_window: Dict[str, Any] = field(default_factory=dict)
    open_tabs: list = field(default_factory=list)
    tab_files: Dict[str, str] = field(default_factory=dict)
    current_tab_index: int = 0
    infinite_loop: bool = False
    timeout_seconds: float = 0
    
    _config_path: str = field(default='', repr=False)
    
    def __post_init__(self):
        self._config_path = self._get_default_config_path()
    
    def _get_default_config_path(self) -> str:
        config_dir = os.path.join(os.path.expanduser('~'), '.simpleRPA')
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, 'config.json')
    
    def save(self, path: str = None) -> bool:
        try:
            save_path = path or self._config_path
            
            data = {
                'default_speed': self.default_speed,
                'default_repeat_count': self.default_repeat_count,
                'record_mouse_move': self.record_mouse_move,
                'record_mouse_click': self.record_mouse_click,
                'record_mouse_scroll': self.record_mouse_scroll,
                'record_keyboard': self.record_keyboard,
                'min_move_distance': self.min_move_distance,
                'move_sample_interval': self.move_sample_interval,
                'action_delay': self.action_delay,
                'auto_save': self.auto_save,
                'recent_files': self.recent_files[-10:],
                'window_geometry': self.window_geometry,
                'theme': self.theme,
                'language': self.language,
                'bound_window': self.bound_window,
                'open_tabs': self.open_tabs,
                'tab_files': self.tab_files,
                'current_tab_index': self.current_tab_index,
                'infinite_loop': self.infinite_loop,
                'timeout_seconds': self.timeout_seconds,
            }
            
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Save config failed: {e}")
            return False
    
    def load(self, path: str = None) -> bool:
        try:
            load_path = path or self._config_path
            
            if not os.path.exists(load_path):
                return False
            
            with open(load_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.default_speed = data.get('default_speed', self.default_speed)
            self.default_repeat_count = data.get('default_repeat_count', self.default_repeat_count)
            self.record_mouse_move = data.get('record_mouse_move', self.record_mouse_move)
            self.record_mouse_click = data.get('record_mouse_click', self.record_mouse_click)
            self.record_mouse_scroll = data.get('record_mouse_scroll', self.record_mouse_scroll)
            self.record_keyboard = data.get('record_keyboard', self.record_keyboard)
            self.min_move_distance = data.get('min_move_distance', self.min_move_distance)
            self.move_sample_interval = data.get('move_sample_interval', self.move_sample_interval)
            self.action_delay = data.get('action_delay', self.action_delay)
            self.auto_save = data.get('auto_save', self.auto_save)
            self.recent_files = data.get('recent_files', [])
            self.window_geometry = data.get('window_geometry', self.window_geometry)
            self.theme = data.get('theme', self.theme)
            self.language = data.get('language', self.language)
            self.bound_window = data.get('bound_window', {})
            self.open_tabs = data.get('open_tabs', [])
            self.tab_files = data.get('tab_files', {})
            self.current_tab_index = data.get('current_tab_index', 0)
            self.infinite_loop = data.get('infinite_loop', False)
            self.timeout_seconds = data.get('timeout_seconds', 0)
            
            return True
        except Exception as e:
            print(f"Load config failed: {e}")
            return False
    
    def add_recent_file(self, filepath: str):
        if filepath in self.recent_files:
            self.recent_files.remove(filepath)
        self.recent_files.insert(0, filepath)
        self.recent_files = self.recent_files[-10:]
    
    def clear_recent_files(self):
        self.recent_files = []
    
    def set_window_geometry(self, x: int, y: int, width: int, height: int):
        self.window_geometry = {'x': x, 'y': y, 'width': width, 'height': height}
    
    @classmethod
    def get_instance(cls) -> 'Config':
        if not hasattr(cls, '_instance'):
            cls._instance = cls()
            cls._instance.load()
        return cls._instance
