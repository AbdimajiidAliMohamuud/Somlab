from io import BytesIO
from tempfile import TemporaryDirectory

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from PIL import Image, ImageDraw

from catalog.images import NORMALIZED_SIZE, normalize_product_image
from catalog.models import Category, Product, ProductMedia


LOCAL_TEST_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=LOCAL_TEST_STORAGES)
class ProductUploadPreservationTests(TestCase):
    def make_png(self, size, background, foreground):
        image = Image.new("RGB", size, background)
        ImageDraw.Draw(image).rectangle(
            (size[0] // 3, size[1] // 3, size[0] * 2 // 3, size[1] * 2 // 3),
            fill=foreground,
        )
        output = BytesIO()
        image.save(output, "PNG")
        return output.getvalue()

    def test_main_and_gallery_uploads_preserve_original_canvas_and_aspect_ratio(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            category = Category.objects.get(slug="chemistry")
            main_bytes = self.make_png((640, 360), "white", (5, 75, 95))
            product = Product.objects.create(
                category=category,
                name="Wide product",
                slug="wide-product-image-test",
                product_code="IMAGE-TEST-001",
                short_description="Image preservation test.",
                description="Image preservation test.",
                image=SimpleUploadedFile("wide.png", main_bytes, content_type="image/png"),
            )
            gallery_bytes = self.make_png((240, 480), (242, 230, 210), (5, 75, 95))
            media = ProductMedia.objects.create(
                product=product,
                media_type="image",
                file=SimpleUploadedFile("portrait.png", gallery_bytes, content_type="image/png"),
            )

            for field, expected_bytes, expected_size, corner in (
                (product.image, main_bytes, (640, 360), (255, 255, 255)),
                (product.source_image, main_bytes, (640, 360), (255, 255, 255)),
                (media.file, gallery_bytes, (240, 480), (242, 230, 210)),
                (media.source_file, gallery_bytes, (240, 480), (242, 230, 210)),
            ):
                with self.subTest(field=field.name), field.open("rb") as uploaded:
                    stored = uploaded.read()
                    self.assertEqual(stored, expected_bytes)
                    with Image.open(BytesIO(stored)) as image:
                        self.assertEqual(image.size, expected_size)
                        self.assertEqual(image.convert("RGB").getpixel((0, 0)), corner)

            response = self.client.get(product.get_absolute_url())
            self.assertContains(response, product.source_image.url, count=2)
            self.assertContains(response, media.source_file.url, count=2)
            self.assertContains(
                response,
                f'data-image-fallback="{product.image.url}"',
                count=2,
            )
            self.assertContains(
                response,
                f'data-image-fallback="{media.file.url}"',
                count=2,
            )


class ProductImageNormalizationTests(SimpleTestCase):
    def make_source(self, size, box, *, transparent=False):
        mode = "RGBA" if transparent else "RGB"
        background = (255, 255, 255, 0) if transparent else "white"
        image = Image.new(mode, size, background)
        ImageDraw.Draw(image).rectangle(box, fill=(5, 75, 95, 255) if transparent else (5, 75, 95))
        output = BytesIO()
        image.save(output, "PNG")
        return ContentFile(output.getvalue(), name="source.png")

    def assert_normalized(self, source):
        result = normalize_product_image(source)
        with Image.open(result) as image:
            self.assertEqual(image.size, (NORMALIZED_SIZE, NORMALIZED_SIZE))
            alpha_bounds = image.convert("RGBA").getchannel("A").getbbox()
            self.assertIsNotNone(alpha_bounds)
            width = alpha_bounds[2] - alpha_bounds[0]
            height = alpha_bounds[3] - alpha_bounds[1]
            self.assertGreater(max(width, height), NORMALIZED_SIZE * .85)
            self.assertLessEqual(max(width, height), NORMALIZED_SIZE * .94)

    def test_normalizes_portrait_landscape_and_square_white_margins(self):
        for size, box in (
            ((800, 1200), (300, 120, 500, 1080)),
            ((1400, 800), (100, 300, 1300, 500)),
            ((1000, 1000), (200, 200, 800, 800)),
        ):
            with self.subTest(size=size):
                self.assert_normalized(self.make_source(size, box))

    def test_normalizes_transparent_margins(self):
        self.assert_normalized(
            self.make_source((1000, 1000), (250, 120, 750, 880), transparent=True)
        )

    def test_removes_edge_connected_white_background_without_erasing_white_product(self):
        image = Image.new("RGB", (900, 700), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((180, 100, 720, 600), fill=(12, 76, 94))
        draw.rectangle((260, 180, 640, 520), fill="white")
        output = BytesIO()
        image.save(output, "PNG")

        result = normalize_product_image(ContentFile(output.getvalue(), name="equipment.png"))
        with Image.open(result).convert("RGBA") as normalized:
            self.assertEqual(normalized.getpixel((0, 0))[3], 0)
            self.assertGreater(normalized.getpixel((600, 600))[3], 240)


class ProductImageCommandTests(SimpleTestCase):
    def test_brand_option_is_available(self):
        from catalog.management.commands.normalize_product_images import Command

        parser = Command().create_parser("manage.py", "normalize_product_images")
        options = parser.parse_args(["--brand", "Vatech Dental", "--reprocess", "--dry-run"])
        self.assertEqual(options.brand, "Vatech Dental")
        self.assertTrue(options.reprocess)
