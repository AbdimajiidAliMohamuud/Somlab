from catalog.navigation import product_navigation_groups


def site_context(request):
    return {
        "product_navigation_groups": product_navigation_groups(),
    }
