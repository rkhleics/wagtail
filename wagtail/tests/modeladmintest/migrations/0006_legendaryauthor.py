# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-12-10 10:56
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('modeladmintest', '0005_book_cover_image'),
    ]

    operations = [
        migrations.CreateModel(
            name='LegendaryAuthor',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
            },
            bases=('modeladmintest.author',),
        ),
    ]
