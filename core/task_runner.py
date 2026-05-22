"""脚本执行任务执行器 — 供执行面板与定时调度复用。"""

import os
import json
import time
import threading
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Dict, Any, Tuple

from .actions import Action, ActionType
from .action_group import LocalActionGroupManager
from .player import Player, PlayerState
from .exporter import Exporter
from .command_manager import CommandManager
from utils.window_utils import WindowUtils


@dataclass
class RunResult:
    success: bool
    message: str = ""
    actions_count: int = 0
    repeats: int = 0


@dataclass
class BatchScriptItem:
    id: str
    name: str
    path: str
    delay_before: float = 0.0
    repeat_count: int = 1
    enabled: bool = True
    actions: List[Action] = field(default_factory=list)
    local_group_manager: Optional[LocalActionGroupManager] = None


class TaskRunner:
    """统一执行 .rpa.json 单脚本或 .scripts.json 脚本列表。"""

    def __init__(self):
        self._window_utils = WindowUtils()
        self._stop_flag = threading.Event()

    def stop(self):
        self._stop_flag.set()

    def reset(self):
        self._stop_flag.clear()

    def is_stopped(self) -> bool:
        return self._stop_flag.is_set()

    def load_single_script(
        self, filepath: str
    ) -> Tuple[Optional[List[Action]], Optional[LocalActionGroupManager]]:
        if not os.path.exists(filepath):
            return None, None
        local_mgr = LocalActionGroupManager()
        result = Exporter.import_from_json(filepath, local_mgr)
        if result is None:
            return None, None
        actions = result if isinstance(result, list) else result.get('actions', [])
        return actions, local_mgr

    def load_batch_list(self, filepath: str) -> Tuple[List[BatchScriptItem], Dict[str, Any]]:
        meta: Dict[str, Any] = {}
        items: List[BatchScriptItem] = []
        if not os.path.exists(filepath):
            return items, meta

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        meta['window'] = data.get('window', {})
        meta['speed'] = data.get('speed', 1.0)
        meta['repeat'] = data.get('repeat', 1)
        meta['infinite'] = data.get('infinite', False)
        meta['launch_command_id'] = data.get('launch_command_id', '')

        for s in data.get('scripts', []):
            script_path = s.get('path', '')
            if not script_path or not os.path.exists(script_path):
                continue
            local_mgr = LocalActionGroupManager()
            result = Exporter.import_from_json(script_path, local_mgr)
            if result is None:
                continue
            actions = result if isinstance(result, list) else result.get('actions', [])
            if not actions:
                continue
            items.append(BatchScriptItem(
                id=s.get('id', script_path),
                name=s.get('name', os.path.basename(script_path)),
                path=script_path,
                delay_before=s.get('delay_before', 0),
                repeat_count=s.get('repeat_count', 1),
                enabled=s.get('enabled', True),
                actions=actions,
                local_group_manager=local_mgr,
            ))
        return items, meta

    def run_script_file(
        self,
        filepath: str,
        *,
        speed: float = 1.0,
        repeat_count: int = 1,
        infinite_loop: bool = False,
        window_hwnd: int = 0,
        window_title: str = "",
        launch_command_id: str = "",
        on_progress: Optional[Callable[[float, int, int], None]] = None,
        on_action_start: Optional[Callable[[Action, int], None]] = None,
    ) -> RunResult:
        self.reset()
        actions, local_mgr = self.load_single_script(filepath)
        if not actions:
            return RunResult(False, "无法加载脚本或脚本为空")

        hwnd, title = self._resolve_window(
            window_hwnd, window_title, launch_command_id
        )
        if launch_command_id and not hwnd:
            return RunResult(False, "启动命令后未找到目标窗口")

        return self._run_actions(
            actions, local_mgr,
            speed=speed, repeat_count=repeat_count, infinite_loop=infinite_loop,
            window_hwnd=hwnd, window_title=title,
            on_progress=on_progress, on_action_start=on_action_start,
        )

    def run_batch_list(
        self,
        filepath: str,
        *,
        on_progress: Optional[Callable[[float, int, int], None]] = None,
        on_script_start: Optional[Callable[[str, int], None]] = None,
    ) -> RunResult:
        self.reset()
        items, meta = self.load_batch_list(filepath)
        enabled = [i for i in items if i.enabled]
        if not enabled:
            return RunResult(False, "脚本列表为空或全部已禁用")

        speed = meta.get('speed', 1.0)
        hwnd = meta.get('window', {}).get('hwnd', 0)
        title = meta.get('window', {}).get('title', '')
        launch_id = meta.get('launch_command_id', '')

        hwnd, title = self._resolve_window(hwnd, title, launch_id)
        total = len(enabled)

        for idx, item in enumerate(enabled):
            if self.is_stopped():
                return RunResult(False, "已取消", repeats=idx)

            if on_script_start:
                on_script_start(item.name, idx)

            if on_progress:
                on_progress((idx + 1) / total, idx, 1)

            if item.delay_before > 0:
                time.sleep(item.delay_before)

            result = self._run_actions(
                item.actions, item.local_group_manager,
                speed=speed, repeat_count=item.repeat_count,
                window_hwnd=hwnd, window_title=title,
            )
            if not result.success:
                return RunResult(False, f"[{item.name}] {result.message}", repeats=idx + 1)

        return RunResult(True, "批量执行完成", actions_count=sum(len(i.actions) for i in enabled), repeats=total)

    def _resolve_window(
        self, hwnd: int, title: str, launch_command_id: str
    ) -> Tuple[int, str]:
        if hwnd:
            info = self._window_utils.get_window_by_hwnd(hwnd)
            if info:
                return hwnd, info.title
            return hwnd, title

        if not launch_command_id:
            return 0, title

        cmd_manager = CommandManager.get_instance()
        cmd = cmd_manager.get_command(launch_command_id)
        if not cmd:
            return 0, title

        success, _, _ = cmd_manager.check_and_launch(launch_command_id)
        if not success:
            return 0, title

        if cmd.delay_after_launch > 0:
            time.sleep(cmd.delay_after_launch)

        pattern = (cmd.window_title_pattern or cmd.name).lower()
        for _ in range(60):
            if self.is_stopped():
                break
            windows = self._window_utils.get_all_windows()
            for w in windows:
                if pattern in w.title.lower():
                    return w.hwnd, w.title
            time.sleep(0.5)
        return 0, title

    def _run_actions(
        self,
        actions: List[Action],
        local_mgr: Optional[LocalActionGroupManager],
        *,
        speed: float = 1.0,
        repeat_count: int = 1,
        infinite_loop: bool = False,
        window_hwnd: int = 0,
        window_title: str = "",
        on_progress: Optional[Callable[[float, int, int], None]] = None,
        on_action_start: Optional[Callable[[Action, int], None]] = None,
    ) -> RunResult:
        player = Player(tab_key="task_runner", local_group_manager=local_mgr)
        player.set_actions(actions)
        player.set_speed(speed)
        player.set_repeat_count(repeat_count)
        player.set_infinite_loop(infinite_loop)

        if on_progress:
            player.add_callback('on_progress', on_progress)
        if on_action_start:
            player.add_callback('on_action_start', on_action_start)

        if window_hwnd:
            player.set_window_hwnd(window_hwnd, self._window_utils)
            info = self._window_utils.get_window_by_hwnd(window_hwnd)
            if info:
                player.set_window_offset((info.x, info.y))
            self._window_utils.activate_window(window_hwnd)

        if window_title:
            player.set_window_title(window_title)
            for action in actions:
                if action.action_type in [
                    ActionType.ACTION_GROUP_REF, ActionType.IMAGE_CLICK,
                    ActionType.IMAGE_WAIT_CLICK, ActionType.IMAGE_CHECK,
                ]:
                    action.window_title = window_title
                if action.background_mode:
                    action.window_title = window_title

        player.play()
        while player.state not in (PlayerState.IDLE,):
            if self.is_stopped():
                player.stop()
                break
            time.sleep(0.1)

        success = player.state == PlayerState.IDLE and not self.is_stopped()
        return RunResult(
            success=success,
            message="执行完成" if success else "执行中断",
            actions_count=len(actions),
            repeats=player.current_repeat,
        )
