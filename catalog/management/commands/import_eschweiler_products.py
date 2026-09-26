from io import BytesIO
from pathlib import Path
import ssl
from urllib.request import Request, urlopen

from django.core.files import File
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from PIL import Image, UnidentifiedImageError

from catalog.models import Category, Product, ProductSubcategory
from core.models import Partner


ASSET_DIR = Path(__file__).resolve().parent.parent / "data" / "eschweiler"
BRAND = "Eschweiler ABG"

OFFICIAL_IMAGE_SOURCES = {
    "modular-touchscreen.png": "https://www.eschweiler-kiel.de/wp-content/uploads/2018/12/modular-screen-e1540385461820.png",
    "modular-sample-port.jpg": "https://www.eschweiler-kiel.de/wp-content/uploads/2018/11/mp-spritze-e1543745525165-933x1024.jpg",
    "modular-barcode-reader.png": "https://www.eschweiler-kiel.de/wp-content/uploads/2018/12/barcodereader-e1543746381371-1024x921.png",
    "modular-sensors.png": "https://www.eschweiler-kiel.de/wp-content/uploads/2018/11/combiline3-sensoren.png",
    "modular-calpack.jpg": "https://www.eschweiler-kiel.de/wp-content/uploads/2018/12/kassetten-e1543863389761-1024x908.jpg",
    "combi-operation.jpg": "https://www.eschweiler-kiel.de/wp-content/uploads/2018/12/bedienung-cl2.jpg",
    "combi-sample-input.jpg": "https://www.eschweiler-kiel.de/wp-content/uploads/2018/11/probe-cl2@2x.jpg",
    "combi-biosensors.jpg": "https://www.eschweiler-kiel.de/wp-content/uploads/2018/11/biosensoren-cl2.jpg",
    "combi-calibration-solutions.png": "https://www.eschweiler-kiel.de/wp-content/uploads/2018/11/ESCHWEILER-combi-line-2014-e1543755910172-998x1024.png",
}


def item(group, code, slug, name, short, description, specifications="", image="", source_url=""):
    return {
        "group": group,
        "product_code": code,
        "slug": slug,
        "name": name,
        "short_description": short,
        "description": description,
        "specifications": specifications,
        "image": image,
        "source_url": source_url,
    }


MODULAR_PAGE = "https://www.eschweiler-kiel.de/en/products/modular-pro-2/"
MODULAR_SENSOR_PAGE = f"{MODULAR_PAGE}sensors-mp-en/"
COMBI_PAGE = "https://www.eschweiler-kiel.de/en/products/combi-line-2/"

