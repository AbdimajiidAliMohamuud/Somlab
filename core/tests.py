from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.html import conditional_escape
from catalog.models import Category, Product
from catalog.scope import public_products
from .models import (
    ContactMessage, Customer, CustomerProject, CustomerProjectMedia, Partner,
    Service, Testimonial,
)


class PublicPageTests(TestCase):
    def test_core_pages_render(self):
        for name in ("home", "about", "services", "partners", "customers", "contact"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_shared_header_uses_required_navigation_order_on_public_pages(self):
        page_names = (
            "home",
            "product_list",
            "partners",
            "services",
            "about",
            "contact",
            "product_inquiry",
            "customers",
        )
        markers = (
            ">About Us</a>",
            "Products &amp; Solutions",
            ">Partners</a>",
            ">Customers</a>",
            ">Services</a>",
        )

        for page_name in page_names:
            with self.subTest(page=page_name):
                response = self.client.get(reverse(page_name))
                self.assertEqual(response.status_code, 200)
                content = response.content.decode()
                nav_start = content.index(
                    '<nav class="container main-nav" aria-label="Main navigation">'
                )
                nav_end = content.index("</nav>", nav_start)
                navigation = content[nav_start:nav_end]
                positions = [navigation.index(marker) for marker in markers]
                self.assertEqual(positions, sorted(positions))
                self.assertIn('class="nav-contact" href="/contact/"', content)
                self.assertNotIn('class="cart-link"', content)

    def test_navigation_marks_each_top_level_page_active(self):
        expected = {
            "about": 'href="/about/" class="active" aria-current="page"',
            "product_list": 'class="nav-products active"',
            "partners": 'href="/partners/" class="active" aria-current="page"',
            "customers": 'href="/customers/" class="active" aria-current="page"',
            "services": 'href="/services/" class="active" aria-current="page"',
        }

        for page_name, marker in expected.items():
            with self.subTest(page=page_name):
                response = self.client.get(reverse(page_name))
                self.assertContains(response, marker)

    def test_catalogue_and_partner_filters_share_canonical_category_destinations(self):
        Partner.objects.all().delete()
        partner = Partner.objects.create(
            name="Acme Diagnostics",
            website="https://acme.example.com/",
            display_order=0,
            is_active=True,
        )
        chemistry = Category.objects.get(slug="chemistry")
        Product.objects.create(
            category=chemistry,
            name="Acme Canonical Routing Product",
            slug="acme-canonical-routing-product",
            brand=partner.name,
            product_code="ACME-CANONICAL-1",
            short_description="Product used to test canonical category routing.",
            description="Product used to test canonical category routing.",
        )

        categories = [
            Category.objects.get(slug=slug)
            for slug in (
                "chemistry",
                "immunoassay",
                "hematology",
                "microbiology",
            )
        ]
        home = self.client.get(reverse("home"))
        catalogue = self.client.get(reverse("product_list"))
        partner_catalogue = self.client.get(
            reverse("product_list"),
            {"brand": "acme-diagnostics"},
        )

        self.assertContains(
            home,
            f'href="{reverse("product_list")}">Explore products',
        )
        self.assertContains(
            home,
            'href="/products/?brand=acme-diagnostics"',
            count=2,
        )
        for category in categories:
            with self.subTest(category=category.slug):
                canonical_url = category.get_absolute_url()
                self.assertContains(catalogue, f'href="{canonical_url}"')
                self.assertContains(
                    partner_catalogue,
                    f'href="{canonical_url}"',
                )
                self.assertNotContains(
                    partner_catalogue,
                    f'href="{canonical_url}?brand=acme-diagnostics"',
                )

        self.assertEqual(
            Category.objects.get(slug="microbiology").get_absolute_url(),
            reverse("microbiology_landing"),
        )

    def test_customers_page_and_detail_use_active_database_portfolio(self):
        customer = Customer.objects.create(
            name="Example Hospital",
            slug="example-hospital",
            website="https://example.org/",
            short_description="A hospital supported by Somlab Diagnostics.",
            description="A full organization profile.",
            facebook_url="https://facebook.com/example-hospital",
            display_order=0,
            is_active=True,
        )
        Customer.objects.create(
            name="Hidden Hospital",
            slug="hidden-hospital",
            is_active=False,
        )
        Customer.objects.create(
            name="No Link Hospital",
            slug="no-link-hospital",
            is_active=True,
        )
        product = Product.objects.create(
            category=Category.objects.get(slug="chemistry"),
            name="Customer Chemistry System",
            slug="customer-chemistry-system",
            brand="Example Diagnostics",
            product_code="CUSTOMER-CHEM-1",
            short_description="A supplied chemistry system.",
            description="A supplied chemistry system.",
        )
        customer.products.add(product)
        project = CustomerProject.objects.create(
            customer=customer,
            title="Laboratory installation",
            work_type="installation",
            description="Equipment installation and staff training.",
        )
        project.products.add(product)
        CustomerProjectMedia.objects.create(
            project=project,
            file="customers/projects/example.jpg",
            media_type="image",
            caption="Installed laboratory system",
        )
        CustomerProjectMedia.objects.create(
            project=project,
            file="customers/projects/example.mp4",
            media_type="video",
            display_order=1,
        )
        CustomerProjectMedia.objects.create(
            project=project,
            media_type="video",
            video_url="https://www.youtube.com/watch?v=example123",
            caption="Installation overview",
            display_order=2,
        )

        response = self.client.get(reverse("customers"))

        self.assertNotContains(response, "Customer portfolio")
        self.assertContains(response, "Healthcare organizations we support")
        self.assertContains(response, 'class="customers-marquee-track"')
        self.assertContains(response, 'class="customers-marquee-sequence"', count=2)
        self.assertContains(response, "Example Hospital")
        self.assertNotContains(response, "Hidden Hospital")
        self.assertContains(
            response,
            f'href="{customer.get_absolute_url()}"',
            count=3,
        )
        self.assertNotContains(response, 'href="https://example.org/"')
        self.assertNotContains(response, "A hospital supported by Somlab Diagnostics.")
        self.assertNotContains(response, "View projects")
        self.assertNotContains(response, "View customer portfolio")
        self.assertNotContains(response, "customer organizations")
        self.assertNotContains(response, "customers/projects/example.jpg")

        detail = self.client.get(customer.get_absolute_url())
        self.assertContains(detail, "A hospital supported by Somlab Diagnostics.")
        self.assertContains(detail, "A full organization profile.")
        self.assertContains(detail, "Customer Chemistry System")
        self.assertContains(detail, "Products supplied by Somlab")
        self.assertContains(detail, "Chemistry")
        self.assertContains(detail, "A supplied chemistry system.")
        self.assertContains(detail, product.get_absolute_url())
        self.assertContains(detail, "Laboratory installation")
        self.assertContains(detail, "Equipment installed")
        self.assertContains(detail, "Work delivered")
        self.assertContains(detail, "customers/projects/example.jpg")
        self.assertContains(detail, "data-customer-lightbox")
        self.assertContains(detail, "<video controls", html=False)
        self.assertContains(detail, "playsinline", html=False)
        self.assertContains(detail, 'type="video/mp4"', html=False)
        self.assertContains(detail, "youtube-nocookie.com/embed/example123")
        self.assertNotContains(detail, "Visit customer website")
        self.assertContains(detail, "Learn more about Example Hospital")
        self.assertNotContains(detail, "Visit website")
        self.assertContains(detail, "Our Platform")
        self.assertContains(detail, 'target="_blank" rel="noopener noreferrer"')
        self.assertNotContains(detail, "https://facebook.com/example-hospital")

        hidden_detail = self.client.get(reverse("customer_detail", args=["hidden-hospital"]))
        self.assertEqual(hidden_detail.status_code, 404)

    def test_marwo_portfolio_import_is_scoped_idempotent_and_rendered(self):
        from core.management.commands.import_marwo_portfolio import MEDIA

        local_storages = {
            "default": {
                "BACKEND": "django.core.files.storage.FileSystemStorage",
            },
            "staticfiles": {
                "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
            },
        }
        with TemporaryDirectory() as source_root, TemporaryDirectory() as media_root:
            source_directory = Path(source_root)
            for filename, _caption in MEDIA:
                (source_directory / filename).write_bytes(
                    b"marwo-project-photo-" + filename.encode()
                )

            with override_settings(STORAGES=local_storages, MEDIA_ROOT=media_root):
                call_command("import_marwo_portfolio", source_directory, verbosity=0)
                call_command("import_marwo_portfolio", source_directory, verbosity=0)

                customer = Customer.objects.get(slug="marwo-fertility-center")
                project = customer.projects.get(title="Laboratory equipment delivery")
                self.assertEqual(project.work_type, "supply")
                self.assertIsNone(project.date)
                self.assertEqual(project.media.count(), 11)
                self.assertEqual(customer.projects.count(), 1)
                for item in project.media.all():
                    self.assertTrue(Path(media_root, item.file.name).is_file())

                response = self.client.get(customer.get_absolute_url())
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "customer-record-card--marwo-gallery")
                self.assertContains(response, "customer-record-card--featured-gallery")
                self.assertContains(response, "Delivered systems portfolio")
                self.assertContains(response, "Laboratory equipment delivery")
                self.assertContains(response, "Beckman Coulter DxH 560")
                self.assertNotContains(response, "No portfolio records published yet")

    def test_horyaal_portfolio_import_is_scoped_idempotent_and_rendered(self):
        from core.management.commands.import_horyaal_portfolio import MEDIA

        local_storages = {
            "default": {
                "BACKEND": "django.core.files.storage.FileSystemStorage",
            },
            "staticfiles": {
                "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
            },
        }
        marwo = Customer.objects.get(slug="marwo-fertility-center")
        marwo_project_count = marwo.projects.count()
        with TemporaryDirectory() as source_root, TemporaryDirectory() as media_root:
            source_directory = Path(source_root)
            for filename, _caption in MEDIA:
                (source_directory / filename).write_bytes(
                    b"horyaal-project-photo-" + filename.encode()
                )

            with override_settings(STORAGES=local_storages, MEDIA_ROOT=media_root):
                call_command("import_horyaal_portfolio", source_directory, verbosity=0)
                call_command("import_horyaal_portfolio", source_directory, verbosity=0)

                customer = Customer.objects.get(slug="horyaal-hospital")
                project = customer.projects.get(title="Laboratory equipment delivery")
                self.assertEqual(project.work_type, "supply")
                self.assertIsNone(project.date)
                self.assertEqual(project.media.count(), 28)
                self.assertEqual(customer.projects.count(), 1)
                self.assertEqual(marwo.projects.count(), marwo_project_count)
                for item in project.media.all():
                    self.assertTrue(Path(media_root, item.file.name).is_file())

                response = self.client.get(customer.get_absolute_url())
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "customer-record-card--horyaal-gallery")
                self.assertContains(response, "customer-record-card--featured-gallery")
                self.assertContains(response, "Delivered systems portfolio")
                self.assertContains(response, "Laboratory equipment delivery")
                self.assertContains(response, "Beckman Coulter AU480")
                self.assertContains(response, "Eschweiler combi line")
                self.assertNotContains(response, "No portfolio records published yet")

    def test_mogadishu_portfolio_import_is_scoped_idempotent_and_rendered(self):
        from core.management.commands.import_mogadishu_portfolio import MEDIA

        local_storages = {
            "default": {
                "BACKEND": "django.core.files.storage.FileSystemStorage",
            },
            "staticfiles": {
                "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
            },
        }
        protected_counts = {
            slug: (
                Customer.objects.get(slug=slug).projects.count(),
                CustomerProjectMedia.objects.filter(project__customer__slug=slug).count(),
            )
            for slug in ("horyaal-hospital", "marwo-fertility-center")
        }
        with TemporaryDirectory() as source_root, TemporaryDirectory() as media_root:
            source_directory = Path(source_root)
            for filename, _caption in MEDIA:
                (source_directory / filename).write_bytes(
                    b"mogadishu-project-photo-" + filename.encode()
                )

            with override_settings(STORAGES=local_storages, MEDIA_ROOT=media_root):
                call_command("import_mogadishu_portfolio", source_directory, verbosity=0)
                call_command("import_mogadishu_portfolio", source_directory, verbosity=0)

                customer = Customer.objects.get(slug="mogadishu-specialist-hospital")
                project = customer.projects.get(title="Laboratory equipment delivery")
                self.assertEqual(project.work_type, "supply")
                self.assertIsNone(project.date)
                self.assertEqual(project.media.count(), len(MEDIA))
                self.assertEqual(len(MEDIA), 22)
                self.assertNotIn("DSC09361.JPG", {filename for filename, _ in MEDIA})
                self.assertEqual(customer.projects.count(), 1)
                for slug, counts in protected_counts.items():
                    self.assertEqual(Customer.objects.get(slug=slug).projects.count(), counts[0])
                    self.assertEqual(
                        CustomerProjectMedia.objects.filter(
                            project__customer__slug=slug
                        ).count(),
                        counts[1],
                    )
                for item in project.media.all():
                    self.assertTrue(Path(media_root, item.file.name).is_file())

                response = self.client.get(customer.get_absolute_url())
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "customer-record-card--mogadishu-gallery")
                self.assertContains(response, "customer-record-card--featured-gallery")
                self.assertContains(response, "Delivered systems portfolio")
                self.assertContains(response, "Laboratory equipment delivery")
                self.assertContains(response, "Beckman Coulter DxC 500i")
                self.assertContains(response, "Beckman Coulter MicroScan autoSCAN-4")
            self.assertNotContains(response, "No portfolio records published yet")

    def test_shaafi_portfolio_import_is_scoped_idempotent_and_rendered(self):
        from core.management.commands import import_shaafi_portfolio

        shaafi = Customer.objects.get(slug="shaafi-hospital")
        protected_customers = {
            slug: (
                CustomerProject.objects.filter(customer__slug=slug).count(),
                CustomerProjectMedia.objects.filter(project__customer__slug=slug).count(),
            )
            for slug in (
                "horyaal-hospital",
                "marwo-fertility-center",
                "mogadishu-specialist-hospital",
            )
        }

        local_storages = {
            "default": {
                "BACKEND": "django.core.files.storage.FileSystemStorage",
            },
            "staticfiles": {
                "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
            },
        }
        with TemporaryDirectory() as source_dir, TemporaryDirectory() as media_dir:
            source_path = Path(source_dir)
            for filename, _caption in import_shaafi_portfolio.MEDIA:
                (source_path / filename).write_bytes(filename.encode("utf-8"))

            with override_settings(STORAGES=local_storages, MEDIA_ROOT=media_dir):
                call_command("import_shaafi_portfolio", source_path, verbosity=0)
                call_command("import_shaafi_portfolio", source_path, verbosity=0)

                project = CustomerProject.objects.get(
                    customer=shaafi,
                    title=import_shaafi_portfolio.PROJECT_TITLE,
                )
                media = list(project.media.order_by("display_order"))
                self.assertEqual(len(media), len(import_shaafi_portfolio.MEDIA))
                self.assertEqual(
                    [item.display_order for item in media],
                    list(range(len(import_shaafi_portfolio.MEDIA))),
                )
                self.assertTrue(all(item.file.storage.exists(item.file.name) for item in media))

            for slug, counts in protected_customers.items():
                self.assertEqual(
                    (
                        CustomerProject.objects.filter(customer__slug=slug).count(),
                        CustomerProjectMedia.objects.filter(project__customer__slug=slug).count(),
                    ),
                    counts,
                )

            response = self.client.get(shaafi.get_absolute_url())
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "customer-record-card--shaafi-gallery")
            self.assertContains(response, "customer-record-card--featured-gallery")
            self.assertContains(response, "Delivered systems portfolio")
            self.assertContains(response, "BIOBASE -40°C freezer")
            self.assertNotContains(response, "No portfolio records published yet")

    def test_initial_customer_portfolio_contains_requested_organizations(self):
        self.assertEqual(Customer.objects.filter(is_active=True).count(), 15)
        self.assertTrue(Customer.objects.filter(name="Horyaal Hospital").exists())
        self.assertTrue(Customer.objects.filter(name="SOS Children’s Village").exists())
        self.assertTrue(Customer.objects.filter(name="Dalmar Hospital").exists())

        expected_links = {
            "horyaal-hospital": ("https://www.horyaalhospital.so/", ""),
            "shaafi-hospital": ("https://shaafihospital.so/", ""),
            "mogadishu-specialist-hospital": ("", "https://www.facebook.com/mshospital.so/"),
            "kalkaal-hospital": ("https://kalkaalhospital.so/en", ""),
            "hodan-hospital": ("https://hodanhospital.com/", ""),
            "sos-childrens-village": ("https://www.sos-somalia.org/", ""),
            "marwo-fertility-center": ("https://marwafertility.com/", ""),
            "wadajir-hospital": ("https://wadajirhospital.com/", ""),
            "baraka-hospital": ("", "https://www.facebook.com/albarakathospital/"),
            "jazeera-hospital": ("https://jazeerahospital.so/", ""),
            "nova-diagnostic-center": ("https://nova.com.so/", ""),
            "sahan-diagnostic-center": ("https://sahandiagnostic.com/", ""),
            "dhiblawe-liver-and-digestive-center": ("", "https://www.facebook.com/dhiblaaweclinic/"),
            "ladnan-hospital": ("https://www.ladnan-hospital.com/", ""),
            "dalmar-hospital": ("https://dalmarhospital.so/", ""),
        }
        self.assertEqual(
            {
                customer.slug: (customer.website, customer.facebook_url)
                for customer in Customer.objects.filter(slug__in=expected_links)
            },
            expected_links,
        )

        customer = Customer.objects.get(name="Horyaal Hospital")
        response = self.client.get(customer.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Horyaal Hospital")
        self.assertNotContains(response, "Visit customer website")
        self.assertNotContains(response, "No portfolio records published yet")
        self.assertNotContains(response, "Customer success")
        self.assertNotContains(response, "Work delivered")
        self.assertContains(response, "Learn more about Horyaal Hospital")
        self.assertContains(response, "Our Platform")
        self.assertNotContains(response, "Visit website")

        facebook_customer = Customer.objects.get(slug="baraka-hospital")
        facebook_response = self.client.get(facebook_customer.get_absolute_url())
        self.assertContains(facebook_response, "Our Platform")
        self.assertContains(
            facebook_response,
            "https://www.facebook.com/albarakathospital/",
        )

    def test_featured_gallery_treatment_is_limited_to_four_customers(self):
        featured_slugs = (
            "horyaal-hospital",
            "shaafi-hospital",
            "mogadishu-specialist-hospital",
            "marwo-fertility-center",
        )
        for slug in featured_slugs:
            with self.subTest(slug=slug):
                CustomerProject.objects.create(
                    customer=Customer.objects.get(slug=slug), title="Published work",
                )
                response = self.client.get(reverse("customer_detail", args=[slug]))
                self.assertTrue(response.context["is_featured_gallery"])
                self.assertContains(response, "Delivered systems portfolio")
                self.assertNotContains(response, "customer-gallery-count")
                self.assertNotContains(response, "portfolio image")

        CustomerProject.objects.create(
            customer=Customer.objects.get(slug="kalkaal-hospital"), title="Published work",
        )
        regular = self.client.get(
            reverse("customer_detail", args=["kalkaal-hospital"])
        )
        self.assertFalse(regular.context["is_featured_gallery"])
        self.assertContains(regular, "Work delivered")
        self.assertNotContains(regular, "customer-record-card--featured-gallery")

    def test_services_page_uses_premium_lifecycle_composition(self):
        Service.objects.all().delete()
        service_names = (
            "Equipment Installation",
            "Training & Application Support",
            "Maintenance & Technical Support",
            "Laboratory Project Development",
            "Laboratory Management Systems",
            "Turnkey Laboratory Projects",
        )
        for display_order, name in enumerate(service_names):
            Service.objects.create(
                name=name,
                slug=name.lower().replace(" & ", "-").replace(" ", "-"),
                short_description=f"Professional {name.lower()} support.",
                description=f"Somlab {name.lower()} service.",
                display_order=display_order,
                is_active=True,
            )

        response = self.client.get(reverse("services"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Technical support built around laboratory performance.",
        )
        self.assertContains(response, 'id="services-overview"')
        self.assertContains(response, 'class="services-premium-card"', count=6)
        self.assertContains(response, "Why Somlab")
        self.assertContains(response, "A clear path from requirement to operation")
        self.assertContains(response, "Need technical support or planning a laboratory project?")
        self.assertContains(response, "Request support")
        self.assertContains(response, "Discuss a project")

        for service in Service.objects.filter(is_active=True):
            with self.subTest(service=service.name):
                self.assertContains(response, conditional_escape(service.name))
                self.assertContains(response, service.get_absolute_url())

        self.assertNotContains(response, 'class="service-list-item"')

    def test_public_navigation_hides_dashboard_and_uses_transparent_footer_logo(self):
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, 'href="/dashboard/"')
        self.assertNotContains(response, 'href="/admin"')
        self.assertNotContains(response, "Sign in")
        self.assertContains(response, "SLD_Logo_-02")

    def test_home_quality_standard_uses_linked_partner_logos(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Somlab Quality Standard")
        self.assertNotContains(response, "Ready")
        self.assertContains(response, 'data-quality-logo-carousel')
        self.assertContains(response, 'class="hero-partner-logo"', count=4)
        self.assertContains(response, 'class="hero-partner-logo is-active"', count=1)
        self.assertContains(response, 'aria-hidden="true" tabindex="-1"', count=4)
        self.assertNotContains(response, '--logo-index:')
        self.assertEqual(
            [partner.name for partner in response.context["quality_partners"]],
            [
                "Beckman Coulter",
                "ZEISS",
                "SD Biosensor",
                "Vatech Dental",
                "Molbio Diagnostics",
            ],
        )
        for partner in response.context["quality_partners"]:
            self.assertContains(response, partner.product_url)
            self.assertContains(response, partner.name)
        self.assertContains(response, 'placeholder="Search by our product"')
        self.assertContains(response, "Verified quality")
        self.assertContains(response, "Technical support")

    def test_home_does_not_render_catalogue_showcase_sections(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Selected for you")
        self.assertNotContains(response, "Featured products")
        self.assertNotContains(response, "Browse catalogue")
        self.assertNotContains(response, "Our catalogue")
        self.assertNotContains(response, "Solutions for every laboratory")
        self.assertNotContains(response, 'data-product-showcase')
        self.assertNotContains(response, "showcase-category-links")
        self.assertNotContains(response, "showcase-product-card")
        self.assertContains(response, "A partner in laboratory performance.")

    def test_home_statistics_use_current_backend_values(self):
        Partner.objects.create(name="Active Brand", is_active=True)
        Partner.objects.create(name="Inactive Brand", is_active=False)
        Service.objects.create(
            name="Active Service",
            slug="active-service-test",
            short_description="Technical support.",
            description="Technical support.",
            is_active=True,
        )
        Service.objects.create(
            name="Inactive Service",
            slug="inactive-service-test",
            short_description="Not public.",
            description="Not public.",
            is_active=False,
        )

        response = self.client.get(reverse("home"))
        statistics = {
            item["label"]: item["value"]
            for item in response.context["home_statistics"]
        }

        self.assertEqual(statistics["Laboratory Products"], public_products().count())
        self.assertEqual(
            statistics["International Brands"],
            Partner.objects.filter(is_active=True).count(),
        )
        self.assertEqual(
            statistics["Technical Services"],
            Service.objects.filter(is_active=True).count(),
        )
        self.assertEqual(statistics["Regional Support"], "East Africa")
        self.assertContains(response, 'data-counter')

    def test_home_manufacturer_logo_links_to_filtered_catalogue(self):
        Partner.objects.all().delete()
        partner = Partner.objects.create(
            name="Visible Logo Diagnostics",
            website="https://logos.example.com/",
            logo="partners/visible-logo.svg",
            display_order=0,
            is_active=True,
        )

        response = self.client.get(reverse("home"))

        self.assertContains(response, "partners/visible-logo.svg")
        self.assertContains(response, 'data-manufacturer-logo')
        self.assertContains(
            response,
            'href="/products/?brand=visible-logo-diagnostics"',
            count=2,
        )
        self.assertContains(
            response,
            'aria-label="View Visible Logo Diagnostics products"',
        )
        self.assertNotContains(
            response,
            'href="https://logos.example.com/"',
        )
        self.assertContains(response, 'alt="Visible Logo Diagnostics logo"')
        self.assertContains(response, 'class="manufacturer-logo-visual"')

    def test_zeiss_partner_card_omits_catalogue_links(self):
        zeiss = Partner.objects.get(name="ZEISS")
        self.assertTrue(zeiss.is_active)
        home = self.client.get(reverse("home"))
        self.assertContains(home, 'href="/products/?brand=zeiss"', count=3)
        self.assertContains(
            home,
            'aria-label="View ZEISS products"',
        )

        partners = self.client.get(reverse("partners"))
        self.assertContains(partners, 'id="partner-zeiss"')
        self.assertNotContains(partners, ">ZEISS Microscopy</a>")
        self.assertNotContains(partners, ">ZEISS Light Microscopes</a>")
        filtered = self.client.get(reverse("product_list"), {"brand": "zeiss"})
        self.assertEqual(filtered.status_code, 200)
        self.assertTrue(filtered.context["products"])
        self.assertTrue(all(
            product.brand.casefold() == "zeiss"
            for product in filtered.context["products"]
        ))

    def test_home_uses_every_original_partner_logo_and_dynamic_card_link(self):
        Partner.objects.all().delete()
        partner_names = (
            "Beckman Coulter",
            "DIAGNOSTICS i.n.c.",
            "Medical Electronic Systems",
            "SD Biosensor",
            "Bioer Technology",
            "Molbio Diagnostics",
            "Biosan",
            "Polycheck",
            "Turklab",
            "GeneProof",
        )
        for display_order, name in enumerate(partner_names):
            Partner.objects.create(
                name=name,
                website=f"https://partner-{display_order}.example.com/",
                logo=f"partners/{display_order}.png",
                display_order=display_order,
                is_active=True,
            )

        response = self.client.get(reverse("home"))
        content = response.content.decode()
        marquee_start = content.index('<div class="partners-marquee"')
        marquee_end = content.index("</section>", marquee_start)
        marquee = content[marquee_start:marquee_end]

        self.assertContains(response, 'class="partners-marquee-track"')
        self.assertContains(response, 'class="partners-marquee-sequence"', count=2)
        for partner in response.context["partners"]:
            with self.subTest(partner=partner.name):
                self.assertEqual(
                    marquee.count(f'href="/products/?brand={partner.product_brand_slug}"'),
                    2,
                )
                self.assertNotIn(f'href="{partner.website}"', marquee)
                self.assertEqual(
                    marquee.count(f'partners/{partner.display_order}.png'),
                    2,
                )
                self.assertEqual(
                    marquee.count(f'alt="{partner.name} logo"'),
                    1,
                )
        self.assertNotContains(response, "static/img/partners/")

    def test_home_and_partners_page_share_all_active_partners_in_order(self):
        Partner.objects.all().delete()
        expected_names = ("First Brand", "Second Brand", "Third Brand")
        for display_order, name in enumerate(expected_names):
            Partner.objects.create(
                name=name,
                display_order=display_order,
                is_active=True,
            )
        Partner.objects.create(
            name="Hidden Brand",
            display_order=99,
            is_active=False,
        )

        home_response = self.client.get(reverse("home"))
        partners_response = self.client.get(reverse("partners"))
        home_names = [partner.name for partner in home_response.context["partners"]]
        page_names = [partner.name for partner in partners_response.context["partners"]]

        self.assertEqual(home_names, list(expected_names))
        self.assertEqual(home_names, page_names)

    def test_trusted_network_is_immediately_after_homepage_search(self):
        response = self.client.get(reverse("home"))
        content = response.content.decode()

        search_position = content.index('<section class="search-band">')
        trusted_position = content.index("Working with leading manufacturers")
        customers_position = content.index(
            "Trusted by leading healthcare organizations"
        )
        statistics_position = content.index('<section class="home-stats"')

        self.assertLess(search_position, trusted_position)
        self.assertLess(trusted_position, customers_position)
        self.assertLess(customers_position, statistics_position)
        self.assertNotIn("Solutions for every laboratory", content)

    def test_home_reuses_active_customer_marquee_and_internal_links(self):
        customer = Customer.objects.create(
            name="Homepage Customer",
            slug="homepage-customer",
            logo="customers/logos/homepage-customer.svg",
            display_order=0,
            is_active=True,
        )
        Customer.objects.create(
            name="Hidden Homepage Customer",
            slug="hidden-homepage-customer",
            is_active=False,
        )

        home_response = self.client.get(reverse("home"))
        customers_response = self.client.get(reverse("customers"))

        self.assertContains(
            home_response,
            "Trusted by leading healthcare organizations",
        )
        self.assertContains(home_response, "Trusted network")
        self.assertNotContains(home_response, "Customer network")
        self.assertContains(
            home_response,
            "Access to specialised laboratory products",
        )
        self.assertNotContains(
            home_response,
            "Hospitals, clinics and diagnostic teams rely on Somlab",
        )
        self.assertContains(
            home_response,
            'class="section home-customers-section"',
        )
        self.assertContains(home_response, 'class="customers-marquee-track"')
        self.assertContains(
            home_response,
            f'href="{customer.get_absolute_url()}"',
            count=2,
        )
        self.assertContains(
            customers_response,
            f'href="{customer.get_absolute_url()}"',
            count=3,
        )
        self.assertContains(
            home_response,
            "customers/logos/homepage-customer.svg",
            count=2,
        )
        self.assertNotContains(home_response, "Hidden Homepage Customer")
        self.assertEqual(
            {item.pk for item in home_response.context["customers"]},
            {item.pk for item in customers_response.context["customers"]},
        )

    def test_customers_page_rotates_first_customer_without_duplicates(self):
        first_page = self.client.get(reverse("customers"))
        next_page = self.client.get(reverse("customers"))
        first_ids = [item.pk for item in first_page.context["customers"]]
        next_ids = [item.pk for item in next_page.context["customers"]]
        self.assertGreater(len(first_ids), 1)
        self.assertNotEqual(first_ids[0], next_ids[0])
        self.assertEqual(set(first_ids), set(next_ids))
        self.assertEqual(len(first_ids), len(set(first_ids)))
        self.assertEqual(len(next_ids), len(set(next_ids)))

    def test_home_omits_customer_experience_but_preserves_customers_page(self):
        testimonial = Testimonial.objects.create(
            customer_name="Future Customer",
            organization="Future Organization",
            review="This testimonial remains available for future customer content.",
            rating=5,
            display_order=0,
            is_active=True,
        )

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Customer experience")
        self.assertNotContains(response, "Trusted by laboratory teams")
        self.assertNotContains(response, 'data-testimonial-slider')
        self.assertNotContains(response, 'data-testimonial-slide')
        self.assertNotContains(response, testimonial.review)
        self.assertContains(response, 'href="/customers/"')
        self.assertContains(response, "From delivery to dependable operation")
        self.assertContains(response, "Need help choosing the right product?")
        self.assertTrue(Testimonial.objects.filter(pk=testimonial.pk).exists())

        customers_response = self.client.get(reverse("customers"))
        self.assertEqual(customers_response.status_code, 200)
        self.assertContains(
            customers_response,
            "Healthcare organizations we support",
        )

    def test_partner_website_links_marquee_and_full_profile_card(self):
        Partner.objects.create(
            name="Example Diagnostics",
            country="Kenya",
            website="https://example.com/",
            is_active=True,
        )
        response = self.client.get(reverse("partners"))
        self.assertContains(
            response,
            'aria-label="Visit Example Diagnostics official website"',
            count=2,
        )
        self.assertEqual(response.content.count(b'https://example.com/'), 3)
        self.assertContains(response, 'class="partner-card-link"')
        self.assertContains(
            response,
            'href="https://example.com/" target="_blank" rel="noopener noreferrer"',
            count=3,
        )
        self.assertNotContains(response, "Visit website")

    def test_partners_page_has_premium_intro_and_accessible_logo_marquee(self):
        Partner.objects.create(
            name="Marquee Diagnostics",
            country="Germany",
            website="https://marquee.example.com/",
            logo="partners/marquee.svg",
            description="International diagnostic manufacturer.",
            is_active=True,
        )

        response = self.client.get(reverse("partners"))

        self.assertContains(response, "Our Global Partners")
        self.assertContains(response, 'class="partners-marquee-track"')
        self.assertEqual(response.content.count(b"partners/marquee.svg"), 3)
        self.assertContains(response, 'aria-hidden="true"')
        self.assertContains(response, "Marquee Diagnostics")
        self.assertContains(response, "International diagnostic manufacturer.")

    def test_contact_submission_is_saved(self):
        response = self.client.post(reverse("contact"), {
            "full_name": "Amina Ali",
            "company_name": "City Lab",
            "email": "amina@example.com",
            "phone": "+252 61 1234567",
            "subject": "Chemistry analyser",
            "message": "Please share availability.",
        })
        self.assertRedirects(response, reverse("contact"))
        self.assertEqual(ContactMessage.objects.count(), 1)

    def test_customer_has_no_order_history_or_dashboard_navigation(self):
        customer = User.objects.create_user("customer", password="test-pass-123")
        self.client.force_login(customer)
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "My orders")
        self.assertNotContains(response, "Order history")
        self.assertNotContains(response, 'href="/dashboard/"')
        self.assertEqual(self.client.get("/my-orders/").status_code, 404)

    def test_dashboard_navigation_is_hidden_from_staff_on_public_website(self):
        staff = User.objects.create_user(
            "admin", password="test-pass-123", is_staff=True
        )
        self.client.force_login(staff)
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, 'href="/dashboard/"')
        self.assertNotContains(response, 'href="/admin"')
