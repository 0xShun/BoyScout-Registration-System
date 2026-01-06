# Generated manually for is_published field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('announcements', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='announcement',
            name='is_published',
            field=models.BooleanField(default=True, help_text='If false, announcement is hidden from regular users.'),
        ),
    ]
