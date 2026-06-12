from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .forms import TeacherSignUpForm
from .models import (ClassRoom, Exam, Mark, Student, Subject, Teacher,
                     TeachingAssignment)
from .results import class_results, form_results, student_report


def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = TeacherSignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(
            request,
            "Welcome! Your teacher account is ready. The admin will assign "
            "you subjects and classes before you can enter marks.")
        return redirect("dashboard")
    return render(request, "registration/signup.html", {"form": form})


def _teacher_or_none(user) -> Teacher | None:
    return getattr(user, "teacher", None)


@login_required
def dashboard(request):
    teacher = _teacher_or_none(request.user)
    assignments = (teacher.assignments.select_related("subject", "classroom__stream")
                   if teacher else [])
    return render(request, "exams/dashboard.html", {
        "teacher": teacher,
        "assignments": assignments,
        "exams": Exam.objects.all()[:12],
        "classrooms": ClassRoom.objects.select_related("stream"),
    })


@login_required
def mark_entry(request, assignment_id: int, exam_id: int):
    assignment = get_object_or_404(
        TeachingAssignment.objects.select_related(
            "subject", "classroom__stream", "teacher__user"),
        pk=assignment_id)
    exam = get_object_or_404(Exam, pk=exam_id)

    teacher = _teacher_or_none(request.user)
    if not request.user.is_staff and (teacher is None or assignment.teacher_id != teacher.id):
        raise PermissionDenied("You can only enter marks for your own classes.")
    if exam.published:
        messages.error(request, f"{exam} is published — marks are locked.")
        return redirect("dashboard")

    students = list(assignment.classroom.students.filter(
        active=True, subjects=assignment.subject))
    existing = {m.student_id: m.score for m in Mark.objects.filter(
        exam=exam, subject=assignment.subject, student__in=students)}

    if request.method == "POST":
        errors, saved = [], 0
        with transaction.atomic():
            for student in students:
                raw = request.POST.get(f"score_{student.id}", "").strip()
                if raw == "":
                    continue  # blank = not sat / not yet entered
                try:
                    score = Decimal(raw)
                except InvalidOperation:
                    errors.append(f"{student.full_name}: '{raw}' is not a number")
                    continue
                if not 0 <= score <= exam.out_of:
                    errors.append(f"{student.full_name}: {score} is outside 0–{exam.out_of}")
                    continue
                Mark.objects.update_or_create(
                    exam=exam, student=student, subject=assignment.subject,
                    defaults={"score": score, "entered_by": teacher})
                saved += 1
        if saved:
            messages.success(request, f"Saved {saved} marks for {assignment.subject}.")
        for err in errors:
            messages.error(request, err)
        if not errors:
            return redirect("dashboard")
        existing = {m.student_id: m.score for m in Mark.objects.filter(
            exam=exam, subject=assignment.subject, student__in=students)}

    rows = [{"student": s, "score": existing.get(s.id, "")} for s in students]
    return render(request, "exams/mark_entry.html", {
        "assignment": assignment, "exam": exam, "rows": rows,
    })


@login_required
def class_results_view(request, classroom_id: int, exam_id: int):
    classroom = get_object_or_404(
        ClassRoom.objects.select_related("stream"), pk=classroom_id)
    exam = get_object_or_404(Exam, pk=exam_id)
    subjects = Subject.objects.filter(students__classroom=classroom).distinct()
    return render(request, "exams/class_results.html", {
        "classroom": classroom, "exam": exam, "subjects": subjects,
        "lines": class_results(classroom, exam),
    })


@login_required
def form_results_view(request, form: int, exam_id: int):
    exam = get_object_or_404(Exam, pk=exam_id)
    subjects = Subject.objects.filter(students__classroom__form=form).distinct()
    return render(request, "exams/form_results.html", {
        "form": form, "exam": exam, "subjects": subjects,
        "lines": form_results(form, exam),
    })


@login_required
def report_view(request, student_id: int, exam_id: int):
    student = get_object_or_404(
        Student.objects.select_related("classroom__stream"), pk=student_id)
    exam = get_object_or_404(Exam, pk=exam_id)
    report = student_report(student, exam)
    subject_rows = []
    if report["line"]:
        for subject in student.subjects.all():
            entry = report["line"]["scores"].get(subject.id)
            subject_rows.append({
                "subject": subject,
                "score": entry[0] if entry else None,
                "grade": entry[1] if entry else "—",
                "points": entry[2] if entry else None,
            })
    return render(request, "exams/report.html", {
        "student": student, "exam": exam, "report": report,
        "subject_rows": subject_rows,
        "other_exams": Exam.objects.exclude(pk=exam.pk)[:6],
    })
