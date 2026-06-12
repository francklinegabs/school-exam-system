from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Teacher


class TeacherSignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    staff_no = forms.CharField(
        max_length=20, label="Staff / TSC number",
        help_text="Your school staff or TSC number.")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name")

    def clean_staff_no(self):
        staff_no = self.cleaned_data["staff_no"].strip()
        if Teacher.objects.filter(staff_no__iexact=staff_no).exists():
            raise forms.ValidationError(
                "A teacher with this staff number is already registered.")
        return staff_no

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            Teacher.objects.create(user=user,
                                   staff_no=self.cleaned_data["staff_no"])
        return user
