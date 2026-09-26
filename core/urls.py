from django.urls import path
from . import views
from .customer_video_views import customer_video_source

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("services/", views.services, name="services"),
    path("services/<slug:slug>/", views.service_detail, name="service_detail"),
    path("partners/", views.partners, name="partners"),
    path("customers/", views.customers, name="customers"),
    path("customers/<slug:slug>/", views.customer_detail, name="customer_detail"),
    path("customers/<slug:slug>/videos/<int:pk>/", customer_video_source, name="customer_video_source"),
    path("contact/", views.contact, name="contact"),
    path("register/", views.register, name="register"),
]
