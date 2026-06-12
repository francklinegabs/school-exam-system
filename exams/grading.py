"""KCSE-style grading: marks -> letter grade and points (A=12 ... E=1)."""

from decimal import Decimal

# (lower bound inclusive, grade, points)
GRADE_BANDS = [
    (80, "A", 12),
    (75, "A-", 11),
    (70, "B+", 10),
    (65, "B", 9),
    (60, "B-", 8),
    (55, "C+", 7),
    (50, "C", 6),
    (45, "C-", 5),
    (40, "D+", 4),
    (35, "D", 3),
    (30, "D-", 2),
    (0, "E", 1),
]

POINTS_TO_GRADE = {points: grade for _, grade, points in GRADE_BANDS}


def grade_for(score) -> tuple[str, int]:
    """Return (letter, points) for a percentage score."""
    score = float(score)
    if not 0 <= score <= 100:
        raise ValueError(f"score {score} out of range 0-100")
    for lower, letter, points in GRADE_BANDS:
        if score >= lower:
            return letter, points
    return "E", 1  # unreachable, bands cover 0


def mean_grade(mean_points: float | Decimal) -> str:
    """Map mean points (1-12) to the nearest grade letter, KNEC style."""
    rounded = max(1, min(12, round(float(mean_points))))
    return POINTS_TO_GRADE[rounded]
