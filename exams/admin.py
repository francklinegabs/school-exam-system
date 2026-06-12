from django.contrib import admin

from .models import (ClassRoom, Exam, Mark, Stream, Student, Subject, Teacher,
                     TeachingAssignment)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("admission_no", "full_name", "classroom", "active")
    list_filter = ("classroom__form", "classroom__stream", "active")
    search_fields = ("admission_no", "full_name")
    filter_horizontal = ("subjects",)


@admin.register(TeachingAssignment)
class TeachingAssignmentAdmin(admin.ModelAdmin):
    list_display = ("subject", "classroom", "teacher")
    list_filter = ("classroom__form", "subject")


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("name", "year", "term", "out_of", "published")
    list_filter = ("year", "term", "published")


@admin.register(Mark)
class MarkAdmin(admin.ModelAdmin):
    list_display = ("student", "subject", "exam", "score", "entered_by", "updated_at")
    list_filter = ("exam", "subject")
    search_fields = ("student__admission_no", "student__full_name")


admin.site.register([Subject, Stream, ClassRoom, Teacher])
admin.site.site_header = "School Exam System — Administration"
