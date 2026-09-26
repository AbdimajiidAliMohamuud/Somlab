from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.files.storage import default_storage
from django.test import TestCase, override_settings

from catalog.management.commands.reconcile_zeiss_light_microscopes import (
    Command,
)
from catalog.models import Category, Product, ProductSubcategory


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    },
)
class ZeissImageImportTests(TestCase):
    fixtures = []

    def test_import_attaches_all_verified_images_and_is_idempotent(self):
        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                call_command("reconcile_zeiss_light_microscopes", verbosity=0)
                products = Product.objects.filter(brand__iexact="ZEISS")
                self.assertEqual(products.count(), 36)
                self.assertFalse(products.filter(image="").exists())
                category = Category.objects.get(slug="light-microscopes")
                self.assertEqual(
                    category.image.name,
                    "categories/zeiss/light-microscopes-"
                    f"{Command.category_representative.lower()}.jpg",
                )
                self.assertTrue(Path(media_root, category.image.name).is_file())
                subcategories = ProductSubcategory.objects.filter(
                    category=category,
                )
                self.assertEqual(subcategories.count(), 6)
                self.assertFalse(subcategories.filter(image="").exists())

                first_names = dict(products.values_list("product_code", "image"))
                call_command("reconcile_zeiss_light_microscopes", verbosity=0)
                second_names = dict(products.values_list("product_code", "image"))
                self.assertEqual(first_names, second_names)

                expected_subcategory_images = {
                    slug: (
                        f"subcategories/zeiss/{slug}-{product_code.lower()}"
                        "-cutout.png"
                    )
                    for slug, product_code in (
                        Command.subcategory_representatives.items()
                    )
                }
                first_subcategory_names = dict(
                    subcategories.values_list("slug", "image")
                )
                self.assertEqual(
                    first_subcategory_names,
                    expected_subcategory_images,
                )
                for image_name in first_subcategory_names.values():
                    self.assertTrue(Path(media_root, image_name).is_file())
                    with default_storage.open(image_name, "rb") as stored_image:
                        from PIL import Image
                        image = Image.open(stored_image)
                        self.assertEqual(image.mode, "RGBA")
                        alpha_extrema = image.getchannel("A").getextrema()
                        self.assertEqual(alpha_extrema[0], 0)
                        self.assertEqual(alpha_extrema[1], 255)

                for image_name in first_names.values():
                    self.assertTrue(Path(media_root, image_name).is_file())
                    self.assertIn("products/zeiss/fit-v2/", image_name)

                with default_storage.open(
                    first_names["ZEISS-LM-CF-001"], "rb"
                ) as stored_image:
                    from PIL import Image
                    image = Image.open(stored_image)
                    self.assertEqual(image.size, (1200, 1200))

                category_ids = set(products.values_list("category__slug", flat=True))
                self.assertEqual(category_ids, {"light-microscopes"})
                self.assertFalse(products.filter(subcategory__isnull=True).exists())
