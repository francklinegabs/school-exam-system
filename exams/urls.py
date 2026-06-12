from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("accounts/signup/", views.signup, name="signup"),
    path("entry/<int:assignment_id>/<int:exam_id>/", views.mark_entry,
         name="mark_entry"),
    path("results/class/<int:classroom_id>/<int:exam_id>/",
         views.class_results_view, name="class_results"),
    path("results/form/<int:form>/<int:exam_id>/",
         views.form_results_view, name="form_results"),
    path("report/<int:student_id>/<int:exam_id>/", views.report_view,
         name="report"),
]
