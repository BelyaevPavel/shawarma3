# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-12-10 05:22


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shaw_queue', '0016_order_servery'),
    ]

    operations = [
        migrations.AddField(
            model_name='ordercontent',
            name='quantity',
            field=models.FloatField(default=1.0, verbose_name='Quantity'),
        ),
    ]
