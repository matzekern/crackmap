from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Crack


def make_jpeg_with_gps():
    """A tiny JPEG carrying a fake GPS EXIF tag."""
    img = Image.new("RGB", (3000, 1500), "gray")
    exif = Image.Exif()
    exif[0x8825] = {1: "N", 2: (47.0, 30.0, 0.0)}  # GPSInfo
    buffer = BytesIO()
    img.save(buffer, format="JPEG", exif=exif)
    return SimpleUploadedFile("IMG_1234.jpg", buffer.getvalue(), content_type="image/jpeg")


class MapPageTests(TestCase):
    def test_map_page_loads(self):
        response = self.client.get(reverse("cracks:map"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="map"')

    def test_crack_appears_as_pin_data(self):
        Crack.objects.create(
            name="Test Splitter", width=Crack.Width.HANDS, grade="6a",
            latitude=47.5, longitude=11.25,
        )
        response = self.client.get(reverse("cracks:map"))
        self.assertContains(response, "Test Splitter")
        self.assertContains(response, "47.5")

    def test_html_in_name_is_escaped(self):
        Crack.objects.create(
            name="<script>alert(1)</script>", width=Crack.Width.FISTS,
            latitude=0, longitude=0,
        )
        response = self.client.get(reverse("cracks:map"))
        self.assertNotContains(response, "<script>alert(1)</script>")

    def test_form_only_for_signed_in_users(self):
        response = self.client.get(reverse("cracks:map"))
        self.assertNotContains(response, '<template id="add-form-template"')
        self.assertContains(response, "Sign up")

        self.client.force_login(User.objects.create_user("climber", password="x-pass-123"))
        response = self.client.get(reverse("cracks:map"))
        self.assertContains(response, '<template id="add-form-template"')


class CrackModelTests(TestCase):
    def test_unnamed_crack_has_readable_label(self):
        crack = Crack(width=Crack.Width.OFFWIDTH, latitude=0, longitude=0)
        self.assertEqual(str(crack), "Unnamed offwidth crack")


class AddCrackTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("climber", password="x-pass-123")
        self.url = reverse("cracks:add")
        self.valid = {"width": "hands", "latitude": "47.123456", "longitude": "11.654321",
                      "access_status": "unknown"}

    def test_requires_login(self):
        response = self.client.post(self.url, self.valid)
        self.assertEqual(response.status_code, 302)  # redirect to sign-in
        self.assertEqual(Crack.objects.count(), 0)

    def test_get_not_allowed(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_creates_crack_and_returns_pin(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, self.valid)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["pin"]["width"], "Hands")
        crack = Crack.objects.get()
        self.assertEqual(crack.created_by, self.user)

    def test_missing_width_returns_errors(self):
        self.client.force_login(self.user)
        data = {**self.valid, "width": ""}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("width", response.json()["errors"])

    def test_out_of_range_latitude_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {**self.valid, "latitude": "95"})
        self.assertEqual(response.status_code, 400)

    def test_fake_image_rejected(self):
        self.client.force_login(self.user)
        fake = SimpleUploadedFile("evil.jpg", b"not an image", content_type="image/jpeg")
        response = self.client.post(self.url, {**self.valid, "photo": fake})
        self.assertEqual(response.status_code, 400)


@override_settings(MEDIA_ROOT="/tmp/crackmap-test-media")
class PhotoCleaningTests(TestCase):
    def test_gps_removed_and_resized(self):
        user = User.objects.create_user("climber", password="x-pass-123")
        self.client.force_login(user)
        data = {"width": "fists", "latitude": "1", "longitude": "2",
                "access_status": "unknown", "photo": make_jpeg_with_gps()}
        response = self.client.post(reverse("cracks:add"), data)
        self.assertEqual(response.status_code, 201)

        crack = Crack.objects.get()
        with Image.open(crack.photo.path) as saved:
            self.assertEqual(len(saved.getexif()), 0)   # no metadata left
            self.assertEqual(max(saved.size), 2000)     # shrunk from 3000 px


class CrackDetailTests(TestCase):
    def setUp(self):
        self.crack = Crack.objects.create(
            name="Sandstone Splitter", width=Crack.Width.HANDS, grade="6b",
            length_m=12, rock_type="Sandstone", access_status=Crack.Access.CLOSED,
            access_notes="Bird nesting until July", latitude=50.9, longitude=14.1,
        )

    def test_detail_page_shows_fields(self):
        response = self.client.get(self.crack.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        for text in ["Sandstone Splitter", "Hands", "6b", "12 m", "Sandstone",
                     "Closed", "Bird nesting until July", "No photo yet"]:
            self.assertContains(response, text)

    def test_missing_crack_is_404(self):
        self.assertEqual(self.client.get("/cracks/99999/").status_code, 404)

    def test_map_pins_link_to_detail(self):
        response = self.client.get(reverse("cracks:map"))
        self.assertContains(response, self.crack.get_absolute_url())

    def test_html_in_notes_is_escaped(self):
        self.crack.access_notes = "<img src=x onerror=alert(1)>"
        self.crack.save()
        response = self.client.get(self.crack.get_absolute_url())
        self.assertNotContains(response, "<img src=x onerror=alert(1)>")

class CommentTests(TestCase):
    def setUp(self):
        self.crack = Crack.objects.create(width=Crack.Width.HANDS, latitude=1, longitude=2)
        self.user = User.objects.create_user("climber", password="x-pass-123")
        self.url = reverse("cracks:add_comment", args=[self.crack.pk])

    def test_signed_in_user_can_comment(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"text": "Bring doubles in #2"})
        self.assertRedirects(response, self.crack.get_absolute_url() + "#comments",
                             fetch_redirect_response=False)
        page = self.client.get(self.crack.get_absolute_url())
        self.assertContains(page, "Bring doubles in #2")
        self.assertContains(page, "climber")

    def test_anonymous_cannot_comment(self):
        response = self.client.post(self.url, {"text": "spam"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.crack.comments.count(), 0)
        page = self.client.get(self.crack.get_absolute_url())
        self.assertContains(page, "to comment")

    def test_empty_comment_ignored(self):
        self.client.force_login(self.user)
        self.client.post(self.url, {"text": ""})
        self.assertEqual(self.crack.comments.count(), 0)

    def test_too_long_comment_rejected(self):
        self.client.force_login(self.user)
        self.client.post(self.url, {"text": "x" * 2001})
        self.assertEqual(self.crack.comments.count(), 0)

    def test_comment_html_escaped(self):
        self.client.force_login(self.user)
        self.client.post(self.url, {"text": "<script>alert(1)</script>"})
        page = self.client.get(self.crack.get_absolute_url())
        self.assertNotContains(page, "<script>alert(1)</script>")

class InfoFieldTests(TestCase):
    def setUp(self):
        self.crack = Crack.objects.create(
            width=Crack.Width.OFFWIDTH, latitude=1, longitude=2, o_grade="OW3",
            info_source="Elbsandstein guide p. 42, see https://example.com/crack",
        )

    def test_detail_shows_o_grade_and_clickable_link(self):
        page = self.client.get(self.crack.get_absolute_url())
        self.assertContains(page, "OW3")
        self.assertContains(page, "Elbsandstein guide p. 42")
        self.assertContains(page, 'href="https://example.com/crack"')

    def test_info_source_html_escaped(self):
        self.crack.info_source = "<script>alert(1)</script>"
        self.crack.save()
        page = self.client.get(self.crack.get_absolute_url())
        self.assertNotContains(page, "<script>alert(1)</script>")

    def test_new_fields_saved_from_popup_form(self):
        self.client.force_login(User.objects.create_user("climber", password="x-pass-123"))
        response = self.client.post(reverse("cracks:add"), {
            "width": "hands", "latitude": "3", "longitude": "4", "access_status": "unknown",
            "o_grade": "O2", "info_source": "Ask at the local gym",
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["pin"]["o_grade"], "O2")
        self.assertEqual(Crack.objects.get(o_grade="O2").info_source, "Ask at the local gym")

class AccountTests(TestCase):
    def test_signup_creates_user_and_logs_in(self):
        response = self.client.post(reverse("signup"), {
            "username": "newclimber",
            "password1": "jam-crack-2026!",
            "password2": "jam-crack-2026!",
        })
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertTrue(User.objects.filter(username="newclimber").exists())
        page = self.client.get(reverse("cracks:map"))
        self.assertContains(page, "Hi, newclimber")

    def test_signup_rejects_mismatched_passwords(self):
        response = self.client.post(reverse("signup"), {
            "username": "newclimber", "password1": "jam-crack-2026!", "password2": "other-pass-2026!",
        })
        self.assertEqual(response.status_code, 200)  # form shown again with errors
        self.assertFalse(User.objects.filter(username="newclimber").exists())

    def test_signup_rejects_weak_password(self):
        self.client.post(reverse("signup"), {
            "username": "newclimber", "password1": "12345678", "password2": "12345678",
        })
        self.assertFalse(User.objects.filter(username="newclimber").exists())

    def test_signup_redirects_to_next_but_not_other_sites(self):
        data = {"username": "a1", "password1": "jam-crack-2026!", "password2": "jam-crack-2026!",
                "next": "/cracks/1/"}
        self.assertRedirects(self.client.post(reverse("signup"), data), "/cracks/1/",
                             fetch_redirect_response=False)
        self.client.logout()
        data.update(username="a2", next="https://evil.example.com/")
        self.assertRedirects(self.client.post(reverse("signup"), data), "/",
                             fetch_redirect_response=False)

    def test_login_and_logout(self):
        User.objects.create_user("climber", password="jam-crack-2026!")
        response = self.client.post(reverse("login"),
                                    {"username": "climber", "password": "jam-crack-2026!"})
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertContains(self.client.get("/"), "Log in")

    def test_anonymous_add_redirects_to_our_login_page(self):
        response = self.client.post(reverse("cracks:add"), {})
        self.assertTrue(response["Location"].startswith("/accounts/login/"))

@override_settings(MEDIA_ROOT="/tmp/crackmap-test-media")
class EditDeleteTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="x-pass-123")
        self.other = User.objects.create_user("other", password="x-pass-123")
        self.admin = User.objects.create_superuser("boss", "", "x-pass-123")
        self.crack = Crack.objects.create(width=Crack.Width.HANDS, latitude=1, longitude=2,
                                          created_by=self.owner)
        self.comment = self.crack.comments.create(author=self.owner, text="first!")
        self.edit_data = {"width": "fists", "latitude": "5.5", "longitude": "6.5",
                          "access_status": "open", "name": "Moved Crack"}

    def test_owner_can_edit_and_move_crack(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("cracks:edit", args=[self.crack.pk])).status_code, 200)
        response = self.client.post(reverse("cracks:edit", args=[self.crack.pk]), self.edit_data)
        self.assertRedirects(response, self.crack.get_absolute_url(), fetch_redirect_response=False)
        self.crack.refresh_from_db()
        self.assertEqual(self.crack.name, "Moved Crack")
        self.assertEqual(float(self.crack.latitude), 5.5)

    def test_other_user_gets_403(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("cracks:edit", args=[self.crack.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("cracks:delete", args=[self.crack.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("cracks:delete_comment", args=[self.comment.pk])).status_code, 403)
        self.assertTrue(Crack.objects.filter(pk=self.crack.pk).exists())

    def test_anonymous_redirected_to_login(self):
        response = self.client.post(reverse("cracks:delete", args=[self.crack.pk]))
        self.assertTrue(response["Location"].startswith("/accounts/login/"))

    def test_admin_can_delete_any_crack(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("cracks:delete", args=[self.crack.pk]))
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertFalse(Crack.objects.exists())
        self.assertFalse(self.crack.comments.exists())  # comments go with it

    def test_owner_can_edit_and_delete_comment(self):
        self.client.force_login(self.owner)
        self.client.post(reverse("cracks:edit_comment", args=[self.comment.pk]), {"text": "edited"})
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.text, "edited")
        self.client.post(reverse("cracks:delete_comment", args=[self.comment.pk]))
        self.assertFalse(self.crack.comments.exists())

    def test_buttons_only_for_owner(self):
        url = self.crack.get_absolute_url()
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(url), "Edit crack")
        self.client.force_login(self.owner)
        page = self.client.get(url)
        self.assertContains(page, "Edit crack")
        self.assertContains(page, "Delete crack")

    def test_replacing_photo_cleans_it_and_removes_old_file(self):
        self.client.force_login(self.owner)
        url = reverse("cracks:edit", args=[self.crack.pk])
        self.client.post(url, {**self.edit_data, "photo": make_jpeg_with_gps()})
        self.crack.refresh_from_db()
        first_path = self.crack.photo.path
        with Image.open(first_path) as img:
            self.assertEqual(len(img.getexif()), 0)

        self.client.post(url, {**self.edit_data, "photo": make_jpeg_with_gps()})
        self.crack.refresh_from_db()
        self.assertNotEqual(self.crack.photo.path, first_path)
        import os
        self.assertFalse(os.path.exists(first_path))
