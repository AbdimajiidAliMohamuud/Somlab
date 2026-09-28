from functools import wraps

from botocore.exceptions import BotoCoreError, ClientError
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from catalog.models import Category, Product, ProductSubcategory
from core.models import (
    AboutPageContent, ContactPageContent, ContactMessage, Customer,
    CustomerProject, CustomerProjectMedia, Partner, Service,
)
from orders.models import ProductInquiry
from .forms import (
    AboutPageContentForm, ContactPageContentForm,
    AdminUserCreateForm, AdminUserUpdateForm, CategoryForm,
    CustomerForm, CustomerProjectForm, CustomerProjectMediaForm, PartnerForm, ProductForm,
    ProductSubcategoryForm, ServiceForm, InquiryUpdateForm,
)


def admin_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if (
            not request.user.is_authenticated
            or not request.user.is_active
            or not request.user.is_staff
        ):
            return redirect("admin_login")
        return view(request, *args, **kwargs)
    return wrapped


@admin_required
def overview(request):
    inquiries = ProductInquiry.objects.select_related("product")
    stats = {
        "products": Product.objects.filter(is_active=True).count(),
        "categories": Category.objects.filter(is_active=True).count(),
        "unread_messages": ContactMessage.objects.filter(is_read=False).count(),
        "new_inquiries": inquiries.filter(status="new").count(),
        "active_inquiries": inquiries.exclude(status__in=["responded", "closed"]).count(),
    }
    status_counts = dict(
        inquiries.values_list("status").annotate(count=Count("id"))
    )
    return render(request, "dashboard/overview.html", {
        "stats": stats,
        "recent_inquiries": inquiries[:8],
        "status_counts": status_counts,
    })


