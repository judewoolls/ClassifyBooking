# Generated by Django 4.2.17 on 2025-06-18 22:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0012_company_auto_updates'),
    ]

    operations = [
        migrations.AlterField(
            model_name='company',
            name='auto_updates',
            field=models.BooleanField(default=True),
        ),
    ]
