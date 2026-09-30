"""Product upload optimization and public ranged playback."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from catalog.models import Category, Product, ProductMedia
from catalog.media_lifecycle import schedule_product_gallery_cleanup
from core.customer_video import save_video_media
from core.test_customer_video import test_video_bytes


class ProductVideoTests(TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory(prefix="somlab-product-video-")
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
        category = Category.objects.get(slug="chemistry")
        self.product = Product.objects.create(
            category=category, name="Video analyser", slug="video-analyser-test",
            product_code="VIDEO-TEST", short_description="Video QA",
            description="Video QA", is_active=True,
        )
        self.staff = User.objects.create_user("product-video-staff", is_staff=True)

    def upload(self):
        return SimpleUploadedFile("demo.mp4", test_video_bytes(), content_type="video/mp4")

    def test_optimized_product_video_keeps_original_and_streams_ranges(self):
        upload = self.upload()
        media = ProductMedia(product=self.product, file=upload, media_type="video")
        save_video_media(media, upload)
        self.assertTrue(media.file.storage.exists(media.file.name))
        self.assertTrue(media.playback_file.storage.exists(media.playback_file.name))
        self.assertTrue(media.video_poster.storage.exists(media.video_poster.name))
        with media.file.open("rb") as original:
            self.assertEqual(original.read(), test_video_bytes())
        with media.playback_file.open("rb") as optimized:
            content = optimized.read()
        self.assertLess(content.index(b"moov"), content.index(b"mdat"))

        page = self.client.get(self.product.get_absolute_url())
        source = reverse("product_video_source", args=[self.product.slug, media.pk])
        self.assertContains(page, f'data-src="{source}"')
        self.assertContains(page, 'preload="none"')
        self.assertContains(page, '<video autoplay muted loop playsinline webkit-playsinline preload="none"')
        self.assertContains(page, "data-product-video-open")
        self.assertContains(page, "data-product-video-fullscreen")
        self.assertContains(page, "data-video-lightbox-player")
        self.assertContains(page, media.video_poster.url)
        self.assertNotContains(page, f'<source src="{source}"')
        response = self.client.get(source, HTTP_RANGE="bytes=10-49")
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response["Accept-Ranges"], "bytes")
        self.assertEqual(response["Content-Type"], "video/mp4")
        self.assertEqual(b"".join(response.streaming_content), content[10:50])

        self.product.is_active = False
        self.product.save(update_fields=["is_active"])
        self.assertEqual(self.client.get(source).status_code, 404)

    def test_r2_style_redirect_uses_fresh_playback_url(self):
        media = ProductMedia.objects.create(
            product=self.product, file="products/gallery/original.mov",
            playback_file="products/gallery/playback/optimized.mp4",
            media_type="video",
        )
        source = reverse("product_video_source", args=[self.product.slug, media.pk])
        with patch.object(media.playback_file.storage, "url", return_value="https://media.example/optimized.mp4?fresh=1"):
            response = self.client.get(source, HTTP_RANGE="bytes=0-1023")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "https://media.example/optimized.mp4?fresh=1")
        self.assertIn("no-store", response["Cache-Control"])

    def test_failed_optimization_preserves_existing_original_and_playback(self):
        original_upload = self.upload()
        media = ProductMedia(product=self.product, file=original_upload, media_type="video")
        save_video_media(media, original_upload)
        old_names = (media.file.name, media.playback_file.name, media.video_poster.name)
        with patch("core.customer_video.run_ffmpeg", side_effect=ValidationError("Cannot optimize")):
            with self.assertRaisesMessage(ValidationError, "Cannot optimize"):
                save_video_media(media, self.upload())
        media.refresh_from_db()
        self.assertEqual(
            (media.file.name, media.playback_file.name, media.video_poster.name),
            old_names,
        )
        self.assertTrue(all(
            field.storage.exists(field.name)
            for field in (media.file, media.playback_file, media.video_poster)
        ))

    def test_admin_video_failure_does_not_delete_existing_gallery_media(self):
        original_upload = self.upload()
        media = ProductMedia(product=self.product, file=original_upload, media_type="video")
        save_video_media(media, original_upload)
        original_name = media.file.name
        self.client.force_login(self.staff)
        payload = {
            "category": self.product.category_id,
            "name": self.product.name,
            "slug": self.product.slug,
            "product_code": self.product.product_code,
            "short_description": self.product.short_description,
            "description": self.product.description,
            "availability": self.product.availability,
            "is_active": "on",
            "delete_media": [media.pk],
            "gallery_videos": [self.upload()],
        }
        with patch("core.customer_video.run_ffmpeg", side_effect=ValidationError("Cannot optimize")):
            response = self.client.post(
                reverse("dashboard_product_edit", args=[self.product.pk]), payload,
            )
        self.assertContains(response, "Cannot optimize")
        self.assertTrue(ProductMedia.objects.filter(pk=media.pk).exists())
        self.assertTrue(media.file.storage.exists(original_name))

    def test_product_cleanup_protects_shared_files(self):
        upload = self.upload()
        first = ProductMedia(product=self.product, file=upload, media_type="video")
        save_video_media(first, upload)
        shared = ProductMedia.objects.create(
            product=self.product, file=first.file.name, media_type="video",
        )
        name = first.file.name
        with self.captureOnCommitCallbacks(execute=True):
            first.delete()
            schedule_product_gallery_cleanup(first.file.storage, name)
        self.assertTrue(shared.file.storage.exists(name))
        with self.captureOnCommitCallbacks(execute=True):
            shared.delete()
            schedule_product_gallery_cleanup(shared.file.storage, name)
        self.assertFalse(shared.file.storage.exists(name))

    def test_storage_failure_cleans_new_derivative_without_publishing_original(self):
        upload = self.upload()
        media = ProductMedia(product=self.product, file=upload, media_type="video")
        with patch.object(media.video_poster, "save", side_effect=OSError("Storage unavailable")):
            with self.assertRaises(OSError):
                save_video_media(media, upload)
        self.assertFalse(ProductMedia.objects.filter(product=self.product).exists())
        playback_root = Path(self.directory.name) / "products/gallery/playback"
        self.assertFalse(list(playback_root.rglob("*.mp4")))
