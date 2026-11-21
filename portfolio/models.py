"""Database models for the portfolio app."""
import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.db import models

from .validators import validate_cv_file, validate_profile_picture


def get_private_storage():
    """Storage for files that must never be reachable through a plain URL (CVs)."""
    return FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT)


def _unique_upload_path(folder, instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"{folder}/{instance.user_id}/{uuid.uuid4().hex}{ext}"


def profile_picture_path(instance, filename):
    return _unique_upload_path("profile_pictures", instance, filename)


def cv_path(instance, filename):
    return _unique_upload_path("cvs", instance, filename)


class Profile(models.Model):
    """One portfolio per user. Created automatically when a user is created."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    full_name = models.CharField(max_length=150, blank=True)
    headline = models.CharField(
        max_length=200, blank=True, help_text="For example: Full-stack developer"
    )
    bio = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    location = models.CharField(max_length=150, blank=True)
    website = models.URLField(blank=True)
    profile_picture = models.ImageField(
        upload_to=profile_picture_path,
        blank=True,
        validators=[validate_profile_picture],
        help_text="JPG, PNG, GIF or WEBP.",
    )
    cv = models.FileField(
        "CV / resume",
        upload_to=cv_path,
        storage=get_private_storage,
        blank=True,
        validators=[validate_cv_file],
        help_text="PDF, DOC or DOCX.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        return self.full_name or self.user.get_full_name() or self.user.get_username()

    @property
    def cv_extension(self):
        return os.path.splitext(self.cv.name)[1].lower() if self.cv else ""

    @property
    def cv_label(self):
        return f"CV ({self.cv_extension.lstrip('.').upper()})" if self.cv else ""

    def save(self, *args, **kwargs):
        # Remember files that this save replaces or clears, then remove them
        # from disk once the new state has been stored successfully.
        replaced = []
        if self.pk:
            previous = Profile.objects.filter(pk=self.pk).first()
            if previous:
                for field_name in ("profile_picture", "cv"):
                    old_file = getattr(previous, field_name)
                    new_file = getattr(self, field_name)
                    if old_file and old_file.name != (new_file.name or None):
                        replaced.append(old_file)
        super().save(*args, **kwargs)
        for old_file in replaced:
            old_file.delete(save=False)


class Skill(models.Model):
    class Level(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"
        EXPERT = "expert", "Expert"

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="skills")
    name = models.CharField(max_length=100)
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.INTERMEDIATE)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class _DateRangeMixin(models.Model):
    """Shared validation for sections that have a start and an end date."""

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "The end date cannot be before the start date."})


class Project(_DateRangeMixin):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="projects")
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    url = models.URLField("Project link", blank=True)
    technologies = models.CharField(
        max_length=250, blank=True, help_text="Comma-separated, e.g. Python, Django, SQLite"
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-start_date", "title"]

    def __str__(self):
        return self.title


class Experience(_DateRangeMixin):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="experiences")
    position = models.CharField(max_length=150)
    company = models.CharField(max_length=150)
    location = models.CharField(max_length=150, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField("I currently work here", default=False)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-is_current", "-start_date"]

    def __str__(self):
        return f"{self.position} at {self.company}"

    def clean(self):
        if self.is_current:
            self.end_date = None
        elif not self.end_date and self.start_date:
            raise ValidationError(
                {"end_date": 'Add an end date or tick "I currently work here".'}
            )
        super().clean()


class Education(_DateRangeMixin):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="educations")
    institution = models.CharField(max_length=200)
    degree = models.CharField(max_length=150)
    field_of_study = models.CharField(max_length=150, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(
        null=True, blank=True, help_text="Leave blank if you are still studying."
    )
    grade = models.CharField(max_length=50, blank=True, help_text="Optional, e.g. CGPA 3.8/4.0")
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-start_date", "-end_date"]
        verbose_name_plural = "education"

    def __str__(self):
        return f"{self.degree}, {self.institution}"
