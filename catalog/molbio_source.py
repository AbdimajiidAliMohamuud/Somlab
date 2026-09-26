"""Official-source parser for the Molbio Diagnostics catalogue.

The manufacturer currently publishes all Truenat assays on one page.  Keeping
the parser here makes source refreshes repeatable while the checked-in JSON
snapshot keeps normal imports deterministic and network-independent.
"""

from html import unescape
import os
import re
import ssl
from urllib.request import Request, urlopen

from .prorad_atlas import PRORAD_ATLAS_PRODUCTS


MOLBIO_BASE_URL = "https://www.molbiodiagnostics.com"
MOLBIO_PAGES = {
    "truenat": f"{MOLBIO_BASE_URL}/truenat/",
    "assays": f"{MOLBIO_BASE_URL}/truenat-assays/",
    "ibreastexam": f"{MOLBIO_BASE_URL}/ibreastexam/",
    "prorad": f"{MOLBIO_BASE_URL}/prorad-atlas-ultraportable/",
    "optrascan": f"{MOLBIO_BASE_URL}/optrascan-digital-pathology-solutions/",
}

ASSAY_GROUPS = {
    "Respiratory Infections": (
        "Truenat® MTB", "Truenat® MTB Plus", "Truenat® MTB-RIF Dx",
        "Truenat® MTB-INH", "Truenat® Influenza A/B", "Truenat® H3N2/H1N1",
        "Truenat® COVID-19", "Truenat® Inf A,B/COVID-19",
    ),
    "Vector Borne Disease": (
        "Truenat® Malaria Pv/Pf", "Truenat® Dengue/Chikungunya",
        "Truenat® Dengue", "Truenat® Chikungunya",
    ),
    "Hepatitis": (
        "Truenat® HBV", "Truenat® HCV", "Truenat® HAV", "Truenat® HEV",
    ),
    "Sexually Transmitted Infections": (
        "Truenat® HPV-HR Plus", "Truenat® HIV-1/HIV-2", "Truenat® HPV-HR",
        "Truenat® HSV 1/2", "Truenat® CT/NG", "Truenat® Trich",
        "Truenat® Mgen",
    ),
    "Zoonotic Diseases": ("Truenat® Rabies", "Truenat® Nipah"),
    "Viral Infections": ("Truenat® EBV", "Truenat® CMV"),
    "Bacterial Infections": (
        "Truenat® Salmonella", "Truenat® GBS", "Truenat® LTS",
        "Truenat® Scrub T", "Truenat® Shigella", "Truenat® CDI",
        "Truenat® Cholera", "Truenat® M. leprae",
    ),
    "Others": ("Truenat® HLA-B27",),
}

ASSAY_GROUP_BY_NAME = {
    name: group for group, names in ASSAY_GROUPS.items() for name in names
}


def molbio_ssl_context():
    """Use certifi when available, retaining the platform trust store fallback."""
    configured = os.environ.get("SSL_CERT_FILE")
    if configured:
        return ssl.create_default_context(cafile=configured)
    try:
        import certifi
    except ImportError:
        system_bundle = "/etc/ssl/cert.pem"
        if os.path.isfile(system_bundle):
            return ssl.create_default_context(cafile=system_bundle)
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def _text(fragment):
    fragment = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.I)
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"[ \t\r\f\v]+", " ", unescape(fragment)).strip()


def _cells(row):
    return [_text(cell) for cell in re.findall(r"<td\b[^>]*>(.*?)</td>", row, re.I | re.S)]


