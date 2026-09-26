from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from catalog.models import Category, Product
from core.models import Partner, Service


CATEGORIES = [
    ("Chemistry", "Analysers, reagents, calibrators and controls for routine chemistry."),
    ("Immunoassay", "Immunoassay products for infectious disease, autoimmunity and routine diagnostics."),
    ("Hematology", "Hematology analysers, reagents and supporting laboratory products."),
    ("Urinalysis", "Urinalysis analysers, test strips and supporting diagnostic products."),
    ("Microbiology", "Culture, susceptibility testing, ESR and microbiology laboratory equipment."),
    ("Blood Banking", "Blood storage, grouping, separation and donor-care products."),
    ("ZEISS Light Microscopes", "ZEISS light microscopy systems for scientific research, routine laboratories, education and industrial inspection."),
    ("Eschweiler ABG", "ESCHWEILER blood gas, electrolyte and metabolite analysers, system components and consumables."),
    ("AMA Helic UBT Reader", "Non-invasive Helicobacter pylori breath-testing equipment from AMA-Med."),
    ("Vatech Dental", "Vatech dental imaging systems and intraoral imaging solutions."),
    ("Polycheck", "Polycheck® multiparameter in vitro diagnostic panels for allergy, autoimmune and veterinary testing."),
    ("Molbio", "Molbio Diagnostics point-of-care molecular diagnostics, screening, portable radiology and digital pathology solutions."),
    ("SD Biosensor Rapid Test", "Selected STANDARD Q rapid diagnostic tests from SD BIOSENSOR for malaria, hepatitis and blood-borne infections."),
    ("Semen Analyzers (SQA)", "Medical Electronic Systems automated semen-analysis equipment for clinical and andrology laboratories."),
]

PRODUCTS = [
    ("Blood Bank Refrigerator BBR-300", "Blood Banking", "Somlab Select", "SL-BB-300", "Purpose-built cold storage for safe and consistent blood-bank operation.", "A dependable blood-bank refrigerator engineered for stable temperature control, clear monitoring and everyday clinical use.", "Capacity: 300 L\nTemperature range: 2–6°C\nDigital alarm system\nGlass access door", Decimal("4850.00"), "on_request", True),
    ("Automated Chemistry Analyser CX-200", "Chemistry", "Beckman Coulter", "SL-CC-200", "A compact automated chemistry platform for efficient routine diagnostics.", "Designed for hospital and private laboratory workflows that need dependable throughput, straightforward operation and consistent results.", "Throughput: up to 200 tests/hour\nOpen reagent system\nAutomatic calibration\nBidirectional LIS support", None, "on_request", True),
    ("ZEISS Stemi 355", "ZEISS Light Microscopes", "ZEISS", "ZEISS-STEMI-355", "A compact stereo microscope for education, laboratory work and industrial inspection.", "Part of the official ZEISS Stereo and Zoom Microscopes portfolio. Contact Somlab for configuration, availability and application guidance.", "Type: Stereo microscope\nConfigurations: Education, Labs and Industry\nModel: Stemi 355", None, "on_request", False),
    ("ZEISS SteREO Discovery.V8", "ZEISS Light Microscopes", "ZEISS", "ZEISS-DISCOVERY-V8", "A modular stereo microscope delivering crisp 3D images throughout an 8:1 manual zoom range.", "Part of the official ZEISS Stereo and Zoom Microscopes portfolio. Contact Somlab for configuration, availability and application guidance.", "Type: Stereo microscope\nZoom range: 8:1 manual zoom\nModel: SteREO Discovery.V8", None, "on_request", False),
    ("ZEISS SteREO Discovery.V12", "ZEISS Light Microscopes", "ZEISS", "ZEISS-DISCOVERY-V12", "A modular stereo microscope with reproducible imaging across a motorized 12:1 zoom range.", "Part of the official ZEISS Stereo and Zoom Microscopes portfolio. Contact Somlab for configuration, availability and application guidance.", "Type: Stereo microscope\nZoom range: 12:1 motorized zoom\nModel: SteREO Discovery.V12", None, "on_request", False),
    ("ZEISS SteREO Discovery.V20", "ZEISS Light Microscopes", "ZEISS", "ZEISS-DISCOVERY-V20", "A high-performance modular stereo microscope with a motorized 20:1 zoom range.", "Part of the official ZEISS Stereo and Zoom Microscopes portfolio. Contact Somlab for configuration, availability and application guidance.", "Type: Stereo microscope\nZoom range: 20:1 motorized zoom\nModel: SteREO Discovery.V20", None, "on_request", False),
]

SERVICES = [
    ("Equipment Installation", "Professional setup and commissioning of supplied laboratory instruments.", "Our technical team coordinates delivery, placement, setup, commissioning and basic operational checks so equipment is ready for safe use."),
    ("Training & Application Support", "Practical training that helps laboratory teams use equipment confidently.", "We provide user training, workflow orientation and application support tailored to the supplied system and the experience of your laboratory team."),
    ("Maintenance & Technical Support", "Preventive maintenance, troubleshooting and responsive after-sales care.", "Somlab supports equipment uptime through planned maintenance, fault assessment, repairs and coordination of compatible spare parts."),
    ("Laboratory Project Development", "Product selection and planning based on your facility's requirements.", "We translate your service scope, testing volume and available space into a practical equipment and supply plan."),
    ("Laboratory Management Systems", "Digital tools that support laboratory workflow and information management.", "We help institutions identify and implement laboratory management solutions that improve traceability, reporting and everyday workflow."),
    ("Turnkey Laboratory Projects", "End-to-end support from planning and supply to installation and training.", "For new and upgraded laboratories, Somlab coordinates equipment, core supplies, installation and staff orientation as one structured project."),
]

