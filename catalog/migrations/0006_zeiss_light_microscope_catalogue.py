from django.db import migrations, models
import django.db.models.deletion


SUBCATEGORIES = (
    ("Widefield Microscopes", "widefield-microscopes", "Widefield systems for research, routine work, inspection and education."),
    ("Stereo and Zoom Microscopes", "stereo-and-zoom-microscopes", "Three-dimensional observation with large object fields and extended working distances."),
    ("Digital Microscopes", "digital-microscopes", "Integrated systems for digital inspection, documentation and analysis."),
    ("Super-Resolution Microscopes", "super-resolution-microscopes", "Structured-illumination systems for resolving biological structures beyond conventional light microscopy."),
    ("Light Sheet Microscopes", "light-sheet-microscopes", "Fast, gentle volumetric fluorescence imaging for living and cleared specimens."),
    ("Confocal Laser Scanning Microscopes", "confocal-laser-scanning-microscopes", "Spectral confocal imaging, optical sectioning and surface topography."),
)


# Names, positioning statements and verified headline capabilities were checked
# against the official ZEISS Light Microscopes catalogue and its six category
# pages in August 2026. Images intentionally remain empty for Somlab uploads.
PRODUCTS = (
    # Widefield microscopes
    ("widefield-microscopes", "ZEISS Axio Observer for Life Science Research", "zeiss-axio-observer-life-science", "ZEISS-LM-WF-001", "An open and flexible inverted microscope platform with AI-assisted experiment startup.", "Format: Inverted widefield microscope\nApplication: Advanced life science research\nWorkflow: AI-assisted experiment startup"),
    ("widefield-microscopes", "ZEISS Axio Observer for Materials", "zeiss-axio-observer-materials", "ZEISS-LM-WF-002", "An inverted microscope system for metallography and materials research.", "Format: Inverted widefield microscope\nApplication: Metallography and materials research"),
    ("widefield-microscopes", "ZEISS Axioscope for Biology", "zeiss-axioscope-biology", "ZEISS-LM-WF-003", "A smart upright microscope for biomedical routine work and research.", "Format: Upright widefield microscope\nApplication: Biomedical routine and research\nSupported family: Axioscope 5 and Axioscope 7"),
    ("widefield-microscopes", "ZEISS Axioscope for Materials", "zeiss-axioscope-materials", "ZEISS-LM-WF-004", "An upright microscope for research and routine work in the materials laboratory.", "Format: Upright widefield microscope\nApplication: Materials research and routine inspection"),
    ("widefield-microscopes", "ZEISS Axiolab 5 for Biology", "zeiss-axiolab-5-biology", "ZEISS-LM-WF-005", "A smart routine microscope designed for straightforward digital documentation.", "Format: Upright widefield microscope\nApplication: Biology routine and documentation\nModel: Axiolab 5"),
    ("widefield-microscopes", "ZEISS Axiolab 5 for Materials", "zeiss-axiolab-5-materials", "ZEISS-LM-WF-006", "A routine materialography microscope with smart documentation workflows.", "Format: Upright widefield microscope\nApplication: Routine materialography\nModel: Axiolab 5"),
    ("widefield-microscopes", "ZEISS Axio Imager 2 for Life Science Research", "zeiss-axio-imager-2-life-science", "ZEISS-LM-WF-007", "An upright research microscope platform for advanced life science imaging.", "Format: Upright widefield microscope\nApplication: Advanced life science research\nModel: Axio Imager 2"),
    ("widefield-microscopes", "ZEISS Axio Imager 2 for Materials Research", "zeiss-axio-imager-2-materials", "ZEISS-LM-WF-008", "An open microscope system for automated materials analysis.", "Format: Upright widefield microscope\nApplication: Automated materials analysis\nModel: Axio Imager 2"),
    ("widefield-microscopes", "ZEISS Axio Imager 2 Pol", "zeiss-axio-imager-2-pol", "ZEISS-LM-WF-009", "A polarized-light microscope for demanding research tasks.", "Format: Upright polarized-light microscope\nApplication: Polarization research\nModel: Axio Imager 2 Pol"),
    ("widefield-microscopes", "ZEISS Axio Imager Vario for Materials", "zeiss-axio-imager-vario-materials", "ZEISS-LM-WF-010", "An upright research microscope designed for large materials samples.", "Format: Upright widefield microscope\nApplication: Large materials samples\nModel: Axio Imager Vario"),
    ("widefield-microscopes", "ZEISS Primostar 3", "zeiss-primostar-3", "ZEISS-LM-WF-011", "A microscope for digital teaching and routine laboratory work.", "Format: Upright widefield microscope\nApplication: Education and routine laboratory work\nModel: Primostar 3"),
    ("widefield-microscopes", "ZEISS Primostar 3 iLED", "zeiss-primostar-3-iled", "ZEISS-LM-WF-012", "An iLED microscope configuration for visualizing tuberculosis samples.", "Format: Upright fluorescence microscope\nApplication: Tuberculosis visualization\nModel: Primostar 3 iLED"),
    ("widefield-microscopes", "ZEISS Primovert", "zeiss-primovert", "ZEISS-LM-WF-013", "An inverted microscope for quickly assessing living cells.", "Format: Inverted widefield microscope\nApplication: Living-cell observation\nModel family: Primovert"),
    ("widefield-microscopes", "ZEISS Primovert digital", "zeiss-primovert-digital", "ZEISS-LM-WF-014", "An inverted digital microscope for efficient observation and documentation of living cells.", "Format: Inverted digital widefield microscope\nApplication: Living-cell observation and documentation\nModel: Primovert digital"),
    ("widefield-microscopes", "ZEISS Axiovert 7 for Biology", "zeiss-axiovert-7-biology", "ZEISS-LM-WF-015", "An inverted microscope for automated life-science workflows.", "Format: Inverted widefield microscope\nApplication: Automated life-science workflows\nModel: Axiovert 7"),
    ("widefield-microscopes", "ZEISS Axiovert 5 for Biology", "zeiss-axiovert-5-biology", "ZEISS-LM-WF-016", "A smart inverted microscope for cell culture and research.", "Format: Inverted widefield microscope\nApplication: Cell culture and research\nModel: Axiovert 5"),
    ("widefield-microscopes", "ZEISS Axiovert 5 digital", "zeiss-axiovert-5-digital", "ZEISS-LM-WF-017", "An all-in-one inverted cell-imaging system.", "Format: Inverted digital widefield microscope\nApplication: Cell imaging\nModel: Axiovert 5 digital"),
    ("widefield-microscopes", "ZEISS Axio Examiner", "zeiss-axio-examiner", "ZEISS-LM-WF-018", "A fixed-stage research microscope for patch-clamp experiments.", "Format: Fixed-stage upright microscope\nApplication: Patch-clamp research\nModel: Axio Examiner"),
    # Stereo and zoom microscopes
    ("stereo-and-zoom-microscopes", "ZEISS Axio Zoom.V16 for Biology", "zeiss-axio-zoom-v16-biology", "ZEISS-LM-SZ-001", "A fluorescence zoom microscope for high-resolution imaging across large fields.", "Type: Zoom microscope\nApplication: Biology and fluorescence imaging\nModel: Axio Zoom.V16"),
    ("stereo-and-zoom-microscopes", "ZEISS Axio Zoom.V16 for Materials", "zeiss-axio-zoom-v16-materials", "ZEISS-LM-SZ-002", "A high-resolution zoom microscope for large materials fields.", "Type: Zoom microscope\nApplication: Materials inspection\nModel: Axio Zoom.V16"),
    ("stereo-and-zoom-microscopes", "ZEISS SteREO Discovery.V8", "stereo-discovery-v8", "ZEISS-DISCOVERY-V8", "A modular stereo microscope delivering crisp 3D images throughout an 8:1 manual zoom range.", "Type: Stereo microscope\nZoom range: 8:1 manual zoom\nFocus and stages: Manual or motorized options\nModel: SteREO Discovery.V8"),
    ("stereo-and-zoom-microscopes", "ZEISS SteREO Discovery.V12", "stereo-discovery-v12", "ZEISS-DISCOVERY-V12", "A modular stereo microscope with reproducible imaging across a motorized 12:1 zoom range.", "Type: Stereo microscope\nZoom range: 12:1 motorized zoom\nControl: SYCOP touch panel\nModel: SteREO Discovery.V12"),
    ("stereo-and-zoom-microscopes", "ZEISS SteREO Discovery.V20", "stereo-discovery-v20", "ZEISS-DISCOVERY-V20", "A high-performance modular stereo microscope with a motorized 20:1 zoom range.", "Type: Stereo microscope\nZoom range: 20:1 motorized zoom\nMaximum total magnification: Up to 345x\nMaximum resolution: Up to 1000 LP/mm\nModel: SteREO Discovery.V20"),
    ("stereo-and-zoom-microscopes", "ZEISS Stemi 355", "stemi-355", "ZEISS-STEMI-355", "A compact stereo microscope for education, laboratory work and industrial inspection.", "Type: Stereo microscope\nImaging: High-contrast three-dimensional observation\nIllumination: Integrated LED options\nConfigurations: Education, Labs and Industry\nModel: Stemi 355"),
    ("stereo-and-zoom-microscopes", "ZEISS Stemi 508", "zeiss-stemi-508", "ZEISS-LM-SZ-007", "A Greenough stereo microscope with an 8:1 zoom for routine observation and documentation.", "Type: Greenough stereo microscope\nZoom range: 8:1\nModel: Stemi 508"),
    # Digital microscopes
    ("digital-microscopes", "ZEISS Smartzoom 100", "zeiss-smartzoom-100", "ZEISS-LM-DM-001", "A compact all-in-one digital microscope for efficient optical inspection.", "Type: Digital microscope\nApplication: Optical inspection\nConfiguration: All-in-one system\nModel: Smartzoom 100"),
    ("digital-microscopes", "ZEISS Smartzoom 5", "zeiss-smartzoom-5", "ZEISS-LM-DM-002", "An automated digital microscope for routine inspection and failure analysis.", "Type: Automated digital microscope\nApplication: Routine inspection and failure analysis\nImaging: 2D, 3D and extended depth-of-field workflows\nModel: Smartzoom 5"),
    # Super-resolution microscopes
    ("super-resolution-microscopes", "ZEISS Lattice SIM 3", "zeiss-lattice-sim-3", "ZEISS-LM-SR-001", "A fast optical-sectioning system for developing organisms and tissue microstructures.", "Technology: SIM Apotome and Lattice SIM\nLateral resolution with SIM²: Down to 140 nm\nApplication: Organisms, organoids and tissue sections\nModel: Lattice SIM 3"),
    ("super-resolution-microscopes", "ZEISS Lattice SIM 5", "zeiss-lattice-sim-5", "ZEISS-LM-SR-002", "A live-imaging system providing uniform super-resolution in all spatial dimensions.", "Technology: Structured illumination microscopy\nApplication: High-speed live-cell imaging\nModel: Lattice SIM 5"),
    ("super-resolution-microscopes", "ZEISS Elyra 7 with Lattice SIM", "zeiss-elyra-7-lattice-sim", "ZEISS-LM-SR-003", "A live-imaging system for super-resolution down to molecular detail.", "Technology: Lattice structured illumination microscopy\nApplication: Molecular-detail live imaging\nModel: Elyra 7 with Lattice SIM"),
    # Light sheet microscopes
    ("light-sheet-microscopes", "ZEISS Lattice Lightsheet 7", "zeiss-lattice-lightsheet-7", "ZEISS-LM-LS-001", "An automated system for long-term volumetric imaging of living cells at subcellular resolution.", "Technology: Lattice light sheet fluorescence microscopy\nApplication: Long-term live-cell volumetric imaging\nSample carriers: Standard microscopy sample carriers\nModel: Lattice Lightsheet 7"),
    ("light-sheet-microscopes", "ZEISS Lightsheet 7", "zeiss-lightsheet-7", "ZEISS-LM-LS-002", "A light-sheet multiview system for living and optically cleared specimens.", "Technology: Light sheet fluorescence microscopy\nSpecimen size: Up to 2 cm\nRefractive-index range: 1.33 to 1.58\nImaging: Living and cleared specimens\nModel: Lightsheet 7"),
    # Confocal laser scanning microscopes
    ("confocal-laser-scanning-microscopes", "ZEISS LSM 910", "zeiss-lsm-910", "ZEISS-LM-CF-001", "A compact confocal microscope for innovative imaging and smart analysis.", "Type: Confocal laser scanning microscope\nApplication: Life-science imaging and smart analysis\nModel: LSM 910"),
    ("confocal-laser-scanning-microscopes", "ZEISS LSM 990", "zeiss-lsm-990", "ZEISS-LM-CF-002", "A top-class confocal platform for multimodal imaging.", "Type: Confocal laser scanning microscope\nApplication: Advanced multimodal imaging\nModel: LSM 990"),
    ("confocal-laser-scanning-microscopes", "ZEISS LSM 910 for Materials", "zeiss-lsm-910-materials", "ZEISS-LM-CF-003", "A versatile confocal microscope for advanced materials imaging and surface topography.", "Type: Confocal laser scanning microscope\nApplication: Materials imaging and surface topography\nModel: LSM 910 for Materials"),
)


