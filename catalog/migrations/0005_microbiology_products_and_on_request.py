from django.db import migrations, models


# Product facts and model numbers are taken from the official Beckman Coulter
# product pages listed in each record.  Source URLs remain here as an audit
# trail because the existing Product model intentionally has no source field.
MICROBIOLOGY_PRODUCTS = (
    {
        "name": "LabPro Information Manager",
        "slug": "labpro-information-manager",
        "brand": "Beckman Coulter",
        "product_code": "SL-CC-226",
        "short_description": (
            "Microbiology information management software that organizes test "
            "data and helps laboratories turn accurate results into action."
        ),
        "description": (
            "LabPro Information Manager brings microbiology test data into an "
            "easy-to-use information management environment. It supports "
            "customized reporting and notifications, makes patient-care "
            "information accessible, and can use LabPro with AlertEX to detect "
            "atypical results and guide staff according to predefined conditions "
            "and institutional procedures. LabPro v5.0 adds configurable security "
            "features for protected electronic health information."
        ),
        "specifications": (
            "Current verified release: LabPro v5.0\n"
            "Security features:\n"
            "  Data encryption\n"
            "  User account management\n"
            "  Customizable security settings\n"
            "  Application Controlled\n"
            "  Automatic audit trail\n"
            "Workflow features:\n"
            "  ESBL confirmation\n"
            "  Revised Drug Group Alert Rule parameter\n"
            "  Archived alert rules\n"
            "  Reagent lot management\n"
            "LabPro with AlertEX: included with MicroScan instrument systems and available for standalone manual-panel workflows"
        ),
        "variants": (
            ("LabPro Computer and Monitor", "B1018-510"),
        ),
        "source_url": (
            "https://www.beckmancoulter.com/en/products/microbiology/"
            "labpro-information-manager"
        ),
    },
    {
        "name": "LabPro Connect",
        "slug": "labpro-connect",
        "brand": "Beckman Coulter",
        "product_code": "SL-CC-227",
        "short_description": (
            "Network software that gives multiple users access to LabPro data "
            "from laboratory workstations or offices."
        ),
        "description": (
            "LabPro Connect extends LabPro Information Manager access beyond the "
            "instrument computer. Laboratory teams can manage identification and "
            "antimicrobial susceptibility data, review quality control, generate "
            "reports, and consolidate information from multiple MicroScan testing "
            "systems. Open and closed configurations support different laboratory "
            "network policies while maintaining one LIS connection for multiple "
            "testing systems."
        ),
        "specifications": (
            "Configurations:\n"
            "  Open system: connects workstation computers through the hospital LAN\n"
            "  Closed system: hardwired computers connect to a centralized LabPro database computer\n"
            "Open-system LAN minimum requirements:\n"
            "  Network speed: 100 Mbps\n"
            "  Protocol: TCP/IP\n"
            "  Required port: TCP 3050\n"
            "LAN workstation minimum requirements listed by manufacturer:\n"
            "  Processor: 2 GHz CPU\n"
            "  Memory: 512 MB RAM; 2 GB for Windows 7 64-bit\n"
            "  Storage: 40 GB hard drive with at least 500 MB free\n"
            "  Network interface: 10/100 NIC\n"
            "  Monitor resolution: 1024 x 768\n"
            "  Software: Adobe Reader\n"
            "Manufacturer note: workstation requirements on the official page are dated December 2014"
        ),
        "variants": (
            ("LabPro Connect Open System", "B1018-600"),
            ("LabPro Connect Closed System", "B1018-601"),
        ),
        "source_url": (
            "https://www.beckmancoulter.com/en/products/microbiology/"
            "labpro-connect"
        ),
    },
    {
        "name": "Copan WASP® DT: Walk-Away Specimen Processor",
        "slug": "copan-wasp-dt-walk-away-specimen-processor",
        "brand": "COPAN",
        "product_code": "SL-CC-228",
        "short_description": (
            "A modular open platform that automates microbiology specimen "
            "processing, including plating, streaking and slide preparation."
        ),
        "description": (
            "The Copan WASP DT standardizes specimen-culturing activities on a "
            "modular, open automation platform. It automates plating and streaking, "
            "Gram slide preparation, broth inoculation and disk application. "
            "LIS-driven protocols select media, loop size and streaking patterns, "
            "while Smart Scan barcode processing and image analysis support sample "
            "and loop verification. Continuous loading reduces batch processing and "
            "supports automated streaking of up to 130 plates per hour."
        ),
        "specifications": (
            "Dimensions:\n"
            "  Depth: 46.45 in\n"
            "  Width: 75.27 in\n"
            "  Height: 76.44 in\n"
            "Weight: approximately 1,700 lb\n"
            "Electrical power: 208/240 VAC; 50/60 Hz; 16 A\n"
            "Peak power: 1,500 W maximum\n"
            "Operating temperature: 5°C (41°F) to 40°C (104°F)\n"
            "Humidity: 0 to 95%\n"
            "Maximum altitude: 2,000 m (6,561 ft)\n"
            "Network: Ethernet 10/100/1000 MB\n"
            "Interface: LIS interface available upon request\n"
            "Peripherals: touch screen, external barcode reader and label printer\n"
            "Certifications: CE, CSA and compliance with IEC 61010 laboratory equipment safety standard\n"
            "Noise level:\n"
            "  Mean acoustic pressure at 1 m: 58.5 dB(A)\n"
            "  Maximum acoustic pressure: 67.4 dB(A)\n"
            "Processing capacity: automated streaking of up to 130 plates per hour"
        ),
        "variants": (
            ("WASP Basic Instrument", "W086"),
        ),
        "source_url": (
            "https://www.beckmancoulter.com/en/products/microbiology/"
            "copan-wasp-dt-walk-away-specimen-processor"
        ),
    },
    {
        "name": "Copan WASPLab™ Microbiology Automation System",
        "slug": "copan-wasplab-microbiology-automation-system",
        "brand": "COPAN",
        "product_code": "SL-CC-229",
        "short_description": (
            "A modular, scalable culture-processing system with automated "
            "incubation, high-resolution imaging and digital plate reading."
        ),
        "description": (
            "Copan WASPLab is a configurable clinical microbiology automation "
            "system for specimen processing and culture work-up. It combines "
            "Copan WASP DT pre-analytical processing with robotic incubation, "
            "high-resolution imaging and a barcode-driven conveyor track. The "
            "integrated workflow can automate pre-analytical, analytical and "
            "post-analytical tasks, reduce manual plate transport, support digital "
            "culture review and help laboratories report results sooner."
        ),
        "specifications": (
            "Configuration: customized to laboratory testing and workflow requirements\n"
            "System design: modular, scalable and customizable\n"
            "Specimen processing: barcode-driven Copan WASP DT platform\n"
            "Incubation: robotic automated incubation\n"
            "Imaging: high-resolution digital culture imaging\n"
            "Transport: customizable barcode-driven conveyor track\n"
            "Software capabilities:\n"
            "  PhenoMATRIX artificial intelligence supports culture review and resulting\n"
            "  Read-when-ready image evaluation supports 24/7 reporting\n"
            "  WASPLab software supports culture documentation\n"
            "Regulatory note: PhenoMATRIX is not FDA-cleared"
        ),
        "variants": (
            ("WASPLab Server Rack Hardware", "10976013"),
        ),
        "source_url": (
            "https://www.beckmancoulter.com/en/products/microbiology/"
            "copan-wasplab-system"
        ),
    },
)


