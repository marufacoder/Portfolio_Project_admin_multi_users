"""Views for the portfolio app.

Every view that touches a portfolio goes through ``_get_manageable_profile``
(or ``admin_required``), so ownership is checked in exactly one place.
"""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from accounts.forms import RegistrationForm

from .forms import EducationForm, ExperienceForm, ProfileForm, ProjectForm, SkillForm
from .models import Education, Experience, Profile, Project, Skill
from .permissions import admin_required, can_manage_profile

SECTIONS = {
    "skill": {"model": Skill, "form": SkillForm, "label": "Skill"},
    "project": {"model": Project, "form": ProjectForm, "label": "Project"},
    "experience": {"model": Experience, "form": ExperienceForm, "label": "Experience"},
    "education": {"model": Education, "form": EducationForm, "label": "Education"},
}


def _get_section(section):
    try:
        return SECTIONS[section]
    except KeyError:
        raise Http404("Unknown portfolio section.")


def _get_manageable_profile(request, pk):
    """Return the profile or raise 403 if the user may not access it."""
    profile = get_object_or_404(Profile.objects.select_related("user"), pk=pk)
    if not can_manage_profile(request.user, profile):
        raise PermissionDenied
    return profile


# --------------------------------------------------------------------------
# Landing page / dashboard
# --------------------------------------------------------------------------
def home(request):
    if request.user.is_authenticated:
        return redirect("portfolio:dashboard")
    return render(request, "home.html")


@login_required
def dashboard(request):
    """Send the user to their own portfolio."""
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return redirect("portfolio:profile_detail", pk=profile.pk)


# --------------------------------------------------------------------------
# Portfolio (owner or administrator)
# --------------------------------------------------------------------------
@login_required
def profile_detail(request, pk):
    profile = _get_manageable_profile(request, pk)
    context = {
        "profile": profile,
        "skills": profile.skills.all(),
        "projects": profile.projects.all(),
        "experiences": profile.experiences.all(),
        "educations": profile.educations.all(),
        "viewing_other": profile.user_id != request.user.pk,
    }
    return render(request, "portfolio/profile_detail.html", context)


@login_required
def profile_edit(request, pk):
    profile = _get_manageable_profile(request, pk)

    # Read these before the form touches the instance: a failed upload would
    # otherwise leave unsaved file data on it.
    current_picture_url = profile.profile_picture.url if profile.profile_picture else ""
    current_cv_label = profile.cv_label

    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile saved.")
            return redirect("portfolio:profile_detail", pk=profile.pk)
    else:
        form = ProfileForm(instance=profile)

    context = {
        "form": form,
        "profile": profile,
        "current_picture_url": current_picture_url,
        "current_cv_label": current_cv_label,
        "cv_max_mb": settings.CV_MAX_UPLOAD_MB,
        "picture_max_mb": settings.PROFILE_PICTURE_MAX_UPLOAD_MB,
        "viewing_other": profile.user_id != request.user.pk,
    }
    return render(request, "portfolio/profile_form.html", context)


@login_required
def cv_download(request, pk):
    """Serve a CV only to its owner or an administrator."""
    profile = _get_manageable_profile(request, pk)
    if not profile.cv:
        raise Http404("No CV has been uploaded.")

    try:
        handle = profile.cv.storage.open(profile.cv.name, "rb")
    except FileNotFoundError:
        raise Http404("The CV file could not be found.")

    base_name = slugify(profile.display_name) or slugify(profile.user.get_username()) or "cv"
    response = FileResponse(
        handle,
        as_attachment=True,
        filename=f"{base_name}-cv{profile.cv_extension}",
    )
    response["Cache-Control"] = "private, no-store"
    return response


