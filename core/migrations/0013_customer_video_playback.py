from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0012_restore_five_partners")]
    operations = [
        migrations.AddField(
            model_name="customerprojectmedia", name="playback_file",
            field=models.FileField(blank=True, upload_to="customers/projects/playback/"),
        ),
        migrations.AddField(
            model_name="customerprojectmedia", name="video_poster",
            field=models.ImageField(blank=True, upload_to="customers/projects/posters/"),
        ),
    ]