def add_products_and_normalize_availability(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Product = apps.get_model("catalog", "Product")
    ProductVariant = apps.get_model("catalog", "ProductVariant")

    category = Category.objects.get(slug="microbiology")
    Product.objects.exclude(availability="on_request").update(
        availability="on_request"
    )

    for product_data in MICROBIOLOGY_PRODUCTS:
        product = Product.objects.filter(
            product_code=product_data["product_code"]
        ).first()
        if product is None:
            product = Product.objects.filter(slug=product_data["slug"]).first()
        if product is None:
            product = Product(
                product_code=product_data["product_code"],
                slug=product_data["slug"],
            )

        product.category = category
        product.name = product_data["name"]
        product.slug = product_data["slug"]
        product.brand = product_data["brand"]
        product.product_code = product_data["product_code"]
        product.short_description = product_data["short_description"]
        product.description = product_data["description"]
        product.specifications = product_data["specifications"]
        product.price = None
        product.availability = "on_request"
        product.is_featured = False
        product.is_active = True
        product.save()

        ProductVariant.objects.filter(product=product).delete()
        ProductVariant.objects.bulk_create([
            ProductVariant(
                product=product,
                name=name,
                model_number=model_number,
                display_order=index,
            )
            for index, (name, model_number) in enumerate(
                product_data["variants"]
            )
        ])


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0004_product_gallery_and_variants"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="availability",
            field=models.CharField(
                choices=[
                    ("available", "Available"),
                    ("low_stock", "Low stock"),
                    ("on_request", "Available on request"),
                    ("unavailable", "Unavailable"),
                ],
                default="on_request",
                max_length=20,
            ),
        ),
        migrations.RunPython(
            add_products_and_normalize_availability,
            migrations.RunPython.noop,
        ),
    ]
