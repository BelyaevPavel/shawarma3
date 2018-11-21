# -*- coding: utf-8 -*-

from .models import Menu, Staff, Order, StaffCategory,\
    MenuCategory, Servery, ServicePoint, Printer, CallData, Customer, Delivery, DeliveryOrder
from django.contrib import admin

# Register your models here.
admin.site.register(Menu)
admin.site.register(Staff)
admin.site.register(Servery)
admin.site.register(Order)
admin.site.register(StaffCategory)
admin.site.register(MenuCategory)
admin.site.register(ServicePoint)
admin.site.register(Printer)
admin.site.register(CallData)
admin.site.register(Customer)
admin.site.register(Delivery)
admin.site.register(DeliveryOrder)
