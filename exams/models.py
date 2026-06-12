from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

FORM_CHOICES = [(i, f"Form {i}") for i in (1, 2, 3, 4)]
TERM_CHOICES = [(i, f"Term {i}") for i in (1, 2, 3)]


class Subject(models.Model):
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=10, unique=True)  # e.g. 121 for Maths

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.name


class Stream(models.Model):
    name = models.CharField(max_length=20, unique=True)  # e.g. East, West

    def __str__(self):
        return self.name


class ClassRoom(models.Model):
    form = models.PositiveSmallIntegerField(choices=FORM_CHOICES)
    stream = models.ForeignKey(Stream, on_delete=models.PROTECT)

    class Meta:
        unique_together = [("form", "stream")]
        ordering = ["form", "stream__name"]

    def __str__(self):
        return f"Form {self.form} {self.stream}"


class Student(models.Model):
    admission_no = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=100)
    classroom = models.ForeignKey(ClassRoom, on_delete=models.PROTECT,
                                  related_name="students")
    subjects = models.ManyToManyField(Subject, related_name="students")
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["admission_no"]

    def __str__(self):
        return f"{self.admission_no} {self.full_name}"


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    staff_no = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class TeachingAssignment(models.Model):
    """Which teacher enters marks for which subject in which class."""
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE,
                                related_name="assignments")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE)

    class Meta:
        unique_together = [("subject", "classroom")]  # one teacher per subject per class
        ordering = ["classroom__form", "classroom__stream__name", "subject__code"]

    def __str__(self):
        return f"{self.subject} — {self.classroom} ({self.teacher})"


class Exam(models.Model):
    name = models.CharField(max_length=50)  # e.g. Mid-Term, End-Term
    year = models.PositiveIntegerField()
    term = models.PositiveSmallIntegerField(choices=TERM_CHOICES)
    out_of = models.PositiveSmallIntegerField(default=100)
    published = models.BooleanField(
        default=False,
        help_text="Once published, results are visible and marks are locked.")

    class Meta:
        unique_together = [("name", "year", "term")]
        ordering = ["-year", "-term", "name"]

    def __str__(self):
        return f"{self.name} — Term {self.term} {self.year}"


class Mark(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="marks")
    student = models.ForeignKey(Student, on_delete=models.CASCADE,
                                related_name="marks")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    score = models.DecimalField(
        max_digits=5, decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(100)])
    entered_by = models.ForeignKey(Teacher, null=True, on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("exam", "student", "subject")]

    def __str__(self):
        return f"{self.student} {self.subject} {self.exam}: {self.score}"
