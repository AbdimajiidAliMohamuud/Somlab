from django.urls import path
from . import views

urlpatterns = [
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/<int:product_id>/", views.cart_add, name="cart_add"),
    path("cart/update/<str:line_key>/", views.cart_update, name="cart_update"),
    path("cart/remove/<str:line_key>/", views.cart_remove, name="cart_remove"),
    path("checkout/", views.checkout, name="checkout"),
    path("success/", views.order_success, name="order_success"),
]
