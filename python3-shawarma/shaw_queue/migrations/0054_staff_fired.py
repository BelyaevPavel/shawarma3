# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2021-09-19 16:09
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shaw_queue', '0053_order_is_preorder'),
    ]

    operations = [
        migrations.AddField(
            model_name='staff',
            name='fired',
            field=models.BooleanField(default='False'),
        ),
    ]
