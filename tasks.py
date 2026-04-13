from src.tasks import (
    TASK_REGISTRY,
    TaskGrader,
    get_task_easy,
    get_task_hard,
    get_task_medium,
    grade_easy,
    grade_hard,
    grade_medium,
)

easy_memory_leak = get_task_easy
medium_traffic_spike = get_task_medium
hard_cascading_failure = get_task_hard


def grade_easy_result(final_state=None):
    return grade_easy(final_state)


def grade_medium_result(final_state=None):
    return grade_medium(final_state)


def grade_hard_result(final_state=None):
    return grade_hard(final_state)


__all__ = [
    "TaskGrader",
    "get_task_easy",
    "get_task_medium",
    "get_task_hard",
    "grade_easy",
    "grade_medium",
    "grade_hard",
    "grade_easy_result",
    "grade_medium_result",
    "grade_hard_result",
    "easy_memory_leak",
    "medium_traffic_spike",
    "hard_cascading_failure",
    "TASK_REGISTRY",
]