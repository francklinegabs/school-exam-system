# School Exam System

A results-management web app for Kenyan high schools (Form 1–4), built with Django. Teachers log in and key in marks for the subjects and classes they teach; the system collects everything and produces graded, ranked results — per class, per form, and as printable student report forms.

## Features

- **Students** — admission number, name, class (form + stream), and the subjects each student takes
- **Teachers** — individual logins; each teacher sees and can enter marks for *only* their own subject + class assignments
- **Exams** — created per term (e.g. Term 1 Mid-Term / End-Term); publishing an exam locks its marks against further edits
- **KCSE-style grading** — A (12 pts) down to E (1 pt), editable bands in [`exams/grading.py`](exams/grading.py)
- **Results** — totals, mean score, total/mean points, mean grade, and position in class **and** in the whole form (ties share a rank)
- **Report forms** — printable per-student report with subject grades and positions
- **Admin panel** — register students, teachers, subjects, classes, assignments, and exams through Django admin

## Quick start

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo        # demo school: 96 students, 5 teachers, 2 exams
python manage.py runserver
```

Then open http://127.0.0.1:8000 and log in:

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Teachers | `jotieno`, `mwanjiru`, `pkiprotich`, `gakinyi`, `dmutua` | `teacher123` |

(Skip `seed_demo` for a real school — create your own data via `python manage.py createsuperuser` and the admin panel at `/admin/`.)

## How marks flow

1. Admin registers subjects, classes, students, teachers, and **teaching assignments** (teacher × subject × class), then creates an exam for the term.
2. Each teacher logs in, opens their class, and keys in scores. Blank = student didn't sit. Scores outside 0–100 are rejected.
3. Results pages compute grades, totals, and rankings live — class-by-class or merged across the whole form.
4. When all marks are in, the admin marks the exam **published**: marks lock, and the report forms are ready to print.

## Project layout

| File | What it does |
|------|--------------|
| [`exams/models.py`](exams/models.py) | Students, teachers, subjects, classes, exams, marks |
| [`exams/grading.py`](exams/grading.py) | KCSE grade bands and points |
| [`exams/results.py`](exams/results.py) | Totals, mean grades, class/form ranking |
| [`exams/views.py`](exams/views.py) | Mark entry (with access control), results, report forms |
| [`exams/management/commands/seed_demo.py`](exams/management/commands/seed_demo.py) | Demo data |

## Tests

```bash
python manage.py test
```

15 tests cover the grade bands, ranking (including ties and students with missing marks), report positions, and the access rules — a teacher cannot open another teacher's mark-entry page, and published exams reject edits.

## License

MIT
