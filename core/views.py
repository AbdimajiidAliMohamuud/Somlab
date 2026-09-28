import hashlib

from django.contrib import messages
from django.contrib.auth import login, logout
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from catalog.scope import public_products
from .forms import AdminLoginForm, ContactForm, RegisterForm
from .models import AboutPageContent, ContactPageContent, Customer, CustomerProject, Partner, Service

HERO_IMAGE_NAMES = (
    "472810462_122191066214174861_7361353671595623629_n.jpg",
    "471471280_122188786328174861_5653736459606775729_n.jpg",
    "472027568_122188786934174861_1263058537599639747_n.jpg",
    "473280964_122191681514174861_6153930134110929263_n.jpg",
    "473570635_122191681862174861_2762880802754851474_n.jpg",
    "473615386_122191681778174861_5729472265126044793_n.jpg",
)

QUALITY_PARTNER_NAMES = (
    "Beckman Coulter",
    "ZEISS",
    "SD Biosensor",
    "Vatech Dental",
    "Molbio Diagnostics",
)

FEATURED_CUSTOMER_GALLERY_SLUGS = {
    "horyaal-hospital",
    "shaafi-hospital",
    "mogadishu-specialist-hospital",
    "marwo-fertility-center",
}


def active_partners():
    """Return the shared, ordered partner source used by public pages."""
    return Partner.objects.filter(is_active=True)


def active_customers():
    """Return the shared, ordered customer source used by public pages."""
    return Customer.objects.filter(is_active=True)


def home(request):
    product_count = public_products().count()
    partner_queryset = active_partners()
    active_services = Service.objects.filter(is_active=True)
    homepage_partners = list(partner_queryset)
    for partner in homepage_partners:
        partner.product_brand_slug = slugify(partner.name)
    quality_partner_map = {
        partner.name: partner for partner in homepage_partners
        if partner.name in QUALITY_PARTNER_NAMES
    }
    quality_partners = []
    for name in QUALITY_PARTNER_NAMES:
        partner = quality_partner_map.get(name)
        if partner is not None:
            partner.product_url = (
                f"{reverse('product_list')}?brand={partner.product_brand_slug}"
            )
            quality_partners.append(partner)

    return render(request, "core/home.html", {
        "hero_images": [
            default_storage.url(image_name) for image_name in HERO_IMAGE_NAMES
        ],
        "services": active_services[:3],
        "partners": homepage_partners,
        "quality_partners": quality_partners,
        "customers": active_customers(),
        "home_statistics": (
            {
                "label": "Laboratory Products",
                "value": product_count,
                "animate": True,
            },
            {
                "label": "International Brands",
                "value": partner_queryset.count(),
                "animate": True,
            },
            {
                "label": "Technical Services",
                "value": active_services.count(),
                "animate": True,
            },
            {
                "label": "Regional Support",
                "value": "East Africa",
                "animate": False,
            },
        ),
    })


def about(request):
    return render(request, "core/about.html", {
        "about_content": AboutPageContent.objects.first() or AboutPageContent(),
    })


def services(request):
    return render(request, "core/services.html", {
        "services": Service.objects.filter(is_active=True)
    })


def service_detail(request, slug):
    service = get_object_or_404(Service, slug=slug, is_active=True)
    return render(request, "core/service_detail.html", {"service": service})


def partners(request):
    return render(request, "core/partners.html", {
        "partners": active_partners()
    })


def customers(request):
    return render(request, "core/customers.html", {
        "customers": active_customers(),
    })


def customer_detail(request, slug):
    customer = get_object_or_404(
        Customer.objects.prefetch_related(
            Prefetch("products", queryset=public_products().select_related("category")),
            Prefetch(
                "projects",
                queryset=CustomerProject.objects.prefetch_related(
                    "products__category",
                    "media",
                ),
            ),
        ),
        slug=slug,
        is_active=True,
    )
    supplied_products = list(customer.products.all())
    projects = list(customer.projects.all())
    section_definitions = (
        ("installation", "Equipment installations"),
        ("project", "Completed projects"),
        ("service", "Technical and service work"),
        ("supply", "Product supply records"),
        ("other", "Other completed work"),
    )
    portfolio_sections = [
        {
            "slug": work_type,
            "title": title,
            "projects": [
                project for project in projects
                if project.work_type == work_type
            ],
        }
        for work_type, title in section_definitions
    ]
    portfolio_sections = [
        section for section in portfolio_sections if section["projects"]
    ]
    return render(request, "core/customer_detail.html", {
        "customer": customer,
        "supplied_products": supplied_products,
        "portfolio_sections": portfolio_sections,
        "project_count": len(projects),
        "is_featured_gallery": customer.slug in FEATURED_CUSTOMER_GALLERY_SLUGS,
    })


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Thank you. Your message has been sent to our team.")
        return redirect("contact")
    return render(request, "core/contact.html", {
        "form": form,
        "contact_content": ContactPageContent.objects.first() or ContactPageContent(),
    })


def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Your Somlab account is ready.")
        return redirect("home")
    return render(request, "registration/register.html", {"form": form})


def admin_login(request):
    if request.user.is_authenticated and request.user.is_active and request.user.is_staff:
        return redirect("dashboard")

    identifier = request.POST.get("username", "").strip().lower()
    client_address = request.META.get("REMOTE_ADDR", "unknown")
    rate_identity = hashlib.sha256(
        f"{client_address}:{identifier}".encode()
    ).hexdigest()
    rate_address = hashlib.sha256(client_address.encode()).hexdigest()
    rate_keys = (
        f"somlab-admin-login-ip:{rate_address}",
        f"somlab-admin-login-identity:{rate_identity}",
    )
    attempt_count = max(cache.get(key, 0) for key in rate_keys)

    form = AdminLoginForm(request, data=request.POST or None)
    status = 200
    if request.method == "POST" and attempt_count >= 5:
        form.add_error(
            None,
            "Too many sign-in attempts. Please wait 15 minutes and try again.",
        )
        status = 429
    elif request.method == "POST" and form.is_valid():
        cache.delete_many(rate_keys)
        login(request, form.get_user())
        if form.cleaned_data["remember_me"]:
            request.session.set_expiry(60 * 60 * 24 * 30)
        else:
            request.session.set_expiry(0)
        return redirect("dashboard")
    elif request.method == "POST":
        for rate_key in rate_keys:
            if not cache.add(rate_key, 1, timeout=60 * 15):
                try:
                    cache.incr(rate_key)
                except ValueError:
                    cache.set(rate_key, 1, timeout=60 * 15)

    return render(
        request,
        "registration/admin_login.html",
        {"form": form},
        status=status,
    )


@require_POST
def admin_logout(request):
    logout(request)
    return redirect("admin_login")
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect("dashboard")

    return render(request, "registration/admin_login.html", {"form": form})
