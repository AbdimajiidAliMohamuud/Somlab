import base64
from datetime import timedelta
from io import StringIO
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.customer_media_lifecycle import is_file_referenced, is_managed_customer_media_name
from core.models import Customer, CustomerProject, CustomerProjectMedia
from dashboard.forms import CustomerProjectForm, CustomerProjectMediaForm


PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC"
    "AAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class CustomerMediaLifecycleTests(TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory(prefix="customer-media-lifecycle-")
        self.addCleanup(self.directory.cleanup)
        override = override_settings(
            MEDIA_ROOT=self.directory.name,
            STORAGES={
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
            },
        )
        override.enable()
        self.addCleanup(override.disable)
        customer = Customer.objects.create(name="Media lifecycle QA", slug="media-lifecycle-qa")
        self.project = CustomerProject.objects.create(customer=customer, title="Managed project")

    def stored_media(self, name, order, *, media_type="image"):
        media = CustomerProjectMedia(project=self.project, media_type=media_type, display_order=order)
        media.file.save(name, ContentFile(PNG), save=True)
        return media

    def test_delete_keeps_shared_file_then_removes_last_reference_and_closes_gaps(self):
        first = self.stored_media("shared.png", 0)
        shared_name = first.file.name
        second = CustomerProjectMedia.objects.create(
            project=self.project, media_type="image", file=shared_name, display_order=4,
        )
        third = self.stored_media("third.png", 9)
        with self.captureOnCommitCallbacks(execute=True):
            first.delete()
        self.assertTrue(second.file.storage.exists(shared_name))
        self.assertEqual(
            list(self.project.media.order_by("display_order", "pk").values_list("display_order", flat=True)),
            [0, 1],
        )
        with self.captureOnCommitCallbacks(execute=True):
            second.delete()
        self.assertFalse(third.file.storage.exists(shared_name))
        third.refresh_from_db()
        self.assertEqual(third.display_order, 0)

    def test_replace_image_removes_old_file_after_commit_and_moves_to_requested_index(self):
        first = self.stored_media("first.png", 0)
        second = self.stored_media("second.png", 1)
        old_name = second.file.name
        form = CustomerProjectMediaForm(
            {"media_type": "image", "display_order": 0},
            {"file": SimpleUploadedFile("replacement.png", PNG, content_type="image/png")},
            instance=second,
        )
        self.assertTrue(form.is_valid(), form.errors)
        with self.captureOnCommitCallbacks(execute=True):
            replaced = form.save()
        self.assertFalse(replaced.file.storage.exists(old_name))
        self.assertTrue(replaced.file.storage.exists(replaced.file.name))
        self.assertEqual(
            list(self.project.media.order_by("display_order").values_list("pk", "display_order")),
            [(second.pk, 0), (first.pk, 1)],
        )

    def test_replacement_cleans_old_video_derivatives(self):
        media = self.stored_media("old-video.mp4", 0, media_type="video")
        media.playback_file.save("old-playback.mp4", ContentFile(b"playback"), save=False)
        media.video_poster.save("old-poster.jpg", ContentFile(b"poster"), save=True)
        old_paths = [(field.storage, field.name) for field in (
            media.file, media.playback_file, media.video_poster,
        )]
        form = CustomerProjectMediaForm(
            {"media_type": "image", "display_order": 0},
            {"file": SimpleUploadedFile("new-image.png", PNG, content_type="image/png")},
            instance=media,
        )
        self.assertTrue(form.is_valid(), form.errors)
        with self.captureOnCommitCallbacks(execute=True):
            updated = form.save()
        self.assertTrue(all(not storage.exists(name) for storage, name in old_paths))
        self.assertFalse(updated.playback_file)
        self.assertFalse(updated.video_poster)
        self.assertTrue(updated.file.storage.exists(updated.file.name))

    def test_admin_reorder_without_file_change_is_gap_free(self):
        first = self.stored_media("order-first.png", 0)
        second = self.stored_media("order-second.png", 4)
        third = self.stored_media("order-third.png", 9)
        original_name = third.file.name
        form = CustomerProjectMediaForm(
            {"media_type": "image", "display_order": 0},
            instance=third,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        third.refresh_from_db()
        self.assertEqual(third.file.name, original_name)
        self.assertEqual(
            list(self.project.media.order_by("display_order").values_list("pk", "display_order")),
            [(third.pk, 0), (first.pk, 1), (second.pk, 2)],
        )

    def test_file_referenced_by_another_model_is_preserved(self):
        media = self.stored_media("also-customer-logo.png", 0)
        name = media.file.name
        other = Customer.objects.create(name="Shared image holder", logo=name)
        with self.captureOnCommitCallbacks(execute=True):
            media.delete()
        self.assertTrue(other.logo.storage.exists(name))

    def test_encoded_text_link_is_considered_a_shared_reference(self):
        Customer.objects.create(
            name="Linked file holder",
            description="https://media.example/media/customers/projects/shared%20photo.png",
        )
        self.assertTrue(is_file_referenced("customers/projects/shared photo.png"))

    def test_admin_delete_removes_file_and_normalizes_remaining_order(self):
        staff = User.objects.create_user("media-admin", is_staff=True)
        self.client.force_login(staff)
        removed = self.stored_media("admin-delete.png", 0)
        remaining = self.stored_media("remaining.png", 7)
        storage, old_name = removed.file.storage, removed.file.name
        url = reverse("dashboard_customer_project_media_delete", args=[
            self.project.customer_id, self.project.pk, removed.pk,
        ])
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(storage.exists(old_name))
        remaining.refresh_from_db()
        self.assertEqual(remaining.display_order, 0)

    def test_bulk_project_edit_delete_uses_same_cleanup_and_ordering(self):
        removed = self.stored_media("bulk-delete.png", 0)
        remaining = self.stored_media("bulk-remaining.png", 8)
        storage, old_name = removed.file.storage, removed.file.name
        form = CustomerProjectForm(
            {"title": self.project.title, "delete_media": [removed.pk]},
            instance=self.project,
        )
        self.assertTrue(form.is_valid(), form.errors)
        with self.captureOnCommitCallbacks(execute=True):
            form.save()
        self.assertFalse(storage.exists(old_name))
        remaining.refresh_from_db()
        self.assertEqual(remaining.display_order, 0)

    def test_cascade_delete_removes_original_playback_and_poster(self):
        media = self.stored_media("original.mp4", 3, media_type="video")
        media.playback_file.save("playback.mp4", ContentFile(b"playback"), save=False)
        media.video_poster.save("poster.jpg", ContentFile(b"poster"), save=True)
        fields = (media.file, media.playback_file, media.video_poster)
        paths = [(field.storage, field.name) for field in fields]
        with self.captureOnCommitCallbacks(execute=True):
            self.project.delete()
        self.assertTrue(all(not storage.exists(name) for storage, name in paths))

    def test_rolled_back_delete_keeps_storage_file(self):
        media = self.stored_media("rollback.png", 0)
        media_pk = media.pk
        storage, name = media.file.storage, media.file.name
        try:
            with transaction.atomic():
                media.delete()
                raise RuntimeError("rollback")
        except RuntimeError:
            pass
        self.assertTrue(CustomerProjectMedia.objects.filter(pk=media_pk).exists())
        self.assertTrue(storage.exists(name))

    def test_cleanup_rejects_paths_outside_customer_uploads(self):
        for name in ("static/logo.png", "customers/logos/logo.png", "customers/projects/../logo.png", "/customers/projects/a.png"):
            self.assertFalse(is_managed_customer_media_name(name))


class CustomerMediaR2CommandTests(TestCase):
    @override_settings(R2_ENABLED=False)
    def test_refuses_cleanup_without_configured_r2(self):
        with self.assertRaises(CommandError):
            call_command("cleanup_customer_media_r2", stdout=StringIO())

    def test_dry_run_then_delete_only_old_unreferenced_customer_uploads(self):
        from core.management.commands.cleanup_customer_media_r2 import Command

        old = timezone.now() - timedelta(days=3)
        client = Mock()
        client.get_paginator.return_value.paginate.return_value = [{"Contents": [
            {"Key": "media/customers/projects/orphan.png", "Size": 10, "ETag": '"orphan"', "LastModified": old},
            {"Key": "media/customers/projects/shared.png", "Size": 20, "ETag": '"shared"', "LastModified": old},
            {"Key": "media/customers/projects/fresh.png", "Size": 5, "ETag": '"fresh"', "LastModified": timezone.now()},
            {"Key": "media/static/logo.png", "Size": 30, "ETag": '"static"', "LastModified": old},
        ]}]
        client.head_object.return_value = {
            "ContentLength": 10, "ETag": '"orphan"', "LastModified": old,
        }
        storage = Mock(location="media")

        def mark_shared(collector):
            collector.add_file_reference("customers/projects/shared.png", "shared customer")

        with (
            patch.object(Command, "_r2_context", return_value=(storage, client, "somlab", "media/customers/projects/")),
            patch("core.management.commands.cleanup_customer_media_r2.collect_website_references", side_effect=mark_shared),
            patch("core.management.commands.cleanup_customer_media_r2.r2_hosts", return_value=set()),
        ):
            dry_run = StringIO()
            call_command("cleanup_customer_media_r2", stdout=dry_run)
            client.delete_object.assert_not_called()
            self.assertIn("eligible orphans: 1", dry_run.getvalue())
            self.assertNotIn("media/static/logo.png", dry_run.getvalue())
            self.assertNotIn("fresh.png", dry_run.getvalue())
            deleted = StringIO()
            call_command("cleanup_customer_media_r2", "--delete", stdout=deleted)
        client.delete_object.assert_called_once_with(
            Bucket="somlab", Key="media/customers/projects/orphan.png",
        )
        self.assertIn("Deleted 1", deleted.getvalue())

    def test_rejects_disabling_the_recent_upload_safety_window(self):
        with self.assertRaises(CommandError):
            call_command("cleanup_customer_media_r2", "--delete", "--min-age-hours", "0")

    def test_changed_r2_object_is_skipped_before_delete(self):
        from core.management.commands.cleanup_customer_media_r2 import Command

        old = timezone.now() - timedelta(days=3)
        client = Mock()
        client.get_paginator.return_value.paginate.return_value = [{"Contents": [{
            "Key": "media/customers/projects/changed.png",
            "Size": 10, "ETag": '"original"', "LastModified": old,
        }]}]
        client.head_object.return_value = {
            "ContentLength": 10, "ETag": '"replacement"', "LastModified": old,
        }
        with (
            patch.object(Command, "_r2_context", return_value=(
                Mock(location="media"), client, "somlab", "media/customers/projects/",
            )),
            patch("core.management.commands.cleanup_customer_media_r2.collect_website_references"),
            patch("core.management.commands.cleanup_customer_media_r2.r2_hosts", return_value=set()),
        ):
            output = StringIO()
            call_command("cleanup_customer_media_r2", "--delete", stdout=output)
        client.delete_object.assert_not_called()
        self.assertIn("skipped 1", output.getvalue())
