from django.utils.text import slugify


LABORATORY_DISPLAY_LABELS = {
    "polycheck": "Allergy and Autoimmune Tests",
    "molbio": "Truenat® Real-Time PCR",
    "medical-electronic-systems": "Semen Analyzers (SQA)",
    "ama-helic-ubt-reader": "Urea Breath Test",
    "sd-biosensor": "SD Biosensor Rapid Test",
    "eschweiler-abg": "Eschweiler ABG",
    "vatech-dental": "Dental Imaging",
}

LABORATORY_LABEL_ALIASES = {
    "molbio-diagnostics": "molbio",
    "medical-electronic-system": "medical-electronic-systems",
}


def catalogue_display_label(value, fallback=""):
    """Return the shared public catalogue label without changing stored data."""
    key = slugify(value or "")
    key = LABORATORY_LABEL_ALIASES.get(key, key)
    return LABORATORY_DISPLAY_LABELS.get(key, fallback or value)