ESCHWEILER_PRODUCTS = [
    item(
        "modular-pro", "ESCH-MP-TOUCH", "modular-pro-touchscreen", "touchscreen",
        "A 10.4-inch touchscreen interface for guided modular pro operation.",
        "The large touchscreen provides structured menu navigation, large routine-measurement controls, service and diagnostic programs, and integrated patient and QC databases.",
        "Display size: 10.4 inches\nDisplay type: Colour TFT with LED backlight\nResolution: 800 × 600",
        "modular-touchscreen.png", f"{MODULAR_PAGE}touchscreen-mp-en/",
    ),
    item(
        "modular-pro", "ESCH-MP-SAMPLE", "modular-pro-universal-sample-port", "sample port",
        "An automatic sample-entry component compatible with capillaries and syringes.",
        "After a capillary or syringe is inserted, the modular pro sample port actively draws the specimen and manages the remaining sample-entry steps.",
        "Compatible containers: capillary and syringe\nSample handling: automatic aspiration",
        "modular-sample-port.jpg", f"{MODULAR_PAGE}sample-port-en/",
    ),
    item(
        "modular-pro", "ESCH-MP-BARCODE", "modular-pro-barcode-reader", "barcode reader",
        "A barcode reader for coded patient and quality-control sample data.",
        "The modular pro barcode reader captures coded patient information and coded QC sample data for the analyser workflow.",
        "Data types: coded patient data and coded QC sample data",
        "modular-barcode-reader.png", f"{MODULAR_PAGE}barcode-reader-mp-en/",
    ),
    item(
        "modular-pro", "ESCH-MP-CALPACK", "modular-pro-calpack", "calibration",
        "An exchangeable calibration cassette for modular pro sensor configurations.",
        "CALPACK contains the calibration solutions required for blood gas, electrolyte and metabolite sensors. RFID transfers calibration values automatically, while the analyser monitors fill levels and guides cassette replacement.",
        "Format: exchangeable calibration cassette\nIdentification: RFID\nMonitoring: automatic fill-level monitoring\nCalibration method: liquid calibration",
        "modular-calpack.jpg", f"{MODULAR_PAGE}calibration-mp-en/",
    ),
    item(
        "modular-pro", "ESCH-MP-SENSORS", "modular-pro-sensors", "sensors",
        "Configurable direct-measurement sensors for the modular pro system.",
        "The official modular pro sensors section presents the analyser's blood gas, electrolyte and metabolite sensor system as one configurable section.",
        "Directly measured parameters: pO₂, pCO₂, pH, tHb, Na+, K+, Ca++, Li+, Cl−, glucose and lactate",
        "modular-sensors.png", MODULAR_SENSOR_PAGE,
    ),
    item(
        "modular-pro", "ESCH-MP-LAN", "modular-pro-lan-interface", "network (LAN)",
        "A connectivity interface for exchanging analyser data with clinical networks.",
        "The modular pro LAN interface connects the analyser to internal clinical networks through HL7 and supports patient and QC data transfer to central administration through ODBC.",
        "Network interface: LAN\nClinical protocol: HL7\nData transfer: patient and QC data via ODBC",
        "", f"{MODULAR_PAGE}network-lan-mp-en/",
    ),
    item(
        "modular-pro", "ESCH-MP-TECHNICAL-DATA", "modular-pro-technical-data", "technical data",
        "Official technical data for the modular pro analyser family.",
        "The official technical-data section records the modular pro measurement configuration, sample requirements, interfaces, calibration cycle, dimensions and weight.",
        "Direct measurement: up to 11 configurable parameters\nDisplay: 10.4-inch colour TFT, 800 × 600\nSample material: whole blood, serum, plasma and respiratory gas\nInterfaces: LAN, USB, RS 232 and HL7\nCalibration: automatic every 90 minutes\nDimensions: 520 × 450 × 415 mm\nWeight: approximately 17 kg",
        "", f"{MODULAR_PAGE}technical-data-modular-pro-en/",
    ),
    item(
        "combi-line-2", "ESCH-CL2-OPERATION", "combi-line-2-operation", "operation",
        "Step-by-step operation through the combi line 2 illuminated display.",
        "The official operation section describes the combi line 2 menu-guided workflow, patient and QC data storage, service programs and integrated thermal printer.",
        "Display: illuminated 15-line LCD\nData management: patient and QC databases\nPrinter: integrated thermal printer",
        "combi-operation.jpg", f"{COMBI_PAGE}operation-cl2/",
    ),
    item(
        "combi-line-2", "ESCH-CL2-SAMPLE", "combi-line-2-sample-input", "sample input",
        "A sample-entry system for capillary aspiration and controlled syringe injection.",
        "The combi line 2 aspirates capillary samples automatically. Syringe samples are injected until an acoustic signal confirms filling. Standard, selective and QC test programs are supported according to sensor configuration.",
        "Capillary handling: automatic aspiration\nSyringe handling: injection with acoustic fill confirmation\nPrograms: standard, selective and QC",
        "combi-sample-input.jpg", f"{COMBI_PAGE}sample-input-cl2/",
    ),
    item(
        "combi-line-2", "ESCH-CL2-SENSORS", "combi-line-2-blood-gas-electrolyte-sensors", "sensors",
        "The official combi line 2 blood gas, electrolyte and metabolite sensor section.",
        "The official sensor section combines durable blood-gas and electrolyte sensors with replaceable premembraned cartridges and thick-film glucose and lactate biosensor chips.",
        "Applications: blood gas, electrolyte, glucose and lactate measurement\nBiosensor technology: thick-film sensor chip\nCapacity: up to 1,000 analyses per biosensor",
        "combi-biosensors.jpg", f"{COMBI_PAGE}sensors-cl2-en/",
    ),
    item(
        "combi-line-2", "ESCH-CL2-CAL", "combi-line-2-calibration-solutions", "consumables",
        "Individually replaceable liquid calibration and rinse solutions for combi line 2.",
        "The complete combi line 2 blood gas, electrolyte and metabolite configuration uses four calibration solutions and one rinse solution. Blood-gas-only or electrolyte-only configurations may operate with two calibration solutions.",
        "Complete configuration: four calibration solutions plus one rinse solution\nBlood gas or electrolyte configuration: two calibration solutions\nPackaging: individually replaceable foil packets and bottles",
        "combi-calibration-solutions.png", f"{COMBI_PAGE}comsumables/",
    ),
    item(
        "combi-line-2", "ESCH-CL2-TECHNICAL-DATA", "combi-line-2-technical-data", "technical data",
        "Official technical data for the combi line 2 analyser family.",
        "The official technical-data section records the combi line 2 configurable measurements, display, interface, calibration cycle, dimensions and weight.",
        "Direct measurement: configurable combination of up to 11 parameters\nDisplay: illuminated 15-line LCD\nInterface: RS 232\nCalibration: automatic every 90 minutes\nDimensions: 402 × 320 × 432 mm; 356 mm wide with metabolite configuration\nWeight: approximately 14 kg; 15 kg with metabolite configuration",
        "", f"{COMBI_PAGE}technical-data-combi-line-2/",
    ),
]


