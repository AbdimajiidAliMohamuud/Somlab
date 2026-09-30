from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import subprocess

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from core.customer_video import MAX_VIDEO_BYTES, ffmpeg_executable, save_video_media
from core.models import Customer, CustomerProject, CustomerProjectMedia
from dashboard.forms import CustomerProjectForm, CustomerProjectMediaForm


@lru_cache(maxsize=None)
def test_video_bytes(extension="mp4"):
    with TemporaryDirectory(prefix="somlab-video-test-") as directory:
        output = Path(directory) / f"test.{extension}"
        codecs = {
            "webm": ["-c:v", "libvpx-vp9", "-c:a", "libopus"],
            "ogv": ["-c:v", "libtheora", "-c:a", "libvorbis"],
            "ogg": ["-c:v", "libtheora", "-c:a", "libvorbis"],
        }.get(extension, ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac"])
        subprocess.run([
            ffmpeg_executable(), "-nostdin", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc2=size=240x320:rate=15",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
            "-t", "2", *codecs, str(output),
        ], check=True, capture_output=True, timeout=60)
        return output.read_bytes()


class CustomerVideoTests(TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory(prefix="somlab-video-storage-")
        self.addCleanup(self.directory.cleanup)
        self.settings_override = override_settings(
            MEDIA_ROOT=self.directory.name,
            STORAGES={
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
            },
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.customer = Customer.objects.create(name="Video QA", slug="video-qa", is_active=True)
        self.project = CustomerProject.objects.create(customer=self.customer, title="Video QA project")
        self.staff = User.objects.create_user("video-qa-staff", is_staff=True)
        self.client.force_login(self.staff)

    def upload(self, content=None, extension="mp4"):
        return SimpleUploadedFile(
            f"portrait.{extension}", content if content is not None else test_video_bytes(extension),
            content_type="application/octet-stream",
        )

    def media_form(self, upload):
        return CustomerProjectMediaForm(
            {"media_type": "video"}, {"file": upload},
            instance=CustomerProjectMedia(project=self.project),
        )

    def test_exact_size_boundary_in_both_forms(self):
        for size, valid in ((100 * 1024 * 1024 + 1, True), (MAX_VIDEO_BYTES, True), (MAX_VIDEO_BYTES + 1, False)):
            with self.subTest(size=size):
                upload = self.upload(b"\0\0\0\x18ftypmp42" + b"\0" * 32)
                upload.size = size
                single = self.media_form(upload)
                bulk = CustomerProjectForm({"title": "Video"}, {"project_videos": [upload]})
                self.assertEqual(single.is_valid(), valid, single.errors)
                self.assertEqual(bulk.is_valid(), valid, bulk.errors)
                if not valid:
                    self.assertIn("under 1 GB", str(single.errors))
                    self.assertIn("under 1 GB", str(bulk.errors))

    def test_fake_and_unsupported_videos_are_rejected(self):
        for upload in (self.upload(b"not a video"), self.upload(b"", "mp4"), self.upload(b"hello", "exe")):
            self.assertFalse(self.media_form(upload).is_valid())

    def test_streaming_limit_rejects_before_saving(self):
        with patch("dashboard.customer_uploads.MAX_VIDEO_BYTES", 8):
            response = self.client.post(
                reverse("dashboard_customer_project_add", args=[self.customer.pk]),
                {"title": "Rejected project", "project_videos": [self.upload(b"x" * 100)]},
            )
        self.assertContains(response, "under 1 GB")
        self.assertFalse(CustomerProject.objects.filter(title="Rejected project").exists())

    def test_real_admin_upload_and_public_range_playback(self):
        response = self.client.post(
            reverse("dashboard_customer_project_media_add", args=[self.customer.pk, self.project.pk]),
            {"media_type": "video", "file": self.upload()},
        )
        self.assertEqual(response.status_code, 302)
        media = self.project.media.get()
        for field in (media.file, media.playback_file, media.video_poster):
            self.assertTrue(field.storage.exists(field.name))
        with media.file.open("rb") as original:
            self.assertEqual(original.read(), test_video_bytes())
        with media.playback_file.open("rb") as playback:
            content = playback.read()
        self.assertLess(content.index(b"moov"), content.index(b"mdat"))
        page = self.client.get(self.customer.get_absolute_url())
        self.assertContains(page, "data-customer-video-player")
        self.assertContains(page, 'controls autoplay muted loop playsinline webkit-playsinline preload="none"')
        self.assertContains(page, "data-customer-video-play")
        self.assertContains(page, "data-customer-video-fullscreen")
        self.assertContains(page, "data-video-lightbox-player")
        self.assertContains(page, "data-video-lightbox-close")
        self.assertContains(page, '<video controls playsinline webkit-playsinline preload="none"')
        self.assertNotContains(page, "<span>Play video</span>")
        self.assertContains(page, media.video_poster.url)
        source = reverse("customer_video_source", args=[self.customer.slug, media.pk])
        self.assertContains(page, f'data-src="{source}"')
        response = self.client.get(source, HTTP_RANGE="bytes=10-49")
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response["Content-Type"], "video/mp4")
        self.assertEqual(b"".join(response.streaming_content), content[10:50])
        self.assertEqual(self.client.get(source, HTTP_RANGE="bytes=99999999-").status_code, 416)
        self.customer.is_active = False
        self.customer.save()
        self.assertEqual(self.client.get(source).status_code, 404)

    def test_common_formats_generate_mp4_playback_and_preserve_original(self):
        for extension in ("webm", "mov", "m4v", "ogv", "ogg"):
            with self.subTest(extension=extension):
                form = self.media_form(self.upload(extension=extension))
                self.assertTrue(form.is_valid(), form.errors)
                media = form.save()
                self.assertTrue(media.file.name.endswith(f".{extension}"))
                self.assertTrue(media.playback_file.name.endswith(".mp4"))
                self.assertTrue(media.video_poster.name.endswith(".jpg"))

    def test_high_bitrate_upload_is_substantially_smaller_with_small_poster(self):
        with TemporaryDirectory(prefix="somlab-high-bitrate-") as directory:
            source = Path(directory) / "source.mp4"
            subprocess.run([
                ffmpeg_executable(), "-nostdin", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=30",
                "-t", "3", "-c:v", "libx264", "-crf", "8",
                "-pix_fmt", "yuv420p", str(source),
            ], check=True, capture_output=True, timeout=60)
            upload = self.upload(source.read_bytes())
        media = self.media_form(upload)
        self.assertTrue(media.is_valid(), media.errors)
        saved = media.save()
        self.assertLess(saved.playback_file.size, saved.file.size * 0.5)
        self.assertLess(saved.video_poster.size, 50 * 1024)
        with saved.video_poster.open("rb") as poster:
            with Image.open(poster) as image:
                self.assertLessEqual(max(image.size), 640)

    def test_corrupt_container_returns_form_error_without_publishing(self):
        response = self.client.post(
            reverse("dashboard_customer_project_media_add", args=[self.customer.pk, self.project.pk]),
            {"media_type": "video", "file": self.upload(b"\0\0\0\x18ftypmp42" + b"\0" * 32)},
        )
        self.assertContains(response, "could not be decoded")
        self.assertFalse(self.project.media.exists())

    def test_r2_playback_redirect_is_fresh_and_private_customer_is_not_exposed(self):
        media = CustomerProjectMedia.objects.create(
            project=self.project, media_type="video", file="original.mov", playback_file="playback.mp4",
        )
        with patch.object(media.playback_file.storage, "url", return_value="https://media.example/video.mp4?signature=fresh"):
            response = self.client.get(reverse("customer_video_source", args=[self.customer.slug, media.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "https://media.example/video.mp4?signature=fresh")
        self.assertIn("no-store", response["Cache-Control"])
