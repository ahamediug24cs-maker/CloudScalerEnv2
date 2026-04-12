from .models import EnvState
from .tasks import grade_easy as _grade_easy
from .tasks import grade_hard as _grade_hard
from .tasks import grade_medium as _grade_medium


def grade_easy(final_state: EnvState) -> float:
    """Compatibility wrapper for easy task grader."""
    if final_state is None:
        return 0.0
    return _grade_easy(final_state)


def grade_medium(final_state: EnvState) -> float:
    """Compatibility wrapper for medium task grader."""
    if final_state is None:
        return 0.0
    return _grade_medium(final_state)


def grade_hard(final_state: EnvState) -> float:
    """Compatibility wrapper for hard task grader."""
    if final_state is None:
        return 0.0
    return _grade_hard(final_state)


class EasyGrader:
    def grade(self, final_state: EnvState = None) -> float:
        return grade_easy(final_state)


class MediumGrader:
    def grade(self, final_state: EnvState = None) -> float:
        return grade_medium(final_state)


class HardGrader:
    def grade(self, final_state: EnvState = None) -> float:
        return grade_hard(final_state)


__all__ = [
    "grade_easy",
    "grade_medium",
    "grade_hard",
    "EasyGrader",
    "MediumGrader",
    "HardGrader",
]
