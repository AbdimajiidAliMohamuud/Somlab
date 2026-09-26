from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from catalog.models import Category, Product


LOCAL_TEST_STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


@override_settings(STORAGES=LOCAL_TEST_STORAGES)
class SDBiosensorStandardQImportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("import_sd_biosensor_products", "--skip-images")

    def test_import_is_limited_to_the_five_approved_standard_q_tests(self):
        from core.models import Partner

        category = Category.objects.get(slug="sd-biosensor")
        standard_q = category.subcategories.get(slug="standard-q")
        products = Product.objects.filter(category=category, is_active=True)

        self.assertEqual(category.navigation_name, "SD Biosensor Rapid Test")
        self.assertEqual(standard_q.name, "STANDARD Q")
        self.assertEqual(products.count(), 5)
        self.assertEqual(
            set(products.values_list("product_code", flat=True)),
            {"09MAL30D", "09HCV10D", "09HBS10D", "09HIV30D", "09SYP10D"},
        )
        self.assertFalse(products.exclude(subcategory=standard_q).exists())
        self.assertEqual(
            list(Partner.objects.get(name="SD Biosensor").menu_categories.all()),
            [category],
        )

        call_command("import_sd_biosensor_products", "--skip-images")
        self.assertEqual(Product.objects.filter(category=category, is_active=True).count(), 5)

    def test_import_does_not_change_products_outside_sd_biosensor_category(self):
        chemistry = Category.objects.get(slug="chemistry")
        protected = Product.objects.create(
            category=chemistry,
            name="Protected Existing Product",
            slug="protected-existing-product",
            product_code="PROTECTED-EXISTING-1",
            brand="Existing Brand",
            short_description="Must remain unchanged.",
            description="Must remain unchanged.",
        )

        call_command("import_sd_biosensor_products", "--skip-images")

        protected.refresh_from_db()
        self.assertTrue(protected.is_active)
        self.assertEqual(protected.name, "Protected Existing Product")
        self.assertEqual(protected.category, chemistry)

    def test_menu_category_subcategory_and_product_breadcrumbs(self):
        from catalog.navigation import product_navigation_groups

        laboratory = next(
            group for group in product_navigation_groups()
            if group["slug"] == "laboratory"
        )
        menu_item = next(
            item for item in laboratory["flat_items"]
            if item["label"] == "SD Biosensor Rapid Test"
        )
        standard_q = Category.objects.get(
            slug="sd-biosensor"
        ).subcategories.get(slug="standard-q")
        self.assertEqual(menu_item["url"], reverse("category_detail", args=["sd-biosensor"]))
        self.assertEqual(
            menu_item["children"],
            [{"label": "STANDARD Q", "url": standard_q.get_absolute_url()}],
        )

        product = Product.objects.get(product_code="09MAL30D")
        response = self.client.get(product.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        breadcrumbs = content[content.index('<div class="breadcrumbs">'):]
        breadcrumbs = breadcrumbs[:breadcrumbs.index("</div>")]
        expected_parts = (
            ">Home</a>",
            ">Products</a>",
            ">SD Biosensor Rapid Test</a>",
            ">STANDARD Q</a>",
            f"<strong>{product.name}</strong>",
        )
        positions = [breadcrumbs.index(part) for part in expected_parts]
        self.assertEqual(positions, sorted(positions))

    def test_category_and_standard_q_heroes_use_scoped_contain_fit(self):
        category = Category.objects.get(slug="sd-biosensor")
        standard_q = category.subcategories.get(slug="standard-q")
        hero_name = "categories/sd-biosensor/standard-q-range.jpg"
        category.image.name = hero_name
        category.save(update_fields=["image"])
        standard_q.image.name = hero_name
        standard_q.save(update_fields=["image"])

        category_response = self.client.get(category.get_absolute_url())
        self.assertEqual(category_response.status_code, 200)
        self.assertContains(category_response, "sd-biosensor-hero-fit")
        self.assertContains(category_response, hero_name)

        subcategory_response = self.client.get(standard_q.get_absolute_url())
        self.assertEqual(subcategory_response.status_code, 200)
        self.assertContains(subcategory_response, "sd-standard-q-hero-fit")
        self.assertContains(subcategory_response, hero_name)

    def test_each_product_has_detail_content_and_official_specifications(self):
        products = Product.objects.filter(
            category__slug="sd-biosensor",
            is_active=True,
        )
        for product in products:
            with self.subTest(product=product.product_code):
                response = self.client.get(product.get_absolute_url())
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, product.name)
                self.assertContains(response, product.product_code)
                self.assertContains(response, "Official source:")
                self.assertContains(response, "sdbiosensor.com/product/product_view")
                self.assertContains(response, "Storage temperature:")

        syphilis = products.get(product_code="09SYP10D")
        self.assertEqual(
            list(syphilis.variants.values_list("name", "model_number")),
            [
                ("25 tests per kit", "09SYP10D"),
                ("100 tests per kit", "09SYP10FM"),
            ],
        )

    def test_bundled_official_images_are_attached_without_altering_uploads(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            call_command("import_sd_biosensor_products", "--replace-images")
            products = Product.objects.filter(category__slug="sd-biosensor")
            self.assertEqual(products.exclude(image="").count(), 5)
            self.assertEqual(products.exclude(source_image="").count(), 5)

            for product in products:
                with self.subTest(product=product.product_code):
                    self.assertTrue(Path(media_root, product.image.name).is_file())
                    self.assertTrue(Path(media_root, product.source_image.name).is_file())
                    with product.image.open("rb") as stored_image, product.source_image.open("rb") as source_image:
                        stored_bytes = stored_image.read()
                        source_bytes = source_image.read()
                        self.assertEqual(stored_bytes, source_bytes)
                        self.assertEqual(
                            Image.open(BytesIO(stored_bytes)).size,
                            Image.open(BytesIO(source_bytes)).size,
                        )