def parse_truenat_assays(source):
    """Return every official assay and its on-page catalogue metadata."""
    headings = list(re.finditer(
        r'<h2\b[^>]*class="[^"]*elementor-heading-title[^"]*"[^>]*>'
        r"\s*(Truenat®[^<]+?)\s*</h2>",
        source,
        re.I | re.S,
    ))
    products = []
    for index, match in enumerate(headings):
        name = _text(match.group(1))
        if name not in ASSAY_GROUP_BY_NAME:
            continue
        end = headings[index + 1].start() if index + 1 < len(headings) else len(source)
        chunk = source[match.start():end]

        paragraphs = [_text(value) for value in re.findall(r"<p\b[^>]*>(.*?)</p>", chunk, re.I | re.S)]
        description = next(
            (value for value in paragraphs if value.casefold().startswith(name.casefold())),
            next((value for value in paragraphs if value), ""),
        )

        images = []
        for image_tag in re.findall(r"<img\b[^>]*>", chunk, re.I):
            if "swiper-slide-image" not in image_tag:
                continue
            source_match = re.search(r'\bsrc="([^"]+)"', image_tag, re.I)
            if not source_match:
                continue
            image = unescape(source_match.group(1))
            if "/wp-content/uploads/" in image and image not in images:
                images.append(image)

        specifications = []
        for table in re.findall(
            r'<table\b[^>]*id="[^"]*technical[^"]*specification[^"]*"[^>]*>(.*?)</table>',
            chunk,
            re.I | re.S,
        ):
            for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", table, re.I | re.S):
                cells = _cells(row)
                if len(cells) >= 2 and cells[0] and cells[1]:
                    specifications.append([cells[0], cells[1]])

        kit_contents = []
        kit_match = re.search(
            r"Contents of the kit.*?<ol\b[^>]*>(.*?)</ol>", chunk, re.I | re.S
        )
        if kit_match:
            kit_contents = [
                _text(item)
                for item in re.findall(r"<li\b[^>]*>(.*?)</li>", kit_match.group(1), re.I | re.S)
                if _text(item)
            ]

        variants = []
        for table in re.findall(
            r'<table\b[^>]*id="[^"]*OrderingInformation[^"]*"[^>]*>(.*?)</table>',
            chunk,
            re.I | re.S,
        ):
            for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", table, re.I | re.S):
                cells = _cells(row)
                if len(cells) >= 2 and re.fullmatch(r"\d{6,}", cells[1].replace(" ", "")):
                    variants.append({"name": cells[0], "sku": cells[1].replace(" ", "")})

        products.append({
            "name": name,
            "group": ASSAY_GROUP_BY_NAME[name],
            "subcategory": "Truenat Assays",
            "description": description,
            "specifications": specifications,
            "kit_contents": kit_contents,
            "variants": variants,
            # Preserve the manufacturer's carousel order: the first asset is
            # the section's primary/hero image and later assets belong in the
            # product gallery.  Selecting the second image here previously
            # made many assays look like they shared one generic kit image.
            "image_url": images[0] if images else "",
            "gallery_urls": images[1:],
            "source_url": MOLBIO_PAGES["assays"],
        })
    return products


