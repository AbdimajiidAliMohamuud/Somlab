from django.db import migrations, models


INITIAL_TESTIMONIALS = (
    {
        "customer_name": "Laboratory Manager",
        "organization": "Private Diagnostic Laboratory",
        "review": (
            "Somlab made it easier to compare suitable laboratory systems and "
            "supported our team with clear, practical guidance."
        ),
        "rating": 5,
        "display_order": 1,
    },
    {
        "customer_name": "Biomedical Engineer",
        "organization": "Regional Hospital",
        "review": (
            "The combination of dependable equipment, installation support and "
            "responsive follow-up gave our technical team confidence."
        ),
        "rating": 5,
        "display_order": 2,
    },
    {
        "customer_name": "Procurement Lead",
        "organization": "Healthcare Programme",
        "review": (
            "Product information was clear, communication was timely and the "
            "ordering process stayed straightforward from enquiry to delivery."
        ),
        "rating": 5,
        "display_order": 3,
    },
)


def create_initial_testimonials(apps, schema_editor):
    Testimonial = apps.get_model("core", "Testimonial")
    for testimonial in INITIAL_TESTIMONIALS:
        Testimonial.objects.update_or_create(
            customer_name=testimonial["customer_name"],
            organization=testimonial["organization"],
            defaults={
                "review": testimonial["review"],
                "rating": testimonial["rating"],
                "display_order": testimonial["display_order"],
                "is_active": True,
            },
        )


def remove_initial_testimonials(apps, schema_editor):
    Testimonial = apps.get_model("core", "Testimonial")
    Testimonial.objects.filter(
        customer_name__in=[item["customer_name"] for item in INITIAL_TESTIMONIALS],
        organization__in=[item["organization"] for item in INITIAL_TESTIMONIALS],
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="Testimonial",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("customer_name", models.CharField(max_length=120)),
                ("organization", models.CharField(max_length=160)),
                ("review", models.TextField()),
                (
                    "rating",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        choices=[(1, "1"), (2, "2"), (3, "3"), (4, "4"), (5, "5")],
                        null=True,
                    ),
                ),
                ("display_order", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ("display_order", "id")},
        ),
        migrations.RunPython(
            create_initial_testimonials,
            remove_initial_testimonials,
        ),
    ]
