from django.db import migrations, models


CUSTOMERS = (
    (1, "horyaal-hospital", "Horyaal Hospital", "https://www.horyaalhospital.so/", ""),
    (2, "shaafi-hospital", "Shaafi Hospital", "https://shaafihospital.so/", ""),
    (3, "mogadishu-specialist-hospital", "Mogadishu Specialist Hospital", "", "https://www.facebook.com/mshospital.so/"),
    (4, "kalkaal-hospital", "Kalkaal Hospital", "https://kalkaalhospital.so/en", ""),
    (5, "hodan-hospital", "Hodan Hospital", "https://hodanhospital.com/", ""),
    (6, "sos-childrens-village", "SOS Children’s Village", "https://www.sos-somalia.org/", ""),
    (7, "marwo-fertility-center", "Marwo Fertility Center", "https://marwafertility.com/", ""),
    (8, "wadajir-hospital", "Wadajir Hospital", "https://wadajirhospital.com/", ""),
    (9, "baraka-hospital", "Baraka Hospital", "", "https://www.facebook.com/albarakathospital/"),
    (10, "jazeera-hospital", "Jazeera Hospital", "https://jazeerahospital.so/", ""),
    (11, "nova-diagnostic-center", "Nova Diagnostic Center", "https://nova.com.so/", ""),
    (12, "sahan-diagnostic-center", "Sahan Diagnostic Center", "https://sahandiagnostic.com/", ""),
    (13, "dhiblawe-liver-and-digestive-center", "Dhiblaawe Liver and Digestive Center", "", "https://www.facebook.com/dhiblaaweclinic/"),
    (14, "ladnan-hospital", "Ladnan Hospital", "https://www.ladnan-hospital.com/", ""),
    (15, "dalmar-hospital", "Dalmar Hospital", "https://dalmarhospital.so/", ""),
)


def configure_customer_links(apps, schema_editor):
    Customer = apps.get_model("core", "Customer")
    for order, slug, name, website, facebook_url in CUSTOMERS:
        Customer.objects.update_or_create(
            slug=slug,
            defaults={
                "name": name,
                "website": website,
                "facebook_url": facebook_url,
                "display_order": order,
                "is_active": True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0023_remove_partner_catalogue_entries"),
        ("core", "0010_alter_partner_menu_order"),
    ]

    operations = [
        migrations.AddField(
            model_name="customerproject",
            name="work_type",
            field=models.CharField(
                choices=[
                    ("supply", "Products supplied"),
                    ("installation", "Equipment installed"),
                    ("project", "Project completed"),
                    ("service", "Service delivered"),
                    ("other", "Other completed work"),
                ],
                default="project",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="customerproject",
            name="products",
            field=models.ManyToManyField(
                blank=True,
                help_text="Existing Somlab products supplied or installed in this project.",
                related_name="customer_projects",
                to="catalog.product",
            ),
        ),
        migrations.AlterField(
            model_name="customerprojectmedia",
            name="file",
            field=models.FileField(blank=True, upload_to="customers/projects/"),
        ),
        migrations.AddField(
            model_name="customerprojectmedia",
            name="video_url",
            field=models.URLField(
                blank=True,
                help_text="Optional YouTube, Vimeo, or other external video URL.",
            ),
        ),
        migrations.AddField(
            model_name="customerprojectmedia",
            name="caption",
            field=models.CharField(blank=True, max_length=240),
        ),
        migrations.AddField(
            model_name="customerprojectmedia",
            name="description",
            field=models.TextField(blank=True),
        ),
        migrations.RunPython(configure_customer_links, migrations.RunPython.noop),
    ]
