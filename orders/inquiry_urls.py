from django.urls import path

from . import views


urlpatterns = [
    path("inquiry/", views.product_inquiry, name="product_inquiry"),
    path(
        "inquiry/success/",
        views.product_inquiry_success,
        name="product_inquiry_success",
    ),
]