# --------------------------------------------------------------------------
# Skills, projects, experience and education
# --------------------------------------------------------------------------
@login_required
def section_create(request, pk, section):
    config = _get_section(section)
    profile = _get_manageable_profile(request, pk)

    if request.method == "POST":
        form = config["form"](request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.profile = profile
            item.save()
            messages.success(request, f"{config['label']} added.")
            return redirect("portfolio:profile_detail", pk=profile.pk)
    else:
        form = config["form"]()

    context = {"form": form, "profile": profile, "label": config["label"], "action": "Add"}
    return render(request, "portfolio/section_form.html", context)


def _get_item_and_profile(request, section, pk):
    config = _get_section(section)
    item = get_object_or_404(config["model"].objects.select_related("profile__user"), pk=pk)
    profile = item.profile
    if not can_manage_profile(request.user, profile):
        raise PermissionDenied
    return config, item, profile


@login_required
def section_edit(request, section, pk):
    config, item, profile = _get_item_and_profile(request, section, pk)

    if request.method == "POST":
        form = config["form"](request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f"{config['label']} updated.")
            return redirect("portfolio:profile_detail", pk=profile.pk)
    else:
        form = config["form"](instance=item)

    context = {"form": form, "profile": profile, "label": config["label"], "action": "Edit"}
    return render(request, "portfolio/section_form.html", context)


@login_required
def section_delete(request, section, pk):
    config, item, profile = _get_item_and_profile(request, section, pk)

    if request.method == "POST":
        item.delete()
        messages.success(request, f"{config['label']} deleted.")
        return redirect("portfolio:profile_detail", pk=profile.pk)

    context = {
        "object_label": f"{config['label'].lower()} “{item}”",
        "warning": "This cannot be undone.",
        "cancel_url": "portfolio:profile_detail",
        "cancel_pk": profile.pk,
    }
    return render(request, "portfolio/confirm_delete.html", context)


# --------------------------------------------------------------------------
# Administrator tools
# --------------------------------------------------------------------------
@admin_required
def portfolio_list(request):
    query = request.GET.get("q", "").strip()
    profiles = Profile.objects.select_related("user").annotate(
        skill_count=Count("skills", distinct=True),
        project_count=Count("projects", distinct=True),
        experience_count=Count("experiences", distinct=True),
        education_count=Count("educations", distinct=True),
    )
    if query:
        profiles = profiles.filter(
            Q(user__username__icontains=query)
            | Q(user__email__icontains=query)
            | Q(full_name__icontains=query)
        )

    page_obj = Paginator(profiles, 10).get_page(request.GET.get("page"))
    return render(
        request,
        "portfolio/portfolio_list.html",
        {"page_obj": page_obj, "q": query},
    )


@admin_required
def portfolio_create(request):
    """Create a new user together with an (empty) portfolio."""
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            profile, _ = Profile.objects.get_or_create(user=user)
            messages.success(
                request,
                f"Account created for {user.username}. Fill in their portfolio below.",
            )
            return redirect("portfolio:profile_edit", pk=profile.pk)
    else:
        form = RegistrationForm()

    return render(request, "portfolio/portfolio_create.html", {"form": form})


@admin_required
def profile_delete(request, pk):
    """Delete a user's account together with their whole portfolio."""
    profile = get_object_or_404(Profile.objects.select_related("user"), pk=pk)
    target = profile.user

    if target.pk == request.user.pk:
        messages.error(request, "You cannot delete your own account here.")
        return redirect("portfolio:portfolio_list")
    if target.is_superuser and not request.user.is_superuser:
        raise PermissionDenied

    if request.method == "POST":
        username = target.get_username()
        target.delete()  # cascades to the profile and every section
        messages.success(request, f"Deleted {username} and their portfolio.")
        return redirect("portfolio:portfolio_list")

    context = {
        "object_label": f"the account and portfolio of {target.get_username()}",
        "warning": (
            "The user, their profile, skills, projects, experience, education, "
            "picture and CV will all be removed permanently."
        ),
        "cancel_url": "portfolio:portfolio_list",
        "cancel_pk": None,
    }
    return render(request, "portfolio/confirm_delete.html", context)
