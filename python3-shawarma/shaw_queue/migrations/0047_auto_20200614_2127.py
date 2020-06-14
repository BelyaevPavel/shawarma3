# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2020-06-14 16:27
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shaw_queue', '0046_auto_20200428_0013'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='discounted_total',
            field=models.FloatField(default=0, validators=[django.core.validators.MinValueValidator(0, "Discounted total can't be negative!")], verbose_name='Сумма с учётом скидки'),
        ),
        migrations.AlterField(
            model_name='order',
            name='discount',
            field=models.FloatField(default=0, validators=[django.core.validators.MinValueValidator(0, "Discount can't be negative!"), django.core.validators.MaxValueValidator(100, "Discount can't be greater then 100!")]),
        ),
        migrations.AlterField(
            model_name='order',
            name='total',
            field=models.FloatField(default=0, validators=[django.core.validators.MinValueValidator(0, "Total can't be negative!")], verbose_name='Сумма'),
        ),
    ]
