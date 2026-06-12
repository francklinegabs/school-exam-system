"""Seed the database with a realistic demo school.

Creates: 11 subjects, East/West streams for Forms 1-4, ~12 students per class,
5 teachers with logins, teaching assignments, two Term 1 exams, and marks.

    python manage.py seed_demo

Teacher logins are <username>/teacher123 (printed at the end).
Admin login: admin/admin123.
"""

import random

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from exams.models import (ClassRoom, Exam, Mark, Stream, Student, Subject,
                          Teacher, TeachingAssignment)

SUBJECTS = [
    ("101", "English"), ("102", "Kiswahili"), ("121", "Mathematics"),
    ("231", "Biology"), ("232", "Physics"), ("233", "Chemistry"),
    ("311", "History"), ("312", "Geography"), ("313", "CRE"),
    ("443", "Agriculture"), ("565", "Business Studies"),
]

FIRST_NAMES = [
    "Brian", "Faith", "Kevin", "Mercy", "Dennis", "Cynthia", "Collins",
    "Sharon", "Victor", "Naomi", "Felix", "Diana", "Samuel", "Esther",
    "George", "Lilian", "Moses", "Janet", "Peter", "Gladys",
]
LAST_NAMES = [
    "Otieno", "Wanjiku", "Kipchoge", "Achieng", "Mwangi", "Chebet",
    "Omondi", "Njeri", "Kiprop", "Akinyi", "Kamau", "Wafula", "Mutua",
    "Nekesa", "Karanja", "Atieno",
]

TEACHERS = [
    ("jotieno", "James", "Otieno", "TSC001"),
    ("mwanjiru", "Mary", "Wanjiru", "TSC002"),
    ("pkiprotich", "Paul", "Kiprotich", "TSC003"),
    ("gakinyi", "Grace", "Akinyi", "TSC004"),
    ("dmutua", "David", "Mutua", "TSC005"),
]


class Command(BaseCommand):
    help = __doc__

    @transaction.atomic
    def handle(self, *args, **options):
        if Student.objects.exists():
            self.stdout.write(self.style.WARNING(
                "Database already has students — nothing seeded."))
            return

        rng = random.Random(2026)

        subjects = {code: Subject.objects.create(code=code, name=name)
                    for code, name in SUBJECTS}
        core = [subjects[c] for c in ("101", "102", "121")]
        sciences = [subjects[c] for c in ("231", "232", "233")]
        humanities = [subjects[c] for c in ("311", "312", "313")]
        technical = [subjects[c] for c in ("443", "565")]

        streams = [Stream.objects.create(name=n) for n in ("East", "West")]
        classrooms = [ClassRoom.objects.create(form=f, stream=s)
                      for f in (1, 2, 3, 4) for s in streams]

        # Students: core + 2 sciences + 1 humanity + 1 technical (8 subjects)
        adm = 1000
        for classroom in classrooms:
            for _ in range(12):
                adm += 1
                student = Student.objects.create(
                    admission_no=str(adm),
                    full_name=f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
                    classroom=classroom)
                student.subjects.set(core + rng.sample(sciences, 2)
                                     + [rng.choice(humanities), rng.choice(technical)])

        # Teachers with logins
        teachers = []
        for username, first, last, staff_no in TEACHERS:
            user = User.objects.create_user(
                username=username, password="teacher123",
                first_name=first, last_name=last)
            teachers.append(Teacher.objects.create(user=user, staff_no=staff_no))

        # Spread every (subject, classroom) pair across the five teachers
        pairs = [(s, c) for s in subjects.values() for c in classrooms]
        for i, (subject, classroom) in enumerate(pairs):
            TeachingAssignment.objects.create(
                teacher=teachers[i % len(teachers)],
                subject=subject, classroom=classroom)

        # Exams + marks: every student gets a score in each of their subjects
        exams = [
            Exam.objects.create(name="Mid-Term", year=2026, term=1, published=True),
            Exam.objects.create(name="End-Term", year=2026, term=1),
        ]
        assignment_by_pair = {(a.subject_id, a.classroom_id): a.teacher
                              for a in TeachingAssignment.objects.all()}
        for exam in exams:
            for student in Student.objects.prefetch_related("subjects"):
                ability = rng.gauss(58, 12)  # each student has a base ability
                for subject in student.subjects.all():
                    score = max(5, min(99, rng.gauss(ability, 9)))
                    Mark.objects.create(
                        exam=exam, student=student, subject=subject,
                        score=round(score, 1),
                        entered_by=assignment_by_pair.get(
                            (subject.id, student.classroom_id)))

        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", password="admin123")

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {Student.objects.count()} students, "
            f"{Mark.objects.count()} marks, {len(teachers)} teachers.\n"
            "Logins — admin/admin123, teachers: "
            + ", ".join(f"{u}/teacher123" for u, *_ in TEACHERS)))
