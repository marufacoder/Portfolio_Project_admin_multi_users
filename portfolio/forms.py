from django import forms

from .models import Education, Experience, Profile, Project, Skill


class DateInput(forms.DateInput):
    """HTML5 date picker."""

    input_type = "date"

    def __init__(self, attrs=None, format=None):
        super().__init__(attrs=attrs, format=format or "%Y-%m-%d")


class ProfileForm(forms.ModelForm):
    remove_picture = forms.BooleanField(required=False, label="Remove current profile picture")
    remove_cv = forms.BooleanField(required=False, label="Remove current CV")

    class Meta:
        model = Profile
        fields = [
            "full_name",
            "headline",
            "bio",
            "phone",
            "location",
            "website",
            "profile_picture",
            "cv",
        ]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 5}),
            "profile_picture": forms.FileInput(attrs={"accept": "image/*"}),
            "cv": forms.FileInput(attrs={"accept": ".pdf,.doc,.docx"}),
        }

    def save(self, commit=True):
        profile = super().save(commit=False)
        # A new upload always wins over the "remove" checkbox.
        if self.cleaned_data.get("remove_picture") and "profile_picture" not in self.files:
            profile.profile_picture = ""
        if self.cleaned_data.get("remove_cv") and "cv" not in self.files:
            profile.cv = ""
        if commit:
            profile.save()
        return profile


class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ["name", "level"]


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["title", "description", "url", "technologies", "start_date", "end_date"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "start_date": DateInput(),
            "end_date": DateInput(),
        }


class ExperienceForm(forms.ModelForm):
    class Meta:
        model = Experience
        fields = [
            "position",
            "company",
            "location",
            "start_date",
            "end_date",
            "is_current",
            "description",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "start_date": DateInput(),
            "end_date": DateInput(),
        }


class EducationForm(forms.ModelForm):
    class Meta:
        model = Education
        fields = [
            "institution",
            "degree",
            "field_of_study",
            "start_date",
            "end_date",
            "grade",
            "description",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "start_date": DateInput(),
            "end_date": DateInput(),
        }
