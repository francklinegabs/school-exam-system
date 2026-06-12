from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .grading import grade_for, mean_grade
from .models import (ClassRoom, Exam, Mark, Stream, Student, Subject, Teacher,
                     TeachingAssignment)
from .results import class_results, form_results, student_report


class GradingTest(TestCase):
    def test_band_edges(self):
        self.assertEqual(grade_for(80), ("A", 12))
        self.assertEqual(grade_for(79.9), ("A-", 11))
        self.assertEqual(grade_for(50), ("C", 6))
        self.assertEqual(grade_for(30), ("D-", 2))
        self.assertEqual(grade_for(29.9), ("E", 1))
        self.assertEqual(grade_for(0), ("E", 1))

    def test_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            grade_for(101)
        with self.assertRaises(ValueError):
            grade_for(-1)

    def test_mean_grade_rounding(self):
        self.assertEqual(mean_grade(11.6), "A")     # rounds to 12
        self.assertEqual(mean_grade(6.4), "C")      # rounds to 6
        self.assertEqual(mean_grade(1.0), "E")


class ResultsFixtureMixin:
    """A tiny school: Form 2 East & West, two subjects, three students."""

    @classmethod
    def setUpTestData(cls):
        cls.maths = Subject.objects.create(code="121", name="Mathematics")
        cls.english = Subject.objects.create(code="101", name="English")
        east = Stream.objects.create(name="East")
        west = Stream.objects.create(name="West")
        cls.f2e = ClassRoom.objects.create(form=2, stream=east)
        cls.f2w = ClassRoom.objects.create(form=2, stream=west)
        cls.exam = Exam.objects.create(name="End-Term", year=2026, term=1)

        def make_student(adm, name, classroom, maths_score, english_score):
            s = Student.objects.create(admission_no=adm, full_name=name,
                                       classroom=classroom)
            s.subjects.set([cls.maths, cls.english])
            Mark.objects.create(exam=cls.exam, student=s, subject=cls.maths,
                                score=maths_score)
            Mark.objects.create(exam=cls.exam, student=s, subject=cls.english,
                                score=english_score)
            return s

        cls.amina = make_student("1001", "Amina Hassan", cls.f2e, 85, 78)   # 12+11=23
        cls.brian = make_student("1002", "Brian Otieno", cls.f2e, 62, 55)   # 8+7=15
        cls.carol = make_student("1003", "Carol Njeri", cls.f2w, 90, 82)    # 12+12=24


class ResultsTest(ResultsFixtureMixin, TestCase):
    def test_class_ranking_order(self):
        lines = class_results(self.f2e, self.exam)
        self.assertEqual([l["student"] for l in lines], [self.amina, self.brian])
        self.assertEqual(lines[0]["rank"], 1)
        self.assertEqual(lines[1]["rank"], 2)

    def test_totals_and_grades(self):
        amina = class_results(self.f2e, self.exam)[0]
        self.assertEqual(amina["total"], 163)
        self.assertEqual(amina["total_points"], 23)
        self.assertEqual(amina["mean_grade"], "A")  # 11.5 rounds to 12

    def test_form_results_merge_streams(self):
        lines = form_results(2, self.exam)
        self.assertEqual([l["student"] for l in lines],
                         [self.carol, self.amina, self.brian])

    def test_tied_students_share_rank(self):
        # Give Brian the same scores as Amina -> tie on points AND total.
        Mark.objects.filter(student=self.brian, subject=self.maths).update(score=85)
        Mark.objects.filter(student=self.brian, subject=self.english).update(score=78)
        lines = class_results(self.f2e, self.exam)
        self.assertEqual(lines[0]["rank"], 1)
        self.assertEqual(lines[1]["rank"], 1)

    def test_student_report_positions(self):
        report = student_report(self.amina, self.exam)
        self.assertEqual(report["class_rank"], 1)
        self.assertEqual(report["class_size"], 2)
        self.assertEqual(report["form_rank"], 2)  # Carol beats her form-wide
        self.assertEqual(report["form_size"], 3)

    def test_student_with_no_marks(self):
        s = Student.objects.create(admission_no="1004", full_name="Dan Mwangi",
                                   classroom=self.f2e)
        s.subjects.set([self.maths])
        lines = class_results(self.f2e, self.exam)
        last = lines[-1]
        self.assertEqual(last["student"], s)
        self.assertEqual(last["mean_grade"], "—")


class MarkEntryAccessTest(ResultsFixtureMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        owner = User.objects.create_user("owner", password="pw")
        intruder = User.objects.create_user("intruder", password="pw")
        cls.owner_t = Teacher.objects.create(user=owner, staff_no="T1")
        cls.intruder_t = Teacher.objects.create(user=intruder, staff_no="T2")
        cls.assignment = TeachingAssignment.objects.create(
            teacher=cls.owner_t, subject=cls.maths, classroom=cls.f2e)
        cls.url = reverse("mark_entry", args=[cls.assignment.id, cls.exam.id])

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_assigned_teacher_can_open(self):
        self.client.login(username="owner", password="pw")
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_other_teacher_is_blocked(self):
        self.client.login(username="intruder", password="pw")
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_post_saves_marks(self):
        self.client.login(username="owner", password="pw")
        response = self.client.post(self.url, {f"score_{self.amina.id}": "71"})
        self.assertEqual(response.status_code, 302)
        mark = Mark.objects.get(exam=self.exam, student=self.amina,
                                subject=self.maths)
        self.assertEqual(float(mark.score), 71)
        self.assertEqual(mark.entered_by, self.owner_t)

    def test_post_rejects_out_of_range(self):
        self.client.login(username="owner", password="pw")
        response = self.client.post(self.url, {f"score_{self.amina.id}": "150"})
        self.assertEqual(response.status_code, 200)  # re-renders with error
        mark = Mark.objects.get(exam=self.exam, student=self.amina,
                                subject=self.maths)
        self.assertEqual(float(mark.score), 85)  # unchanged

    def test_published_exam_locks_entry(self):
        self.exam.published = True
        self.exam.save()
        self.client.login(username="owner", password="pw")
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("dashboard"))


class SignUpTest(TestCase):
    def good_form(self, **overrides):
        data = {
            "username": "wmwangi", "first_name": "Wanjiru", "last_name": "Mwangi",
            "staff_no": "TSC900",
            "password1": "korir-mountain-42", "password2": "korir-mountain-42",
        }
        data.update(overrides)
        return data

    def test_signup_creates_teacher_and_logs_in(self):
        response = self.client.post(reverse("signup"), self.good_form())
        self.assertRedirects(response, reverse("dashboard"))
        teacher = Teacher.objects.get(staff_no="TSC900")
        self.assertEqual(teacher.user.username, "wmwangi")
        self.assertEqual(teacher.user.get_full_name(), "Wanjiru Mwangi")
        # Logged in straight away
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)

    def test_duplicate_staff_no_rejected(self):
        user = User.objects.create_user("existing", password="pw")
        Teacher.objects.create(user=user, staff_no="TSC900")
        response = self.client.post(reverse("signup"), self.good_form())
        self.assertEqual(response.status_code, 200)  # re-renders with error
        self.assertContains(response, "already registered")
        self.assertFalse(User.objects.filter(username="wmwangi").exists())

    def test_password_mismatch_rejected(self):
        response = self.client.post(
            reverse("signup"), self.good_form(password2="different-pw-9"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="wmwangi").exists())

    def test_logged_in_user_redirected_away(self):
        User.objects.create_user("someone", password="pw")
        self.client.login(username="someone", password="pw")
        response = self.client.get(reverse("signup"))
        self.assertRedirects(response, reverse("dashboard"))
