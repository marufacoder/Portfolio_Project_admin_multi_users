from django import forms
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import Education, Experience, Profile, Project, Skill


class SkillInline(admin.TabularInline):
    model = Skill
    extra = 0


class ProjectInline(admin.StackedInline):
    model = Project
    extra = 0


class ExperienceInline(admin.StackedInline):
    model = Experience
    extra = 0


class EducationInline(admin.StackedInline):
    model = Education
    extra = 0


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Superusers can view, edit and delete every portfolio from here."""

    list_display = ("display_name", "user", "email", "has_cv", "updated_at")
    list_select_related = ("user",)
    search_fields = ("user__username", "user__email", "full_name")
    inlines = [SkillInline, ProjectInline, ExperienceInline, EducationInline]
    fieldsets = (
        ("Account", {"fields": ("user",)}),
        ("Profile", {"fields": ("full_name", "headline", "bio", "phone", "location", "website")}),
        ("Files", {"fields": ("profile_picture", "cv", "cv_download_link")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def has_add_permission(self, request):
        # Portfolios are created automatically with each user (add users in
        # the "Users" section instead).
        return False

    def get_readonly_fields(self, request, obj=None):
        readonly = ("created_at", "updated_at", "cv_download_link")
        return readonly + ("user",) if obj else readonly

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        # CVs are private: the default widget would link to a URL that does
        # not exist. A plain file input avoids that; use the download link.
        if db_field.name == "cv":
            kwargs["widget"] = forms.FileInput
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    @admin.display(description="Email", ordering="user__email")
    def email(self, obj):
        return obj.user.email

    @admin.display(description="Has CV", boolean=True)
    def has_cv(self, obj):
        return bool(obj.cv)

    @admin.display(description="CV download")
    def cv_download_link(self, obj):
        if obj and obj.pk and obj.cv:
            url = reverse("portfolio:cv_download", args=[obj.pk])
            return format_html('<a href="{}">Download CV</a>', url)
        return "-"
