# -*- coding: utf-8 -*-

from django.core.validators import MinValueValidator
from django.contrib.auth.models import User
from django.db import models


# Create your models here.
class MenuCategory(models.Model):
    title = models.CharField(max_length=20)
    eng_title = models.CharField(max_length=20)
    weight = models.IntegerField(verbose_name="Weight", default=0)
    hidden = models.BooleanField(default="False")

    def __str__(self):
        return "{}".format(self.title)

    def __unicode__(self):
        return "{}".format(self.title)


class StaffCategory(models.Model):
    title = models.CharField(max_length=20)

    def __str__(self):
        return "{}".format(self.title)

    def __unicode__(self):
        return "{}".format(self.title)


class ServicePoint(models.Model):
    title = models.CharField(max_length=100, default="")
    subnetwork = models.CharField(max_length=10, default="")

    def __str__(self):
        return "{}".format(self.title)

    def __unicode__(self):
        return "{}".format(self.title)


class Staff(models.Model):
    staff_category = models.ForeignKey(StaffCategory)
    available = models.BooleanField(default="False")
    super_guy = models.BooleanField(default="False")
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    service_point = models.ForeignKey(ServicePoint, default=None, null=True)

    def __str__(self):
        return "{} {} {}".format(self.staff_category, self.user.first_name, self.user.last_name)

    def __unicode__(self):
        return "{} {} {}".format(self.staff_category, self.user.first_name, self.user.last_name)


class Menu(models.Model):
    title = models.CharField(max_length=200)
    note = models.CharField(max_length=500, null=False)
    price = models.FloatField(default=0, validators=[MinValueValidator(0, "Price can't be negative!")])
    avg_preparation_time = models.DurationField(verbose_name="Average preparation time.")
    can_be_prepared_by = models.ForeignKey(StaffCategory)
    guid_1c = models.CharField(max_length=100, default="")
    category = models.ForeignKey(MenuCategory)

    def __str__(self):
        return "{}".format(self.title)

    def __unicode__(self):
        return "{}".format(self.title)


class Servery(models.Model):
    title = models.CharField(max_length=500, default="")
    ip_address = models.CharField(max_length=500, default="")
    guid_1c = models.CharField(max_length=100, default="")
    service_point = models.ForeignKey(ServicePoint, default=None, null=True)

    def __str__(self):
        return "{}".format(self.title)

    def __unicode__(self):
        return "{}".format(self.title)


class Order(models.Model):
    daily_number = models.IntegerField(verbose_name="Daily Number", unique_for_date=True)
    open_time = models.DateTimeField(verbose_name="Open Time")
    close_time = models.DateTimeField(verbose_name="Close Time", null=True)
    with_shawarma = models.BooleanField(verbose_name="With Shawarma", default=False)
    with_shashlyk = models.BooleanField(verbose_name="With Shashlyk", default=False)
    content_completed = models.BooleanField(verbose_name="Content Completed", default=False)
    shashlyk_completed = models.BooleanField(verbose_name="Shashlyk Completed", default=False)
    supplement_completed = models.BooleanField(verbose_name="Supplement Completed", default=False)
    total = models.FloatField(default=0, validators=[MinValueValidator(0, "Total can't be negative!")])
    is_canceled = models.BooleanField(verbose_name="Is canceled", default=False)
    closed_by = models.ForeignKey(Staff, related_name="closer", verbose_name="Closed By", null=True)
    canceled_by = models.ForeignKey(Staff, related_name="canceler", verbose_name="Canceled By", null=True)
    opened_by = models.ForeignKey(Staff, related_name="opener", verbose_name="Opened By", null=True)
    prepared_by = models.ForeignKey(Staff, related_name="maker", default=None, null=True)
    printed = models.BooleanField(default=False, verbose_name="Check Printed")
    is_paid = models.BooleanField(default=False, verbose_name="Is Paid")
    is_grilling = models.BooleanField(default=False, verbose_name="Is Grilling")
    is_grilling_shash = models.BooleanField(default=False, verbose_name="Shashlyk Is Grilling")
    is_ready = models.BooleanField(default=False, verbose_name="Is Ready")
    is_voiced = models.BooleanField(default=False, verbose_name="Is Voiced")
    # True - if paid with cash, False - if paid with card.
    paid_with_cash = models.BooleanField(default=True, verbose_name="Paid With Cash")
    servery = models.ForeignKey(Servery, verbose_name="Servery")
    guid_1c = models.CharField(max_length=100, default="")
    discount = models.FloatField(default=0, validators=[MinValueValidator(0, "Total can't be negative!")])
    sent_to_1c = models.BooleanField(verbose_name="Sent To 1C", default=False)
    paid_in_1c = models.BooleanField(verbose_name="Paid In 1C", default=False)

    def __str__(self):
        return "{} №{}".format(self.servery, self.daily_number)

    class Meta:
        permissions = (
            ('can_cancel', 'User can cancel order.'),
            ('can_close', 'User can close order.'),
        )


class OrderContent(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    menu_item = models.ForeignKey(Menu, on_delete=models.CASCADE, verbose_name="Menu Item")
    staff_maker = models.ForeignKey(Staff, on_delete=models.CASCADE, verbose_name="Staff Maker", null=True)
    start_timestamp = models.DateTimeField(verbose_name="Start Timestamp", null=True)
    grill_timestamp = models.DateTimeField(verbose_name="Grill Start Timestamp", null=True)
    finish_timestamp = models.DateTimeField(verbose_name="Finish Timestamp", null=True)
    is_in_grill = models.BooleanField(verbose_name="Is in grill", default=False)
    is_canceled = models.BooleanField(verbose_name="Is canceled", default=False)
    canceled_by = models.ForeignKey(Staff, related_name="content_canceler", verbose_name="Canceled By", null=True)
    note = models.CharField(max_length=500, default="")
    quantity = models.FloatField(verbose_name="Quantity", default=1.0, null=False)

    def __str__(self):
        return "№{} {}".format(self.order, self.menu_item)

    def __unicode__(self):
        return "№{} {}".format(self.order, self.menu_item)

    class Meta:
        permissions = (
            ('can_cancel', 'User can cancel order content.'),
            ('can_cook', 'User can cook order content'),
        )


class OrderOpinion(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, blank=True, null=True)
    mark = models.IntegerField(default=0)
    note = models.TextField(max_length=1000, blank=True, null=True)
    post_time = models.DateTimeField(verbose_name="Post Time", null=True)

    def __str__(self):
        return "№{} {}".format(self.order, self.mark)

    def __unicode__(self):
        return "№{} {}".format(self.order, self.mark)


class PauseTracker(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    start_timestamp = models.DateTimeField(verbose_name="Start Timestamp", null=True)
    end_timestamp = models.DateTimeField(verbose_name="End Timestamp", null=True)

