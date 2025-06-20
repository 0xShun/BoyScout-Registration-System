# Generated by Django 5.1.2 on 2025-06-12 17:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='user',
            options={'permissions': [('can_manage_scouts', 'Can manage scouts'), ('can_manage_troop_leaders', 'Can manage troop leaders'), ('can_manage_committee', 'Can manage committee members'), ('can_manage_parents', 'Can manage parents/guardians')], 'verbose_name': 'user', 'verbose_name_plural': 'users'},
        ),
        migrations.AddField(
            model_name='user',
            name='verification_code',
            field=models.CharField(blank=True, max_length=6, null=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='date_joined',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='rank',
            field=models.CharField(choices=[('none', 'No Rank'), ('scout', 'Scout'), ('senior_scout', 'Senior Scout'), ('patrol_leader', 'Patrol Leader'), ('assistant_patrol_leader', 'Assistant Patrol Leader'), ('second_class', 'Second Class'), ('first_class', 'First Class'), ('star', 'Star'), ('life', 'Life'), ('eagle', 'Eagle')], default='scout', max_length=30),
        ),
    ]
