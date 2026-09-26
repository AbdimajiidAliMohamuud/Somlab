from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.html import escape

from catalog.models import Category, Product, ProductRelatedItem


class MESSQACatalogueImportTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls._media_directory = TemporaryDirectory()
        cls._media_override = override_settings(
            MEDIA_ROOT=cls._media_directory.name,
            STORAGES={
                "default": {
                    "BACKEND": "django.core.files.storage.FileSystemStorage"
                },
                "staticfiles": {
                    "BACKEND": (
                        "whitenoise.storage.CompressedManifestStaticFilesStorage"
                    )
                },
            },
        )
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        cls._media_directory.cleanup()

    @classmethod
    def setUpTestData(cls):
        call_command("import_mes_sqa_products")

    def test_import_contains_the_complete_official_mes_catalogue(self):
        from core.models import Partner

        category = Category.objects.get(slug="medical-electronic-systems")
        automated = category.subcategories.get(
            slug="automated-semen-analysis-solutions"
        )
        products = Product.objects.filter(category=category, is_active=True)

        self.assertEqual(category.navigation_name, "Semen Analyzers (SQA)")
        self.assertEqual(automated.name, "Automated Semen Analysis Solutions")
        self.assertEqual(products.count(), 39)
        self.assertEqual(products.filter(is_catalogue_listing=True).count(), 14)
        self.assertEqual(products.filter(is_catalogue_listing=False).count(), 25)
        stored_counts = {
            "automated-semen-analysis-solutions": 10,
            "maleman-reference-lab-services": 1,
            "consumer-semen-analysis-solutions": 3,
            "semen-analysis-validation-kits": 17,
            "veterinary-semen-analysis-solutions": 8,
        }
        self.assertEqual(
            set(category.subcategories.filter(is_active=True).values_list(
                "slug", flat=True
            )),
            set(stored_counts),
        )
        for slug, count in stored_counts.items():
            with self.subTest(subcategory=slug):
                self.assertEqual(
                    products.filter(subcategory__slug=slug).count(), count
                )
        self.assertTrue(products.filter(product_code="YO Home Sperm Test Kit"))
        self.assertTrue(products.filter(product_code="SQA-Vb"))
        self.assertTrue(products.filter(product_code="SQA-Vp"))
        self.assertTrue(products.filter(product_code="SQA-Ve"))
        self.assertTrue(products.filter(product_code="SQA-Vt"))
        self.assertIn(
            category,
            Partner.objects.get(name="Medical Electronic Systems")
            .menu_categories.all(),
        )
        self.assertEqual(products.exclude(image="").count(), 21)

        call_command("import_mes_sqa_products")
        self.assertEqual(
            Product.objects.filter(category=category, is_active=True).count(),
            39,
        )

    def test_import_does_not_change_products_outside_mes_category(self):
        chemistry = Category.objects.get(slug="chemistry")
        protected = Product.objects.create(
            category=chemistry,
            name="Protected Existing Product",
            slug="protected-existing-product-mes",
            product_code="PROTECTED-EXISTING-MES-1",
            brand="Existing Brand",
            short_description="Must remain unchanged.",
            description="Must remain unchanged.",
        )

        call_command("import_mes_sqa_products")

        protected.refresh_from_db()
        self.assertTrue(protected.is_active)
        self.assertEqual(protected.name, "Protected Existing Product")
        self.assertEqual(protected.category, chemistry)

    def test_scoped_relationship_sync_changes_only_selected_parent(self):
        selected = Product.objects.get(product_code="MES-QWIKCHECK-TEST-KITS")
        untouched = Product.objects.get(product_code="SQA-iOw")
        false_selected = ProductRelatedItem.objects.create(
            parent_product=selected,
            name="Unsupported selected item",
        )
        untouched_item = untouched.related_items.first()
        untouched_item.description = "Protected relationship description"
        untouched_item.save(update_fields=["description"])

        call_command(
            "import_mes_sqa_products",
            relationship_parent=["MES-QWIKCHECK-TEST-KITS"],
            skip_images=True,
        )

        self.assertFalse(
            ProductRelatedItem.objects.filter(pk=false_selected.pk).exists()
        )
        self.assertEqual(selected.related_items.count(), 7)
        self.assertFalse(selected.related_items.filter(description="").exists())
        untouched_item.refresh_from_db()
        self.assertEqual(
            untouched_item.description,
            "Protected relationship description",
        )

    def test_menu_hierarchy_and_product_breadcrumb(self):
        from catalog.navigation import product_navigation_groups

        laboratory = next(
            group for group in product_navigation_groups()
            if group["slug"] == "laboratory"
        )
        menu_item = next(
            item for item in laboratory["flat_items"]
            if item["label"] == "Semen Analyzers (SQA)"
        )
        category = Category.objects.get(slug="medical-electronic-systems")
        automated = category.subcategories.get(
            slug="automated-semen-analysis-solutions"
        )
        self.assertEqual(menu_item["url"], category.get_absolute_url())
        self.assertEqual(
            [child["label"] for child in menu_item["children"]],
            [
                "Automated Semen Analysis Solutions",
                "MaleMan Reference Lab Services",
                "Consumer Semen Analysis Solutions",
                "Semen Analysis & Validation Kits",
                "Veterinary Semen Analysis Solutions",
            ],
        )

        product = Product.objects.get(product_code="SQA-Vision")
        response = self.client.get(product.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        breadcrumbs = content[content.index('<div class="breadcrumbs">'):]
        breadcrumbs = breadcrumbs[:breadcrumbs.index("</div>")]
        expected_parts = (
            ">Home</a>",
            ">Products</a>",
            ">Semen Analyzers (SQA)</a>",
            ">Automated Semen Analysis Solutions</a>",
            f"<strong>{product.name}</strong>",
        )
        positions = [breadcrumbs.index(part) for part in expected_parts]
        self.assertEqual(positions, sorted(positions))

    def test_every_product_has_detail_content_and_official_source(self):
        products = Product.objects.filter(
            category__slug="medical-electronic-systems",
            is_active=True,
        )
        for product in products:
            with self.subTest(product=product.product_code):
                response = self.client.get(product.get_absolute_url())
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, escape(product.name))
                self.assertContains(response, escape(product.product_code))
                if product.specifications:
                    self.assertContains(response, "Official source:")
                    self.assertContains(response, "mes-global.com/products/")

    def test_qwikcheck_is_clearly_discontinued(self):
        product = Product.objects.get(product_code="QwikCheck Gold")
        self.assertEqual(product.availability, "unavailable")
        self.assertIn("Product status: Discontinued", product.specifications)
        response = self.client.get(product.get_absolute_url())
        self.assertContains(response, "Discontinued")
        self.assertContains(response, "Unavailable")
        self.assertNotContains(response, "Add to cart")

    def test_sqa_io_restores_the_official_what_is_included_section(self):
        analyzer = Product.objects.get(product_code="SQA-iOw")
        response = self.client.get(analyzer.get_absolute_url())
        expected_names = [
            "SQA-iOw Automated Analyzer",
            "SQA-VU Visualization System",
            "Docking Station for SQA-iOw + VU",
            "Desktop PC + Monitor",
            "SQA Semen Analysis Test Kit",
            "SQA QC & Cleaning Kit",
            "QwikCheck Fixed Coverslip Slides",
            "QwikCheck Proficiency & Training Kit",
        ]
        self.assertEqual(
            list(analyzer.related_items.values_list("name", flat=True)),
            expected_names,
        )
        self.assertContains(response, "Included and related items")
        self.assertContains(response, 'class="product-related-item"', count=8)
        self.assertContains(response, "data-product-related-preview", count=8)
        self.assertContains(response, 'class="product-related-image"', count=8)
        self.assertNotContains(response, "product-related-specifications")
        self.assertNotContains(
            response,
            "Open a row for details, specifications and links",
        )
        self.assertNotContains(response, "Included &amp; Related<span>")
        self.assertNotContains(response, "View item")
        self.assertContains(response, "YOU MAY ALSO NEED")
        self.assertEqual(
            [product.product_code for product in response.context["related"]],
            ["SQA-Vision", "SQA-V Gold", "QwikCheck Gold"],
        )
        for item in response.context["nested_items"]:
            with self.subTest(included_image=item.name):
                self.assertTrue(item.image)
                self.assertContains(response, item.image.url)

    def test_non_included_mentions_are_not_relationships(self):
        empty_parent_codes = {
            "SQA-Vision", "SQA-V Gold", "QwikCheck Gold",
            "MaleMan Reference Lab Services", "YO Home Sperm Test Kit",
            "SQA-Vb", "SQA-Vp", "SQA-Ve", "SQA-Vt",
        }
        for product in Product.objects.filter(product_code__in=empty_parent_codes):
            with self.subTest(product=product.product_code):
                self.assertFalse(product.related_items.exists())

        hidden_codes = {
            "SQA-VU Visualization System", "YO Testing Device",
            "B-Sperm Data Management Software",
            "P-Sperm Data Management Software",
            "E-Sperm Data Management Software",
            "T-Sperm Flock Management Software",
        }
        self.assertFalse(
            Product.objects.filter(
                product_code__in=hidden_codes,
                is_catalogue_listing=True,
            ).exists()
        )

    def test_official_mes_nested_item_images_are_imported(self):
        products = Product.objects.filter(
            category__slug="medical-electronic-systems",
            is_active=True,
        )
        expected_image_codes = {
            "0200", "0800", "0900", "A-CA-01057-00",
            "A-CA-01752-00", "A-CA-01082-00", "0700",
            "A-CA-01873-00", "A-CA-00691-00", "A-CA-01188-00",
            "A-CA-02089-00", "4021-0", "VS-CA-01108-00",
            "Bi-Directional LIS/EMR Interface", "SQA-VU Visualization System",
            "Docking Station for SQA-iOw + VU", "Desktop PC + Monitor",
            "SQA Semen Analysis Test Kit", "SQA QC & Cleaning Kit",
            "SQA-Vision", "SQA-iOw",
        }
        self.assertEqual(
            set(products.exclude(image="").values_list("product_code", flat=True)),
            expected_image_codes,
        )
        response = self.client.get(Product.objects.get(
            product_code="MES-QWIKCHECK-TEST-KITS"
        ).get_absolute_url())
        self.assertContains(response, "data-product-related-preview", count=7)
        self.assertContains(response, 'class="product-related-image"', count=7)
        self.assertNotContains(response, "View item")
        self.assertNotContains(response, "Included &amp; Related<span>")
        for item in response.context["nested_items"]:
            with self.subTest(related_item=item.name):
                self.assertContains(
                    response,
                    f'href="{item.child_product.get_absolute_url()}" '
                    f'aria-label="View {item.name}"',
                )

    def test_subcategory_pages_have_scoped_products_and_placeholders(self):
        category = Category.objects.get(slug="medical-electronic-systems")
        expected_products = {
            "automated-semen-analysis-solutions": [
                "SQA-Vision", "SQA-iO | CLIA Waived", "SQA-V Gold",
                "QwikCheck Gold",
            ],
            "maleman-reference-lab-services": 1,
            "consumer-semen-analysis-solutions": ["YO Home Sperm Test Kit"],
            "semen-analysis-validation-kits": [
                "QwikCheck Test Kits", "Advanced Testing Kits",
                "QwikCheck Validation Kits", "QwikCheck & SQA Supplies",
            ],
            "veterinary-semen-analysis-solutions": [
                "SQA-Vb - Bovine Semen Quality Analyzer",
                "SQA-Vp - Porcine Semen Quality Analyzer",
                "SQA-Ve - Equine Semen Quality Analyzer",
                "SQA-Vt - Avian Semen Quality Analyzer",
            ],
        }
        expected_products["maleman-reference-lab-services"] = [
            "MaleMan Reference Lab Services"
        ]
        for slug, expected_names in expected_products.items():
            with self.subTest(subcategory=slug):
                response = self.client.get(reverse(
                    "subcategory_detail",
                    args=[category.slug, slug],
                ))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    [product.name for product in response.context["products"]],
                    expected_names,
                )
                self.assertContains(response, "category-visual-placeholder")

    def test_image_fit_is_scoped_to_the_three_requested_mes_subcategories(self):
        category = Category.objects.get(slug="medical-electronic-systems")
        fitted_slugs = {
            "automated-semen-analysis-solutions",
            "consumer-semen-analysis-solutions",
            "veterinary-semen-analysis-solutions",
        }

        for subcategory in category.subcategories.filter(is_active=True):
            with self.subTest(subcategory=subcategory.slug):
                response = self.client.get(subcategory.get_absolute_url())
                if subcategory.slug in fitted_slugs:
                    self.assertContains(
                        response,
                        "subcategory-hero-image mes-subcategory-image-fit",
                    )
                    expected_ratio_class = (
                        "mes-subcategory-image-3-2"
                        if subcategory.slug == "automated-semen-analysis-solutions"
                        else "mes-subcategory-image-16-9"
                    )
                    self.assertContains(response, expected_ratio_class)
                else:
                    self.assertNotContains(response, "mes-subcategory-image-fit")
                    self.assertNotContains(response, "mes-subcategory-image-3-2")
                    self.assertNotContains(response, "mes-subcategory-image-16-9")

                self.assertContains(response, subcategory.description)
                self.assertNotContains(response, 'class="section category-intro"')
                self.assertNotContains(response, "Open any product below")

    def test_selected_sqa_groups_and_future_products_inherit_scoped_media_fit(self):
        category = Category.objects.get(slug="medical-electronic-systems")
        subcategory = category.subcategories.get(
            slug="automated-semen-analysis-solutions"
        )
        future_product = Product.objects.create(
            category=category,
            subcategory=subcategory,
            name="Future SQA Product",
            slug="future-sqa-product-media-fit",
            product_code="FUTURE-SQA-MEDIA-FIT",
            short_description="Future SQA catalogue product.",
            description="Future SQA catalogue product.",
            image="products/future-sqa-product.webp",
            source_image="products/originals/future-sqa-product.webp",
        )

        listing = self.client.get(subcategory.get_absolute_url())
        detail = self.client.get(future_product.get_absolute_url())
        unrelated = self.client.get(
            Product.objects.create(
                category=Category.objects.get(slug="chemistry"),
                name="Unrelated Media Fit Product",
                slug="unrelated-media-fit-product",
                product_code="UNRELATED-MEDIA-FIT",
                short_description="Unrelated product.",
                description="Unrelated product.",
                image="products/unrelated-media-fit.webp",
            ).get_absolute_url()
        )
        excluded_sqa_product = Product.objects.filter(
            category=category,
            subcategory__slug="semen-analysis-validation-kits",
            image__gt="",
        ).first()
        excluded_sqa_listing = self.client.get(
            excluded_sqa_product.subcategory.get_absolute_url()
        )
        excluded_sqa_detail = self.client.get(
            excluded_sqa_product.get_absolute_url()
        )

        self.assertContains(listing, "sqa-product-image-fit")
        self.assertContains(
            listing,
            'src="/media/products/originals/future-sqa-product.webp"',
        )
        self.assertContains(
            listing,
            'data-image-fallback="/media/products/future-sqa-product.webp"',
        )
        self.assertContains(detail, "sqa-product-gallery-fit", count=1)
        self.assertNotContains(unrelated, "sqa-product-gallery-fit")
        self.assertNotContains(unrelated, "sqa-product-image-fit")
        self.assertNotContains(excluded_sqa_listing, "sqa-product-image-fit")
        self.assertNotContains(excluded_sqa_detail, "sqa-product-gallery-fit")

    def test_every_mes_parent_owns_only_its_official_included_items(self):
        expected = {
            "SQA-iOw": {
                "SQA-iOw Automated Analyzer", "SQA-VU Visualization System",
                "Docking Station for SQA-iOw + VU", "Desktop PC + Monitor",
                "SQA Semen Analysis Test Kit", "SQA QC & Cleaning Kit",
                "QwikCheck Fixed Coverslip Slides",
                "QwikCheck Proficiency & Training Kit",
            },
            "MES-QWIKCHECK-TEST-KITS": {
                "QwikCheck™ Quality Control Beads", "QwikCheck™ Dilution Kit",
                "QwikCheck™ Liquefaction Kit", "QwikCheck™ 1-Step Vitality Stain",
                "QwikCheck™ WBC/pH Test Strips Quality Control",
                "QwikCheck™ Fixed Coverslip Slides",
                "QwikCheck™ WBC/pH Test Reagent Strips",
            },
            "MES-ADVANCED-TESTING-KITS": {"QwikCheck™ DFI Kit DNA Fragmentation"},
            "MES-QWIKCHECK-VALIDATION-KITS": {
                "QwikCheck Beads™ Proficiency and Training Kit",
                "QwikCheck™ Beads Precision and Linearity Kit",
            },
            "MES-QWIKCHECK-SQA-SUPPLIES": {
                "SQA - Low Volume Testing Capillary", "SQA - Testing Capillary",
                "QwikCheck™ Fixed Coverslip Slides",
                "QwikCheck™ WBC/pH Test Reagent Strips",
                "QwikCheck™ 1-Step Morphology Slides",
            },
        }
        expected_child_codes = {
            "MES-QWIKCHECK-TEST-KITS": {
                "0200", "0800", "0900", "A-CA-01057-00",
                "A-CA-01752-00", "A-CA-01082-00", "0700",
            },
            "MES-ADVANCED-TESTING-KITS": {"A-CA-01873-00"},
            "MES-QWIKCHECK-VALIDATION-KITS": {
                "A-CA-00691-00", "A-CA-01188-00",
            },
            "MES-QWIKCHECK-SQA-SUPPLIES": {
                "A-CA-02089-00", "4021-0", "A-CA-01082-00",
                "0700", "VS-CA-01108-00",
            },
        }
        for parent_code, item_names in expected.items():
            with self.subTest(parent=parent_code):
                parent = Product.objects.get(product_code=parent_code)
                self.assertEqual(
                    set(parent.related_items.values_list("name", flat=True)),
                    item_names,
                )
        for parent_code, child_codes in expected_child_codes.items():
            parent = Product.objects.get(product_code=parent_code)
            self.assertEqual(
                set(parent.related_items.values_list(
                    "child_product__product_code", flat=True
                )),
                child_codes,
            )
        mes_products = Product.objects.filter(
            category__slug="medical-electronic-systems",
            is_active=True,
        )
        self.assertEqual(
            set(
                mes_products.filter(related_items__isnull=False)
                .values_list("product_code", flat=True)
                .distinct()
            ),
            set(expected),
        )
        self.assertEqual(
            ProductRelatedItem.objects.filter(parent_product__in=mes_products).count(),
            23,
        )
        self.assertFalse(
            ProductRelatedItem.objects.filter(
                parent_product__in=mes_products,
                name__in={
                    "User guide", "1 year manufacturer warranty",
                    "YO 3 Test Refill Kit", "Archive software",
                },
            ).exists()
        )
        for relationship in ProductRelatedItem.objects.filter(
            parent_product__in=mes_products,
            child_product__image__gt="",
        ).select_related("child_product"):
            with self.subTest(image=relationship.child_product.product_code):
                self.assertTrue(relationship.child_product.image)
                self.assertTrue(
                    relationship.child_product.image.storage.exists(
                        relationship.child_product.image.name
                    )
                )
