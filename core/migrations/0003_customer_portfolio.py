import django.db.models.deletion
from django.db import migrations, models


INITIAL_CUSTOMERS = (
    ("Horyaal Hospital", "horyaal-hospital"),
    ("Shaafi Hospital", "shaafi-hospital"),
    ("Mogadishu Specialist Hospital", "mogadishu-specialist-hospital"),
    ("Kalkaal Hospital", "kalkaal-hospital"),
    ("Hodan Hospital", "hodan-hospital"),
    ("SOS Children's Village", "sos-childrens-village"),
    ("Marwo Fertility Center", "marwo-fertility-center"),
    ("Wadajir Hospital", "wadajir-hospital"),
    ("Baraka Hospital", "baraka-hospital"),
    ("Jazeera Hospital", "jazeera-hospital"),
    ("Nova Diagnostic Center", "nova-diagnostic-center"),
    ("Sahan Diagnostic Center", "sahan-diagnostic-center"),
    ("Dhiblawe Liver and Digestive Center", "dhiblawe-liver-and-digestive-center"),
    ("Ladnan Hospital", "ladnan-hospital"),
    ("Dalmar Hospital", "dalmar-hospital"),
)


def create_initial_customers(apps, schema_editor):
    Customer = apps.get_model("core", "Customer")
    for display_order, (name, slug) in enumerate(INITIAL_CUSTOMERS, start=1):
        Customer.objects.update_or_create(
            slug=slug,
            defaults={
                "name": name,
                "display_order": display_order,
                "is_active": True,
            },
        )


def remove_initial_customers(apps, schema_editor):
    Customer = apps.get_model("core", "Customer")
    Customer.objects.filter(
        slug__in=[slug for _, slug in INITIAL_CUSTOMERS],
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0002_testimonial")]

    operations = [
        migrations.CreateModel(
            name="Customer",
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
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(unique=True)),
                ("logo", models.ImageField(blank=True, upload_to="customers/logos/")),
                ("website", models.URLField(blank=True)),
                ("short_description", models.TextField(blank=True)),
                ("display_order", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ("display_order", "name")},
        ),
        migrations.CreateModel(
            name="CustomerMedia",
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
                ("file", models.FileField(upload_to="customers/projects/")),
                (
                    "media_type",
                    models.CharField(
                        choices=[("image", "Image"), ("video", "Video")],
                        max_length=10,
                    ),
                ),
                ("display_order", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="media",
                        to="core.customer",
                    ),
                ),
            ],
            options={
                "ordering": ("display_order", "id"),
                "verbose_name_plural": "customer media",
            },
        ),
        migrations.RunPython(create_initial_customers, remove_initial_customers),
    ]