def seed_zeiss_light_microscopes(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Product = apps.get_model("catalog", "Product")
    ProductSubcategory = apps.get_model("catalog", "ProductSubcategory")

    category, _ = Category.objects.update_or_create(
        slug="light-microscopes",
        defaults={
            "name": "ZEISS Light Microscopes",
            "description": (
                "ZEISS light microscopy systems for scientific research, "
                "routine laboratories, education and industrial inspection."
            ),
            "icon": "microscope",
            "display_order": 6,
            "is_active": True,
        },
    )
    subcategories = {}
    for display_order, (name, slug, description) in enumerate(SUBCATEGORIES):
        subcategory, _ = ProductSubcategory.objects.update_or_create(
            category=category,
            slug=slug,
            defaults={
                "name": name,
                "description": description,
                "display_order": display_order,
                "is_active": True,
            },
        )
        subcategories[slug] = subcategory

    for subcategory_slug, name, slug, code, short_description, specifications in PRODUCTS:
        product = Product.objects.filter(product_code=code).first()
        if product is None:
            product = Product.objects.filter(slug=slug).first()
        if product is None:
            product = Product(product_code=code, slug=slug)
        product.category = category
        product.subcategory = subcategories[subcategory_slug]
        product.name = name
        product.slug = slug
        product.brand = "ZEISS"
        product.product_code = code
        product.short_description = short_description
        product.description = (
            f"{short_description} This product is part of the official ZEISS "
            f"{subcategories[subcategory_slug].name} portfolio. Contact Somlab "
            "Diagnostics for configuration and application guidance."
        )
        product.specifications = specifications
        product.price = None
        product.availability = "on_request"
        product.is_featured = False
        product.is_active = True
        product.save()


class Migration(migrations.Migration):

    dependencies = [("catalog", "0005_microbiology_products_and_on_request")]

    operations = [
        migrations.CreateModel(
            name="ProductSubcategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=140)),
                ("slug", models.SlugField()),
                ("description", models.TextField(blank=True)),
                ("display_order", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="subcategories", to="catalog.category")),
            ],
            options={
                "verbose_name_plural": "product subcategories",
                "ordering": ("display_order", "name"),
            },
        ),
        migrations.AddConstraint(
            model_name="productsubcategory",
            constraint=models.UniqueConstraint(fields=("category", "slug"), name="unique_product_subcategory_slug_per_category"),
        ),
        migrations.AddField(
            model_name="product",
            name="subcategory",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="products", to="catalog.productsubcategory"),
        ),
        migrations.RunPython(seed_zeiss_light_microscopes, migrations.RunPython.noop),
    ]