def solution_products():
    """Verified non-assay items listed on Molbio's five solution pages."""
    return [
        {
            "name": "Truelab® Uno Dx",
            "subcategory": "Truenat",
            "description": "A compact one-bay real-time micro-PCR analyser for low-volume laboratories and decentralized molecular testing.",
            "specifications": [["Testing bays", "1"], ["Throughput", "10–12 samples in 8 hours"], ["Access", "Single test workflow"]],
            "variants": [],
            "image_url": "https://www.molbiodiagnostics.com/wp-content/uploads/2025/04/uno.jpg",
            "source_url": MOLBIO_PAGES["truenat"],
            "code": "MOLBIO-TRUELAB-UNO-DX",
        },
        {
            "name": "Truelab® Duo",
            "subcategory": "Truenat",
            "description": "A dual-bay real-time micro-PCR analyser supporting random-access molecular testing.",
            "specifications": [["Testing bays", "2"], ["Throughput", "20–24 samples in 8 hours"], ["Access", "Random access"]],
            "variants": [],
            "image_url": "https://www.molbiodiagnostics.com/wp-content/uploads/2025/04/duo.jpg",
            "source_url": MOLBIO_PAGES["truenat"],
            "code": "MOLBIO-TRUELAB-DUO",
        },
        {
            "name": "Truelab® Quattro",
            "subcategory": "Truenat",
            "description": "A four-bay random-access real-time micro-PCR analyser for higher-throughput decentralized testing.",
            "specifications": [["Testing bays", "4"], ["Throughput", "40–48 samples in 8 hours"], ["Access", "Random access"]],
            "variants": [],
            "image_url": "https://www.molbiodiagnostics.com/wp-content/uploads/2025/04/Quattro.jpg",
            "source_url": MOLBIO_PAGES["truenat"],
            "code": "MOLBIO-TRUELAB-QUATTRO",
        },
        {
            "name": "iBreastExam®",
            "subcategory": "iBreastExam",
            "description": "A handheld, non-invasive breast health screening device that uses dynamic co-planar capacitive sensing to identify tissue abnormalities at the point of care.",
            "specifications": [["Method", "Dynamic co-planar capacitive sensing"], ["Operation", "Handheld, battery-powered and wireless"], ["Result", "Instant electronic result"], ["Imaging radiation", "None"]],
            "variants": [],
            "image_url": "https://www.molbiodiagnostics.com/wp-content/uploads/2025/09/Interface-new.jpg",
            "source_url": MOLBIO_PAGES["ibreastexam"],
            "code": "MOLBIO-IBREASTEXAM",
        },
        *PRORAD_ATLAS_PRODUCTS,
        *[
            {
                "name": name,
                "subcategory": "OptraScan",
                "description": description,
                "specifications": [["Slide capacity", capacity], ["Scan time (15 × 15 mm tissue)", scan_time], ["Weight", weight], ["Dimensions", dimensions]],
                "variants": [],
                "image_url": image,
                "source_url": MOLBIO_PAGES["optrascan"],
                "code": code,
            }
            for name, description, capacity, scan_time, weight, dimensions, image, code in (
                ("OS Ultra", "A high-capacity whole-slide scanner for scalable routine digital pathology workflows.", "80–480 slides", "30 s at 20×; 60 s at 40×", "106 kg", 'W 24.2 × L 37.4 × H 24.8 in', "https://www.molbiodiagnostics.com/wp-content/uploads/2025/12/os-ultra-image-1.jpg", "MOLBIO-OPTRASCAN-OS-ULTRA"),
                ("OS - Lite", "A compact 15-slide whole-slide scanner for routine digital pathology.", "15 slides", "40 s at 20×; 90 s at 40×", "25 kg", 'W 11.2 × L 17.3 × H 15.7 in', "https://www.molbiodiagnostics.com/wp-content/uploads/2025/12/os-lite-image.jpg", "MOLBIO-OPTRASCAN-OS-LITE"),
                ("OS - SiX", "A six-slide whole-slide scanner for compact digital pathology installations.", "6 slides", "120 s at 20×; 240 s at 40×", "25 kg", 'W 11.6 × L 19.5 × H 17.3 in', "https://www.molbiodiagnostics.com/wp-content/uploads/2025/12/os-six-image.jpg", "MOLBIO-OPTRASCAN-OS-SIX"),
                ("OS - FS", "A six-slide scanner configured for frozen-section digital pathology workflows.", "6 slides", "120 s at 20×; 240 s at 40×", "25 kg", 'W 11.6 × L 19.5 × H 17.3 in', "https://www.molbiodiagnostics.com/wp-content/uploads/2025/12/os-fs-image.jpg", "MOLBIO-OPTRASCAN-OS-FS"),
                ("OS - Fli", "A high-capacity fluorescence whole-slide scanner for digital pathology applications.", "80–480 slides", "Under 2 min at 40×", "106 kg", 'W 24.2 × L 37.4 × H 24.8 in', "https://www.molbiodiagnostics.com/wp-content/uploads/2025/12/os-fli-image.jpg", "MOLBIO-OPTRASCAN-OS-FLI"),
            )
        ],
    ]


def fetch_molbio_pages():
    pages = {}
    context = molbio_ssl_context()
    for key, url in MOLBIO_PAGES.items():
        request = Request(url, headers={"User-Agent": "Somlab catalogue importer/1.0"})
        with urlopen(request, timeout=60, context=context) as response:
            pages[key] = response.read().decode("utf-8", errors="replace")
    return pages


def build_molbio_catalogue(pages):
    return solution_products() + parse_truenat_assays(pages["assays"])
