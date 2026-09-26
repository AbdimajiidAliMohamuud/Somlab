import json
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from catalog.molbio_source import ASSAY_GROUPS, parse_truenat_assays


class MolbioSourceParserTests(SimpleTestCase):
    def test_extracts_assay_details_variants_and_product_image(self):
        source = '''
        <h2 class="elementor-heading-title">Truenat® MTB</h2>
        <img class="swiper-slide-image" src="https://www.molbiodiagnostics.com/wp-content/uploads/disease.jpg">
        <img class="swiper-slide-image" src="https://www.molbiodiagnostics.com/wp-content/uploads/kit.jpg">
        <p>Truenat® MTB is a chip-based real-time PCR test.</p>
        <table id="table-TechnicalSpecifications"><tr><td>Assay Method</td><td>Real Time PCR</td></tr></table>
        <span>Contents of the kit</span><ol><li>Micro PCR chip</li></ol>
        <table id="table-OrderingInformation"><tr><td>5T</td><td>601030005</td></tr></table>
        '''
        products = parse_truenat_assays(source)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["group"], "Respiratory Infections")
        self.assertEqual(products[0]["specifications"], [["Assay Method", "Real Time PCR"]])
        self.assertEqual(products[0]["kit_contents"], ["Micro PCR chip"])
        self.assertEqual(products[0]["variants"], [{"name": "5T", "sku": "601030005"}])
        self.assertEqual(
            products[0]["image_url"],
            "https://www.molbiodiagnostics.com/wp-content/uploads/disease.jpg",
        )
        self.assertEqual(
            products[0]["gallery_urls"],
            ["https://www.molbiodiagnostics.com/wp-content/uploads/kit.jpg"],
        )

    def test_bundled_assays_have_distinct_primary_and_gallery_assets(self):
        data_file = (
            Path(__file__).resolve().parent
            / "management"
            / "data"
            / "molbio"
            / "products.json"
        )
        products = json.loads(data_file.read_text(encoding="utf-8"))["products"]
        assays = [
            product for product in products
            if product.get("subcategory") == "Truenat Assays"
        ]
        self.assertEqual(len(assays), 36)
        self.assertEqual(len({product["image_url"] for product in assays}), 36)
        self.assertTrue(all(len(product["gallery_urls"]) == 1 for product in assays))
        self.assertTrue(all(
            product["image_url"] != product["gallery_urls"][0]
            for product in assays
        ))


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
class MolbioImportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("import_molbio_products", "--skip-images")

    def test_imports_complete_grouped_catalogue_idempotently(self):
        from catalog.models import Category, Product
        from core.models import Partner

        category = Category.objects.get(slug="molbio")
        self.assertEqual(
            list(
                category.subcategories.filter(parent__isnull=True)
                .values_list("name", flat=True)
            ),
            ["Truenat", "Truenat Assays", "iBreastExam", "ProRad Atlas", "OptraScan"],
        )
        self.assertEqual(Product.objects.filter(brand="Molbio Diagnostics", is_active=True).count(), 48)
        self.assertEqual(list(Partner.objects.get(name="Molbio Diagnostics").menu_categories.all()), [category])

        call_command("import_molbio_products", "--skip-images")
        self.assertEqual(Product.objects.filter(brand="Molbio Diagnostics", is_active=True).count(), 48)
        self.assertEqual(
            Product.objects.filter(
                subcategory__category=category,
                subcategory__slug="truenat-platform",
                is_active=True,
            ).count(),
            3,
        )

    def test_truenat_assays_use_exact_nested_groups_and_unique_membership(self):
        from catalog.models import Product, ProductSubcategory

        parent = ProductSubcategory.objects.get(
            category__slug="molbio",
            slug="truenat-assays",
        )
        groups = list(
            parent.children.filter(is_active=True)
            .order_by("display_order", "name")
        )
        self.assertEqual(
            [group.name for group in groups],
            list(ASSAY_GROUPS),
        )
        self.assertEqual(
            {
                group.name: Product.objects.filter(
                    subcategory=group,
                    is_active=True,
                    product_code__startswith="MOLBIO-ASSAY-",
                ).count()
                for group in groups
            },
            {name: len(assays) for name, assays in ASSAY_GROUPS.items()},
        )
        assay_products = Product.objects.filter(
            product_code__startswith="MOLBIO-ASSAY-",
            is_active=True,
        )
        self.assertEqual(assay_products.count(), 36)
        self.assertEqual(
            assay_products.values("pk").distinct().count(),
            36,
        )
        self.assertFalse(
            assay_products.exclude(
                subcategory__parent=parent,
            ).exists()
        )

    def test_truenat_assay_pages_use_nested_breadcrumbs_and_accordion(self):
        from catalog.models import ProductSubcategory

        parent = ProductSubcategory.objects.get(
            category__slug="molbio",
            slug="truenat-assays",
        )
        parent_response = self.client.get(parent.get_absolute_url())
        self.assertEqual(parent_response.status_code, 200)
        self.assertContains(
            parent_response,
            'class="product-card"',
            count=8,
        )
        self.assertContains(
            parent_response,
            "truenat-assay-group-card-image-fit",
            count=8,
        )
        self.assertNotContains(
            parent_response,
            'class="product-card truenat-assay-group-card"',
        )
        self.assertNotContains(parent_response, "nested-subcategory-card")
        for group_name in ASSAY_GROUPS:
            self.assertContains(parent_response, group_name)

        group = parent.children.get(slug="respiratory-infections")
        response = self.client.get(group.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'<a href="{parent.get_absolute_url()}">{parent.name}</a>',
            html=False,
        )
        self.assertContains(response, "product-related-item", count=8)
        self.assertContains(response, "Included &amp; Related", html=False)
        for assay_name in ASSAY_GROUPS[group.name]:
            self.assertContains(response, assay_name)
        rendered = response.content.decode()
        positions = [
            rendered.index(assay_name)
            for assay_name in ASSAY_GROUPS[group.name]
        ]
        self.assertEqual(positions, sorted(positions))

    def test_truenat_assay_media_import_stores_all_assays_and_group_heroes(self):
        from catalog.models import Product, ProductSubcategory

        unrelated = Product.objects.get(product_code="MOLBIO-TRUELAB-UNO-DX")
        unrelated_image = unrelated.image.name
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            call_command("import_truenat_assay_media", verbosity=0)

            assay_products = Product.objects.filter(
                product_code__startswith="MOLBIO-ASSAY-",
                is_active=True,
            ).select_related("subcategory")
            self.assertEqual(assay_products.count(), 36)
            for product in assay_products:
                self.assertTrue(product.image.name)
                self.assertEqual(product.source_image.name, product.image.name)
                definition = next(
                    item for item in self._molbio_assays()
                    if item["name"] == product.name
                )
                expected_primary_filename = Path(
                    definition["image_url"]
                ).name
                self.assertTrue(
                    product.image.name.endswith(expected_primary_filename)
                )
                self.assertTrue(Path(media_root, product.image.name).is_file())

            group_heroes = ProductSubcategory.objects.filter(
                category__slug="molbio",
                parent__slug="truenat-assays",
                is_active=True,
            )
            self.assertEqual(group_heroes.count(), 8)
            for group in group_heroes:
                self.assertTrue(group.image.name)
                self.assertTrue(Path(media_root, group.image.name).is_file())

            unrelated.refresh_from_db()
            self.assertEqual(unrelated.image.name, unrelated_image)

            first_images = list(
                assay_products.order_by("pk").values_list("image", flat=True)
            )
            call_command("import_truenat_assay_media", verbosity=0)
            self.assertEqual(
                list(
                    assay_products.order_by("pk")
                    .values_list("image", flat=True)
                ),
                first_images,
            )

    def test_catalogue_search_detail_variants_and_menu_use_existing_architecture(self):
        from catalog.models import Category, Product

        category_response = self.client.get(reverse("category_detail", args=["molbio"]))
        self.assertEqual(category_response.status_code, 200)
        self.assertContains(category_response, "Truenat")
        self.assertContains(category_response, "OptraScan")

        product = Product.objects.get(slug="molbio-truenat-mtb")
        detail_response = self.client.get(product.get_absolute_url())
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Truenat® MTB")
        self.assertContains(detail_response, "601030005")
        self.assertContains(detail_response, "Available on request")

        search_response = self.client.get(reverse("product_list"), {"q": "Truenat MTB"})
        self.assertContains(search_response, "Truenat® MTB")

        menu_response = self.client.get(reverse("home"))
        self.assertContains(menu_response, "Truenat® Real-Time PCR")
        self.assertContains(
            menu_response,
            'aria-controls="laboratory-menu-molbio"',
        )
        self.assertContains(menu_response, "Truenat Assays")
        self.assertContains(menu_response, "ProRad Atlas")

    def test_brand_filter_search_and_availability_cover_all_molbio_items(self):
        from catalog.models import Product

        filtered = self.client.get(
            reverse("product_list"), {"brand": "molbio-diagnostics"}
        )
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(len(filtered.context["products"]), 48)
        self.assertEqual(
            set(filtered.context["products"].values_list("brand", flat=True)),
            {"Molbio Diagnostics"},
        )

        searched = self.client.get(reverse("product_list"), {"q": "OptraScan"})
        self.assertEqual(len(searched.context["products"]), 5)
        self.assertFalse(
            Product.objects.filter(
                brand="Molbio Diagnostics",
                is_active=True,
            ).exclude(availability="on_request").exists()
        )

    def test_clear_images_removes_only_molbio_image_fields_and_image_media(self):
        from catalog.models import Product, ProductMedia

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            product = Product.objects.get(slug="molbio-truenat-mtb")
            Product.objects.filter(pk=product.pk).update(
                image="products/molbio-main.png",
                source_image="products/originals/molbio-main.png",
            )
            ProductMedia.objects.create(
                product=product,
                file=SimpleUploadedFile("gallery.png", self._png_bytes()),
                media_type="image",
            )
            video = ProductMedia.objects.create(
                product=product,
                file=SimpleUploadedFile("demo.mp4", b"video"),
                media_type="video",
            )

            call_command("import_molbio_products", "--clear-images")

            product.refresh_from_db()
            self.assertFalse(product.image)
            self.assertFalse(product.source_image)
            self.assertFalse(product.gallery_media.filter(media_type="image").exists())
            self.assertTrue(product.gallery_media.filter(pk=video.pk).exists())

    def test_manual_molbio_uploads_are_preserved_without_normalization(self):
        from catalog.models import Product, ProductMedia

        product = Product.objects.get(slug="molbio-truenat-mtb")
        original = self._png_bytes(size=(19, 7))
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            product.image = SimpleUploadedFile("approved.png", original, "image/png")
            product.save()
            product.refresh_from_db()
            with product.image.open("rb") as saved:
                self.assertEqual(saved.read(), original)

            gallery = ProductMedia.objects.create(
                product=product,
                file=SimpleUploadedFile("approved-gallery.png", original, "image/png"),
                media_type="image",
            )
            with gallery.file.open("rb") as saved:
                self.assertEqual(saved.read(), original)

    def test_ibreastexam_imports_only_official_product_and_feature_media(self):
        from catalog.models import Product

        product = Product.objects.get(product_code="MOLBIO-IBREASTEXAM")
        unrelated = Product.objects.get(product_code="MOLBIO-TRUELAB-UNO-DX")
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            call_command("import_ibreastexam_media", verbosity=0)
            product.refresh_from_db()
            unrelated.refresh_from_db()

            self.assertEqual(
                product.image.name,
                "products/molbio/ibreastexam/interface-new.jpg",
            )
            self.assertEqual(product.source_image.name, product.image.name)
            self.assertEqual(
                product.subcategory.image.name,
                "subcategories/molbio/ibreastexam/interface-new.jpg",
            )
            self.assertFalse(unrelated.image)
            self.assertEqual(product.gallery_media.count(), 4)
            self.assertEqual(
                list(product.gallery_media.values_list("display_order", flat=True)),
                [10, 11, 12, 13],
            )

            detail = self.client.get(product.get_absolute_url())
            self.assertEqual(detail.status_code, 200)
            self.assertContains(detail, "ibreastexam-product-gallery-fit")
            self.assertContains(detail, "Breast Lumps")
            self.assertContains(detail, "Tactile Imaging")
            self.assertContains(detail, "Early Detection")
            self.assertContains(detail, "Documentation")
            self.assertEqual(detail.content.count(b"data-gallery-slide="), 5)

            subcategory = self.client.get(product.subcategory.get_absolute_url())
            self.assertContains(subcategory, "ibreastexam-subcategory-image-fit")
            self.assertContains(subcategory, "ibreastexam-card-image-fit")

            first_media = list(product.gallery_media.values_list("file", flat=True))
            call_command("import_ibreastexam_media", verbosity=0)
            self.assertEqual(product.gallery_media.count(), 4)
            self.assertEqual(
                list(product.gallery_media.values_list("file", flat=True)),
                first_media,
            )

            for field in [
                product.image,
                product.subcategory.image,
                *(media.file for media in product.gallery_media.all()),
            ]:
                self.assertTrue(Path(media_root, field.name).is_file())

    def test_optrascan_keeps_only_official_models_and_imports_exact_media(self):
        from catalog.models import Product

        official_names = ["OS Ultra", "OS - Lite", "OS - SiX", "OS - FS", "OS - Fli"]
        subcategory = Product.objects.get(
            product_code="MOLBIO-OPTRASCAN-OS-ULTRA"
        ).subcategory
        invalid = Product.objects.create(
            category=subcategory.category,
            subcategory=subcategory,
            name="OptraScan Digital Pathology Solution",
            slug="molbio-optrascan-digital-pathology-solution-test",
            product_code="MOLBIO-OPTRASCAN-SOLUTION",
            brand="Molbio Diagnostics",
            short_description="Invalid aggregate listing.",
            description="Invalid aggregate listing.",
            availability="on_request",
            is_active=True,
        )
        unrelated = Product.objects.get(product_code="MOLBIO-TRUELAB-UNO-DX")

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            call_command("import_optrascan_media", verbosity=0)
            invalid.refresh_from_db()
            unrelated.refresh_from_db()
            subcategory.refresh_from_db()

            products = Product.objects.filter(
                subcategory=subcategory,
                is_active=True,
            ).order_by("id")
            self.assertEqual(list(products.values_list("name", flat=True)), official_names)
            self.assertFalse(invalid.is_active)
            self.assertFalse(unrelated.image)
            self.assertEqual(
                subcategory.image.name,
                "subcategories/molbio/optrascan/os-ultra-image-1.jpg",
            )
            self.assertTrue(Path(media_root, subcategory.image.name).is_file())

            for product in products:
                self.assertTrue(product.image.name.startswith("products/molbio/optrascan/"))
                self.assertEqual(product.source_image.name, product.image.name)
                self.assertTrue(Path(media_root, product.image.name).is_file())

            response = self.client.get(subcategory.get_absolute_url())
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "optrascan-subcategory-image-fit")
            self.assertContains(response, "optrascan-card-image-fit", count=5)
            for name in official_names:
                self.assertContains(response, name)
            self.assertNotContains(response, "OptraScan Digital Pathology Solution")

            first_images = list(products.values_list("image", flat=True))
            call_command("import_optrascan_media", verbosity=0)
            self.assertEqual(
                list(products.values_list("image", flat=True)),
                first_images,
            )

    def test_prorad_atlas_keeps_three_products_with_exact_media(self):
        from catalog.models import Product, ProductSubcategory

        subcategory = ProductSubcategory.objects.get(
            category__slug="molbio",
            slug="prorad-atlas",
        )
        Product.objects.create(
            category=subcategory.category,
            subcategory=subcategory,
            name="Incorrect ProRad listing",
            slug="incorrect-prorad-listing",
            product_code="MOLBIO-PRORAD-EXTRA",
            brand="Molbio Diagnostics",
            short_description="Incorrect listing.",
            description="Incorrect listing.",
            availability="on_request",
            is_active=True,
        )

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            call_command("correct_prorad_atlas", verbosity=0)
            products = Product.objects.filter(
                subcategory=subcategory,
                is_active=True,
            ).order_by("name")
            self.assertEqual(
                list(products.values_list("name", flat=True)),
                [
                    "Atlas Ultraportable",
                    "Atlas Ultraportable Plus",
                    "Atlas Ultraportable Ultima",
                ],
            )
            self.assertEqual(
                set(products.values_list("image", flat=True)),
                {
                    "products/molbio/prorad-atlas/ProRad-Atlas-Ultraportable-Variants.png",
                    "products/molbio/prorad-atlas/Atlas-Ultraportable-Plus.png",
                    "products/molbio/prorad-atlas/Atlas-Ultraportable-Ultima.png",
                },
            )
            for product in products:
                self.assertEqual(product.source_image.name, product.image.name)
                self.assertTrue(Path(media_root, product.image.name).is_file())

            subcategory.refresh_from_db()
            self.assertEqual(
                subcategory.image.name,
                "subcategories/molbio/prorad-atlas/ProRad-Atlas-Ultraportable-Variants.png",
            )
            self.assertTrue(Path(media_root, subcategory.image.name).is_file())

            response = self.client.get(subcategory.get_absolute_url())
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "prorad-atlas-subcategory-image-fit")
            self.assertContains(response, "prorad-atlas-card-image-fit", count=3)
            self.assertNotContains(response, "Incorrect ProRad listing")

            for product in products:
                detail = self.client.get(product.get_absolute_url())
                self.assertEqual(detail.status_code, 200)
                self.assertContains(detail, "prorad-atlas-product-gallery-fit")
                self.assertContains(detail, product.description)

            first_images = list(products.values_list("image", flat=True))
            call_command("correct_prorad_atlas", verbosity=0)
            self.assertEqual(
                list(products.values_list("image", flat=True)),
                first_images,
            )

    def test_truenat_listing_keeps_only_three_truelab_products(self):
        from catalog.models import Product

        expected_names = ["Truelab® Duo", "Truelab® Quattro", "Truelab® Uno Dx"]
        subcategory = Product.objects.get(
            product_code="MOLBIO-TRUELAB-DUO"
        ).subcategory
        for index, name in enumerate(("Truenat®", "Trueprep AUTO v2"), start=1):
            Product.objects.create(
                category=subcategory.category,
                subcategory=subcategory,
                name=name,
                slug=f"truenat-extra-{index}",
                product_code=f"TRUENAT-EXTRA-{index}",
                brand="Molbio Diagnostics",
                short_description="Extra listing.",
                description="Extra listing.",
                availability="on_request",
                is_active=True,
            )

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            call_command("correct_truenat_listing", verbosity=0)
            products = Product.objects.filter(
                subcategory=subcategory,
                is_active=True,
            ).order_by("name")
            self.assertEqual(
                list(products.values_list("name", flat=True)),
                expected_names,
            )
            self.assertEqual(
                set(products.values_list("image", flat=True)),
                {
                    "products/molbio/truenat/duo.jpg",
                    "products/molbio/truenat/Quattro.jpg",
                    "products/molbio/truenat/uno.jpg",
                },
            )
            for product in products:
                self.assertEqual(product.source_image.name, product.image.name)
                self.assertTrue(Path(media_root, product.image.name).is_file())

            subcategory.refresh_from_db()
            self.assertEqual(subcategory.name, "Truenat")
            self.assertEqual(
                subcategory.image.name,
                "subcategories/molbio/truenat/duo.jpg",
            )
            self.assertTrue(Path(media_root, subcategory.image.name).is_file())

            category = subcategory.category
            category.refresh_from_db()
            self.assertEqual(
                category.image.name,
                "subcategories/molbio/truenat/duo.jpg",
            )
            category_response = self.client.get(category.get_absolute_url())
            self.assertEqual(category_response.status_code, 200)
            self.assertContains(category_response, "molbio-category-hero-fit")

            response = self.client.get(subcategory.get_absolute_url())
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "<title>Truenat —", html=False)
            self.assertContains(response, "Products in Truenat")
            self.assertContains(response, "truenat-subcategory-image-fit")
            self.assertContains(response, "truenat-card-image-fit", count=3)
            self.assertNotContains(response, "Trueprep AUTO v2")

            for product in products:
                detail = self.client.get(product.get_absolute_url())
                self.assertEqual(detail.status_code, 200)
                self.assertContains(detail, "truenat-product-gallery-fit")

            first_images = list(products.values_list("image", flat=True))
            call_command("correct_truenat_listing", verbosity=0)
            self.assertEqual(
                list(products.values_list("image", flat=True)),
                first_images,
            )

    @staticmethod
    def _png_bytes(size=(12, 8)):
        output = BytesIO()
        Image.new("RGB", size, "white").save(output, format="PNG")
        return output.getvalue()

    @staticmethod
    def _molbio_assays():
        data_file = (
            Path(__file__).resolve().parent
            / "management"
            / "data"
            / "molbio"
            / "products.json"
        )
        return [
            item
            for item in json.loads(data_file.read_text(encoding="utf-8"))["products"]
            if item.get("subcategory") == "Truenat Assays"
        ]
