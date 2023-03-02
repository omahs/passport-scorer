# Generated by Django 4.1.6 on 2023-03-01 23:25

import account.deduplication
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0008_community_use_case"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="community",
            name="rules",
        ),
        migrations.AddField(
            model_name="community",
            name="rule",
            field=models.CharField(
                choices=[("LIFO", "LIFO"), ("FIFO", "FIFO")],
                default=account.deduplication.Rules["LIFO"],
                max_length=100,
            ),
        ),
    ]
