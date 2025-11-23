# Generated manually to remove badge system and scout ranks

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0021_teacher_role_changes'),
    ]

    operations = [
        # Drop badge-related tables using raw SQL (safer for complex removals)
        migrations.RunSQL(
            sql="""
                DROP TABLE IF EXISTS accounts_userbadge;
                DROP TABLE IF EXISTS accounts_badge;
                DROP TABLE IF EXISTS accounts_batchstudentdata;
                DROP TABLE IF EXISTS accounts_batchregistration;
            """,
            reverse_sql="",  # Cannot reverse
        ),
        
        # Update role field choices (this is metadata only, no DB change needed)
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[('scout', 'Scout'), ('teacher', 'Teacher'), ('admin', 'Administrator')],
                default='scout',
                help_text='Scout (member), Teacher, or Administrator',
                max_length=30,
                verbose_name='User Role'
            ),
        ),
        
        migrations.AlterField(
            model_name='user',
            name='rank',
            field=models.CharField(
                choices=[('scout', 'Scout'), ('teacher', 'Teacher'), ('admin', 'Administrator')],
                default='scout',
                help_text='DEPRECATED: Use \'role\' field instead',
                max_length=30
            ),
        ),
    ]
