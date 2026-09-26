"""Stable Microbiology solution-group configuration.

Product codes are unique catalogue identifiers, so the grouping remains stable
when product names or descriptions are edited in the dashboard.
"""

MICROBIOLOGY_CATEGORY_SLUG = "microbiology"

MICROBIOLOGY_GROUPS = (
    {
        "slug": "microscan-id-ast-panels",
        "title": "MicroScan ID/AST Panels",
        "description": (
            "Identification and antimicrobial susceptibility testing panels "
            "for dependable organism workflows."
        ),
        "product_codes": (
            "SL-CC-217",
            "SL-CC-218",
            "SL-CC-219",
            "SL-CC-220",
            "SL-CC-221",
        ),
    },
    {
        "slug": "microbiology-systems",
        "title": "Microbiology Systems",
        "description": (
            "Automated and benchtop systems that support efficient microbial "
            "identification and susceptibility testing."
        ),
        "product_codes": (
            "SL-CC-222",
            "SL-CC-223",
            "SL-CC-224",
            "SL-CC-225",
        ),
    },
    {
        "slug": "informatics",
        "title": "Informatics",
        "description": (
            "Software and connectivity tools supporting microbiology "
            "workflow data."
        ),
        "product_codes": (
            "SL-CC-226",
            "SL-CC-227",
        ),
    },
    {
        "slug": "microbiology-automation",
        "title": "Microbiology Automation",
        "description": (
            "Automation solutions designed for consistent, efficient "
            "microbiology workflows."
        ),
        "product_codes": (
            "SL-CC-228",
            "SL-CC-229",
        ),
    },
)
