from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from src.tasks import (
    get_task_easy,
    get_task_hard,
    get_task_medium,
    grade_easy,
    grade_hard,
    grade_medium,
)

TASK_REGISTRY: Dict[str, Dict[str, Any]] = {}

try:
    from openenv.tasks import TASK_REGISTRY as _OPENENV_TASK_REGISTRY  # type: ignore
    from openenv.tasks import register_task as _openenv_register_task  # type: ignore
except Exception:
    _OPENENV_TASK_REGISTRY = None
    _openenv_register_task = None


def _as_result(score: float, done: bool = True) -> Dict[str, Any]:
    return {"reward": float(score), "done": bool(done)}


def _try_register_with_openenv(
    task_id: str,
    task_loader: Callable[[], Any],
    grader: Callable[..., Dict[str, Any]],
) -> bool:
    if _openenv_register_task is None:
        return False

    # Adaptively call the upstream decorator across common signatures.
    attempts = [
        lambda: _openenv_register_task(task_id=task_id, grader=grader)(task_loader),
        lambda: _openenv_register_task(task_id, grader=grader)(task_loader),
        lambda: _openenv_register_task(task_id=task_id)(task_loader),
        lambda: _openenv_register_task(task_id)(task_loader),
        lambda: _openenv_register_task(task_loader),
    ]

    for attempt in attempts:
        try:
            attempt()
            return True
        except Exception:
            continue
    return False


def register_task(task_id: str, grader: Optional[Callable[..., Dict[str, Any]]] = None) -> Callable:
    def decorator(task_loader: Callable[[], Any]) -> Callable[[], Any]:
        if grader is None:
            raise ValueError(f"grader is required for task '{task_id}'")

        _try_register_with_openenv(task_id=task_id, task_loader=task_loader, grader=grader)

        TASK_REGISTRY[task_id] = {
            "id": task_id,
            "task_loader": task_loader,
            "entrypoint": task_loader,
            "grader": grader,
        }
        if isinstance(_OPENENV_TASK_REGISTRY, dict):
            _OPENENV_TASK_REGISTRY[task_id] = TASK_REGISTRY[task_id]
        return task_loader

    return decorator


def grade_easy_result(final_state: Any = None, done: bool = True) -> Dict[str, Any]:
    score = 0.0 if final_state is None else grade_easy(final_state)
    return _as_result(score, done=done)


def grade_medium_result(final_state: Any = None, done: bool = True) -> Dict[str, Any]:
    score = 0.0 if final_state is None else grade_medium(final_state)
    return _as_result(score, done=done)


def grade_hard_result(final_state: Any = None, done: bool = True) -> Dict[str, Any]:
    score = 0.0 if final_state is None else grade_hard(final_state)
    return _as_result(score, done=done)


@register_task("easy-memory-leak", grader=grade_easy_result)
def easy_memory_leak():
    return get_task_easy()


@register_task("medium-traffic-spike", grader=grade_medium_result)
def medium_traffic_spike():
    return get_task_medium()


@register_task("hard-cascading-failure", grader=grade_hard_result)
def hard_cascading_failure():
    return get_task_hard()


# Keep direct aliases for validators that import by conventional names.
get_task_easy = easy_memory_leak
get_task_medium = medium_traffic_spike
get_task_hard = hard_cascading_failure


__all__ = [
    "TASK_REGISTRY",
    "register_task",
    "easy_memory_leak",
    "medium_traffic_spike",
    "hard_cascading_failure",
    "get_task_easy",
    "get_task_medium",
    "get_task_hard",
    "grade_easy_result",
    "grade_medium_result",
    "grade_hard_result",
]
