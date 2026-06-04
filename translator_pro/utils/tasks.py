from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from threading import Lock, Semaphore, Thread
from typing import Any, Callable, Dict, Optional
import queue
import uuid


class TaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    DONE = "done"
    FAILED = "failed"


@dataclass
class BackgroundTask:
    title: str
    kind: str
    payload: Dict[str, Any]
    id: str = field(default_factory=lambda: f"task-{uuid.uuid4().hex[:10]}")
    state: TaskState = TaskState.PENDING
    progress_done: int = 0
    progress_total: int = 0
    message: str = "等待中"
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    output_path: str = ""
    error: str = ""
    pause_requested: bool = False
    cancel_requested: bool = False


class BackgroundTaskManager:
    def __init__(self, max_concurrent: int = 2) -> None:
        self._tasks: Dict[str, BackgroundTask] = {}
        self._lock = Lock()
        self._events: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self._sem = Semaphore(max(1, int(max_concurrent)))

    @property
    def events(self) -> "queue.Queue[Dict[str, Any]]":
        return self._events

    def configure_concurrency(self, max_concurrent: int) -> None:
        # A new semaphore is enough for future tasks. Existing running tasks continue.
        self._sem = Semaphore(max(1, int(max_concurrent)))

    def add_task(self, task: BackgroundTask, runner: Callable[[BackgroundTask, Callable[..., None]], None]) -> str:
        with self._lock:
            self._tasks[task.id] = task
        thread = Thread(target=self._run, args=(task.id, runner), daemon=True)
        thread.start()
        self.emit(task.id, "created", message=task.message)
        return task.id

    def _run(self, task_id: str, runner: Callable[[BackgroundTask, Callable[..., None]], None]) -> None:
        with self._sem:
            task = self.get(task_id)
            if not task:
                return
            task.state = TaskState.RUNNING
            self.emit(task_id, "state", state=task.state.value, message="运行中")
            try:
                runner(task, self.emit)
                if task.cancel_requested:
                    task.state = TaskState.CANCELLED
                    task.message = "已取消"
                elif task.state not in (TaskState.FAILED, TaskState.CANCELLED):
                    task.state = TaskState.DONE
                    task.message = "已完成"
                self.emit(task_id, "state", state=task.state.value, message=task.message, output_path=task.output_path)
            except Exception as exc:
                task.state = TaskState.FAILED
                task.error = str(exc)
                task.message = "失败"
                self.emit(task_id, "error", state=task.state.value, error=task.error, message=task.message)

    def emit(self, task_id: str, event: str, **kwargs: Any) -> None:
        task = self.get(task_id)
        if task:
            for k, v in kwargs.items():
                if hasattr(task, k):
                    setattr(task, k, v)
        self._events.put({"task_id": task_id, "event": event, **kwargs})

    def get(self, task_id: str) -> Optional[BackgroundTask]:
        with self._lock:
            return self._tasks.get(task_id)

    def all(self) -> Dict[str, BackgroundTask]:
        with self._lock:
            return dict(self._tasks)

    def pause(self, task_id: str) -> None:
        task = self.get(task_id)
        if task and task.state == TaskState.RUNNING:
            task.pause_requested = True
            task.state = TaskState.PAUSED
            self.emit(task_id, "state", state=task.state.value, message="已暂停")

    def resume(self, task_id: str) -> None:
        task = self.get(task_id)
        if task and task.state == TaskState.PAUSED:
            task.pause_requested = False
            task.state = TaskState.RUNNING
            self.emit(task_id, "state", state=task.state.value, message="运行中")

    def cancel(self, task_id: str) -> None:
        task = self.get(task_id)
        if task:
            task.cancel_requested = True
            task.state = TaskState.CANCELLED
            self.emit(task_id, "state", state=task.state.value, message="正在取消/已取消")
