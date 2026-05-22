"""定时任务调度服务。"""

import uuid
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Callable, Dict, Any

from .task_runner import TaskRunner, RunResult


class ScheduleType(str, Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    INTERVAL = "interval"


WEEKDAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


@dataclass
class ScheduledTask:
    id: str = ""
    name: str = ""
    script_path: str = ""
    schedule_type: str = ScheduleType.DAILY.value
    time_str: str = "09:00"
    weekdays: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])
    interval_minutes: int = 60
    enabled: bool = True
    speed: float = 1.0
    repeat_count: int = 1
    last_run: str = ""
    last_result: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat(timespec='seconds')

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScheduledTask':
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', ''),
            script_path=data.get('script_path', ''),
            schedule_type=data.get('schedule_type', ScheduleType.DAILY.value),
            time_str=data.get('time_str', '09:00'),
            weekdays=data.get('weekdays', [0, 1, 2, 3, 4]),
            interval_minutes=data.get('interval_minutes', 60),
            enabled=data.get('enabled', True),
            speed=data.get('speed', 1.0),
            repeat_count=data.get('repeat_count', 1),
            last_run=data.get('last_run', ''),
            last_result=data.get('last_result', ''),
            created_at=data.get('created_at', ''),
        )

    def schedule_summary(self) -> str:
        st = self.schedule_type
        if st == ScheduleType.ONCE.value:
            return f"单次 {self.time_str}"
        if st == ScheduleType.DAILY.value:
            return f"每天 {self.time_str}"
        if st == ScheduleType.WEEKLY.value:
            days = ", ".join(WEEKDAY_LABELS[d] for d in sorted(self.weekdays) if 0 <= d < 7)
            return f"每周 {days} {self.time_str}"
        if st == ScheduleType.INTERVAL.value:
            if self.interval_minutes >= 60:
                h = self.interval_minutes // 60
                m = self.interval_minutes % 60
                return f"每 {h} 小时" + (f" {m} 分" if m else "")
            return f"每 {self.interval_minutes} 分钟"
        return self.time_str

    def script_basename(self) -> str:
        import os
        return os.path.basename(self.script_path) if self.script_path else "未选择脚本"


