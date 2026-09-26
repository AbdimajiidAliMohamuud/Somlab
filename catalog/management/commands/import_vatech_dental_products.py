import io
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from catalog.models import Category, Product, ProductSubcategory
from core.models import Partner


BRAND = "Vatech Dental"
OFFICIAL_CATALOGUE = "https://www.vatech.com/Dental"
ASSET_DIR = Path(__file__).resolve().parent.parent / "data" / "vatech_dental"


def product(group, source_id, name, short, description, specifications, image_path):
    source_section = "product_3d" if group == "3d-imaging" else "product_2d" if group == "2d-imaging" else "io"
    return {
        "group": group,
        "source_id": source_id,
        "source_url": f"https://www.vatech.com/{source_section}/{source_id}",
        "name": name,
        "slug": name.lower().replace(" ", "-").replace("-i3d", "-i3d").replace("+", "plus"),
        "product_code": f"VATECH-{source_section.upper().replace('_', '-')}-{source_id}",
        "short_description": short,
        "description": description,
        "specifications": specifications,
        "image_url": f"https://www.vatech.com/files/thumbnails/{image_path}/400x400.crop.jpg",
        "image_name": f"vatech-{source_section}-{source_id}.jpg",
    }


VATECH_PRODUCTS = (
    product("3d-imaging", "35891", "Vatech A9", "A dental 3D imaging system with an 8 × 8 cm field of view.", "Vatech A9 combines panoramic imaging and CBCT for dental diagnosis and treatment planning, with Vatech image processing and optional rapid cephalometric imaging.", "System type: Panoramic and CBCT imaging\nCBCT field of view: 8 × 8 cm\nPanoramic processing: MAGIC PAN optional\nMetal artefact reduction: ART-V\nCephalometric imaging: Rapid Ceph optional", "891/035"),
    product("3d-imaging", "34455", "Green X", "An advanced 4-in-1 digital X-ray imaging system for multi-modality dental workflows.", "Green X combines panoramic, optional cephalometric, CBCT and model scanning, with selectable fields of view and a high-resolution endodontic mode.", "Modalities: Panoramic, CBCT, model scan and optional cephalometric\nSelectable FOV: 16 × 9, 12 × 9, 8 × 8, 8 × 5, 5 × 5 and 4 × 4 cm\nEndodontic mode: 4 × 4 cm, 50 μm voxel\nMetal artefact reduction: ART-V\nModel scanning: Supported", "455/034"),
    product("3d-imaging", "314", "Green 21", "A large-field multi-modality CBCT system for dental and maxillofacial imaging.", "Green 21 provides dental and ENT CBCT modes, panoramic imaging and a broad range of fields of view for complex diagnostic workflows.", "Function: CT with Auto Pano/Auto Ceph, panoramic and optional 3D photo\nDental CT FOV: 21 × 19, 17 × 15, 12 × 9 and 8 × 8 cm\nScan time: Panoramic 13.5 seconds; CT 18 seconds\nVoxel size: 0.12–0.4 mm\nSensor: CMOS\nGrey scale: 14 bit", "314"),
    product("3d-imaging", "2698", "Green 18", "A 4-in-1 dental X-ray imaging system with an 18 × 10 cm maximum field of view.", "Green 18 integrates panoramic, optional cephalometric, CBCT and model scanning for dental, implant and maxillofacial imaging.", "Modalities: Panoramic, CBCT, model scan and optional cephalometric\nSelectable FOV: 18 × 10, 13 × 10, 8 × 10 and 5 × 5 cm\nModel scanning: Supported\nMetal artefact reduction: ART-V\nPanoramic processing: MAGIC PAN optional", "698/002"),
    product("3d-imaging", "312", "PaX-i3D Green", "A low-dose CBCT platform with rapid scanning and multiple field-of-view options.", "PaX-i3D Green combines CBCT and panoramic imaging with optional cephalometric configurations, rapid acquisition and Ez3D-i workflow software.", "Function: Panoramic, CBCT and optional cephalometric\nFOV range: 5 × 5 to 16 × 10 cm; 15 × 15 cm configuration available\nCBCT scan time: 5.9 seconds; 9 seconds for 15 × 15 mode\nGrey scale: 14 bit\nPatient position: Standing and wheelchair accessible\nSoftware: Ez3D-i", "312"),
    product("3d-imaging", "315", "Green 16", "A 4-in-1 dental X-ray system with multi-FOV CBCT and model scanning.", "Green 16 combines panoramic, optional cephalometric, CBCT and model scanning with selectable fields of view for focused and full-arch diagnosis.", "Modalities: Panoramic, CBCT, model scan and optional cephalometric\nSelectable FOV: 16 × 9, 12 × 9, 8 × 9 and 5 × 5 cm\nMetal artefact reduction: ART-V\nModel scanning: Supported\nPanoramic processing: MAGIC PAN optional", "315"),
    product("3d-imaging", "2678", "Smart Plus", "A practical 3-in-1 CBCT system with an anatomical 12 × 9 cm field of view.", "Smart Plus combines CBCT with Auto Pano, panoramic and optional cephalometric imaging, plus Vatech artefact reduction and model scanning.", "Function: CT with Auto Pano, panoramic, cephalometric and model scan\nCT FOV: 10 × 8.5 cm anatomical 12 × 9; 10 × 7 and 5 × 5 cm\nVoxel size: 0.08, 0.12, 0.2 and 0.3 mm\nCT scan time: 18 seconds\nGrey scale: 14 bit\nMetal artefact reduction: ART-V", "678/002"),
    product("3d-imaging", "313", "PaX-i3D Smart", "A 3-in-1 CBCT imaging system that can produce CT and Auto Pano images from one scan.", "PaX-i3D Smart combines CBCT, panoramic and optional cephalometric imaging with an anatomical field of view and ART-V artefact reduction.", "Function: CT with Auto Pano, panoramic and optional cephalometric\nCT FOV: 10 × 8.5 cm anatomical 12 × 9; 10 × 7, 8 × 8 and 5 × 5 cm\nVoxel size: 0.08, 0.2 and 0.3 mm\nCT scan time: 18 seconds\nGrey scale: 14 bit\nMetal artefact reduction: ART-V", "313"),
    product("3d-imaging", "311", "PaX-i3D", "A multi-FOV CBCT system for focused, arch and full dental diagnosis.", "PaX-i3D combines panoramic and CBCT imaging with optional scan or one-shot cephalometric configurations and Ez3D-i software support.", "Function: Panoramic, CBCT and optional cephalometric\nSelectable FOV: 5 × 5, 8 × 5, 8 × 8 and 12 × 9 cm\nCBCT scan time: 15 seconds standard; 24 seconds high\nGrey scale: 14 bit\nPatient position: Standing and wheelchair accessible\nSoftware: Ez3D-i", "311"),
    product("2d-imaging", "1818", "PaX-i Insight", "A panoramic system that captures multiple focal layers to add depth to 2D imaging.", "PaX-i Insight provides multi-layer Insight Pan imaging and optional rapid cephalometric acquisition for more detailed panoramic assessment.", "Function: Panoramic and optional cephalometric\nPanoramic scan time: 10.4, 14.0 or 21.0 seconds\nInsight Pan scan time: 10.4 seconds\nCephalometric scan time: 1.9 or 3.9 seconds\nFocal spot: 0.5 mm\nGrey scale: 14 bit", "818/001"),
    product("2d-imaging", "2715", "PaX-i Plus", "A panoramic and optional cephalometric system with rapid acquisition modes.", "PaX-i Plus supports high-quality panoramic imaging, multiple examination modes and an optional rapid cephalometric configuration.", "Function: Panoramic and optional cephalometric\nPanoramic scan time: 10.4 seconds normal; 14 seconds HD\nCephalometric scan time: 1.9 or 3.9 seconds\nFocal spot: 0.5 mm\nTube voltage/current: 60–90 kV / 4–10 mA\nGrey scale: 14 bit", "715/002"),
    product("2d-imaging", "330", "PaX-i", "A compact panoramic imaging system with optional scan or one-shot cephalometric configurations.", "PaX-i combines panoramic imaging, dedicated sensor options and multiple capture modes for dental and orthodontic workflows.", "Function: Panoramic and optional cephalometric\nPanoramic scan time: 13.5 seconds HD; 10.1 seconds normal\nCephalometric scan time: 12.9 seconds scan; 0.9 seconds one-shot\nFocal spot: 0.5 mm\nGrey scale: 14 bit\nPatient position: Standing and wheelchair accessible", "330"),
    product("ios-iox", "2728", "EzRay Air Portable", "A lightweight 1.8 kg portable intraoral X-ray unit.", "EzRay Air Portable is designed for stable handheld positioning, clear dental images and operator protection using internal and external shielding.", "System type: Portable intraoral X-ray\nWeight: 1.8 kg\nControls: Single-dial operation\nPositioning: Smart angulation\nProtection: Internal shielding and external backscatter shield", "728/002"),
    product("ios-iox", "2732", "EzRay Air Wall", "A compact wall-mounted intraoral X-ray system with a lightweight tube head.", "EzRay Air Wall combines a 0.4 mm focal spot, intuitive controls and configurable arm lengths for efficient intraoral imaging.", "Focal spot: 0.4 mm\nTube voltage/current: 65 kV / 3.0 mA\nExposure time: 0.05–0.5 seconds\nSource-to-skin distance: Minimum 200 mm\nArm lengths: 450, 600 or 900 mm\nTube-head weight: 2.4 kg", "732/002"),
    product("ios-iox", "2736", "EzRay Chair", "A chair-mounted intraoral X-ray system with compact, lightweight components.", "EzRay Chair provides ergonomic positioning, intuitive controls and modern DC technology for repeatable intraoral X-ray output.", "System type: Chair-mounted intraoral X-ray\nPositioning: Smart angulation\nControls: Intuitive panel and single dial\nTechnology: DC X-ray generation\nDesign: Compact and lightweight components", "736/002"),
    product("ios-iox", "337", "EzSensor HD", "A high-resolution intraoral CMOS sensor available in three sizes.", "EzSensor HD combines 14.8 μm pixels, high theoretical resolution, IP68 protection and reinforced cable strain relief for intraoral imaging.", "Detector: CMOS\nPixel size: 14.8 μm\nTheoretical resolution: 33.78 lp/mm\nDynamic range: 12 bit\nSizes: 1.0, 1.5 and 2.0\nThickness: 4.8 mm\nCable length: 2.7 m\nIngress protection: IP68", "337"),
    product("ios-iox", "331", "EzSensor Soft", "A flexible-exterior intraoral CMOS sensor designed for comfortable positioning.", "EzSensor Soft uses a biocompatible silicone exterior, 14.8 μm pixels and three sizes to support comfortable positioning and detailed dental imaging.", "Detector: CMOS\nPixel size: 14.8 μm\nTheoretical resolution: 33.7 lp/mm\nDynamic range: 12 bit\nSizes: 1.0, 1.5 and 2.0\nExterior material: Biocompatible silicone\nCable length: 2.7 m", "331"),
    product("ios-iox", "338", "EzSensor Classic", "An ultra-slim intraoral CMOS sensor with rounded patient-oriented edges.", "EzSensor Classic provides three sensor sizes, a slim 4.8 mm profile and a high-sensitivity CMOS detector for consistent intraoral imaging.", "Detector: CMOS\nPixel size: 29.6 μm\nTheoretical resolution: 17 lp/mm\nDynamic range: 12 bit\nSizes: 1.0, 1.5 and 2.0\nThickness: 4.8 mm\nCable length: 2.7 m", "338"),
)