@admin_required
def inquiry_list(request):
    inquiries = ProductInquiry.objects.select_related("product")
    status = request.GET.get("status", "")
    query = request.GET.get("q", "").strip()
    valid_statuses = {value for value, _ in ProductInquiry.STATUS_CHOICES}
    if status in valid_statuses:
        inquiries = inquiries.filter(status=status)
    else:
        status = ""
    if query:
        inquiries = inquiries.filter(
            Q(inquiry_number__icontains=query)
            | Q(full_name__icontains=query)
            | Q(organization__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
            | Q(product_name__icontains=query)
            | Q(product_code__icontains=query)
        )
    return render(request, "dashboard/inquiry_list.html", {
        "inquiries": inquiries,
        "status": status,
        "query": query,
        "statuses": ProductInquiry.STATUS_CHOICES,
    })


@admin_required
def inquiry_detail(request, inquiry_number):
    inquiry = get_object_or_404(
        ProductInquiry.objects.select_related("product"),
        inquiry_number=inquiry_number,
    )
    form = InquiryUpdateForm(request.POST or None, instance=inquiry)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Inquiry {inquiry.inquiry_number} was updated.")
        return redirect(
            "dashboard_inquiry_detail",
            inquiry_number=inquiry.inquiry_number,
        )
    return render(request, "dashboard/inquiry_detail.html", {
        "inquiry": inquiry,
        "form": form,
    })


@admin_required
def messages_list(request):
    messages_qs = ContactMessage.objects.all()
    return render(request, "dashboard/messages.html", {"contact_messages": messages_qs})


@admin_required
def message_detail(request, pk):
    item = get_object_or_404(ContactMessage, pk=pk)
    if not item.is_read:
        item.is_read = True
        item.save(update_fields=["is_read"])
    return render(request, "dashboard/message_detail.html", {"item": item})


def _edit_page_content(request, model, form_class, title, url_name):
    content, _ = model.objects.get_or_create(pk=1)
    form = form_class(request.POST or None, instance=content)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{title} content was updated.")
        return redirect(url_name)
    return render(request, "dashboard/page_content_form.html", {
        "form": form,
        "title": title,
    })


@admin_required
def about_content(request):
    return _edit_page_content(
        request, AboutPageContent, AboutPageContentForm,
        "About Us", "dashboard_about_content",
    )


@admin_required
def contact_content(request):
    return _edit_page_content(
        request, ContactPageContent, ContactPageContentForm,
        "Contact Us", "dashboard_contact_content",
    )


def _save_form(request, form_class, template_title, success_name, instance=None):
    form = form_class(request.POST or None, request.FILES or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        item = form.save()
        messages.success(request, f"{item} was saved.")
        return redirect(success_name)
    return render(request, "dashboard/manage_form.html", {
        "form": form,
        "title": template_title,
        "is_editing": instance is not None,
        "cancel_url_name": success_name,
    })


def _delete_item(request, item, type_name, success_name):
    if request.method == "POST":
        try:
            label = str(item)
            item.delete()
            messages.success(request, f"{type_name} “{label}” was deleted.")
        except ProtectedError:
            messages.error(
                request,
                f"This {type_name.lower()} cannot be deleted because products still use it.",
            )
        return redirect(success_name)
    return render(request, "dashboard/confirm_delete.html", {
        "item": item, "type_name": type_name, "cancel_url_name": success_name,
    })


def _save_customer_form(request, template_title, instance=None):
    form = CustomerForm(
        request.POST or None,
        request.FILES or None,
        instance=instance,
    )
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                customer = form.save()
        except (BotoCoreError, OSError):
            form.add_error(
                None,
                "Customer details could not be saved because media storage is "
                "temporarily unavailable. Existing logo and project media were "
                "preserved. Please try the upload again later.",
            )
        else:
            messages.success(request, f"{customer} was saved.")
            return redirect("dashboard_customers")
    return render(request, "dashboard/manage_form.html", {
        "form": form,
        "title": template_title,
        "is_editing": instance is not None,
        "cancel_url_name": "dashboard_customers",
    })


@admin_required
def product_list(request):
    products = Product.objects.select_related("category", "subcategory")
    query = request.GET.get("q", "").strip()
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(product_code__icontains=query) |
            Q(brand__icontains=query)
        )
    return render(request, "dashboard/product_list.html", {"products": products, "query": query})


@admin_required
def product_create(request):
    return _save_form(request, ProductForm, "Add product", "dashboard_products")


@admin_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return _save_form(request, ProductForm, f"Edit {product.name}", "dashboard_products", product)


@admin_required
def product_delete(request, pk):
    return _delete_item(request, get_object_or_404(Product, pk=pk), "Product", "dashboard_products")


@admin_required
def category_list(request):
    return render(request, "dashboard/category_list.html", {
        "categories": Category.objects.annotate(product_total=Count("products"))
    })


@admin_required
def category_create(request):
    return _save_form(request, CategoryForm, "Add category", "dashboard_categories")


@admin_required
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    return _save_form(request, CategoryForm, f"Edit {category.name}", "dashboard_categories", category)


@admin_required
def category_delete(request, pk):
    return _delete_item(request, get_object_or_404(Category, pk=pk), "Category", "dashboard_categories")


@admin_required
def subcategory_list(request):
    return render(request, "dashboard/subcategory_list.html", {
        "subcategories": ProductSubcategory.objects.select_related(
            "category"
        ).annotate(product_total=Count("products")),
    })


@admin_required
def subcategory_create(request):
    return _save_subcategory_form(
        request,
        "Add product subcategory",
    )


@admin_required
def subcategory_edit(request, pk):
    subcategory = get_object_or_404(ProductSubcategory, pk=pk)
    return _save_subcategory_form(
        request,
        f"Edit {subcategory.name}",
        subcategory,
    )


def _save_subcategory_form(request, template_title, instance=None):
    form = ProductSubcategoryForm(
        request.POST or None,
        request.FILES or None,
        instance=instance,
    )
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                subcategory = form.save()
        except (BotoCoreError, OSError):
            form.add_error(
                None,
                "The subcategory could not be saved because image storage "
                "is temporarily unavailable. Please try again later.",
            )
        else:
            messages.success(request, f"{subcategory} was saved.")
            return redirect("dashboard_subcategories")
    return render(request, "dashboard/manage_form.html", {
        "form": form,
        "title": template_title,
        "is_editing": instance is not None,
        "cancel_url_name": "dashboard_subcategories",
    })


@admin_required
def subcategory_delete(request, pk):
    return _delete_item(
        request,
        get_object_or_404(ProductSubcategory, pk=pk),
        "Product subcategory",
        "dashboard_subcategories",
    )


@admin_required
def partner_list(request):
    return render(request, "dashboard/partner_list.html", {"partners": Partner.objects.all()})


@admin_required
def partner_create(request):
    return _save_form(request, PartnerForm, "Add partner", "dashboard_partners")


@admin_required
def partner_edit(request, pk):
    partner = get_object_or_404(Partner, pk=pk)
    return _save_form(request, PartnerForm, f"Edit {partner.name}", "dashboard_partners", partner)


@admin_required
def partner_delete(request, pk):
    return _delete_item(request, get_object_or_404(Partner, pk=pk), "Partner", "dashboard_partners")


@admin_required
def customer_list(request):
    return render(request, "dashboard/customer_list.html", {
        "customers": Customer.objects.annotate(project_total=Count("projects", distinct=True)),
    })


@admin_required
def customer_create(request):
    return _save_customer_form(request, "Add customer")


@admin_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    return _save_customer_form(request, f"Edit {customer.name}", customer)


@admin_required
def customer_delete(request, pk):
    return _delete_item(
        request,
        get_object_or_404(Customer, pk=pk),
        "Customer",
        "dashboard_customers",
    )


@admin_required
def customer_project_list(request, customer_pk):
    customer = get_object_or_404(Customer, pk=customer_pk)
    return render(request, "dashboard/customer_project_list.html", {
        "customer": customer,
        "projects": customer.projects.annotate(media_total=Count("media")),
    })


def _save_customer_project_form(request, customer, template_title, instance=None):
    is_editing = instance is not None
    if instance is None:
        instance = CustomerProject(customer=customer)
    form = CustomerProjectForm(
        request.POST or None,
        request.FILES or None,
        instance=instance,
    )
    for error in getattr(request, "customer_upload_errors", []):
        form.add_error(None, error)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                project = form.save()
        except ValidationError as error:
            form.add_error(None, error)
        except (BotoCoreError, ClientError, OSError):
            form.add_error(
                None,
                "The project could not be saved because media storage is "
                "temporarily unavailable. Please try the upload again later.",
            )
        else:
            messages.success(request, f"{project.title} was saved.")
            return redirect("dashboard_customer_projects", customer_pk=customer.pk)
    return render(request, "dashboard/manage_form.html", {
        "form": form,
        "title": template_title,
        "is_editing": is_editing,
        "cancel_url": reverse(
            "dashboard_customer_projects", kwargs={"customer_pk": customer.pk}
        ),
    })


@admin_required
def customer_project_create(request, customer_pk):
    customer = get_object_or_404(Customer, pk=customer_pk)
    return _save_customer_project_form(
        request, customer, f"Add project for {customer.name}"
    )


@admin_required
def customer_project_edit(request, customer_pk, pk):
    customer = get_object_or_404(Customer, pk=customer_pk)
    project = get_object_or_404(CustomerProject, pk=pk, customer=customer)
    return _save_customer_project_form(
        request, customer, f"Edit {project.title}", project
    )


@admin_required
def customer_project_delete(request, customer_pk, pk):
    customer = get_object_or_404(Customer, pk=customer_pk)
    project = get_object_or_404(CustomerProject, pk=pk, customer=customer)
    success_url = reverse(
        "dashboard_customer_projects", kwargs={"customer_pk": customer.pk}
    )
    if request.method == "POST":
        label = project.title
        project.delete()
        messages.success(request, f"Project “{label}” was deleted.")
        return redirect(success_url)
    return render(request, "dashboard/confirm_delete.html", {
        "item": project,
        "type_name": "Project",
        "cancel_url": success_url,
    })


@admin_required
def customer_project_media_list(request, customer_pk, project_pk):
    customer = get_object_or_404(Customer, pk=customer_pk)
    project = get_object_or_404(
        CustomerProject,
        pk=project_pk,
        customer=customer,
    )
    return render(request, "dashboard/customer_project_media_list.html", {
        "customer": customer,
        "project": project,
        "media_items": project.media.all(),
    })


def _save_customer_project_media_form(
    request,
    customer,
    project,
    template_title,
    instance=None,
):
    is_editing = instance is not None
    if instance is None:
        instance = CustomerProjectMedia(project=project)
    form = CustomerProjectMediaForm(
        request.POST or None,
        request.FILES or None,
        instance=instance,
    )
    for error in getattr(request, "customer_upload_errors", []):
        form.add_error(None, error)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                media = form.save()
        except ValidationError as error:
            form.add_error(None, error)
        except (BotoCoreError, ClientError, OSError):
            form.add_error(
                None,
                "The media item could not be saved because storage is "
                "temporarily unavailable. Please try again later.",
            )
        else:
            messages.success(request, f"{media.get_media_type_display()} was saved.")
            return redirect(
                "dashboard_customer_project_media",
                customer_pk=customer.pk,
                project_pk=project.pk,
            )
    return render(request, "dashboard/manage_form.html", {
        "form": form,
        "title": template_title,
        "is_editing": is_editing,
        "cancel_url": reverse(
            "dashboard_customer_project_media",
            kwargs={"customer_pk": customer.pk, "project_pk": project.pk},
        ),
    })


@admin_required
def customer_project_media_create(request, customer_pk, project_pk):
    customer = get_object_or_404(Customer, pk=customer_pk)
    project = get_object_or_404(CustomerProject, pk=project_pk, customer=customer)
    return _save_customer_project_media_form(
        request,
        customer,
        project,
        f"Add media to {project.title}",
    )


@admin_required
def customer_project_media_edit(request, customer_pk, project_pk, pk):
    customer = get_object_or_404(Customer, pk=customer_pk)
    project = get_object_or_404(CustomerProject, pk=project_pk, customer=customer)
    media = get_object_or_404(CustomerProjectMedia, pk=pk, project=project)
    return _save_customer_project_media_form(
        request,
        customer,
        project,
        f"Edit media for {project.title}",
        media,
    )


@admin_required
def customer_project_media_delete(request, customer_pk, project_pk, pk):
    customer = get_object_or_404(Customer, pk=customer_pk)
    project = get_object_or_404(CustomerProject, pk=project_pk, customer=customer)
    media = get_object_or_404(CustomerProjectMedia, pk=pk, project=project)
    success_url = reverse(
        "dashboard_customer_project_media",
        kwargs={"customer_pk": customer.pk, "project_pk": project.pk},
    )
    if request.method == "POST":
        media.delete()
        messages.success(request, "Project media was deleted.")
        return redirect(success_url)
    return render(request, "dashboard/confirm_delete.html", {
        "item": media,
        "type_name": "Project media",
        "cancel_url": success_url,
    })


@admin_required
def service_list(request):
    return render(request, "dashboard/service_list.html", {"services": Service.objects.all()})


@admin_required
def service_create(request):
    return _save_form(request, ServiceForm, "Add service", "dashboard_services")


@admin_required
def service_edit(request, pk):
    service = get_object_or_404(Service, pk=pk)
    return _save_form(request, ServiceForm, f"Edit {service.name}", "dashboard_services", service)


@admin_required
def service_delete(request, pk):
    return _delete_item(request, get_object_or_404(Service, pk=pk), "Service", "dashboard_services")


@admin_required
def user_list(request):
    users = User.objects.all().order_by("-is_staff", "username")
    return render(request, "dashboard/user_list.html", {"users": users})


@admin_required
def user_create(request):
    return _save_form(request, AdminUserCreateForm, "Add user", "dashboard_users")


@admin_required
def user_edit(request, pk):
    item = get_object_or_404(User, pk=pk)
    form = AdminUserUpdateForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        if user.pk == request.user.pk:
            user.is_active = True
            user.is_staff = True
        user.save()
        messages.success(request, f"{user.username} was updated.")
        return redirect("dashboard_users")
    return render(request, "dashboard/manage_form.html", {
        "form": form, "title": f"Edit {item.username}",
        "is_editing": True, "cancel_url_name": "dashboard_users",
    })