class SchedulerService:
    """后台定时检查并触发任务。"""

    _instance: Optional['SchedulerService'] = None

    def __init__(self):
        self._tasks: List[ScheduledTask] = []
        self._runner = TaskRunner()
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._check_interval = 30
        self._last_fired: Dict[str, str] = {}
        self._on_triggered: List[Callable[[ScheduledTask], None]] = []
        self._on_completed: List[Callable[[ScheduledTask, RunResult], None]] = []
        self._on_error: List[Callable[[ScheduledTask, str], None]] = []
        self._is_executing = False

    @classmethod
    def get_instance(cls) -> 'SchedulerService':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def tasks(self) -> List[ScheduledTask]:
        return list(self._tasks)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_executing(self) -> bool:
        return self._is_executing

    def add_callback(self, event: str, callback: Callable):
        if event == 'on_triggered':
            self._on_triggered.append(callback)
        elif event == 'on_completed':
            self._on_completed.append(callback)
        elif event == 'on_error':
            self._on_error.append(callback)

    def load_tasks(self, tasks_data: List[Dict[str, Any]]):
        with self._lock:
            self._tasks = [ScheduledTask.from_dict(t) for t in tasks_data]

    def get_tasks_data(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._tasks]

    def add_task(self, task: ScheduledTask) -> ScheduledTask:
        with self._lock:
            self._tasks.append(task)
        return task

    def update_task(self, task: ScheduledTask):
        with self._lock:
            for i, t in enumerate(self._tasks):
                if t.id == task.id:
                    self._tasks[i] = task
                    return
            self._tasks.append(task)

    def remove_task(self, task_id: str):
        with self._lock:
            self._tasks = [t for t in self._tasks if t.id != task_id]
        self._last_fired.pop(task_id, None)

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        return next((t for t in self._tasks if t.id == task_id), None)

    def set_task_enabled(self, task_id: str, enabled: bool):
        task = self.get_task(task_id)
        if task:
            task.enabled = enabled

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._runner.stop()

    def run_now(self, task_id: str) -> bool:
        task = self.get_task(task_id)
        if not task:
            return False
        threading.Thread(target=self._execute_task, args=(task,), daemon=True).start()
        return True

    def get_next_run_hint(self, task: ScheduledTask) -> str:
        if not task.enabled:
            return "已禁用"
        now = datetime.now()
        try:
            if task.schedule_type == ScheduleType.INTERVAL.value:
                if task.last_run:
                    last = datetime.fromisoformat(task.last_run)
                    nxt = last + timedelta(minutes=task.interval_minutes)
                    if nxt > now:
                        return nxt.strftime("%m-%d %H:%M")
                return "即将检查"
            hour, minute = map(int, task.time_str.split(':'))
            candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if task.schedule_type == ScheduleType.ONCE.value:
                return candidate.strftime("%Y-%m-%d %H:%M") if candidate > now else "已过期"
            if task.schedule_type == ScheduleType.DAILY.value:
                if candidate <= now:
                    candidate += timedelta(days=1)
                return candidate.strftime("%m-%d %H:%M")
            if task.schedule_type == ScheduleType.WEEKLY.value:
                for d in range(8):
                    day = (now.weekday() + d) % 7
                    if day in task.weekdays:
                        target = now + timedelta(days=d)
                        target = target.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        if target > now:
                            return target.strftime("%m-%d %H:%M")
                return "—"
        except Exception:
            pass
        return "—"

    def _loop(self):
        while self._running:
            try:
                self._check_due_tasks()
            except Exception as e:
                print(f"[Scheduler] check error: {e}")
            for _ in range(self._check_interval):
                if not self._running:
                    break
                threading.Event().wait(1)

    def _check_due_tasks(self):
        if self._is_executing:
            return
        now = datetime.now()
        for task in list(self._tasks):
            if not task.enabled or not task.script_path:
                continue
            if self._should_run(task, now):
                fire_key = f"{task.id}_{now.strftime('%Y%m%d%H%M')}"
                if task.schedule_type == ScheduleType.INTERVAL.value:
                    fire_key = task.id
                    if task.last_run:
                        try:
                            last = datetime.fromisoformat(task.last_run)
                            if now - last < timedelta(minutes=task.interval_minutes):
                                continue
                        except ValueError:
                            pass
                elif fire_key in self._last_fired:
                    continue
                self._last_fired[fire_key] = now.isoformat()
                threading.Thread(target=self._execute_task, args=(task,), daemon=True).start()

    def _should_run(self, task: ScheduledTask, now: datetime) -> bool:
        try:
            hour, minute = map(int, task.time_str.split(':'))
        except ValueError:
            hour, minute = 9, 0

        st = task.schedule_type
        if st == ScheduleType.INTERVAL.value:
            if not task.last_run:
                return True
            try:
                last = datetime.fromisoformat(task.last_run)
                return now - last >= timedelta(minutes=max(1, task.interval_minutes))
            except ValueError:
                return True

        if now.hour != hour or now.minute != minute:
            return False

        if st == ScheduleType.ONCE.value:
            if task.last_run:
                return False
            return True
        if st == ScheduleType.DAILY.value:
            return True
        if st == ScheduleType.WEEKLY.value:
            return now.weekday() in task.weekdays
        return False

    def _execute_task(self, task: ScheduledTask):
        if self._is_executing:
            return
        self._is_executing = True
        for cb in self._on_triggered:
            try:
                cb(task)
            except Exception:
                pass

        try:
            import os
            if not os.path.exists(task.script_path):
                raise FileNotFoundError(f"脚本不存在: {task.script_path}")

            self._runner.reset()
            path = task.script_path.lower()
            if path.endswith('.scripts.json'):
                result = self._runner.run_batch_list(task.script_path)
            else:
                result = self._runner.run_script_file(
                    task.script_path,
                    speed=task.speed,
                    repeat_count=task.repeat_count,
                )

            task.last_run = datetime.now().isoformat(timespec='seconds')
            task.last_result = "成功" if result.success else result.message
            self.update_task(task)

            for cb in self._on_completed:
                try:
                    cb(task, result)
                except Exception:
                    pass
        except Exception as e:
            task.last_run = datetime.now().isoformat(timespec='seconds')
            task.last_result = str(e)
            self.update_task(task)
            for cb in self._on_error:
                try:
                    cb(task, str(e))
                except Exception:
                    pass
        finally:
            self._is_executing = False
