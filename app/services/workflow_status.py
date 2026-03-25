"""
工作流状态管理器
用于跟踪当前运行的工作流状态
"""

from typing import Optional, Dict, Any
from datetime import datetime
import asyncio

from app.services.account_context import get_account_id


def _account_key(account_id: Optional[str] = None) -> str:
    return (account_id or get_account_id() or "_default").strip() or "_default"


def _empty_status() -> Dict[str, Any]:
    return {
        "running": False,
        "current_step": None,
        "progress": 0,
        "started_at": None,
        "topic": None,
        "current_source": None,
    }


class WorkflowStatusManager:
    """管理工作流状态"""

    def __init__(self):
        self._status_by_account: Dict[str, Dict[str, Any]] = {
            _account_key(): _empty_status()
        }
        self._lock = asyncio.Lock()

    async def start_workflow(self, topic: str, account_id: Optional[str] = None):
        """开始工作流"""
        async with self._lock:
            self._status_by_account[_account_key(account_id)] = {
                "running": True,
                "current_step": "source_retriever",
                "progress": 0,
                "started_at": datetime.now().isoformat(),
                "topic": topic,
                "current_source": None,
            }

    async def update_step(
        self,
        step: str,
        progress: Optional[int] = None,
        current_source: Any = "UNCHANGED",
        account_id: Optional[str] = None,
    ):
        """更新当前步骤"""
        async with self._lock:
            status = self._status_by_account.setdefault(
                _account_key(account_id), _empty_status()
            )
            if step != status["current_step"] and current_source == "UNCHANGED":
                status["current_source"] = None

            status["current_step"] = step
            if progress is not None:
                status["progress"] = progress
            else:
                step_progress = {
                    "source_retriever": 10,
                    "reporter": 25,
                    "analyst": 40,
                    "debater": 60,
                    "writer": 80,
                    "image_generator": 95,
                }
                status["progress"] = step_progress.get(step, status["progress"])

            if current_source != "UNCHANGED":
                status["current_source"] = current_source

    async def finish_workflow(self, account_id: Optional[str] = None):
        """完成工作流"""
        async with self._lock:
            current = self._status_by_account.setdefault(
                _account_key(account_id), _empty_status()
            )
            self._status_by_account[_account_key(account_id)] = {
                "running": False,
                "current_step": None,
                "progress": 100,
                "started_at": current.get("started_at"),
                "topic": current.get("topic"),
                "current_source": None,
            }

    async def get_status(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        """获取当前状态"""
        async with self._lock:
            return self._status_by_account.setdefault(
                _account_key(account_id), _empty_status()
            ).copy()

    async def reset(self, account_id: Optional[str] = None):
        """重置状态"""
        async with self._lock:
            self._status_by_account[_account_key(account_id)] = _empty_status()


# 全局实例
workflow_status = WorkflowStatusManager()
