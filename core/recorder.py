import time
import threading
import os
from typing import List, Callable, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
from pynput import mouse, keyboard
from .actions import Action, ActionType


class RecordState(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"


@dataclass
class RecordConfig:
    record_mouse_move: bool = False
    record_mouse_click: bool = True
    record_mouse_scroll: bool = True
    record_keyboard: bool = True
    min_move_distance: int = 10
    move_sample_interval: float = 0.1
    ignore_last_click: bool = True
    record_as_image_click: bool = False
    image_capture_size: int = 30


class Recorder:
    def __init__(self, config: Optional[RecordConfig] = None):
        self.config = config or RecordConfig()
        self.state = RecordState.IDLE
        self.actions: List[Action] = []
        self.last_mouse_pos: Optional[tuple] = None
        self.last_move_time: float = 0
        self.start_time: float = 0
        self.last_action_time: float = 0
        self._stop_time: float = 0
        self._stopping: bool = False
        self._lock = threading.Lock()
        
        self._mouse_listener: Optional[mouse.Listener] = None
        self._keyboard_listener: Optional[keyboard.Listener] = None
        
        self._callbacks: Dict[str, List[Callable]] = {
            'on_action_recorded': [],
            'on_state_changed': [],
            'on_error': [],
            'on_last_action_removed': []
        }
        
        self._recorded_keys: List[str] = []
        self._is_recording_text: bool = False
        self._text_start_time: float = 0
    
    def add_callback(self, event: str, callback: Callable):
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def remove_callback(self, event: str, callback: Callable):
        if event in self._callbacks and callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)
    
    def _emit(self, event: str, *args, **kwargs):
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                print(f"Callback error: {e}")
    
    def start(self):
        if self.state == RecordState.RECORDING:
            return
        
        self.actions = []
        self.state = RecordState.RECORDING
        self.start_time = time.time()
        self.last_action_time = self.start_time
        self.last_mouse_pos = None
        self._recorded_keys = []
        self._is_recording_text = False
        
        self._mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll
        )
        
        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        
        self._mouse_listener.start()
        self._keyboard_listener.start()
        
        self._emit('on_state_changed', self.state)
    
    def stop(self):
        with self._lock:
            if self.state == RecordState.IDLE:
                return
            
            self._stopping = True
            self.state = RecordState.IDLE
        
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None
        
        if self._keyboard_listener:
            self._keyboard_listener.stop()
            self._keyboard_listener = None
        
        removed_last = False
        with self._lock:
            if self._is_recording_text and self._recorded_keys:
                self._flush_text_input()
            
            if self.actions and self.config.ignore_last_click:
                last_action = self.actions[-1]
                if last_action.action_type in (ActionType.MOUSE_CLICK, ActionType.IMAGE_CLICK):
                    self.actions.pop()
                    removed_last = True
            
            self._stopping = False
        
        if removed_last:
            self._emit('on_last_action_removed')
        
        self._emit('on_state_changed', self.state)
    
    def pause(self):
        if self.state == RecordState.RECORDING:
            self.state = RecordState.PAUSED
            self._emit('on_state_changed', self.state)
    
    def resume(self):
        if self.state == RecordState.PAUSED:
            self.state = RecordState.RECORDING
            self._emit('on_state_changed', self.state)
    
    def _get_elapsed_time(self) -> float:
        return time.time() - self.last_action_time
    
    def _add_action(self, action: Action):
        with self._lock:
            if self.state != RecordState.RECORDING:
                return
            
            elapsed = self._get_elapsed_time()
            action.delay_before = elapsed
            action.description = action._generate_description()
            self.actions.append(action)
            self.last_action_time = time.time()
        self._emit('on_action_recorded', action)
    
    def _on_mouse_move(self, x: int, y: int):
        if self.state != RecordState.RECORDING:
            return
        
        if not self.config.record_mouse_move:
            return
        
        current_time = time.time()
        
        if current_time - self.last_move_time < self.config.move_sample_interval:
            return
        
        if self.last_mouse_pos:
            distance = ((x - self.last_mouse_pos[0]) ** 2 + (y - self.last_mouse_pos[1]) ** 2) ** 0.5
            if distance < self.config.min_move_distance:
                return
        
        self.last_mouse_pos = (x, y)
        self.last_move_time = current_time
        
        action = Action(
            action_type=ActionType.MOUSE_MOVE,
            params={'x': x, 'y': y, 'duration': 0.0}
        )
        self._add_action(action)
    
    def _on_mouse_click(self, x: int, y: int, button: mouse.Button, pressed: bool):
        if not pressed:
            return
        
        if not self.config.record_mouse_click:
            return
        
        with self._lock:
            if self.state != RecordState.RECORDING:
                return
            
            if self._stopping:
                return
            
            if self._is_recording_text:
                self._flush_text_input()
            
            button_name = 'left' if button == mouse.Button.left else 'right' if button == mouse.Button.right else 'middle'
            
            if self.config.record_as_image_click:
                image_path = self._capture_click_region(x, y)
                if image_path:
                    action = Action(
                        action_type=ActionType.IMAGE_CLICK,
                        params={'image_path': image_path, 'confidence': 0.9}
                    )
                else:
                    action = Action(
                        action_type=ActionType.MOUSE_CLICK,
                        params={'x': x, 'y': y, 'button': button_name, 'clicks': 1}
                    )
            else:
                action = Action(
                    action_type=ActionType.MOUSE_CLICK,
                    params={'x': x, 'y': y, 'button': button_name, 'clicks': 1}
                )
            
            elapsed = self._get_elapsed_time()
            action.delay_before = elapsed
            action.description = action._generate_description()
            self.actions.append(action)
            self.last_action_time = time.time()
        
        self._emit('on_action_recorded', action)
    
    def _capture_click_region(self, x: int, y: int) -> Optional[str]:
        try:
            import pyautogui
            
            size = self.config.image_capture_size
            region = (
                max(0, x - size // 2),
                max(0, y - size // 2),
                size,
                size
            )
            
            screenshot = pyautogui.screenshot(region=region)
            
            images_dir = os.path.join(os.path.expanduser('~'), '.simpleRPA', 'images')
            os.makedirs(images_dir, exist_ok=True)
            
            filename = f"click_{int(time.time() * 1000)}.png"
            filepath = os.path.join(images_dir, filename)
            
            screenshot.save(filepath)
            
            return filepath
        except Exception as e:
            print(f"截图失败: {e}")
            return None
    
    def _on_mouse_scroll(self, x: int, y: int, dx: int, dy: int):
        if self.state != RecordState.RECORDING:
            return
        
        if not self.config.record_mouse_scroll:
            return
        
        if self._is_recording_text:
            self._flush_text_input()
        
        action = Action(
            action_type=ActionType.MOUSE_SCROLL,
            params={'clicks': dy, 'x': x, 'y': y}
        )
        self._add_action(action)
    
    def _on_key_press(self, key):
        if self.state != RecordState.RECORDING:
            return
        
        if not self.config.record_keyboard:
            return
        
        try:
            if hasattr(key, 'char') and key.char:
                if not self._is_recording_text:
                    self._is_recording_text = True
                    self._text_start_time = time.time()
                self._recorded_keys.append(key.char)
            else:
                if self._is_recording_text:
                    self._flush_text_input()
                
                key_name = self._get_key_name(key)
                if key_name:
                    modifier_keys = ['ctrl', 'alt', 'shift', 'cmd', 'win']
                    if key_name.lower() in modifier_keys:
                        return
                    
                    action = Action(
                        action_type=ActionType.KEY_PRESS,
                        params={'key': key_name}
                    )
                    self._add_action(action)
        except Exception as e:
            print(f"Key press error: {e}")
    
    def _on_key_release(self, key):
        pass
    
    def _get_key_name(self, key) -> Optional[str]:
        key_map = {
            keyboard.Key.space: 'space',
            keyboard.Key.enter: 'enter',
            keyboard.Key.tab: 'tab',
            keyboard.Key.backspace: 'backspace',
            keyboard.Key.delete: 'delete',
            keyboard.Key.esc: 'escape',
            keyboard.Key.up: 'up',
            keyboard.Key.down: 'down',
            keyboard.Key.left: 'left',
            keyboard.Key.right: 'right',
            keyboard.Key.home: 'home',
            keyboard.Key.end: 'end',
            keyboard.Key.page_up: 'pageup',
            keyboard.Key.page_down: 'pagedown',
            keyboard.Key.caps_lock: 'capslock',
            keyboard.Key.f1: 'f1',
            keyboard.Key.f2: 'f2',
            keyboard.Key.f3: 'f3',
            keyboard.Key.f4: 'f4',
            keyboard.Key.f5: 'f5',
            keyboard.Key.f6: 'f6',
            keyboard.Key.f7: 'f7',
            keyboard.Key.f8: 'f8',
            keyboard.Key.f9: 'f9',
            keyboard.Key.f10: 'f10',
            keyboard.Key.f11: 'f11',
            keyboard.Key.f12: 'f12',
        }
        
        if key in key_map:
            return key_map[key]
        
        if hasattr(key, 'name'):
            return key.name
        
        return None
    
    def _flush_text_input(self):
        if not self._recorded_keys:
            self._is_recording_text = False
            return
        
        text = ''.join(self._recorded_keys)
        action = Action(
            action_type=ActionType.KEY_TYPE,
            params={'text': text, 'interval': 0.0}
        )
        self._add_action(action)
        
        self._recorded_keys = []
        self._is_recording_text = False
    
    def get_actions(self) -> List[Action]:
        if self._is_recording_text and self._recorded_keys:
            self._flush_text_input()
        return self.actions.copy()
    
    def clear_actions(self):
        self.actions = []
        self.last_action_time = time.time()
    
    def is_recording(self) -> bool:
        return self.state == RecordState.RECORDING
    
    def get_state(self) -> RecordState:
        return self.state
