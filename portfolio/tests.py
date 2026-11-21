"""Tests for registration, login, ownership rules and CV handling.

Run with:  python manage.py test
"""
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import Profile, Skill

User = get_user_model()
PASSWORD = "Str0ng-Pass!234"


class RegistrationAndLoginTests(TestCase):
    def test_register_creates_user_and_empty_profile(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "newuser",
                "email": "New@Example.com",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        self.assertRedirects(
            response, reverse("portfolio:dashboard"), fetch_redirect_response=False
        )
        user = User.objects.get(username="newuser")
        self.assertEqual(user.email, "new@example.com")
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user("alice", "alice@example.com", PASSWORD)
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "other",
                "email": "ALICE@example.com",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="other").exists())

    def test_login_with_username_and_with_email(self):
        User.objects.create_user("bob", "bob@example.com", PASSWORD)
        for identifier in ("bob", "bob@example.com"):
            with self.subTest(identifier=identifier):
                self.client.logout()
                response = self.client.post(
                    reverse("accounts:login"), {"username": identifier, "password": PASSWORD}
                )
                self.assertEqual(response.status_code, 302)
                self.assertIn("_auth_user_id", self.client.session)

    def test_anonymous_users_are_sent_to_login(self):
        response = self.client.get(reverse("portfolio:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])


class PortfolioTestCase(TestCase):
    """Creates alice, bob and an administrator, and a private CV storage folder."""

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        cv_field = Profile._meta.get_field("cv")
        original_storage = cv_field.storage
        cv_field.storage = FileSystemStorage(location=folder.name)
        self.addCleanup(setattr, cv_field, "storage", original_storage)

        self.alice = User.objects.create_user("alice", "alice@example.com", PASSWORD)
        self.bob = User.objects.create_user("bob", "bob@example.com", PASSWORD)
        self.admin = User.objects.create_superuser("root", "root@example.com", PASSWORD)

    def login(self, user):
        self.client.logout()
        self.assertTrue(self.client.login(username=user.username, password=PASSWORD))


class OwnershipTests(PortfolioTestCase):
    def test_user_can_view_and_edit_own_portfolio(self):
        self.login(self.alice)
        pk = self.alice.profile.pk
        self.assertEqual(self.client.get(reverse("portfolio:profile_detail", args=[pk])).status_code, 200)
        response = self.client.post(
            reverse("portfolio:profile_edit", args=[pk]), {"full_name": "Alice A."}
        )
        self.assertEqual(response.status_code, 302)
        self.alice.profile.refresh_from_db()
        self.assertEqual(self.alice.profile.full_name, "Alice A.")

    def test_user_cannot_view_or_edit_another_users_portfolio(self):
        self.login(self.alice)
        pk = self.bob.profile.pk
        self.assertEqual(self.client.get(reverse("portfolio:profile_detail", args=[pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("portfolio:profile_edit", args=[pk])).status_code, 403)
        response = self.client.post(
            reverse("portfolio:profile_edit", args=[pk]), {"full_name": "Hacked"}
        )
        self.assertEqual(response.status_code, 403)
        self.bob.profile.refresh_from_db()
        self.assertNotEqual(self.bob.profile.full_name, "Hacked")

    def test_user_can_add_skill_to_own_portfolio_only(self):
        self.login(self.alice)
        own = reverse("portfolio:section_create", args=[self.alice.profile.pk, "skill"])
        response = self.client.post(own, {"name": "Django", "level": "advanced"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Skill.objects.filter(profile=self.alice.profile).count(), 1)

        other = reverse("portfolio:section_create", args=[self.bob.profile.pk, "skill"])
        response = self.client.post(other, {"name": "Sneaky", "level": "expert"})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Skill.objects.filter(profile=self.bob.profile).exists())

    def test_user_cannot_edit_or_delete_another_users_items(self):
        skill = Skill.objects.create(profile=self.bob.profile, name="Python")
        self.login(self.alice)
        edit_url = reverse("portfolio:section_edit", args=["skill", skill.pk])
        delete_url = reverse("portfolio:section_delete", args=["skill", skill.pk])
        self.assertEqual(self.client.get(edit_url).status_code, 403)
        self.assertEqual(self.client.post(edit_url, {"name": "X", "level": "beginner"}).status_code, 403)
        self.assertEqual(self.client.post(delete_url).status_code, 403)
        skill.refresh_from_db()
        self.assertEqual(skill.name, "Python")

    def test_unknown_section_is_404(self):
        self.login(self.alice)
        url = reverse("portfolio:section_create", args=[self.alice.profile.pk, "nonsense"])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_regular_user_cannot_use_administrator_pages(self):
        self.login(self.alice)
        self.assertEqual(self.client.get(reverse("portfolio:portfolio_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("portfolio:portfolio_create")).status_code, 403)
        delete_url = reverse("portfolio:profile_delete", args=[self.bob.profile.pk])
        self.assertEqual(self.client.post(delete_url).status_code, 403)
        self.assertTrue(User.objects.filter(pk=self.bob.pk).exists())


class AdministratorTests(PortfolioTestCase):
    def test_admin_can_list_view_edit_and_add_items_for_any_user(self):
        self.login(self.admin)
        pk = self.bob.profile.pk
        self.assertEqual(self.client.get(reverse("portfolio:portfolio_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("portfolio:profile_detail", args=[pk])).status_code, 200)

        self.client.post(reverse("portfolio:profile_edit", args=[pk]), {"full_name": "Bob B."})
        self.bob.profile.refresh_from_db()
        self.assertEqual(self.bob.profile.full_name, "Bob B.")

        self.client.post(
            reverse("portfolio:section_create", args=[pk, "skill"]),
            {"name": "SQL", "level": "intermediate"},
        )
        skill = Skill.objects.get(profile=self.bob.profile)

        self.client.post(
            reverse("portfolio:section_edit", args=["skill", skill.pk]),
            {"name": "PostgreSQL", "level": "advanced"},
        )
        skill.refresh_from_db()
        self.assertEqual(skill.name, "PostgreSQL")

        self.client.post(reverse("portfolio:section_delete", args=["skill", skill.pk]))
        self.assertFalse(Skill.objects.filter(pk=skill.pk).exists())

    def test_admin_can_add_a_user_with_a_portfolio(self):
        self.login(self.admin)
        response = self.client.post(
            reverse("portfolio:portfolio_create"),
            {
                "username": "carol",
                "email": "carol@example.com",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        self.assertEqual(response.status_code, 302)
        carol = User.objects.get(username="carol")
        self.assertTrue(Profile.objects.filter(user=carol).exists())

    def test_admin_can_delete_a_users_portfolio_but_not_their_own(self):
        self.login(self.admin)
        self.client.post(reverse("portfolio:profile_delete", args=[self.bob.profile.pk]))
        self.assertFalse(User.objects.filter(pk=self.bob.pk).exists())

        self.client.post(reverse("portfolio:profile_delete", args=[self.admin.profile.pk]))
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())


class CVTests(PortfolioTestCase):
    PDF_BYTES = b"%PDF-1.4\n%demo cv\n"

    def test_cv_download_is_limited_to_owner_and_administrators(self):
        profile = self.alice.profile
        profile.cv.save("resume.pdf", ContentFile(self.PDF_BYTES))
        url = reverse("portfolio:cv_download", args=[profile.pk])

        # Anonymous visitors are sent to the login page.
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        # Another regular user is refused.
        self.login(self.bob)
        self.assertEqual(self.client.get(url).status_code, 403)

        # The owner and an administrator can download it.
        for user in (self.alice, self.admin):
            with self.subTest(user=user.username):
                self.login(user)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertIn("attachment", response["Content-Disposition"])
                self.assertEqual(b"".join(response.streaming_content), self.PDF_BYTES)
                response.close()

    def test_download_without_cv_is_404(self):
        self.login(self.alice)
        url = reverse("portfolio:cv_download", args=[self.alice.profile.pk])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_valid_pdf_upload_is_accepted(self):
        self.login(self.alice)
        upload = SimpleUploadedFile("cv.pdf", self.PDF_BYTES, content_type="application/pdf")
        response = self.client.post(
            reverse("portfolio:profile_edit", args=[self.alice.profile.pk]),
            {"full_name": "Alice", "cv": upload},
        )
        self.assertEqual(response.status_code, 302)
        self.alice.profile.refresh_from_db()
        self.assertTrue(self.alice.profile.cv)
        self.assertEqual(self.alice.profile.cv_extension, ".pdf")

    def test_wrong_extension_and_fake_content_are_rejected(self):
        self.login(self.alice)
        url = reverse("portfolio:profile_edit", args=[self.alice.profile.pk])
        bad_uploads = [
            SimpleUploadedFile("cv.exe", b"MZ\x90\x00", content_type="application/octet-stream"),
            SimpleUploadedFile("cv.pdf", b"this is not a pdf", content_type="application/pdf"),
        ]
        for upload in bad_uploads:
            with self.subTest(name=upload.name):
                response = self.client.post(url, {"full_name": "Alice", "cv": upload})
                self.assertEqual(response.status_code, 200)
                self.assertIn("cv", response.context["form"].errors)
        self.alice.profile.refresh_from_db()
        self.assertFalse(self.alice.profile.cv)

    def test_cv_can_be_removed(self):
        profile = self.alice.profile
        profile.cv.save("resume.pdf", ContentFile(self.PDF_BYTES))
        self.login(self.alice)
        response = self.client.post(
            reverse("portfolio:profile_edit", args=[profile.pk]),
            {"full_name": "Alice", "remove_cv": "on"},
        )
        self.assertEqual(response.status_code, 302)
        profile.refresh_from_db()
        self.assertFalse(profile.cv)
