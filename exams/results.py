"""Results processing: collect marks for an exam and produce ranked results.

A result line for one student looks like:
    {student, scores: {subject_id: (score, grade, points)},
     total, mean_score, total_points, mean_points, mean_grade, rank}
Ranking uses total points, with total marks as the tiebreaker. Students tied
on both share a rank (competition ranking: 1, 2, 2, 4).
"""

from __future__ import annotations

from .grading import grade_for, mean_grade
from .models import ClassRoom, Exam, Mark, Student


def _result_line(student: Student, marks: list[Mark]) -> dict:
    scores = {}
    total = 0.0
    total_points = 0
    for mark in marks:
        letter, points = grade_for(mark.score)
        scores[mark.subject_id] = (mark.score, letter, points)
        total += float(mark.score)
        total_points += points
    n = len(marks)
    return {
        "student": student,
        "scores": scores,
        "subjects_done": n,
        "total": total,
        "mean_score": total / n if n else 0.0,
        "total_points": total_points,
        "mean_points": total_points / n if n else 0.0,
        "mean_grade": mean_grade(total_points / n) if n else "—",
    }


def _rank(lines: list[dict]) -> list[dict]:
    lines.sort(key=lambda r: (-r["total_points"], -r["total"]))
    prev_key, prev_rank = None, 0
    for i, line in enumerate(lines, start=1):
        key = (line["total_points"], line["total"])
        line["rank"] = prev_rank if key == prev_key else i
        prev_key, prev_rank = key, line["rank"]
    return lines


def _results_for_students(students, exam: Exam) -> list[dict]:
    marks_by_student: dict[int, list[Mark]] = {}
    qs = (Mark.objects.filter(exam=exam, student__in=students)
          .select_related("subject"))
    for mark in qs:
        marks_by_student.setdefault(mark.student_id, []).append(mark)
    lines = [_result_line(s, marks_by_student.get(s.id, [])) for s in students]
    return _rank(lines)


def class_results(classroom: ClassRoom, exam: Exam) -> list[dict]:
    """Ranked results for one class (stream)."""
    students = list(classroom.students.filter(active=True))
    return _results_for_students(students, exam)


def form_results(form: int, exam: Exam) -> list[dict]:
    """Ranked results for a whole form, merged across streams."""
    students = list(Student.objects.filter(active=True, classroom__form=form)
                    .select_related("classroom__stream"))
    return _results_for_students(students, exam)


def student_report(student: Student, exam: Exam) -> dict:
    """One student's report: per-subject grades plus class & form position."""
    in_class = class_results(student.classroom, exam)
    in_form = form_results(student.classroom.form, exam)
    own = next((r for r in in_class if r["student"].id == student.id), None)
    form_line = next((r for r in in_form if r["student"].id == student.id), None)
    return {
        "line": own,
        "class_rank": own["rank"] if own else None,
        "class_size": len(in_class),
        "form_rank": form_line["rank"] if form_line else None,
        "form_size": len(in_form),
    }
