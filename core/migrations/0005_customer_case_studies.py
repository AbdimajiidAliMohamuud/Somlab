from django.db import migrations, models
import django.db.models.deletion


def move_legacy_media_to_projects(apps, schema_editor):
    CustomerMedia = apps.get_model("core", "CustomerMedia")
    CustomerProject = apps.get_model("core", "CustomerProject")
    CustomerProjectMedia = apps.get_model("core", "CustomerProjectMedia")

    for customer_id in CustomerMedia.objects.order_by().values_list(
        "customer_id", flat=True
    ).distinct():
        project = CustomerProject.objects.create(
            customer_id=customer_id,
            title="Completed work",
        )
        for item in CustomerMedia.objects.filter(customer_id=customer_id):
            CustomerProjectMedia.objects.create(
                project_id=project.pk,
                file=item.file.name,
                media_type=item.media_type,
                display_order=item.display_order,
            )


def restore_legacy_media(apps, schema_editor):
    CustomerMedia = apps.get_model("core", "CustomerMedia")
    CustomerProjectMedia = apps.get_model("core", "CustomerProjectMedia")

    for item in CustomerProjectMedia.objects.select_related("project"):
        CustomerMedia.objects.create(
            customer_id=item.project.customer_id,
            file=item.file.name,
            media_type=item.media_type,
            display_order=item.display_order,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0005_microbiology_products_and_on_request"),
        ("core", "0004_customer_optional_display_order"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="description",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="customer",
            name="facebook_url",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="customer",
            name="instagram_url",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="customer",
            name="linkedin_url",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="customer",
            name="other_url",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="customer",
            name="youtube_url",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="customer",
            name="products",
            field=models.ManyToManyField(
                blank=True,
                related_name="customers",
                to="catalog.product",
            ),
        ),
        migrations.CreateModel(
            name="CustomerProject",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("description", models.TextField(blank=True)),
                ("date", models.DateField(blank=True, null=True)),
                ("display_order", models.PositiveSmallIntegerField(blank=True, default=0)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="projects", to="core.customer")),
            ],
            options={"ordering": ("display_order", "-date", "id")},
        ),
        migrations.CreateModel(
            name="CustomerProjectMedia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to="customers/projects/")),
                ("media_type", models.CharField(choices=[("image", "Image"), ("video", "Video")], max_length=10)),
                ("display_order", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="media", to="core.customerproject")),
            ],
            options={
                "verbose_name_plural": "customer project media",
                "ordering": ("display_order", "id"),
            },
        ),
        migrations.RunPython(move_legacy_media_to_projects, restore_legacy_media),
        migrations.DeleteModel(name="CustomerMedia"),
    ]
