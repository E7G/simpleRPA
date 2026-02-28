import time
import threading
from typing import List, Callable, Optional, Tuple
from enum import Enum
from .actions import Action


class PlayerState(Enum):
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"


class Player:
    def __init__(self, tab_key: str = "", local_group_manager=None):
        self._tab_key = tab_key
        self._state = PlayerState.IDLE
        self._state_lock = threading.Lock()
        self.actions: List[Action] = []
        self.current_index: int = 0
        self.speed: float = 1.0
        self.repeat_count: int = 1
        self.current_repeat: int = 0
        self.infinite_loop: bool = False
        self.timeout_seconds: float = 0
        self._local_group_manager = local_group_manager
        
        self._thread: Optional[threading.Thread] = None
        self._pause_event = threading.Event()
        self._stop_flag = False
        self._window_offset: Optional[Tuple[int, int]] = None
        self._start_time: float = 0
        
        self._callbacks = {
            'on_action_start': [],
            'on_action_end': [],
            'on_state_changed': [],
            'on_progress': [],
            'on_error': [],
            'on_finished': [],
            'on_repeat_changed': []
        }
    
    def set_local_group_manager(self, manager):
        self._local_group_manager = manager
    
    def get_local_group_manager(self):
        return self._local_group_manager
    
    @property
    def state(self) -> PlayerState:
        with self._state_lock:
            return self._state
    
    @state.setter
    def state(self, value: PlayerState):
        with self._state_lock:
            self._state = value
    
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
    
    def set_actions(self, actions: List[Action]):
        if self.state != PlayerState.IDLE:
            return
        self.actions = actions.copy()
    
    def set_speed(self, speed: float):
        self.speed = max(0.1, min(10.0, speed))
    
    def set_repeat_count(self, count: int):
        self.repeat_count = max(1, count)
    
    def set_infinite_loop(self, enabled: bool):
        self.infinite_loop = enabled
    
    def set_timeout(self, seconds: float):
        self.timeout_seconds = max(0, seconds)
    
    def set_window_offset(self, offset: Optional[Tuple[int, int]]):
        self._window_offset = offset
    
    def play(self):
        if self.state == PlayerState.PLAYING:
            return
        
        if not self.actions:
            return
        
        if self.state == PlayerState.PAUSED:
            self.state = PlayerState.PLAYING
            self._pause_event.set()
            self._emit('on_state_changed', self.state)
            return
        
        self.state = PlayerState.PLAYING
        self.current_index = 0
        self.current_repeat = 0
        self._stop_flag = False
        self._pause_event.set()
        self._start_time = time.time()
        
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        
        self._emit('on_state_changed', self.state)
    
    def pause(self):
        if self.state == PlayerState.PLAYING:
            self.state = PlayerState.PAUSED
            self._pause_event.clear()
            self._emit('on_state_changed', self.state)
    
    def resume(self):
        if self.state == PlayerState.PAUSED:
            self.state = PlayerState.PLAYING
            self._pause_event.set()
            self._emit('on_state_changed', self.state)
    
    def toggle_pause(self) -> PlayerState:
        with self._state_lock:
            if self._state == PlayerState.PLAYING:
                self._state = PlayerState.PAUSED
                self._pause_event.clear()
                result_state = self._state
            elif self._state == PlayerState.PAUSED:
                self._state = PlayerState.PLAYING
                self._pause_event.set()
                result_state = self._state
            else:
                result_state = self._state
        
        self._emit('on_state_changed', result_state)
        return result_state
    
    def stop(self):
        current_state = self.state
        if current_state in [PlayerState.PLAYING, PlayerState.PAUSED]:
            self._stop_flag = True
            self._pause_event.set()
            self.state = PlayerState.STOPPED
            self._emit('on_state_changed', self.state)
    
    def stop_and_wait(self, timeout: float = 2.0) -> bool:
        current_state = self.state
        if current_state in [PlayerState.PLAYING, PlayerState.PAUSED]:
            self._stop_flag = True
            self._pause_event.set()
            
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=timeout)
                if self._thread.is_alive():
                    return False
            
            self.state = PlayerState.IDLE
        return True
    
    def _interruptible_sleep(self, seconds: float):
        end_time = time.time() + seconds
        while time.time() < end_time:
            if self._stop_flag:
                return
            sleep_time = min(0.05, end_time - time.time())
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    @property
    def tab_key(self) -> str:
        return self._tab_key
    
    def _run(self):
        completed_actions = 0
        repeat_count = 0
        
        while True:
            if self._stop_flag:
                self.state = PlayerState.IDLE
                self._emit('on_state_changed', self.state)
                self._emit('on_finished', False)
                return
            
            if self.timeout_seconds > 0:
                elapsed = time.time() - self._start_time
                if elapsed >= self.timeout_seconds:
                    self.state = PlayerState.IDLE
                    self._emit('on_state_changed', self.state)
                    self._emit('on_finished', False)
                    return
            
            if not self.infinite_loop and repeat_count >= self.repeat_count:
                break
            
            self.current_repeat = repeat_count
            self._emit('on_repeat_changed', repeat_count + 1)
            
            for i, action in enumerate(self.actions):
                if self._stop_flag:
                    self.state = PlayerState.IDLE
                    self._emit('on_state_changed', self.state)
                    self._emit('on_finished', False)
                    return
                
                if self.timeout_seconds > 0:
                    elapsed = time.time() - self._start_time
                    if elapsed >= self.timeout_seconds:
                        self.state = PlayerState.IDLE
                        self._emit('on_state_changed', self.state)
                        self._emit('on_finished', False)
                        return
                
                self._pause_event.wait()
                
                if self._stop_flag:
                    self.state = PlayerState.IDLE
                    self._emit('on_state_changed', self.state)
                    self._emit('on_finished', False)
                    return
                
                self.current_index = i
                
                if not action.check_condition():
                    print(f"[条件跳过] {action.description} - 条件不满足: {action.condition}")
                    completed_actions += 1
                    self._emit('on_progress', -1, i, repeat_count)
                    continue
                
                adjusted_delay_before = action.delay_before / self.speed if self.speed > 0 else action.delay_before
                adjusted_delay_after = action.delay_after / self.speed if self.speed > 0 else action.delay_after
                
                if adjusted_delay_before > 0:
                    self._interruptible_sleep(adjusted_delay_before)
                
                if self._stop_flag:
                    self.state = PlayerState.IDLE
                    self._emit('on_state_changed', self.state)
                    self._emit('on_finished', False)
                    return
                
                self._emit('on_action_start', action, i)
                
                try:
                    success = action.execute(window_offset=self._window_offset, should_stop=lambda: self._stop_flag, local_group_manager=self._local_group_manager)
                    self._emit('on_action_end', action, i, success)
                except Exception as e:
                    self._emit('on_error', action, i, str(e))
                    self._emit('on_action_end', action, i, False)
                
                completed_actions += 1
                self._emit('on_progress', -1, i, repeat_count)
                
                if adjusted_delay_after > 0:
                    self._interruptible_sleep(adjusted_delay_after)
            
            repeat_count += 1
        
        self.state = PlayerState.IDLE
        self._emit('on_state_changed', self.state)
        self._emit('on_finished', True)
    
    def get_state(self) -> PlayerState:
        return self.state
    
    def get_progress(self) -> Tuple[int, int, int]:
        return self.current_index, len(self.actions), self.current_repeat
    
    def is_playing(self) -> bool:
        return self.state == PlayerState.PLAYING
    
    def is_paused(self) -> bool:
        return self.state == PlayerState.PAUSED
    
    def execute_single_action(self, index: int, window_offset: Optional[Tuple[int, int]] = None) -> bool:
        if index < 0 or index >= len(self.actions):
            return False
        
        action = self.actions[index]
        
        adjusted_delay_before = action.delay_before / self.speed if self.speed > 0 else action.delay_before
        adjusted_delay_after = action.delay_after / self.speed if self.speed > 0 else action.delay_after
        
        if adjusted_delay_before > 0:
            time.sleep(adjusted_delay_before)
        
        self._emit('on_action_start', action, index)
        
        try:
            success = action.execute(window_offset=window_offset or self._window_offset, should_stop=lambda: self._stop_flag)
            self._emit('on_action_end', action, index, success)
            
            if adjusted_delay_after > 0:
                time.sleep(adjusted_delay_after)
            
            return success
        except Exception as e:
            self._emit('on_error', action, index, str(e))
            self._emit('on_action_end', action, index, False)
            raise
