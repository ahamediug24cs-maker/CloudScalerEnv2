from src.tasks import grade_easy, grade_medium, grade_hard

class EasyGrader:
    def grade(self, final_state=None):
        if final_state is None:
            return 0.5
        return grade_easy(final_state)

class MediumGrader:
    def grade(self, final_state=None):
        if final_state is None:
            return 0.5
        return grade_medium(final_state)

class HardGrader:
    def grade(self, final_state=None):
        if final_state is None:
            return 0.5
        return grade_hard(final_state)

__all__ = ["EasyGrader", "MediumGrader", "HardGrader", "grade_easy", "grade_medium", "grade_hard"]