class Command(BaseCommand):
    help = "Import or update the official Vatech Dental catalogue and images."

    def add_arguments(self, parser):
        parser.add_argument("--skip-images", action="store_true")
        parser.add_argument("--replace-images", action="store_true")

    def handle(self, *args, **options):
        category, _ = Category.objects.update_or_create(
            slug="vatech-dental",
            defaults={
                "name": BRAND,
                "menu_label": BRAND,
                "description": "Vatech dental imaging systems and intraoral imaging solutions.",
                "icon": "analyser",
                "display_order": 9,
                "is_active": True,
            },
        )
        groups = {}
        for order, (name, slug, description) in enumerate((
            ("3D Imaging", "3d-imaging", "CBCT and multi-modality dental imaging systems for three-dimensional diagnosis."),
            ("2D Imaging", "2d-imaging", "Panoramic and cephalometric dental imaging systems."),
            ("IOS and IOX", "ios-iox", "Intraoral X-ray generators and digital intraoral sensors."),
        )):
            groups[slug], _ = ProductSubcategory.objects.update_or_create(
                category=category,
                slug=slug,
                defaults={"name": name, "description": description, "display_order": order, "is_active": True},
            )

        partner, _ = Partner.objects.update_or_create(
            name=BRAND,
            defaults={
                "country": "South Korea",
                "website": OFFICIAL_CATALOGUE,
                "equipment_group": "dental",
                "menu_label": BRAND,
                "menu_order": 8,
                "is_active": True,
            },
        )
        partner.menu_categories.set([category])

        created = updated = imaged = 0
        for definition in VATECH_PRODUCTS:
            item, was_created = Product.objects.update_or_create(
                product_code=definition["product_code"],
                defaults={
                    "category": category,
                    "subcategory": groups[definition["group"]],
                    "name": definition["name"],
                    "slug": definition["slug"],
                    "brand": BRAND,
                    "short_description": definition["short_description"],
                    "description": definition["description"],
                    "specifications": definition["specifications"],
                    "price": None,
                    "availability": "on_request",
                    "is_featured": False,
                    "is_active": True,
                },
            )
            created += int(was_created)
            updated += int(not was_created)
            if not options["skip_images"] and (options["replace_images"] or not item.image):
                image_content = self._image_content(definition)
                if image_content:
                    item.image.save(definition["image_name"], image_content, save=True)
                    imaged += 1
            self.stdout.write(f"{'Created' if was_created else 'Updated'} {item.name} ({definition['source_url']})")

        self.stdout.write(self.style.SUCCESS(
            f"Vatech catalogue complete: {created} created, {updated} updated, {imaged} images stored."
        ))

    def _image_content(self, definition):
        local_path = ASSET_DIR / definition["image_name"]
        if local_path.exists():
            return ContentFile(local_path.read_bytes(), name=definition["image_name"])
        try:
            request = Request(definition["image_url"], headers={"User-Agent": "Somlab catalogue importer/1.0"})
            with urlopen(request, timeout=20) as response:
                data = response.read()
            if not data:
                return None
            try:
                from PIL import Image
                image = Image.open(io.BytesIO(data)).convert("RGB")
                output = io.BytesIO()
                image.save(output, "JPEG", quality=88, optimize=True)
                data = output.getvalue()
            except (ImportError, OSError):
                pass
            return ContentFile(data, name=definition["image_name"])
        except (OSError, URLError) as exc:
            self.stderr.write(self.style.WARNING(
                f"Could not import image for {definition['name']}: {exc}"
            ))
            return None
