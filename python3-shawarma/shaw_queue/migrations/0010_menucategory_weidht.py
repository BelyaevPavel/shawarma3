# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-10-27 04:57


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shaw_queue', '0009_menucategory_eng_title'),
    ]

    operations = [
        migrations.AddField(
            model_name='menucategory',
            name='weidht',
            field=models.IntegerField(default=0, verbose_name='Weight'),
        ),
    ]