class Command(BaseCommand):
    help = "Import or update the official Eschweiler system catalogue."

    def add_arguments(self, parser):
        parser.add_argument(
            "--audit-official-images",
            action="store_true",
            help=(
                "Correct names, family assignments and original-resolution "
                "official images for existing Eschweiler products only."
            ),
        )

    def handle(self, *args, **options):
        if options["audit_official_images"]:
            self._audit_existing_products()
            return

        category, _ = Category.objects.update_or_create(
            slug="eschweiler-abg",
            defaults={
                "name": "Eschweiler ABG",
                "description": "ESCHWEILER blood gas, electrolyte and metabolite analysers, system components and consumables.",
                "icon": "analyser",
                "display_order": 7,
                "is_active": True,
            },
        )
        groups = {}
        for order, (name, slug, description) in enumerate((
            ("modular pro", "modular-pro", "The modular pro analyser family, measurement components, calibration and connectivity items."),
            ("combi line 2", "combi-line-2", "The combi line 2 analyser family, sensors, sample handling and calibration consumables."),
        )):
            groups[slug], _ = ProductSubcategory.objects.update_or_create(
                category=category,
                slug=slug,
                defaults={"name": name, "description": description, "display_order": order, "is_active": True},
            )

        partner, _ = Partner.objects.update_or_create(
            name=BRAND,
            defaults={
                "country": "Germany", "website": "https://www.eschweiler-kiel.de/en/products/",
                "equipment_group": "laboratory", "menu_label": BRAND,
                "menu_order": 6, "is_active": True,
            },
        )
        partner.menu_categories.set([category])

        created_count = 0
        for definition in ESCHWEILER_PRODUCTS:
            product, created = Product.objects.update_or_create(
                product_code=definition["product_code"],
                defaults={
                    "category": category, "subcategory": groups[definition["group"]],
                    "name": definition["name"], "slug": definition["slug"], "brand": BRAND,
                    "short_description": definition["short_description"],
                    "description": definition["description"], "specifications": definition["specifications"],
                    "price": None, "availability": "on_request", "is_featured": False, "is_active": True,
                },
            )
            created_count += int(created)
            if definition["image"] and not product.image:
                with (ASSET_DIR / definition["image"]).open("rb") as image_file:
                    product.image.save(f"eschweiler/{definition['image']}", File(image_file), save=True)
            self.stdout.write(f"{'Created' if created else 'Updated'} {product.name} ({definition['source_url']})")

        official_codes = {item["product_code"] for item in ESCHWEILER_PRODUCTS}
        removed_count, _ = Product.objects.filter(
            category=category,
            subcategory__in=groups.values(),
            brand=BRAND,
        ).exclude(product_code__in=official_codes).delete()

        self.stdout.write(self.style.SUCCESS(
            f"Imported {len(ESCHWEILER_PRODUCTS)} Eschweiler catalogue items "
            f"({created_count} created; {removed_count} obsolete records removed)."
        ))

    def _audit_existing_products(self):
        try:
            category = Category.objects.get(slug="eschweiler-abg")
            groups = {
                group.slug: group
                for group in ProductSubcategory.objects.filter(
                    category=category,
                    slug__in={"modular-pro", "combi-line-2"},
                )
            }
        except Category.DoesNotExist as exc:
            raise CommandError("The existing Eschweiler ABG category is missing.") from exc
        if set(groups) != {"modular-pro", "combi-line-2"}:
            raise CommandError("Both existing Eschweiler subcategories are required.")

        codes = {definition["product_code"] for definition in ESCHWEILER_PRODUCTS}
        products = Product.objects.in_bulk(codes, field_name="product_code")
        obsolete = Product.objects.filter(
            category=category,
            subcategory__in=groups.values(),
            brand=BRAND,
        ).exclude(product_code__in=codes)
        for product in obsolete:
            if (
                product.gallery_media.exists()
                or product.variants.exists()
                or product.related_items.exists()
                or product.parent_relations.exists()
            ):
                raise CommandError(
                    f"Refusing to remove shared/dependent product {product.product_code}."
                )

        downloaded = {}
        for definition in ESCHWEILER_PRODUCTS:
            image_filename = definition["image"]
            if not image_filename:
                continue
            source_url = OFFICIAL_IMAGE_SOURCES.get(image_filename)
            if not source_url:
                raise CommandError(
                    f"No verified official image source for {image_filename}."
                )
            if source_url not in downloaded:
                downloaded[source_url] = self._download_official_image(source_url)

        created = renamed = reassigned = corrected_images = cleared_images = 0
        unchanged_images = 0
        with transaction.atomic():
            for definition in ESCHWEILER_PRODUCTS:
                expected_group = groups[definition["group"]]
                product = products.get(definition["product_code"])
                if product is None:
                    product = Product.objects.create(
                        category=category,
                        subcategory=expected_group,
                        name=definition["name"],
                        slug=definition["slug"],
                        brand=BRAND,
                        product_code=definition["product_code"],
                        short_description=definition["short_description"],
                        description=definition["description"],
                        specifications=definition["specifications"],
                        price=None,
                        availability="on_request",
                        is_featured=False,
                        is_active=True,
                    )
                    products[definition["product_code"]] = product
                    created += 1
                update_fields = []
                if product.name != definition["name"]:
                    product.name = definition["name"]
                    update_fields.append("name")
                    renamed += 1
                if product.category_id != category.pk:
                    product.category = category
                    update_fields.append("category")
                    reassigned += 1
                if product.subcategory_id != expected_group.pk:
                    product.subcategory = expected_group
                    update_fields.append("subcategory")
                    reassigned += 1

                image_filename = definition["image"]
                if image_filename:
                    source_url = OFFICIAL_IMAGE_SOURCES[image_filename]
                    content = downloaded[source_url]
                    current_content = b""
                    if product.image:
                        try:
                            with product.image.storage.open(
                                product.image.name, "rb"
                            ) as current_file:
                                current_content = current_file.read()
                        except OSError:
                            current_content = b""
                    current_source_content = b""
                    if product.source_image:
                        try:
                            with product.source_image.storage.open(
                                product.source_image.name, "rb"
                            ) as current_source_file:
                                current_source_content = current_source_file.read()
                        except OSError:
                            current_source_content = b""
                    if (
                        current_content != content
                        or current_source_content != content
                    ):
                        stored_filename = (
                            f"eschweiler/{product.slug}/{image_filename}"
                        )
                        if current_source_content != content:
                            product.source_image.save(
                                stored_filename,
                                ContentFile(content),
                                save=False,
                            )
                            update_fields.append("source_image")
                        if current_content != content:
                            product.image.save(
                                stored_filename,
                                ContentFile(content),
                                save=False,
                            )
                            update_fields.append("image")
                        corrected_images += 1
                    else:
                        unchanged_images += 1
                elif product.image or product.source_image:
                    # Eschweiler publishes no section artwork for the LAN and
                    # technical-data pages. Do not substitute a family image.
                    product.image = ""
                    product.source_image = ""
                    update_fields.extend(["image", "source_image"])
                    cleared_images += 1
                else:
                    unchanged_images += 1

                if update_fields:
                    product.save(update_fields=list(dict.fromkeys(update_fields)))
                    product.refresh_from_db()

                if image_filename:
                    self._verify_stored_image(
                        product,
                        downloaded[OFFICIAL_IMAGE_SOURCES[image_filename]],
                    )
                self.stdout.write(
                    f"Verified {product.product_code}: {product.name} "
                    f"({definition['source_url']})"
                )

            obsolete_count, _ = obsolete.delete()

        self.stdout.write(self.style.SUCCESS(
            "Eschweiler audit complete: "
            f"{len(ESCHWEILER_PRODUCTS)} official sections verified; "
            f"{created} created, {renamed} renamed, {reassigned} reassigned, "
            f"{corrected_images} images corrected, "
            f"{cleared_images} unverified reused images cleared, "
            f"{unchanged_images} images already exact, "
            f"{obsolete_count} obsolete records removed."
        ))

    @staticmethod
    def _download_official_image(source_url):
        request = Request(
            source_url,
            headers={"User-Agent": "Somlab Eschweiler catalogue audit/1.0"},
        )
        try:
            system_ca = Path("/etc/ssl/cert.pem")
            ssl_context = ssl.create_default_context(
                cafile=str(system_ca) if system_ca.exists() else None
            )
            with urlopen(request, timeout=45, context=ssl_context) as response:
                if response.status != 200:
                    raise CommandError(
                        f"Official image returned HTTP {response.status}: {source_url}"
                    )
                content_type = response.headers.get_content_type()
                if not content_type.startswith("image/"):
                    raise CommandError(
                        f"Official image returned {content_type}: {source_url}"
                    )
                content = response.read()
            Image.open(BytesIO(content)).verify()
        except (OSError, UnidentifiedImageError) as exc:
            raise CommandError(
                f"Unable to verify official Eschweiler image {source_url}: {exc}"
            ) from exc
        return content

    @staticmethod
    def _verify_stored_image(product, expected_content):
        for field_name in ("image", "source_image"):
            field = getattr(product, field_name)
            if not field or not field.storage.exists(field.name):
                raise CommandError(
                    f"Stored {field_name} is unavailable for {product.product_code}: "
                    f"{field.name!r}."
                )
            with field.storage.open(field.name, "rb") as stored_file:
                if stored_file.read() != expected_content:
                    raise CommandError(
                        f"Stored {field_name} differs from the official source "
                        f"for {product.product_code}."
                    )