PARTNERS = [
    ("Beckman Coulter", "United States"),
    ("SD Biosensor", "South Korea"),
    ("Bioer Technology", "China"),
    ("Molbio Diagnostics", "India"),
    ("Biosan", "Latvia"),
    ("Polycheck", "Germany"),
    ("Turklab", "Turkey"),
    ("GeneProof", "Czech Republic"),
    ("ZEISS", "Germany"),
]

PRODUCT_MENU_PARTNERS = [
    ("Beckman Coulter", "Beckman Coulter", "laboratory"),
    ("Polycheck", "Polycheck", "laboratory"),
    ("Molbio Diagnostics", "Molbio", "laboratory"),
    ("Medical Electronic Systems", "Medical Electronic System", "laboratory"),
    ("AMA Helic UBT Reader", "AMA Helic UBT Reader", "laboratory"),
    ("SD Biosensor", "SD Biosensor", "laboratory"),
    ("Eschweiler ABG", "Eschweiler ABG", "laboratory"),
    ("ZEISS", "ZEISS Microscopy", "medical"),
    ("Vatech Dental", "Vatech Dental", "dental"),
]

PRODUCT_SLUG_OVERRIDES = {
    "ZEISS-STEMI-355": "stemi-355",
    "ZEISS-DISCOVERY-V8": "stereo-discovery-v8",
    "ZEISS-DISCOVERY-V12": "stereo-discovery-v12",
    "ZEISS-DISCOVERY-V20": "stereo-discovery-v20",
}

CATEGORY_SLUG_OVERRIDES = {
    "ZEISS Light Microscopes": "light-microscopes",
    "SD Biosensor Rapid Test": "sd-biosensor",
    "Semen Analyzers (SQA)": "medical-electronic-systems",
}


class Command(BaseCommand):
    help = "Create the initial Somlab categories, products, services and partners."

    def handle(self, *args, **options):
        category_map = {}
        for index, (name, description) in enumerate(CATEGORIES):
            obj, _ = Category.objects.update_or_create(
                slug=CATEGORY_SLUG_OVERRIDES.get(name, slugify(name)), defaults={
                    "name": name, "description": description,
                    "display_order": index, "is_active": True,
                }
            )
            category_map[name] = obj

        for name, category, brand, code, short, description, specs, price, availability, featured in PRODUCTS:
            Product.objects.update_or_create(
                product_code=code,
                defaults={
                    "name": name, "slug": PRODUCT_SLUG_OVERRIDES.get(code, slugify(name)), "category": category_map[category],
                    "brand": brand, "short_description": short, "description": description,
                    "specifications": specs, "price": price, "availability": availability,
                    "is_featured": featured, "is_active": True,
                },
            )

        allowed_slugs = {
            CATEGORY_SLUG_OVERRIDES.get(name, slugify(name))
            for name, _ in CATEGORIES
        }
        Category.objects.exclude(slug__in=allowed_slugs).update(is_active=False)
        Product.objects.exclude(category__slug__in=allowed_slugs).update(
            is_active=False,
            is_featured=False,
        )

        for index, (name, short, description) in enumerate(SERVICES):
            Service.objects.update_or_create(
                slug=slugify(name),
                defaults={"name": name, "short_description": short, "description": description, "display_order": index},
            )

        for index, (name, country) in enumerate(PARTNERS):
            Partner.objects.update_or_create(
                name=name, defaults={"country": country, "display_order": index, "is_active": True}
            )

        Partner.objects.update(equipment_group="", menu_label="", menu_order=0)
        for menu_order, (name, menu_label, equipment_group) in enumerate(
            PRODUCT_MENU_PARTNERS
        ):
            partner, _ = Partner.objects.update_or_create(
                name=name,
                defaults={
                    "menu_label": menu_label,
                    "equipment_group": equipment_group,
                    "menu_order": menu_order,
                    "is_active": True,
                },
            )
            if name == "Beckman Coulter":
                partner.menu_categories.set(
                    Category.objects.filter(slug__in={
                        "chemistry", "immunoassay", "hematology", "urinalysis",
                        "microbiology", "blood-banking",
                    })
                )
            elif name == "ZEISS":
                light_microscopes = Category.objects.filter(
                    slug="light-microscopes"
                )
                light_microscopes.update(menu_label="ZEISS Light Microscopes")
                partner.menu_categories.set(light_microscopes)
            elif name == "Eschweiler ABG":
                partner.menu_categories.set(
                    Category.objects.filter(slug="eschweiler-abg")
                )
            elif name == "AMA Helic UBT Reader":
                partner.menu_categories.set(
                    Category.objects.filter(slug="ama-helic-ubt-reader")
                )
            elif name == "Vatech Dental":
                partner.menu_categories.set(
                    Category.objects.filter(slug="vatech-dental")
                )
            elif name == "Polycheck":
                partner.menu_categories.set(
                    Category.objects.filter(slug="polycheck")
                )
            elif name == "Molbio Diagnostics":
                partner.menu_categories.set(
                    Category.objects.filter(slug="molbio")
                )
            elif name == "SD Biosensor":
                partner.menu_categories.set(
                    Category.objects.filter(slug="sd-biosensor")
                )
            elif name == "Medical Electronic Systems":
                partner.menu_categories.add(
                    *Category.objects.filter(slug="medical-electronic-systems")
                )

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(CATEGORIES)} categories, {len(PRODUCTS)} products, "
            f"{len(SERVICES)} services and {len(PARTNERS)} partners."
        ))
