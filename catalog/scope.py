from .models import Category, Product


PUBLIC_CATEGORY_DEFINITIONS = (
    (
        "Chemistry",
        "chemistry",
        "Analysers, reagents, calibrators and controls for routine chemistry.",
    ),
    (
        "Immunoassay",
        "immunoassay",
        "Immunoassay products for infectious disease, autoimmunity and routine diagnostics.",
    ),
    (
        "Hematology",
        "hematology",
        "Hematology analysers, reagents and supporting laboratory products.",
    ),
    (
        "Urinalysis",
        "urinalysis",
        "Urinalysis analysers, test strips and supporting diagnostic products.",
    ),
    (
        "Microbiology",
        "microbiology",
        "Culture, susceptibility testing, ESR and microbiology laboratory equipment.",
    ),
    (
        "Blood Banking",
        "blood-banking",
        "Blood storage, grouping, separation and donor-care products.",
    ),
    (
        "ZEISS Light Microscopes",
        "light-microscopes",
        "ZEISS stereo and light microscopy solutions for laboratory, research and education.",
    ),
    (
        "Eschweiler ABG",
        "eschweiler-abg",
        "ESCHWEILER blood gas, electrolyte and metabolite analysers, system components and consumables.",
    ),
    (
        "AMA Helic UBT Reader",
        "ama-helic-ubt-reader",
        "Non-invasive Helicobacter pylori breath-testing equipment from AMA-Med.",
    ),
    (
        "Vatech Dental",
        "vatech-dental",
        "Vatech dental imaging systems and intraoral imaging solutions.",
    ),
    (
        "Polycheck",
        "polycheck",
        "Polycheck® multiparameter in vitro diagnostic panels for allergy, autoimmune and veterinary testing.",
    ),
    (
        "Molbio",
        "molbio",
        "Molbio Diagnostics point-of-care molecular diagnostics, screening, portable radiology and digital pathology solutions.",
    ),
    (
        "SD Biosensor Rapid Test",
        "sd-biosensor",
        "Selected STANDARD Q rapid diagnostic tests from SD BIOSENSOR for malaria, hepatitis and blood-borne infections.",
    ),
    (
        "Semen Analyzers (SQA)",
        "medical-electronic-systems",
        "Medical Electronic Systems automated semen-analysis equipment for clinical and andrology laboratories.",
    ),
)

PUBLIC_CATEGORY_SLUGS = tuple(item[1] for item in PUBLIC_CATEGORY_DEFINITIONS)


def public_categories():
    return Category.objects.filter(
        is_active=True,
        slug__in=PUBLIC_CATEGORY_SLUGS,
    )


def public_products():
    return Product.objects.filter(
        is_active=True,
        category__is_active=True,
        category__slug__in=PUBLIC_CATEGORY_SLUGS,
    )
