from django.urls import path
from . import views

urlpatterns = [
    path("", views.product_list, name="product_list"),
    path(
        "group/<slug:slug>/",
        views.equipment_group_products,
        name="equipment_group_products",
    ),
    path("suggestions/", views.product_suggestions, name="product_suggestions"),
    path(
        "zeiss-microscopy/",
        views.zeiss_microscopy,
        name="zeiss_microscopy",
    ),
    path(
        "microbiology/",
        views.microbiology_landing,
        name="microbiology_landing",
    ),
    path(
        "vatech/<slug:slug>",
        views.vatech_category,
        name="vatech_category",
    ),
    path(
        "category/<slug:category_slug>/<slug:slug>/",
        views.subcategory_detail,
        name="subcategory_detail",
    ),
    path("category/<slug:slug>/", views.category_detail, name="category_detail"),
    path("<slug:slug>/", views.product_detail, name="product_detail"),
]
